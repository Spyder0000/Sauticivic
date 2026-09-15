import httpx
import pytest

from app.services import sahara_asr


def test_sahara_400_is_not_retried(monkeypatch):
    response = httpx.Response(400, text='{"detail":"unsupported audio format"}')

    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def post(self, *args, **kwargs): return response

    monkeypatch.setattr(sahara_asr.httpx, "Client", lambda **_: Client())
    monkeypatch.setattr(sahara_asr.settings, "sahara_api_key", "test")
    with pytest.raises(RuntimeError, match=r"Sahara rejected the audio \(400\)"):
        sahara_asr._call_sahara(b"not-a-wav", "recording.wav")
