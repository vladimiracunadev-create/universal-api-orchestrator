import base64
from email.message import EmailMessage

from universal_api_orchestrator.connectors.mail_content import (
    evidence_for_ai,
    gmail_content,
    normalize_gmail,
)


def encoded(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")

def test_plain_utf8_and_headers():
    message={"id":"1","payload":{"headers":[{"name":"Subject","value":"Solicitud"}],"mimeType":"text/plain","body":{"data":encoded("Mañana reunión")}}}
    result=gmail_content(message)
    assert result["_content"]["text"]=="Mañana reunión"
    assert result["_content"]["subject"]=="Solicitud"
    assert "payload" not in evidence_for_ai(result)

def test_html_no_active_script():
    result=gmail_content({"payload":{"mimeType":"text/html","body":{"data":encoded("<p>Hola</p><script>secreto()</script><style>div{}</style>")}}})
    assert result["_content"]["text"].strip()=="Hola"

def test_attachments_not_downloaded_or_used_as_body():
    value={"payload":{"parts":[{"filename":"a.txt","mimeType":"text/plain","body":{"data":encoded("ADJUNTO"),"attachmentId":"abc"}},{"mimeType":"text/plain","body":{"data":encoded("CUERPO")}}]}}
    content=gmail_content(value)["_content"]
    assert content["text"]=="CUERPO"
    assert content["attachments"][0]["attachment_id"]=="abc"

def test_raw_mime():
    message=EmailMessage();message["Subject"]="Hola";message.set_content("Cuerpo real")
    result=gmail_content({"raw":base64.urlsafe_b64encode(message.as_bytes()).decode()})
    assert "Cuerpo real" in result["_content"]["text"]

def test_listing_does_not_fabricate_content():
    listing={"messages":[{"id":"1","threadId":"2"}]}
    assert normalize_gmail(listing)==listing

def test_thread_and_truncation():
    value={"messages":[{"payload":{"mimeType":"text/plain","body":{"data":encoded("a"*100001)}}}]}
    content=normalize_gmail(value)["messages"][0]["_content"]
    assert content["truncated"] and len(content["text"])==100000
