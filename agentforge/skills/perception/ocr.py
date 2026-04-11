"""OCR skill — extract text from images using Tesseract or OpenAI Vision."""
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput
from agentforge.skills.registry import register

@register
class OCRSkill(BaseSkill):
    name = 'ocr'
    description = 'Extract text from images using OCR (Tesseract) or GPT-4 Vision'
    category = 'perception'

    async def execute(self, input: SkillInput) -> SkillOutput:
        image_path = input.data.get('image_path')
        image_url = input.data.get('image_url')
        mode = input.data.get('mode', 'vision')  # 'tesseract' | 'vision'

        if mode == 'tesseract':
            try:
                import pytesseract
                from PIL import Image
                img = Image.open(image_path)
                text = pytesseract.image_to_string(img)
                return SkillOutput.ok(text.strip())
            except ImportError:
                return SkillOutput.fail('pytesseract not installed. Run: pip install pytesseract Pillow')
            except Exception as e:
                return SkillOutput.fail(str(e))
        else:
            from openai import AsyncOpenAI
            from agentforge.core.config import settings
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            content = [{'type': 'text', 'text': 'Extract all text from this image. Return only the text content.'}]
            if image_url:
                content.append({'type': 'image_url', 'image_url': {'url': image_url}})
            elif image_path:
                import base64
                with open(image_path, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode()
                ext = image_path.rsplit('.', 1)[-1].lower()
                content.append({'type': 'image_url', 'image_url': {'url': f'data:image/{ext};base64,{b64}'}})
            else:
                return SkillOutput.fail('Provide image_path or image_url')
            response = await client.chat.completions.create(
                model='gpt-4o',
                messages=[{'role': 'user', 'content': content}],
            )
            return SkillOutput.ok(response.choices[0].message.content)
