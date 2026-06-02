"""
pipeline.py — OCR → 採点 → PDF×3 生成 → DB 保存 の全工程をテストするサンプルスクリプト

Usage:
    # 単一画像でテスト
    python -m app.sample.pipeline path/to/image.png

    # 複数画像でテスト
    python -m app.sample.pipeline path/to/image1.png path/to/image2.png

    # 問題文を指定してテスト
    python -m app.sample.pipeline path/to/image.png --problem "次の数式を解け: E = mc^2"

    # DB初期化から実行
    python -m app.sample.pipeline path/to/image.png --init-db
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.db.database import SessionLocal
from app.db.file_manager import FileManager
from app.db.init_db import init_db
from app.db.model import Answer, Question, Session
from app.services.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test the full OCR→Grading→PDF pipeline"
    )
    parser.add_argument("images", nargs="+", type=Path, help="Path(s) to test image(s)")
    parser.add_argument(
        "--problem", type=str, default="この数式を解いてください。", help="Problem text"
    )
    parser.add_argument(
        "--init-db", action="store_true", help="Reinitialize database before running"
    )
    args = parser.parse_args()

    # 画像の存在チェック
    for img in args.images:
        if not img.exists():
            raise FileNotFoundError(f"Image not found: {img}")

    # DB初期化（オプション）
    if args.init_db:
        print("[pipeline] Initializing database...")
        init_db()

    db = SessionLocal()
    file_manager = FileManager()

    try:
        # ── Step 0: Session / Question を事前に作成 ──
        print("[pipeline] Creating Session and Question...")
        session = Session(title="Pipeline test session")
        db.add(session)
        db.flush()

        # 画像パスは data/ 起点の相対パスで保存（実際にはアップロード処理で配置済みと仮定）
        image_paths_rel = [
            f"sessions/{session.id}/images/{i}{img.suffix}"
            for i, img in enumerate(args.images)
        ]

        question = Question(
            session_id=session.id,
            prompt=args.problem,
            image_paths=image_paths_rel,
        )
        db.add(question)
        db.flush()

        print(f"  Session  id={session.id}")
        print(f"  Question id={question.id}")
        print(f"  Problem  ={args.problem!r}")
        print(f"  Images   ={len(args.images)} file(s)")

        # ── Step 1-5: パイプライン実行 ──
        print("\n[pipeline] Running full pipeline...")
        result = run_pipeline(
            question_id=question.id,
            session_id=session.id,
            image_paths=[img.resolve() for img in args.images],
            problem=args.problem,
            db=db,
            file_manager=file_manager,
        )

        # ── 結果表示 ──
        print("\n" + "=" * 60)
        print("[pipeline] Pipeline completed successfully!")
        print("=" * 60)
        print(f"  answer_id         : {result.answer_id}")
        print(f"  tex_transcribed   : {len(result.tex_transcribed)} chars")
        print(f"  tex_correct       : {len(result.tex_correct)} chars")
        print(f"  diff_tex          : {len(result.diff_tex)} chars")
        print(f"  pdf_transcribed   : {result.pdf_transcribed_path or '(failed)'}")
        print(f"  pdf_correct       : {result.pdf_correct_path or '(failed)'}")
        print(f"  pdf_diff          : {result.pdf_diff_path or '(failed)'}")

        # ── DB 確認 ──
        print("\n[pipeline] Verifying Answer in DB...")
        answer: Answer | None = (
            db.query(Answer).filter(Answer.question_id == question.id).first()
        )
        if answer:
            print(f"  Answer found: id={answer.id}")
            print(f"    tex_transcribed  : {answer.tex_transcribed[:80]!r}...")
            print(f"    tex_correct      : {answer.tex_correct[:80]!r}...")
            print(f"    diff_latex       : {answer.diff_latex[:80]!r}...")
            print(f"    pdf_transcribed  : {answer.pdf_transcribed_path}")
            print(f"    pdf_correct      : {answer.pdf_correct_path}")
            print(f"    pdf_diff         : {answer.pdf_diff_path}")
        else:
            print("  ERROR: Answer not found in DB!")

        print("\n[pipeline] Done.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
