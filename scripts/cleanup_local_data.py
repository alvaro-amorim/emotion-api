from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlmodel import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.repository import count_audio_analyses, count_learning_examples  # noqa: E402
from app.db.session import get_engine, reset_engine_for_tests  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Limpa dados locais do SQLite com confirmacao.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que seria apagado sem apagar.")
    parser.add_argument("--yes", action="store_true", help="Confirma a remocao sem prompt interativo.")
    return parser.parse_args()


def _sqlite_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    raw_path = database_url.removeprefix("sqlite:///")
    if raw_path == ":memory:":
        return None
    return Path(raw_path)


def _counts(database_path: Path) -> tuple[int, int]:
    if not database_path.exists():
        return 0, 0
    with Session(get_engine()) as session:
        return count_audio_analyses(session), count_learning_examples(session)


def main() -> int:
    args = _parse_args()
    settings = get_settings()
    database_path = _sqlite_path(settings.database_url)
    if database_path is None:
        print("Cleanup automatico disponivel apenas para SQLite em arquivo.")
        return 2

    analyses_count, examples_count = _counts(database_path)
    print(f"Banco local: {database_path}")
    print(f"Analises salvas: {analyses_count}")
    print(f"Learning examples: {examples_count}")

    if args.dry_run:
        print("Dry-run: nenhum dado foi apagado.")
        return 0

    if not database_path.exists():
        print("Nenhum banco local encontrado para apagar.")
        return 0

    if not args.yes:
        confirmation = input("Digite APAGAR para remover o banco SQLite local: ").strip()
        if confirmation != "APAGAR":
            print("Operacao cancelada.")
            return 1

    reset_engine_for_tests()
    database_path.unlink()
    print(f"Banco local removido: {database_path}")
    print("Fixtures, .env, .venv e storage nao foram alterados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
