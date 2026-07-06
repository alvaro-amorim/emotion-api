from pathlib import Path
from types import SimpleNamespace

from app.services.audio_preprocessor import ProcessedAudio, optimize_audio_for_transcription


def test_optimize_audio_for_transcription_falls_back_to_standard_wav(tmp_path, monkeypatch):
    processed_path = tmp_path / "audio_16khz_mono.wav"
    processed_path.write_bytes(b"fake wav")

    monkeypatch.setattr("app.services.audio_preprocessor.shutil.which", lambda name: "ffmpeg")
    monkeypatch.setattr(
        "app.services.audio_preprocessor.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1),
    )

    processed_audio = ProcessedAudio(
        original_path=str(tmp_path / "audio.webm"),
        processed_path=str(processed_path),
    )
    settings = SimpleNamespace(
        processed_audio_dir=str(tmp_path),
        max_audio_duration_seconds=600,
    )

    result = optimize_audio_for_transcription(processed_audio, settings)

    assert result.processed_path == processed_audio.processed_path
    assert result.optimized_for_transcription is False
    assert result.transcription_source_path == processed_audio.processed_path
    assert result.transcription_fallback_reason == "optimized_conversion_failed"
    assert not Path(str(tmp_path / "audio_16khz_mono_transcription.wav")).exists()
