"""
services/grading.py

tex_transcribed（OCR 結果）と問題文を LLM に渡し、
  1. tex_correct  : 正解 LaTeX
  2. diff_tex     : 添削済み LaTeX（\\textcolor{green}{...} / \\textcolor{red}{\\sout{...}}）
の 2 つを生成する。

2 ステップ構成:
  Step 1 — generate_correct : 正解 tex を生成
  Step 2 — generate_diff    : transcribed と correct を比較して diff_tex を生成
"""

from __future__ import annotations

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from .llm import create_llm

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
#  Step 1 — 正解 tex 生成
# ══════════════════════════════════════════════════════════════

_CORRECT_SYSTEM = """\
You are an expert mathematics tutor and LaTeX author.
Given a student's answer transcribed to LaTeX and the original problem statement,
produce the CORRECT, fully worked solution in LaTeX.

Rules:
- Output ONLY the LaTeX body (no \\documentclass, no \\begin{document}).
- Use standard AMS-LaTeX (amsmath, amssymb).
- Be concise but complete; show all necessary steps.
- Do NOT add any explanation outside the LaTeX source—pure LaTeX only.
"""


def _correct_prompt(problem: str, tex_transcribed: str) -> str:
    return (
        f"## Problem\n{problem}\n\n"
        f"## Student Answer (LaTeX transcription)\n```latex\n{tex_transcribed}\n```\n\n"
        "Produce the correct solution in LaTeX body only."
    )


def generate_correct(problem: str, tex_transcribed: str) -> str:
    """
    問題文と書き起こし tex から正解 tex を生成する。

    Parameters
    ----------
    problem : str
        問題文（ユーザー入力のプロンプト）。
    tex_transcribed : str
        OCR で得た学生の回答 LaTeX。

    Returns
    -------
    str
        正解 LaTeX ボディ文字列。
    """
    llm = create_llm()
    messages = [
        SystemMessage(content=_CORRECT_SYSTEM),
        HumanMessage(content=_correct_prompt(problem, tex_transcribed)),
    ]
    logger.info("Generating correct tex.")
    response = llm.invoke(messages)
    return response.content.strip()


# ══════════════════════════════════════════════════════════════
#  Step 2 — diff tex 生成（添削バージョン）
# ══════════════════════════════════════════════════════════════

_DIFF_SYSTEM = r"""
You are a meticulous LaTeX proofreader.
You will receive two LaTeX bodies:
  - STUDENT: the student's answer (may contain errors)
  - CORRECT: the correct solution

Produce a single LaTeX body that shows the differences inline using:
  \textcolor{green}{<added or correct text>}
  \textcolor{red}{\sout{<removed or wrong text>}}

Rules:
- Keep unchanged parts as-is.
- Wrap additions/corrections in \textcolor{green}{...}.
- Wrap deletions/mistakes in \textcolor{red}{\sout{...}}.
- Output ONLY the LaTeX body—no \documentclass, no \begin{document}.
- Do NOT add any commentary or explanation—pure LaTeX only.
""".strip()


def _diff_prompt(tex_transcribed: str, tex_correct: str) -> str:
    return (
        f"## STUDENT\n```latex\n{tex_transcribed}\n```\n\n"
        f"## CORRECT\n```latex\n{tex_correct}\n```\n\n"
        r"Produce the diff LaTeX body using \textcolor{green}{} and \textcolor{red}{\sout{}}."
    )


def generate_diff(tex_transcribed: str, tex_correct: str) -> str:
    """
    学生 tex と正解 tex を比較して添削済み diff tex を生成する。

    Parameters
    ----------
    tex_transcribed : str
        OCR で得た学生の回答 LaTeX。
    tex_correct : str
        generate_correct で得た正解 LaTeX。

    Returns
    -------
    str
        添削済み diff LaTeX ボディ文字列。
    """
    llm = create_llm()
    messages = [
        SystemMessage(content=_DIFF_SYSTEM),
        HumanMessage(content=_diff_prompt(tex_transcribed, tex_correct)),
    ]
    logger.info("Generating diff tex.")
    response = llm.invoke(messages)
    return response.content.strip()


# ══════════════════════════════════════════════════════════════
#  まとめて呼べるヘルパー
# ══════════════════════════════════════════════════════════════


def run_grading(
    problem: str,
    tex_transcribed: str,
) -> tuple[str, str]:
    """
    正解 tex と diff tex をまとめて生成して返す。

    Returns
    -------
    (tex_correct, diff_tex) のタプル。
    """
    tex_correct = generate_correct(problem, tex_transcribed)
    diff_tex = generate_diff(tex_transcribed, tex_correct)
    return tex_correct, diff_tex
