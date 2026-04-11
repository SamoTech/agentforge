"""Data analysis skill — analyze DataFrames and JSON data."""
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput
from agentforge.skills.registry import register

@register
class DataAnalyzerSkill(BaseSkill):
    name = 'data_analyzer'
    description = 'Analyze structured data (CSV, JSON) and return statistics, insights'
    category = 'data'

    async def execute(self, input: SkillInput) -> SkillOutput:
        data = input.data.get('data')  # list of dicts or CSV string
        analysis_type = input.data.get('type', 'describe')  # describe | correlate | trend
        try:
            import pandas as pd
            if isinstance(data, str):
                import io
                df = pd.read_csv(io.StringIO(data))
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                return SkillOutput.fail('data must be a CSV string or list of dicts')

            if analysis_type == 'describe':
                desc = df.describe(include='all').to_dict()
                return SkillOutput.ok({'shape': df.shape, 'columns': list(df.columns),
                                        'dtypes': df.dtypes.astype(str).to_dict(), 'describe': desc})
            elif analysis_type == 'correlate':
                corr = df.select_dtypes(include='number').corr().to_dict()
                return SkillOutput.ok({'correlation': corr})
            elif analysis_type == 'trend':
                date_col = input.data.get('date_column', df.columns[0])
                value_col = input.data.get('value_column', df.columns[1] if len(df.columns) > 1 else df.columns[0])
                trend = df[[date_col, value_col]].to_dict('records')
                return SkillOutput.ok({'trend': trend, 'total': df[value_col].sum() if pd.api.types.is_numeric_dtype(df[value_col]) else None})
        except ImportError:
            return SkillOutput.fail('pandas not installed. Run: pip install pandas')
        except Exception as e:
            return SkillOutput.fail(str(e))
