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
from typing import TypeVar
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

from .llm import create_llm

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _clean_latex(text: str) -> str:
    """Remove markdown code fences from LaTeX output."""
    text = text.strip()
    text = re.sub(r"^```latex\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    text = re.sub(r"^```\s*\n?", "", text)
    return text.strip()


class RobustPydanticOutputParser(PydanticOutputParser[T]):
    """Pydantic parser that handles markdown-wrapped JSON and invalid escapes gracefully."""

    def parse(self, text: str) -> T:
        import json

        text = text.strip()
        # Strip markdown code fences (```json, ```JSON, ```, etc.)
        text = re.sub(r"^```(?:json|JSON)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()

        # Try to extract JSON from the text if it's wrapped in other content
        json_start = text.find("{")
        json_end = text.rfind("}")
        if json_start != -1 and json_end != -1:
            text = text[json_start : json_end + 1]

        # Fix invalid escape sequences in JSON strings
        # Replace backslash followed by non-escape-char with double backslash
        text = re.sub(r'\\([^"\\/bfnrtu])', r"\\\\\1", text)

        try:
            json_obj = json.loads(text)
            return self.pydantic_object.model_validate(json_obj)
        except (json.JSONDecodeError, ValueError) as e:
            raise OutputParserException(f"Failed to parse JSON: {text[:200]}...") from e


# ══════════════════════════════════════════════════════════════
#  Step 1 — 正解 tex 生成
# ══════════════════════════════════════════════════════════════


class LaTeXOutput(BaseModel):
    """Pure LaTeX output without markdown code fences."""

    latex: str = Field(
        description="Pure LaTeX body content without ``` fences or markdown formatting"
    )


_parser = RobustPydanticOutputParser(pydantic_object=LaTeXOutput)
_format_instructions = _parser.get_format_instructions()


_CORRECT_SYSTEM = """\
You are an expert mathematics tutor and LaTeX author.
Given a student's answer transcribed to LaTeX and the original problem statement,
produce the CORRECT, fully worked solution in LaTeX.

Rules:
- Output ONLY the LaTeX body (no \\documentclass, no \\begin{{document}}).
- Use standard AMS-LaTeX (amsmath, amssymb).
- Be concise but complete; show all necessary steps.
- Do NOT add any explanation outside the LaTeX source—pure LaTeX only.
- Do NOT wrap the output in ```latex or ``` code fences.

{format_instructions}
""".format(format_instructions=_format_instructions)


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
    from langchain_openai import ChatOpenAI
    import os
    from dotenv import load_dotenv

    load_dotenv()
    OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

    llm = ChatOpenAI(
        model="google/gemini-2.5-flash-lite",
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.7,
    )

    chain = (llm | _parser).with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,
        retry_if_exception_type=(OutputParserException,),
    )
    messages = [
        SystemMessage(content=_CORRECT_SYSTEM),
        HumanMessage(content=_correct_prompt(problem, tex_transcribed)),
    ]
    logger.info("Generating correct tex.")
    response: LaTeXOutput = chain.invoke(messages)
    return _clean_latex(response.latex)


# ══════════════════════════════════════════════════════════════
#  Step 2 — diff tex 生成（添削バージョン）
# ══════════════════════════════════════════════════════════════

_DIFF_SYSTEM = (r"""
You are a meticulous LaTeX proofreader.
You will receive two LaTeX bodies:
  - STUDENT: the student's answer (may contain errors)
  - CORRECT: the correct solution

Produce a single LaTeX body that shows the differences inline using:
  \textcolor{{green}}{{<added or correct text>}}
  \textcolor{{red}}{{\sout{{<removed or wrong text>}}}}

Rules:
- Keep unchanged parts as-is.
- Wrap addition/corrections in \textcolor{{green}}{{...}}.
- Wrap deletions/mistakes in \textcolor{{red}}{{\sout{{...}}}}.
- Output ONLY the LaTeX body—no \documentclass, no \begin{{document}}.
- Do NOT add any commentary or explanation—pure LaTeX only.
- Do NOT wrap the output in ```latex or ``` code fences.

{format_instructions}
""").strip().format(format_instructions=_format_instructions)


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
    from langchain_openai import ChatOpenAI
    import os
    from dotenv import load_dotenv

    load_dotenv()
    OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

    llm = ChatOpenAI(
        model="google/gemini-2.5-flash-lite",
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.7,
    )

    chain = (llm | _parser).with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,
        retry_if_exception_type=(OutputParserException,),
    )
    messages = [
        SystemMessage(content=_DIFF_SYSTEM),
        HumanMessage(content=_diff_prompt(tex_transcribed, tex_correct)),
    ]
    logger.info("Generating diff tex.")
    response: LaTeXOutput = chain.invoke(messages)
    return _clean_latex(response.latex)


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
