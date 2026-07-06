from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AudioEmotionError(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class UnsupportedAudioFormatError(AudioEmotionError):
    status_code = 400

    def __init__(self) -> None:
        super().__init__("Formato de áudio não suportado. Envie mp3, wav, m4a, webm ou ogg.")


class EmptyAudioFileError(AudioEmotionError):
    status_code = 400

    def __init__(self) -> None:
        super().__init__("Arquivo de áudio vazio.")


class AudioFileTooLargeError(AudioEmotionError):
    status_code = 413

    def __init__(self, max_size_mb: int) -> None:
        super().__init__(f"Arquivo de áudio excede o limite de {max_size_mb} MB.")


class AudioDurationTooLongError(AudioEmotionError):
    status_code = 413

    def __init__(self, max_duration_seconds: int) -> None:
        super().__init__(f"Áudio excede o limite de {max_duration_seconds} segundos da V1.")


class FFmpegNotFoundError(AudioEmotionError):
    status_code = 500

    def __init__(self) -> None:
        super().__init__("FFmpeg não encontrado no PATH. Instale o FFmpeg e tente novamente.")


class AudioConversionError(AudioEmotionError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("Não foi possível converter o áudio. Verifique se o arquivo é válido.")


class InvalidAudioFileError(AudioEmotionError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("Não foi possível ler o áudio convertido. Verifique a qualidade do arquivo.")


class TranscriptionError(AudioEmotionError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("Não foi possível transcrever o áudio. Verifique a qualidade do arquivo.")


class AnalysisNotFoundError(AudioEmotionError):
    status_code = 404

    def __init__(self, analysis_id: str) -> None:
        super().__init__(f"Análise não encontrada: {analysis_id}.")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AudioEmotionError)
    async def handle_audio_emotion_error(
        request: Request,
        exc: AudioEmotionError,
    ) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
