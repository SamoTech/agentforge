"""Skill: data_analyzer — statistical analysis and insights from tabular data."""
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class DataAnalyzerSkill(BaseSkill):
    name = "data_analyzer"
    description = "Analyze CSV/JSON tabular data: stats, correlations, trends, and LLM-generated insights."
    category = "data"
    tags = ["pandas", "csv", "statistics", "analysis", "data", "insights"]
    level = "intermediate"
    requires_llm = True
    input_schema = {
        "data":       {"type": "string",  "required": True,  "description": "CSV string or JSON array of objects"},
        "format":     {"type": "string",  "required": False, "description": "csv | json (default: csv)"},
        "question":   {"type": "string",  "required": False, "description": "Natural language question about the data"},
        "operations": {"type": "array",   "required": False, "description": "describe | correlate | top_n | trend"},
    }
    output_schema = {
        "summary":      {"type": "string"},
        "stats":        {"type": "object"},
        "insight":      {"type": "string"},
        "row_count":    {"type": "integer"},
        "column_count": {"type": "integer"},
    }

    async def execute(self, inp: SkillInput) -> SkillOutput:
        raw       = inp.data.get("data", "")
        fmt       = inp.data.get("format", "csv")
        question  = inp.data.get("question", "")
        ops       = inp.data.get("operations", ["describe"])
        if not raw:
            return SkillOutput.fail("data is required")
        try:
            import pandas as pd, io, json
            if fmt == "json":
                df = pd.read_json(io.StringIO(raw))
            else:
                df = pd.read_csv(io.StringIO(raw))

            stats: dict = {}
            if "describe" in ops:
                stats["describe"] = json.loads(df.describe(include="all").to_json())
            if "correlate" in ops:
                numeric = df.select_dtypes(include="number")
                if not numeric.empty:
                    stats["correlation"] = json.loads(numeric.corr().to_json())
            if "top_n" in ops:
                for col in df.select_dtypes(include="number").columns[:3]:
                    stats[f"top_5_{col}"] = df.nlargest(5, col)[[col]].to_dict("records")

            summary = f"{df.shape[0]} rows × {df.shape[1]} columns. Columns: {', '.join(df.columns[:10])}"

            insight = ""
            if question:
                from openai import AsyncOpenAI
                from agentforge.core.config import settings
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                prompt = (
                    f"Dataset summary: {summary}\n"
                    f"Stats: {json.dumps(stats, default=str)[:3000]}\n"
                    f"Question: {question}"
                )
                resp = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                )
                insight = resp.choices[0].message.content or ""

            return SkillOutput(data={
                "summary":      summary,
                "stats":        stats,
                "insight":      insight,
                "row_count":    df.shape[0],
                "column_count": df.shape[1],
            })
        except Exception as e:
            return SkillOutput.fail(str(e))
