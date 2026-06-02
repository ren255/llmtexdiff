"""
services/pipeline.py

OCR → 採点 → PDF×3 生成 → DB 保存 を一気通貫で行うパイプライン。
router からはこの関数だけを呼ぶ。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session as DBSession

from ..db.file_manager import FileManager
from ..db.model import Answer, Question
from .grading import run_grading
from .latex import LatexCompileError, compile_tex
from .ocr import run_ocr

logger = logging.getLogger(__name__)


# ── 結果データクラス ───────────────────────────────────────────
@dataclass
class PipelineResult:
    """pipeline.run_pipeline の返り値。"""

    answer_id: str
    tex_transcribed: str
    tex_correct: str
    diff_tex: str
    pdf_transcribed_path: str  # data/ 起点の相対パス
    pdf_correct_path: str
    pdf_diff_path: str


# ── 内部ヘルパー ───────────────────────────────────────────────
def _safe_compile(tex_body: str, label: str) -> bytes | None:
    """
    コンパイルに失敗しても例外を握り潰してログだけ残す。
    呼び出し側で None チェックして DB パスを None にする設計。
    """
    try:
        return compile_tex(tex_body)
    except LatexCompileError as exc:
        logger.warning(
            "pdflatex failed for %s: %s\nstdout: %s",
            label,
            exc,
            exc.stdout[-500:],  # 長すぎるログを末尾 500 文字に切り詰め
        )
        return None


# ── メイン関数 ─────────────────────────────────────────────────
def run_pipeline(
    *,
    question_id: str,
    session_id: str,
    image_paths: list[Path],
    problem: str,
    db: DBSession,
    file_manager: FileManager,
) -> PipelineResult:
    """
    OCR → 採点 → PDF 生成 → DB 保存 の全工程を実行する。

    Parameters
    ----------
    question_id : str
        処理対象の Question.id。
    session_id : str
        親 Session.id（ファイル保存パスの構成に使用）。
    image_paths : list[Path]
        アップロード済み画像の絶対パスリスト。
    problem : str
        ユーザーが入力した問題文テキスト。
    db : DBSession
        SQLAlchemy セッション。
    file_manager : FileManager
        PDF ファイルの保存・パス管理を担うオブジェクト。

    Returns
    -------
    PipelineResult
    """

    # ─────────────────────────────────────────
    # Step 1: OCR
    # ─────────────────────────────────────────
    logger.info("[pipeline] Step 1: OCR  question_id=%s", question_id)
    tex_transcribed = run_ocr(image_paths, prompt_hint=problem)

    # ─────────────────────────────────────────
    # Step 2: 採点（正解 tex + diff tex 生成）
    # ─────────────────────────────────────────
    logger.info("[pipeline] Step 2: Grading  question_id=%s", question_id)
    tex_correct, diff_tex = run_grading(problem, tex_transcribed)

    # ─────────────────────────────────────────
    # Step 3: PDF 生成（失敗しても続行）
    # ─────────────────────────────────────────
    logger.info("[pipeline] Step 3: PDF generation  question_id=%s", question_id)

    pdf_transcribed_bytes = _safe_compile(tex_transcribed, "transcribed")
    pdf_correct_bytes = _safe_compile(tex_correct, "correct")
    pdf_diff_bytes = _safe_compile(diff_tex, "diff")

    # ─────────────────────────────────────────
    # Step 4: ファイル保存（FileManager に委譲）
    # ─────────────────────────────────────────
    logger.info("[pipeline] Step 4: Saving PDFs  question_id=%s", question_id)

    def _save(pdf_bytes: bytes | None, filename: str) -> str | None:
        if pdf_bytes is None:
            return None
        return file_manager.save_pdf(
            session_id=session_id,
            filename=filename,
            data=pdf_bytes,
        )

    pdf_transcribed_path = _save(pdf_transcribed_bytes, "transcribed.pdf")
    pdf_correct_path = _save(pdf_correct_bytes, "correct.pdf")
    pdf_diff_path = _save(pdf_diff_bytes, "diff.pdf")

    # ─────────────────────────────────────────
    # Step 5: Answer を DB に保存
    # ─────────────────────────────────────────
    logger.info("[pipeline] Step 5: Saving Answer to DB  question_id=%s", question_id)

    # 既存の Answer があれば更新、なければ新規作成（冪等性確保）
    answer: Answer | None = (
        db.query(Answer).filter(Answer.question_id == question_id).first()
    )

    if answer is None:
        answer = Answer(question_id=question_id)
        db.add(answer)

    answer.tex_transcribed = tex_transcribed
    answer.tex_correct = tex_correct
    answer.diff_latex = diff_tex
    answer.pdf_transcribed_path = pdf_transcribed_path
    answer.pdf_correct_path = pdf_correct_path
    answer.pdf_diff_path = pdf_diff_path

    db.commit()
    db.refresh(answer)

    logger.info("[pipeline] Done.  answer_id=%s", answer.id)

    return PipelineResult(
        answer_id=answer.id,
        tex_transcribed=tex_transcribed,
        tex_correct=tex_correct,
        diff_tex=diff_tex,
        pdf_transcribed_path=pdf_transcribed_path or "",
        pdf_correct_path=pdf_correct_path or "",
        pdf_diff_path=pdf_diff_path or "",
    )
