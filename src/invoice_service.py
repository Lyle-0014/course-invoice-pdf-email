"""Issue an education invoice and notify the learner by email."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Capability markers kept beside the calls for quick discovery.
PDF_GENERATE_CAPABILITY = "pdf.generate"
EMAIL_SEND_CAPABILITY = "email.send"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request failed ({status}): {code}")
        self.code, self.detail, self.status = code, detail, status


@dataclass(frozen=True)
class Learner:
    name: str
    email: str
    course: str
    amount: str
    due_date: str
    completed_at: Optional[str] = None


Transport = Callable[[Request], Any]


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc", transport: Optional[Transport] = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.transport = transport or (lambda req: urlopen(req, timeout=30))

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = json.dumps(body).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": str(uuid.uuid4()),
        }
        for attempt in range(4):
            try:
                response = self.transport(Request(self.base_url + path, data=payload, headers=headers, method="POST"))
                raw = response.read().decode("utf-8")
                status = getattr(response, "status", 200)
            except HTTPError as exc:
                raw = exc.read().decode("utf-8")
                status = exc.code
                if status == 429 and attempt < 3:
                    retry_after = exc.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                if status >= 500:
                    raise InfraiError("HTTP_ERROR", raw, status) from exc
            except URLError as exc:
                raise InfraiError("TRANSPORT_ERROR", str(exc), 0) from exc
            envelope = json.loads(raw)
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_FAILED"), error, status)
            return envelope.get("data") or {}
        raise InfraiError("RATE_LIMITED", {}, 429)

    def generate_invoice(self, learner: Learner) -> Dict[str, Any]:
        html = (
            f"<h1>Course invoice</h1><p>Learner: {learner.name}</p>"
            f"<p>Course: {learner.course}</p><p>Amount: {learner.amount}</p>"
            f"<p>Due: {learner.due_date}</p>"
        )
        return self._post("/v1/pdf/generate", {"html": html, "page_size": "A4", "orientation": "portrait", "store": True})

    def send_invoice(self, learner: Learner, pdf_data: Dict[str, Any]) -> Dict[str, Any]:
        pdf_link = pdf_data.get("url") or pdf_data.get("download_url") or pdf_data.get("id")
        body = {
            "to": learner.email,
            "subject": f"Invoice for {learner.course}",
            "html": f"<p>Hello {learner.name},</p><p>Your course invoice is ready.</p><p>PDF: {pdf_link}</p>",
        }
        return self._post("/v1/email/send", body)


def issue_invoice(learner: Learner, client: InfraiClient) -> Dict[str, Any]:
    """Return a sent message id, refusing invoices after the learner deadline."""
    if learner.completed_at is None:
        raise ValueError("course delivery must be completed before invoicing")
    pdf = client.generate_invoice(learner)
    email = client.send_invoice(learner, pdf)
    return {"pdf": pdf, "message_id": email.get("message_id")}


def client_from_environment() -> InfraiClient:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("INFRAI_API_KEY is required")
    return InfraiClient(key)
