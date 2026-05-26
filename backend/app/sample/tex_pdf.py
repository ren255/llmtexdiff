"""
TEX → PDF 変換サンプル。

Usage (Docker コンテナ内 or texlive 環境):
    python -m app.sample.tex_run

出力:
    data/sessions/{session_id}/transcribed.pdf
"""

import subprocess
import tempfile
from pathlib import Path

from app.db.database import SessionLocal
from app.db.model import Answer, Question, Session
from app.db import file_manager as fm

# ---------------------------------------------------------------------------
# サンプル用 TeX ソース
# ---------------------------------------------------------------------------

SAMPLE_TEX = r"""
\documentclass{article}
\usepackage{amsmath}
\begin{document}

\section*{Sample}

Einstein's mass-energy equivalence:
\[
  E = mc^{2}
\]

Maxwell's equations (differential form):
\begin{align}
  \nabla \cdot \mathbf{E}  &= \frac{\rho}{\varepsilon_0} \\
  \nabla \cdot \mathbf{B}  &= 0 \\
  \nabla \times \mathbf{E} &= -\frac{\partial \mathbf{B}}{\partial t} \\
  \nabla \times \mathbf{B} &= \mu_0 \mathbf{J}
                              + \mu_0\varepsilon_0 \frac{\partial \mathbf{E}}{\partial t}
\end{align}

\end{document}
""".strip()


# ---------------------------------------------------------------------------
# TeX → PDF 変換
# ---------------------------------------------------------------------------


def tex_to_pdf(tex_source: str) -> bytes:
    """
    pdflatex で TeX ソースをコンパイルし、PDF バイト列を返す。
    失敗時は RuntimeError を送出。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tex_file = tmp / "main.tex"
        tex_file.write_text(tex_source, encoding="utf-8")

        result = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-output-directory",
                str(tmp),
                str(tex_file),
            ],
            capture_output=True,
            text=True,
        )

        pdf_file = tmp / "main.pdf"
        if result.returncode != 0 or not pdf_file.exists():
            raise RuntimeError(
                f"pdflatex failed (returncode={result.returncode})\n"
                f"--- stdout ---\n{result.stdout}\n"
                f"--- stderr ---\n{result.stderr}"
            )

        return pdf_file.read_bytes()


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------


def main() -> None:
    db = SessionLocal()
    try:
        # 1. Session 作成
        print("=== CREATE SESSION ===")
        session = Session(title="tex_run サンプル")
        db.add(session)
        db.flush()

        question = Question(
            session_id=session.id,
            prompt="サンプル数式を PDF にレンダリングしてください。",
            image_paths=[],
        )
        db.add(question)
        db.flush()

        answer = Answer(
            question_id=question.id,
            tex_transcribed=SAMPLE_TEX,
        )
        db.add(answer)
        db.flush()

        print(f"  session_id  : {session.id}")
        print(f"  question_id : {question.id}")
        print(f"  answer_id   : {answer.id}")

        # 2. TeX → PDF コンパイル
        print("\n=== COMPILE TEX → PDF ===")
        pdf_bytes = tex_to_pdf(SAMPLE_TEX)
        print(f"  PDF size: {len(pdf_bytes)} bytes")

        # 3. PDF を data/ 以下に保存
        print("\n=== SAVE PDF ===")
        rel_path = f"sessions/{session.id}/transcribed.pdf"
        abs_path = fm.save(rel_path, pdf_bytes)
        print(f"  Relative : {rel_path}")
        print(f"  Absolute : {abs_path.resolve()}")

        # 4. DB に path を記録してコミット
        answer.pdf_transcribed_path = rel_path
        db.commit()
        print("\n=== DONE ===")
        print(f"  DB updated. pdf_transcribed_path = {rel_path!r}")

    except RuntimeError as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
