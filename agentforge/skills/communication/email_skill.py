"""Email skill — send emails via SMTP."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput
from agentforge.skills.registry import register
from agentforge.core.config import settings

@register
class EmailSkill(BaseSkill):
    name = 'send_email'
    description = 'Send an email via SMTP'
    category = 'communication'

    async def execute(self, input: SkillInput) -> SkillOutput:
        to = input.data.get('to', '')
        subject = input.data.get('subject', '')
        body = input.data.get('body', '')
        html = input.data.get('html', False)
        if not all([to, subject, body]):
            return SkillOutput.fail('to, subject, and body are required')
        smtp_host = getattr(settings, 'smtp_host', 'smtp.gmail.com')
        smtp_port = getattr(settings, 'smtp_port', 587)
        smtp_user = getattr(settings, 'smtp_user', '')
        smtp_pass = getattr(settings, 'smtp_password', '')
        if not smtp_user:
            return SkillOutput.fail('SMTP credentials not configured')
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = to
        msg.attach(MIMEText(body, 'html' if html else 'plain'))
        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, to, msg.as_string())
            return SkillOutput.ok({'status': 'sent', 'to': to, 'subject': subject})
        except Exception as e:
            return SkillOutput.fail(f'Email send failed: {e}')
