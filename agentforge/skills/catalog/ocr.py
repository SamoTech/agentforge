"""Skill: ocr — extract text from images using OpenAI Vision or Tesseract."""
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class OCRSkill(BaseSkill):
    name = "ocr"
    description = "Extract text from an image file or URL using vision AI or Tesseract."
    category = "perception"
    tags = ["ocr", "vision", "image", "text-extraction", "tesseract"]
    level = "intermediate"
    requires_llm = True
    requires_network = True
    input_schema = {
        "image_url":  {"type": "string",  "required": False, "description": "Public image URL"},
        "image_b64":  {"type": "string",  "required": False, "description": "Base64-encoded image"},
        "engine":     {"type": "string",  "required": False, "description": "openai | tesseract (default: openai)"},
        "language":   {"type": "string",  "required": False, "description": "Tesseract language code (default: eng)"},
    }
    output_schema = {
        "text":       {"type": "string", "description": "Extracted text"},
        "confidence": {"type": "number", "description": "Confidence score 0-1 (Tesseract only)"},
    }

    async def execute(self, inp: SkillInput) -> SkillOutput:
        engine    = inp.data.get("engine", "openai")
        image_url = inp.data.get("image_url")
        image_b64 = inp.data.get("image_b64")
        if not image_url and not image_b64:
            return SkillOutput.fail("image_url or image_b64 required")

        if engine == "tesseract":
            return await self._tesseract(image_url, image_b64, inp.data.get("language", "eng"))
        return await self._openai_vision(image_url, image_b64)

    async def _openai_vision(self, image_url, image_b64) -> SkillOutput:
        try:
            from openai import AsyncOpenAI
            from agentforge.core.config import settings
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            content: list[dict] = [{"type": "text", "text": "Extract all text from this image verbatim."}]
            if image_url:
                content.append({"type": "image_url", "image_url": {"url": image_url}})
            elif image_b64:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}})
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": content}],
                max_tokens=2000,
            )
            text = response.choices[0].message.content or ""
            return SkillOutput(data={"text": text, "confidence": 1.0},
                               tokens_used=response.usage.total_tokens)
        except Exception as e:
            return SkillOutput.fail(str(e))

    async def _tesseract(self, image_url, image_b64, lang) -> SkillOutput:
        try:
            import pytesseract
            from PIL import Image
            import io
            import base64
            import httpx
            if image_url:
                async with httpx.AsyncClient(timeout=15) as c:
                    r = await c.get(image_url)
                img_bytes = r.content
            else:
                img_bytes = base64.b64decode(image_b64)
            img = Image.open(io.BytesIO(img_bytes))
            data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
            text = " ".join(w for w in data["text"] if w.strip())
            confs = [c for c in data["conf"] if c != -1]
            confidence = sum(confs) / len(confs) / 100 if confs else 0.0
            return SkillOutput(data={"text": text, "confidence": confidence})
        except Exception as e:
            return SkillOutput.fail(str(e))
