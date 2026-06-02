"""
services/latex.py

tex 文字列を受け取り pdflatex を実行して PDF バイト列を返すシンプルなラッパー。
一時ファイルの作成・削除もここで完結する。
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# デフォルトの preamble（日本語対応・数式パッケージ）
_DEFAULT_PREAMBLE = r"""
\documentclass[12pt]{article}
\usepackage{amsmath, amssymb, amsfonts}
\usepackage{color}
\usepackage{luatexja}
\usepackage{ulem}          % \sout（取り消し線）
\pagestyle{empty}
""".strip()


class LatexCompileError(RuntimeError):
    """pdflatex の実行に失敗したときに送出する例外。"""

    def __init__(self, message: str, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


def _wrap_document(body: str, preamble: str | None = None) -> str:
    """
    body が完全な LaTeX ソース（\\documentclass を含む）でなければ
    デフォルト preamble で包んで完全なドキュメントにする。
    """
    if r"\documentclass" in body:
        return body
    pre = preamble if preamble is not None else _DEFAULT_PREAMBLE
    return f"{pre}\n\\begin{{document}}\n{body}\n\\end{{document}}\n"


def compile_tex(
    tex_source: str,
    *,
    preamble: str | None = None,
    timeout: int = 60,
) -> bytes:
    """
    tex_source を pdflatex でコンパイルして PDF バイト列を返す。

    Parameters
    ----------
    tex_source : str
        コンパイルしたい LaTeX ソース。
        \\documentclass が含まれていない場合は _DEFAULT_PREAMBLE で自動補完する。
    preamble : str | None
        自動補完時に使う preamble。None なら _DEFAULT_PREAMBLE を使用。
    timeout : int
        pdflatex のタイムアウト秒数（デフォルト 60）。

    Returns
    -------
    bytes
        生成された PDF のバイト列。

    Raises
    ------
    LatexCompileError
        pdflatex が非ゼロ終了した場合、またはタイムアウトした場合。
    """
    full_source = _wrap_document(tex_source, preamble)
    tmpdir = Path(tempfile.mkdtemp())

    try:
        tex_file = tmpdir / "main.tex"
        tex_file.write_text(full_source, encoding="utf-8")

        cmd = [
            "lualatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory",
            str(tmpdir),
            str(tex_file),
        ]

        # lualatex を 2 回走らせて相互参照を解決する（念のため）
        for _ in range(2):
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(tmpdir),
                errors="replace",  # pdflatex log に非UTF-8文字が含まれる場合がある
            )

        if proc.returncode != 0:
            raise LatexCompileError(
                f"pdflatex exited with code {proc.returncode}",
                stdout=proc.stdout,
                stderr=proc.stderr,
            )

        pdf_path = tmpdir / "main.pdf"
        if not pdf_path.exists():
            raise LatexCompileError(
                "pdflatex succeeded but main.pdf was not produced",
                stdout=proc.stdout,
                stderr=proc.stderr,
            )

        return pdf_path.read_bytes()

    except subprocess.TimeoutExpired as exc:
        raise LatexCompileError(f"pdflatex timed out after {timeout}s") from exc

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
