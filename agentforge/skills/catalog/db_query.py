"""Skill: db_query — safe, read-only SQL queries with parameterisation and schema introspection."""
from __future__ import annotations
import re
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput

# Patterns that must never appear in an allowed query
_WRITE_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|REPLACE|MERGE|EXEC|EXECUTE|CALL|GRANT|REVOKE)\b",
    re.IGNORECASE,
)
# Block stacked queries (SQL injection via semicolons)
_MULTI_STMT = re.compile(r";\s*\w")


class DbQuerySkill(BaseSkill):
    name = "db_query"
    description = (
        "Execute safe, read-only SQL queries against PostgreSQL. "
        "Blocks all write operations (INSERT/UPDATE/DELETE/DROP/etc.) and multi-statement injection. "
        "Supports parameterised queries, schema inspection, and query explain plans."
    )
    category = "data"
    tags = ["sql", "database", "postgres", "query", "analytics", "read-only"]
    level = "advanced"
    input_schema = {
        "query":      {"type": "string",  "required": True,
                       "description": "SQL SELECT query (no INSERT/UPDATE/DELETE)"},
        "params":     {"type": "array",   "default": [],
                       "description": "Positional parameters for $1, $2 placeholders (prevents SQL injection)"},
        "dsn":        {"type": "string",  "default": "",
                       "description": "PostgreSQL DSN (overrides env DATABASE_URL)"},
        "limit":      {"type": "integer", "default": 100,
                       "description": "Auto-appended LIMIT if not already present"},
        "explain":    {"type": "boolean", "default": False,
                       "description": "Return EXPLAIN ANALYZE output instead of rows"},
        "schema":     {"type": "boolean", "default": False,
                       "description": "Return table/column schema for given table name (query = table name)"},
    }
    output_schema = {
        "rows":      {"type": "array"},
        "row_count": {"type": "integer"},
        "columns":   {"type": "array"},
        "explain":   {"type": "string"},
    }

    async def execute(self, inp: SkillInput) -> SkillOutput:
        query   = inp.data.get("query", "").strip()
        params  = inp.data.get("params", []) or []
        limit   = int(inp.data.get("limit", 100))
        explain = bool(inp.data.get("explain", False))
        do_schema = bool(inp.data.get("schema", False))

        if not query:
            return SkillOutput.fail("query is required")

        # Schema introspection mode
        if do_schema:
            query = (
                "SELECT column_name, data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = $1 ORDER BY ordinal_position"
            )
            params = [inp.data.get("query", "")]

        # Security checks
        if _WRITE_PATTERN.search(query):
            return SkillOutput.fail(
                "Query contains a disallowed statement (INSERT/UPDATE/DELETE/DROP/etc.). "
                "Only SELECT queries are permitted."
            )
        if _MULTI_STMT.search(query):
            return SkillOutput.fail(
                "Multi-statement queries (semicolon-separated) are not permitted."
            )

        # Auto-add LIMIT if SELECT and no LIMIT present
        if re.search(r"\bSELECT\b", query, re.IGNORECASE) and not re.search(r"\bLIMIT\b", query, re.IGNORECASE):
            query = f"{query} LIMIT {limit}"

        try:
            import asyncpg
            from agentforge.core.config import settings
            dsn = inp.data.get("dsn") or settings.database_url.replace("+asyncpg", "")
            conn = await asyncpg.connect(dsn)
            try:
                if explain:
                    explain_rows = await conn.fetch(f"EXPLAIN ANALYZE {query}", *params)
                    plan = "\n".join(r[0] for r in explain_rows)
                    return SkillOutput(data={
                        "rows": [], "row_count": 0, "columns": [], "explain": plan
                    })
                records = await conn.fetch(query, *params)
                rows    = [dict(r) for r in records]
                columns = list(rows[0].keys()) if rows else []
            finally:
                await conn.close()

            return SkillOutput(data={
                "rows":      rows,
                "row_count": len(rows),
                "columns":   columns,
                "explain":   "",
            })
        except Exception as e:
            return SkillOutput.fail(str(e))
