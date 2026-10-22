import pytest

from app.config import settings
from app.services import gemini


def test_falls_back_when_primary_model_is_overloaded(monkeypatch):
    monkeypatch.setattr(settings, "gemini_fallback_models", "backup-a,backup-b")
    tried = []

    def fake_once(model, *args):
        tried.append(model)
        if model != "backup-b":
            raise gemini._Overloaded() from RuntimeError("504 DEADLINE_EXCEEDED")
        return "ok"

    monkeypatch.setattr(gemini, "_generate_json_once", fake_once)
    assert gemini.generate_json("primary", "p", object) == "ok"
    assert tried == ["primary", "backup-a", "backup-b"]


def test_reports_busy_when_every_model_is_overloaded(monkeypatch):
    monkeypatch.setattr(settings, "gemini_fallback_models", "backup")

    def overloaded(*args):
        raise gemini._Overloaded() from RuntimeError("429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(gemini, "_generate_json_once", overloaded)
    with pytest.raises(gemini.GenerationUnavailable, match="busy"):
        gemini.generate_json("primary", "p", object)
