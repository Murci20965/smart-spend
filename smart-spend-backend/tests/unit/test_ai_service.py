import pytest

from app.services.ai_service import generate_spending_advice, sanitize_description


def test_sanitize_description():
    txt = "PAYMENT TO 1234 5678 9012"
    out = sanitize_description(txt)
    assert "[REDACTED]" in out


@pytest.mark.asyncio
async def test_generate_spending_advice_mocked(monkeypatch):
    async def fake_post(*args, **kwargs):
        class Resp:
            def json(self):
                return [
                    {"generated_text": "1. Save more\n2. Cut coffee\n3. Cook at home"}
                ]

        return Resp()

    # patch httpx.AsyncClient.post indirectly by patching in module
    monkeypatch.setattr("app.services.ai_service.httpx.AsyncClient.post", fake_post)
    res = await generate_spending_advice("2025-10", 500.0, 400.0)
    assert isinstance(res, str)
