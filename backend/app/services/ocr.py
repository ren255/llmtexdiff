"""
services/ocr.py

画像（1 枚以上）を受け取り、LLM に手書き・印刷された数式・テキストを
LaTeX ソースとして書き起こさせる。
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import TypeVar
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from .llm import load_image_b64

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


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


class LaTeXOutput(BaseModel):
    """Pure LaTeX output without markdown code fences."""

    latex: str = Field(
        description="Pure LaTeX body content without ``` fences or markdown formatting"
    )


_parser = RobustPydanticOutputParser(pydantic_object=LaTeXOutput)
_format_instructions = _parser.get_format_instructions()


def _clean_latex(text: str) -> str:
    """Remove markdown code fences from LaTeX output."""
    text = text.strip()
    text = re.sub(r"^```latex\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    text = re.sub(r"^```\s*\n?", "", text)
    return text.strip()


# ── プロンプト ────────────────────────────────────────────────
_OCR_SYSTEM = """\
You are a precise LaTeX transcription assistant.
Your task is to faithfully transcribe the mathematical expressions and text
visible in the provided image(s) into clean LaTeX source.

Rules:
- Output ONLY the LaTeX body (no \\documentclass, no \\begin{{document}}).
- Preserve the original structure: equations, text blocks, numbering.
- Use standard AMS-LaTeX packages (amsmath, amssymb) for math.
- Do NOT add any explanation or commentary—pure LaTeX only.
- Do NOT wrap the output in ```latex or ``` code fences.

{format_instructions}
""".format(format_instructions=_format_instructions)


def _build_ocr_message(image_paths: list[Path], prompt_hint: str) -> HumanMessage:
    """
    複数画像 + テキストヒントを組み合わせた HumanMessage を構築する。
    OpenRouter / LangChain の multimodal content list 形式を使用。
    """
    content: list[dict] = []

    for img_path in image_paths:
        b64 = load_image_b64(img_path)
        # 拡張子から MIME タイプを推定（jpeg / png / webp / gif に対応）
        suffix = img_path.suffix.lower().lstrip(".")
        mime = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "gif": "image/gif",
        }.get(suffix, "image/png")

        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            }
        )

    # テキスト指示を末尾に追加
    instruction = (
        f"{_OCR_SYSTEM}\n\n"
        f"Additional context from the user: {prompt_hint}\n\n"
        "Transcribe the image(s) above into LaTeX."
    )
    content.append({"type": "text", "text": instruction})

    return HumanMessage(content=content)


def run_ocr(
    image_paths: list[Path],
    prompt_hint: str = "",
) -> str:
    """
    画像リストを LLM に投げて LaTeX 書き起こし文字列を返す。

    Parameters
    ----------
    image_paths : list[Path]
        書き起こし対象の画像ファイルパス（1 枚以上）。
    prompt_hint : str
        ユーザーが入力した補足テキスト（問題の分野・指示など）。

    Returns
    -------
    str
        LLM が生成した LaTeX ボディ文字列（\\documentclass なし）。

    Raises
    ------
    ValueError
        image_paths が空の場合。
    """
    if not image_paths:
        raise ValueError("image_paths must contain at least one image.")

    load_dotenv()
    OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

    llm = ChatOpenAI(
        model="google/gemini-2.5-flash-lite",
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.7,
    )

    message = _build_ocr_message(image_paths, prompt_hint)

    logger.info("Running OCR on %d image(s).", len(image_paths))
    chain = (llm | _parser).with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,
        retry_if_exception_type=(OutputParserException,),
    )
    response: LaTeXOutput = chain.invoke([message])

    tex = _clean_latex(response.latex)
    logger.debug("OCR result (%d chars).", len(tex))
    return tex
