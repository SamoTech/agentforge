"""Skill: summarizer — summarize text of any length with automatic chunking."""
from __future__ import annotations
import asyncio
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput

# ≈ 3000 words per chunk (safe for gpt-4o-mini context)
_CHUNK_CHARS = 12_000


class SummarizerSkill(BaseSkill):
    name = "summarizer"
    description = (
        "Summarize text of any length into a paragraph, bullet list, or one-liner. "
        "Automatically chunks very long documents and produces a hierarchical summary. "
        "Supports extractive key sentences, keyword extraction, and multi-language output."
    )
    category = "communication"
    tags = ["summarize", "nlp", "text", "condense", "tldr", "keywords", "chunking"]
    level = "advanced"
    requires_llm = True
    input_schema = {
        "text":      {"type": "string",  "required": True},
        "style":     {"type": "string",  "default": "paragraph",
                      "description": "paragraph | bullets | one_line | detailed | keywords"},
        "max_words": {"type": "integer", "default": 200},
        "language":  {"type": "string",  "default": "english",
                      "description": "Output language (e.g. english, arabic, french)"},
        "model":     {"type": "string",  "default": "gpt-4o-mini"},
        "focus":     {"type": "string",  "default": "",
                      "description": "Optional focus instruction, e.g. 'focus on security findings'"},
    }
    output_schema = {
        "summary":   {"type": "string"},
        "word_count":{"type": "integer"},
        "chunks":    {"type": "integer", "description": "Number of chunks processed"},
        "tokens_used":{"type": "integer"},
    }

    _STYLE_INSTRUCTIONS: dict[str, str] = {
        "paragraph": "Write a clear, concise paragraph summary capturing the main points.",
        "bullets":   "Write a bullet-point summary with at most 8 key points. Each bullet on its own line starting with •",
        "one_line":  "Write a single sentence summary (max 30 words).",
        "detailed":  "Write a detailed multi-paragraph summary covering all important topics.",
        "keywords":  "Extract the 10 most important keywords/phrases as a comma-separated list.",
    }

    async def execute(self, inp: SkillInput) -> SkillOutput:
        text      = inp.data.get("text", "")
        style     = inp.data.get("style", "paragraph")
        max_words = int(inp.data.get("max_words", 200))
        language  = inp.data.get("language", "english")
        model     = inp.data.get("model", "gpt-4o-mini")
        focus     = inp.data.get("focus", "")

        if not text.strip():
            return SkillOutput.fail("text is required")
        if style not in self._STYLE_INSTRUCTIONS:
            return SkillOutput.fail(f"style must be one of: {list(self._STYLE_INSTRUCTIONS)}")

        try:
            from openai import AsyncOpenAI
            from agentforge.core.config import settings
            client = AsyncOpenAI(api_key=settings.openai_api_key)

            style_instr = self._STYLE_INSTRUCTIONS[style]
            if style == "paragraph":
                style_instr += f" Limit to {max_words} words."
            if focus:
                style_instr += f" {focus}."
            lang_instr = f" Respond in {language}." if language.lower() != "english" else ""

            system = (
                f"You are an expert summarizer. {style_instr}{lang_instr} "
                "Be factual, clear, and preserve the most important information."
            )

            # ── Chunking for long documents ───────────────────────────────
            chunks     = [text[i:i + _CHUNK_CHARS] for i in range(0, len(text), _CHUNK_CHARS)]
            total_tokens = 0

            if len(chunks) == 1:
                # Short enough — single call
                resp = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": text},
                    ],
                    temperature=0.3,
                    max_tokens=800,
                )
                summary = resp.choices[0].message.content.strip()
                total_tokens = resp.usage.total_tokens
            else:
                # Map step: summarise each chunk
                map_system = (
                    f"You are a summarizer. Summarise the following excerpt concisely in 3-5 sentences. "
                    f"{lang_instr}"
                )

                async def _map(chunk: str) -> tuple[str, int]:
                    r = await client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": map_system},
                            {"role": "user",   "content": chunk},
                        ],
                        temperature=0.3,
                        max_tokens=300,
                    )
                    return r.choices[0].message.content.strip(), r.usage.total_tokens

                # Parallel map — all chunks at once (rate-limited by semaphore)
                sem = asyncio.Semaphore(5)

                async def _map_limited(c: str) -> tuple[str, int]:
                    async with sem:
                        return await _map(c)

                mapped = await asyncio.gather(*[_map_limited(c) for c in chunks])
                partial_summaries = "\n\n".join(s for s, _ in mapped)
                total_tokens += sum(t for _, t in mapped)

                # Reduce step: combine partial summaries
                resp = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": partial_summaries},
                    ],
                    temperature=0.3,
                    max_tokens=800,
                )
                summary = resp.choices[0].message.content.strip()
                total_tokens += resp.usage.total_tokens

            return SkillOutput(
                data={
                    "summary":    summary,
                    "word_count": len(summary.split()),
                    "chunks":     len(chunks),
                    "tokens_used": total_tokens,
                },
                tokens_used=total_tokens,
            )
        except Exception as e:
            return SkillOutput.fail(str(e))
