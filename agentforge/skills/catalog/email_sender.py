"""Skill: email_sender — send emails via SMTP or SendGrid."""
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class EmailSenderSkill(BaseSkill):
    name = "email_sender"
    description = "Send an email via SMTP or SendGrid API."
    category = "communication"
    tags = ["email", "smtp", "sendgrid", "notify", "send"]
    level = "basic"
    requires_network = True
    input_schema = {
        "to":       {"type": "string",  "required": True},
        "subject":  {"type": "string",  "required": True},
        "body":     {"type": "string",  "required": True},
        "html":     {"type": "boolean", "required": False, "description": "Send as HTML (default false)"},
        "provider": {"type": "string",  "required": False, "description": "smtp | sendgrid (default smtp)"},
        "from_addr":{"type": "string",  "required": False},
    }
    output_schema = {"sent": {"type": "boolean"}, "message_id": {"type": "string"}}

    async def execute(self, inp: SkillInput) -> SkillOutput:
        provider = inp.data.get("provider", "smtp")
        to       = inp.data.get("to")
        subject  = inp.data.get("subject")
        body     = inp.data.get("body")
        is_html  = inp.data.get("html", False)
        if not all([to, subject, body]):
            return SkillOutput.fail("to, subject, and body are required")
        if provider == "sendgrid":
            return await self._sendgrid(to, subject, body, is_html, inp.data.get("from_addr"))
        return await self._smtp(to, subject, body, is_html, inp.data.get("from_addr"))

    async def _smtp(self, to, subject, body, is_html, from_addr) -> SkillOutput:
        try:
            import smtplib, os
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            mime_type = "html" if is_html else "plain"
            msg = MIMEMultipart()
            msg["From"]    = from_addr or os.getenv("SMTP_FROM", "noreply@agentforge.ai")
            msg["To"]      = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, mime_type))
            host = os.getenv("SMTP_HOST", "localhost")
            port = int(os.getenv("SMTP_PORT", "587"))
            user = os.getenv("SMTP_USER", "")
            pwd  = os.getenv("SMTP_PASS", "")
            with smtplib.SMTP(host, port) as s:
                s.starttls()
                if user:
                    s.login(user, pwd)
                s.send_message(msg)
            return SkillOutput(data={"sent": True, "message_id": msg["Message-ID"] or ""})
        except Exception as e:
            return SkillOutput.fail(str(e))

    async def _sendgrid(self, to, subject, body, is_html, from_addr) -> SkillOutput:
        try:
            import os, httpx
            api_key = os.getenv("SENDGRID_API_KEY", "")
            payload = {
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": from_addr or "noreply@agentforge.ai"},
                "subject": subject,
                "content": [{"type": "text/html" if is_html else "text/plain", "value": body}],
            }
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=15,
                )
            return SkillOutput(data={"sent": r.status_code == 202, "message_id": r.headers.get("X-Message-Id", "")})
        except Exception as e:
            return SkillOutput.fail(str(e))
