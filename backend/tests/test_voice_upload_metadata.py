from app.services.sahara_asr import _get_mime_type


def test_browser_recording_mime_types_preserve_the_actual_extension():
    assert _get_mime_type("recording.webm") == "audio/webm"
    assert _get_mime_type("recording.ogg") == "audio/ogg"
    assert _get_mime_type("recording.wav") == "audio/wav"
