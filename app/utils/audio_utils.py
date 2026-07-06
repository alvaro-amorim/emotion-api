from pathlib import Path


def get_file_extension(file_name: str) -> str:
    return Path(file_name).suffix.lower()

