from pathlib import Path
import re


def sanitize_filename(file_name: str) -> str:
    name = Path(file_name).name.strip()
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return safe_name or "audio.bin"

