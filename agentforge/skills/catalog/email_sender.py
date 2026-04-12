"""Skill: email_sender — send emails via SMTP with async I/O, attachments, and CC/BCC."""
from __future__ import annotations
import asyncio
import os
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class EmailSenderSkill(BaseSkill):
    name = "email_sender"
    description = (
        "Send emails via SMTP. Supports plain text and HTML bodies, "
        "attachments (base64), CC/BCC, reply-to, and custom headers. "
        "Runs SMTP in a thread so it never blocks the async event loop."
    )
    category = "communication"
    tags = ["email", "smtp", "notification", "outreach", "html", "attachment"]
    level = "advanced"
    input_schema = {
        "to":          {"type": "string",  "required": True,  "description": "Recipient email or comma-separated list"},
        "subject":     {"type": "string",  "required": True},
        "body":        {"type": "string",  "required": True,  "description": "Email body (plain text or HTML)"},
        "html":        {"type": "boolean", "default": False,  "description": "Treat body as HTML"},
        "from":        {"type": "string",  "default": "",     "description": "Sender address (falls back to SMTP_FROM env)"},
        "cc":          {"type": "string",  "default": "",     "description": "CC addresses (comma-separated)"},
        "bcc":         {"type": "string",  "default": "",     "description": "BCC addresses (comma-separated)"},
        "reply_to":    {"type": "string",  "default": ""},
        "attachments": {"type": "array",   "default": [],
                        "description": "[{filename: str, content_b64: str, mime_type: str}]"},
        "plain_fallback": {"type": "string", "default": "",
                           "description": "Plain-text fallback for HTML emails"},
    }
    output_schema = {
        "sent":       {"type": "boolean"},
        "message_id": {"type": "string"},
        "recipients": {"type": "integer"},
    }

    async def execute(self, inp: SkillInput) -> SkillOutput:
        to         = inp.data.get("to", "")
        subject    = inp.data.get("subject", "")
        body       = inp.data.get("body", "")
        is_html    = inp.data.get("html", False)
        from_addr  = inp.data.get("from") or os.getenv("SMTP_FROM", "noreply@agentforge.ai")
        cc         = inp.data.get("cc", "")
        bcc        = inp.data.get("bcc", "")
        reply_to   = inp.data.get("reply_to", "")
        attachments = inp.data.get("attachments", [])
        plain_fallback = inp.data.get("plain_fallback", "")

        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")

        if not all([to, subject, body]):
            return SkillOutput.fail("to, subject, and body are required")

        def _build_and_send() -> str:
            """Runs in a thread — SMTP is synchronous."""
            import smtplib
            import base64
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.base import MIMEBase
            from email import encoders
            from email.utils import formatdate, make_msgid

            msg = MIMEMultipart("mixed")
            msg["Subject"]  = subject
            msg["From"]     = from_addr
            msg["To"]       = to
            msg["Date"]     = formatdate(localtime=True)
            msg["Message-ID"] = make_msgid(domain=from_addr.split("@")[-1])
            if cc:
                msg["Cc"] = cc
            if reply_to:
                msg["Reply-To"] = reply_to

            # Body part
            alt = MIMEMultipart("alternative")
            if is_html:
                if plain_fallback:
                    alt.attach(MIMEText(plain_fallback, "plain", "utf-8"))
                alt.attach(MIMEText(body, "html", "utf-8"))
            else:
                alt.attach(MIMEText(body, "plain", "utf-8"))
            msg.attach(alt)

            # Attachments
            for att in attachments:
                part = MIMEBase(*att.get("mime_type", "application/octet-stream").split("/", 1))
                part.set_payload(base64.b64decode(att["content_b64"]))
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=att["filename"])
                msg.attach(part)

            # Build recipient list including BCC
            all_rcpt = [r.strip() for r in to.split(",")]
            if cc:
                all_rcpt += [r.strip() for r in cc.split(",")]
            if bcc:
                all_rcpt += [r.strip() for r in bcc.split(",")]

            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as srv:
                srv.ehlo()
                srv.starttls()
                srv.ehlo()
                if smtp_user and smtp_pass:
                    srv.login(smtp_user, smtp_pass)
                srv.sendmail(from_addr, all_rcpt, msg.as_string())

            return msg["Message-ID"]

        try:
            msg_id = await asyncio.get_event_loop().run_in_executor(None, _build_and_send)
            recipients = len([r.strip() for r in to.split(",")])
            return SkillOutput(data={"sent": True, "message_id": msg_id, "recipients": recipients})
        except Exception as e:
            return SkillOutput.fail(str(e))
