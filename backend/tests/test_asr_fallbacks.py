from app.services import sahara_asr


def test_sahara_failure_uses_deepgram_before_gemini(monkeypatch):
    monkeypatch.setattr(sahara_asr.settings, "sahara_api_key", "sahara")
    monkeypatch.setattr(sahara_asr, "_call_sahara", lambda *_: (_ for _ in ()).throw(RuntimeError("provider down")))
    expected = sahara_asr.ASRResult("pidgin transcript", "en", 0.9, "deepgram")
    monkeypatch.setattr(sahara_asr, "_call_deepgram", lambda *_: expected)
    monkeypatch.setattr(sahara_asr, "_call_gemini", lambda *_: (_ for _ in ()).throw(AssertionError("should not run")))
    assert sahara_asr.transcribe_audio(b"audio", "recording.webm") == expected


def test_no_provider_raises_without_attempting_local_whisper(monkeypatch):
    monkeypatch.setattr(sahara_asr.settings, "sahara_api_key", "")
    monkeypatch.setattr(sahara_asr.settings, "deepgram_api_key", "")
    monkeypatch.setattr(sahara_asr.settings, "gemini_api_key", "")
    monkeypatch.delenv("SAHARA_API_KEY", raising=False)
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(sahara_asr, "_call_deepgram", lambda *_: (_ for _ in ()).throw(RuntimeError("not configured")))
    monkeypatch.setattr(sahara_asr, "_call_gemini", lambda *_: (_ for _ in ()).throw(RuntimeError("not configured")))
    try:
        sahara_asr.transcribe_audio(b"audio", "recording.webm")
    except RuntimeError as exc:
        assert "No configured cloud ASR provider succeeded" in str(exc)
