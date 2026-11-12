"""Decodificación MIME de Gmail, sin descargar adjuntos ni interpretar HTML activo."""
from __future__ import annotations

import base64
import binascii
import re
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from typing import Any


class PlainHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"br", "p", "div", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _decode(data: str, charset: str = "utf-8") -> str:
    try:
        raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
        return raw.decode(charset, errors="replace")
    except (ValueError, binascii.Error, LookupError):
        return ""


def gmail_content(message: dict[str, Any]) -> dict[str, Any]:
    """Añadir un campo _content legible sin alterar campos nativos del proveedor."""
    content: dict[str, Any] = {"subject": "", "from": "", "to": "", "date": "", "text": "", "attachments": []}
    root = message.get("payload")
    plain: list[str] = []
    html: list[str] = []
    if isinstance(root, dict):
        headers = {h.get("name", "").lower(): h.get("value", "") for h in root.get("headers", [])}
        for field in ["subject", "from", "to", "date"]:
            content[field] = headers.get(field, "")
        stack = [root]
        while stack:
            part = stack.pop()
            body = part.get("body", {})
            if part.get("filename") or body.get("attachmentId"):
                content["attachments"].append({"filename": part.get("filename", ""), "attachment_id": body.get("attachmentId"), "mime_type": part.get("mimeType"), "size": body.get("size")})
                continue
            part_headers = {h.get("name", "").lower(): h.get("value", "") for h in part.get("headers", [])}
            match = re.search(r'charset=["\']?([^;"\'\s]+)', part_headers.get("content-type", ""), re.I)
            charset = match.group(1) if match else "utf-8"
            if part.get("mimeType") == "text/plain":
                plain.append(_decode(body.get("data", ""), charset))
            elif part.get("mimeType") == "text/html":
                html.append(_decode(body.get("data", ""), charset))
            stack.extend(reversed(part.get("parts", [])))
    elif isinstance(message.get("raw"), str):
        try:
            raw = message["raw"]
            parsed = BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
            for field in ["subject", "from", "to", "date"]:
                content[field] = str(parsed.get(field, ""))
            for part in parsed.walk():
                if part.is_multipart():
                    continue
                if part.get_filename():
                    content["attachments"].append({"filename": part.get_filename(), "mime_type": part.get_content_type()})
                elif part.get_content_type() == "text/plain":
                    plain.append(str(part.get_content()))
                elif part.get_content_type() == "text/html":
                    html.append(str(part.get_content()))
        except (ValueError, binascii.Error, LookupError):
            content["decode_warning"] = "INVALID_RAW_MIME"
    if plain:
        text = "\n".join(plain)
    else:
        parser = PlainHTML()
        parser.feed("\n".join(html))
        text = "".join(parser.parts)
    content["text"] = text[:100000]
    content["truncated"] = len(text) > 100000
    content["body_available"] = bool(plain or html)
    return {**message, "_content": content}


def normalize_gmail(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    if "payload" in payload or "raw" in payload:
        return gmail_content(payload)
    if isinstance(payload.get("messages"), list):
        return {**payload, "messages": [normalize_gmail(m) for m in payload["messages"]]}
    return payload


def evidence_for_ai(value: Any) -> Any:
    """No duplicar cuerpos codificados; no convertir IDs de listados en textos ficticios."""
    if isinstance(value, dict):
        if "_content" in value:
            return {k: value[k] for k in ["id", "threadId", "snippet", "_content"] if k in value}
        return {k: evidence_for_ai(v) for k, v in value.items()}
    if isinstance(value, list):
        return [evidence_for_ai(v) for v in value]
    return value
