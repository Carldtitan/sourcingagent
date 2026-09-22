"""Real email. Sending over Gmail SMTP, receiving over Gmail IMAP.

Every message in this system is a genuine email with real headers and a real
message id. The counterparties are simulated and all twelve of them live on
plus addresses of one free Gmail account, so nothing ever leaves the mailbox
the person running this owns.
"""

from __future__ import annotations

import email
import email.message
import email.utils
import imaplib
import random
import re
import smtplib
import ssl
import string
from dataclasses import dataclass, field

from . import config


REFERENCE_PATTERN = re.compile(r"\[(AON-[A-Z0-9]{6}-[A-Z0-9]{4})\]")


def new_reference() -> str:
    """The code that carries a negotiation through a mail thread."""
    body = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    tail = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"AON-{body}-{tail}"


def find_reference(text: str) -> str | None:
    match = REFERENCE_PATTERN.search(text or "")
    return match.group(1) if match else None


@dataclass
class Inbound:
    uid: bytes
    message_id: str
    from_addr: str
    to_addr: str
    subject: str
    body: str
    reference: str | None
    headers: dict = field(default_factory=dict)
    attachments: list[tuple[str, bytes]] = field(default_factory=list)


def send(
    *,
    sender: str,
    to: str,
    subject: str,
    body: str,
    reply_to_message_id: str | None = None,
    attachment: tuple[str, bytes] | None = None,
    display_name: str | None = None,
) -> str:
    """Send one message and return its Message-ID."""
    msg = email.message.EmailMessage()
    msg["From"] = email.utils.formataddr((display_name or "", sender))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    message_id = email.utils.make_msgid(domain="aonic-sourcing.local")
    msg["Message-ID"] = message_id
    if reply_to_message_id:
        msg["In-Reply-To"] = reply_to_message_id
        msg["References"] = reply_to_message_id
    msg.set_content(body)

    if attachment:
        name, data = attachment
        msg.add_attachment(data, maintype="application", subtype="pdf", filename=name)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, context=context, timeout=30) as server:
        server.login(config.need("GMAIL_ADDRESS"), config.need("GMAIL_APP_PASSWORD"))
        # The envelope sender must be the account itself. The From header
        # carries the plus address, which is what a reader and our own parser
        # both see.
        server.send_message(msg, from_addr=config.GMAIL_ADDRESS, to_addrs=[to])

    return message_id


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = email.header.decode_header(value)
    out = []
    for text, charset in parts:
        if isinstance(text, bytes):
            out.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _plain_text(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                payload = part.get_payload(decode=True) or b""
                return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True) or b""
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")


def _attachments(msg: email.message.Message) -> list[tuple[str, bytes]]:
    out = []
    if not msg.is_multipart():
        return out
    for part in msg.walk():
        name = part.get_filename()
        if name:
            out.append((_decode(name), part.get_payload(decode=True) or b""))
    return out


def fetch_unread(limit: int = 30, mark_seen: bool = False) -> list[Inbound]:
    """Pull unseen messages out of the mailbox.

    Gmail delivers both sides of every conversation to the same account, so
    this returns messages written by our agents and by the simulated
    suppliers alike. The caller decides which is which from the To address.
    """
    box = imaplib.IMAP4_SSL(config.IMAP_HOST, config.IMAP_PORT)
    try:
        box.login(config.need("GMAIL_ADDRESS"), config.need("GMAIL_APP_PASSWORD"))
        box.select("INBOX")
        status, data = box.search(None, "UNSEEN")
        if status != "OK":
            return []
        ids = data[0].split()[-limit:]

        out: list[Inbound] = []
        for uid in ids:
            fetch_flag = "(RFC822)" if mark_seen else "(BODY.PEEK[])"
            status, payload = box.fetch(uid, fetch_flag)
            if status != "OK" or not payload or not isinstance(payload[0], tuple):
                continue
            msg = email.message_from_bytes(payload[0][1])

            subject = _decode(msg.get("Subject"))
            body = _plain_text(msg)
            to_addr = email.utils.parseaddr(msg.get("To", ""))[1]
            from_addr = email.utils.parseaddr(msg.get("From", ""))[1]

            out.append(
                Inbound(
                    uid=uid,
                    message_id=msg.get("Message-ID", "").strip(),
                    from_addr=from_addr,
                    to_addr=to_addr,
                    subject=subject,
                    body=body,
                    reference=find_reference(subject) or find_reference(body),
                    headers={
                        "date": msg.get("Date", ""),
                        "in_reply_to": msg.get("In-Reply-To", ""),
                        "delivered_to": msg.get("Delivered-To", ""),
                        "return_path": msg.get("Return-Path", ""),
                    },
                    attachments=_attachments(msg),
                )
            )
        return out
    finally:
        try:
            box.logout()
        except Exception:
            pass


def mark_seen(uids: list[bytes]) -> None:
    """Flag messages as handled, so the next tick does not read them again.

    A message is only marked once the engine has finished with it. Anything a
    tick ran out of time for stays unread and is picked up by the next one.
    """
    if not uids:
        return
    box = imaplib.IMAP4_SSL(config.IMAP_HOST, config.IMAP_PORT)
    try:
        box.login(config.need("GMAIL_ADDRESS"), config.need("GMAIL_APP_PASSWORD"))
        box.select("INBOX")
        box.store(b",".join(uids), "+FLAGS", r"\Seen")
    finally:
        try:
            box.logout()
        except Exception:
            pass
