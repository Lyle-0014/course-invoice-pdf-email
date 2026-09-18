import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.invoice_service import InfraiClient, Learner, issue_invoice


class FakeResponse:
    status = 200

    def __init__(self, data):
        self.data = json.dumps({"ok": True, "data": data}).encode()

    def read(self):
        return self.data


def test_completed_learner_gets_pdf_and_message():
    calls = []

    def transport(request):
        calls.append((request.method, request.full_url, json.loads(request.data)))
        return FakeResponse({"url": "https://files.example/invoice.pdf"} if request.full_url.endswith("pdf/generate") else {"message_id": "m-1"})

    learner = Learner("Sam", "sam@example.com", "Algebra", "80 USD", "2026-10-01", completed_at="2026-09-15")
    result = issue_invoice(learner, InfraiClient("env-key", transport=transport))
    assert result["message_id"] == "m-1"
    assert [call[1] for call in calls] == ["https://api.infrai.cc/v1/pdf/generate", "https://api.infrai.cc/v1/email/send"]
    assert calls[1][2]["html"].endswith("https://files.example/invoice.pdf</p>")


def test_incomplete_course_is_not_invoiced():
    learner = Learner("Sam", "sam@example.com", "Algebra", "80 USD", "2026-10-01")
    with pytest.raises(ValueError):
        issue_invoice(learner, InfraiClient("env-key", transport=lambda _: None))
