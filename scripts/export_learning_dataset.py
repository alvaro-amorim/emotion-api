from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlmodel import Session  # noqa: E402

from app.core.config import ensure_storage_directories, get_settings  # noqa: E402
from app.db.repository import list_learning_examples  # noqa: E402
from app.db.session import create_db_and_tables, get_engine  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exporta learning_examples locais em JSONL.")
    parser.add_argument(
        "--approved-only",
        action="store_true",
        help="Exporta apenas exemplos aprovados para reutilizacao.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Caminho de saida. Padrao: exports/learning_dataset.jsonl",
    )
    return parser.parse_args()


def _dataset_row(example) -> dict:
    return {
        "analysis_id": example.source_analysis_id,
        "text_excerpt": example.text_excerpt,
        "transcription_text": example.transcription_excerpt or example.text_excerpt,
        "acoustic_metrics_snapshot": example.acoustic_metrics_snapshot,
        "speech_rate_snapshot": example.speech_rate_snapshot,
        "original_prediction": example.original_prediction,
        "corrected_prediction": example.corrected_prediction,
        "user_feedback": {
            "user_notes": example.user_notes,
            "correction_reason": example.correction_reason,
            "corrected_primary_emotion": example.corrected_primary_emotion,
            "corrected_tone": example.corrected_tone,
        },
        "approved_for_reuse": example.approved_for_reuse,
        "created_at": example.created_at.isoformat(),
        "updated_at": example.updated_at.isoformat() if example.updated_at else None,
    }


def main() -> int:
    args = _parse_args()
    settings = get_settings()
    ensure_storage_directories()
    create_db_and_tables()

    output_path = args.output or (Path(settings.exports_dir) / "learning_dataset.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Session(get_engine()) as session:
        examples = list_learning_examples(
            session,
            approved_only=True if args.approved_only else None,
            limit=10000,
        ).examples

    with output_path.open("w", encoding="utf-8") as dataset_file:
        for example in examples:
            dataset_file.write(
                json.dumps(_dataset_row(example), ensure_ascii=False, default=str) + "\n"
            )

    print(f"Exportados {len(examples)} exemplos para {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
