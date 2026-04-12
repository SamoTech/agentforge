"""Skill: data_analyzer — statistical analysis, visualization, and AI insights from tabular data."""
from __future__ import annotations
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class DataAnalyzerSkill(BaseSkill):
    name = "data_analyzer"
    description = (
        "Analyze CSV/JSON/Excel tabular data: descriptive stats, correlations, outlier detection, "
        "trend analysis, missing-value report, and LLM-generated natural language insights."
    )
    category = "data"
    tags = ["pandas", "csv", "statistics", "analysis", "data", "insights", "outliers", "excel"]
    level = "advanced"
    requires_llm = True
    input_schema = {
        "data":       {"type": "string",  "required": True,
                       "description": "CSV string, JSON array of objects, or base64-encoded Excel"},
        "format":     {"type": "string",  "default": "csv",
                       "description": "csv | json | excel"},
        "question":   {"type": "string",  "default": "",
                       "description": "Natural language question about the data"},
        "operations": {"type": "array",   "default": ["describe"],
                       "description": "describe | correlate | top_n | trend | outliers | missing | dtypes"},
        "model":      {"type": "string",  "default": "gpt-4o-mini"},
        "max_rows_preview": {"type": "integer", "default": 5,
                             "description": "Rows of data sample to include in LLM context"},
    }
    output_schema = {
        "summary":      {"type": "string"},
        "stats":        {"type": "object"},
        "insight":      {"type": "string"},
        "row_count":    {"type": "integer"},
        "column_count": {"type": "integer"},
        "warnings":     {"type": "array",  "description": "Data quality warnings"},
    }

    async def execute(self, inp: SkillInput) -> SkillOutput:
        raw      = inp.data.get("data", "")
        fmt      = inp.data.get("format", "csv")
        question = inp.data.get("question", "")
        ops      = inp.data.get("operations", ["describe"]) or ["describe"]
        model    = inp.data.get("model", "gpt-4o-mini")
        preview_rows = int(inp.data.get("max_rows_preview", 5))

        if not raw:
            return SkillOutput.fail("data is required")

        try:
            import pandas as pd
            import io
            import json

            # ── Load ──────────────────────────────────────────────────────
            if fmt == "json":
                df = pd.read_json(io.StringIO(raw))
            elif fmt == "excel":
                import base64
                df = pd.read_excel(io.BytesIO(base64.b64decode(raw)))
            else:
                df = pd.read_csv(io.StringIO(raw))

            warnings: list[str] = []

            # ── Operations ───────────────────────────────────────────────
            stats: dict = {}

            if "describe" in ops:
                desc = df.describe(include="all")
                # Round floats to avoid sending hundreds of decimal places to LLM
                stats["describe"] = json.loads(desc.round(4).to_json())

            if "dtypes" in ops:
                stats["dtypes"] = df.dtypes.astype(str).to_dict()

            if "missing" in ops:
                missing = df.isnull().sum()
                missing_pct = (missing / len(df) * 100).round(2)
                stats["missing"] = missing_pct[missing_pct > 0].to_dict()
                if stats["missing"]:
                    warnings.append(
                        f"Columns with missing values: {', '.join(stats['missing'].keys())}"
                    )

            if "correlate" in ops:
                numeric = df.select_dtypes(include="number")
                if not numeric.empty:
                    stats["correlation"] = json.loads(numeric.corr().round(4).to_json())

            if "top_n" in ops:
                for col in df.select_dtypes(include="number").columns[:5]:
                    stats[f"top_5_{col}"] = df.nlargest(5, col)[[col]].round(4).to_dict("records")

            if "trend" in ops:
                # Detect monotonic trends in numeric columns
                for col in df.select_dtypes(include="number").columns[:5]:
                    series = df[col].dropna()
                    if len(series) >= 3:
                        delta = series.iloc[-1] - series.iloc[0]
                        direction = "increasing" if delta > 0 else ("decreasing" if delta < 0 else "flat")
                        stats.setdefault("trends", {})[col] = {
                            "direction": direction,
                            "change": round(float(delta), 4),
                            "change_pct": round(float(delta / series.iloc[0] * 100), 2) if series.iloc[0] != 0 else None,
                        }

            if "outliers" in ops:
                from scipy import stats as sp_stats
                for col in df.select_dtypes(include="number").columns[:5]:
                    series = df[col].dropna()
                    if len(series) >= 10:
                        z_scores = sp_stats.zscore(series)
                        outlier_count = int((abs(z_scores) > 3).sum())
                        if outlier_count:
                            stats.setdefault("outliers", {})[col] = outlier_count
                            warnings.append(f"Column '{col}' has {outlier_count} outliers (|z|>3)")

            summary = (
                f"{df.shape[0]:,} rows × {df.shape[1]} columns. "
                f"Columns: {', '.join(df.columns.tolist()[:12])}"
                + (f" (+{df.shape[1]-12} more)" if df.shape[1] > 12 else "")
            )

            insight = ""
            if question:
                from openai import AsyncOpenAI
                from agentforge.core.config import settings
                client = AsyncOpenAI(api_key=settings.openai_api_key)

                # Send a compact context — sample rows + truncated stats
                sample_csv  = df.head(preview_rows).to_csv(index=False)
                stats_brief = json.dumps(
                    {k: v for k, v in stats.items() if k in ("describe", "missing", "trends", "outliers")},
                    default=str
                )[:3000]   # ← hard cap to prevent bloating the LLM context

                prompt = (
                    f"Dataset: {summary}\n"
                    f"Sample ({preview_rows} rows):\n{sample_csv}\n"
                    f"Stats summary:\n{stats_brief}\n"
                    f"Question: {question}"
                )
                resp = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a data analyst. Answer the question based on the dataset."},
                        {"role": "user",   "content": prompt},
                    ],
                    max_tokens=600,
                    temperature=0.2,
                )
                insight = resp.choices[0].message.content or ""

            return SkillOutput(data={
                "summary":      summary,
                "stats":        stats,
                "insight":      insight,
                "row_count":    df.shape[0],
                "column_count": df.shape[1],
                "warnings":     warnings,
            })
        except Exception as e:
            return SkillOutput.fail(str(e))
