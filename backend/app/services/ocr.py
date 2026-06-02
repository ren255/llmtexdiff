"""
services/ocr.py

画像（1 枚以上）を受け取り、LLM に手書き・印刷された数式・テキストを
LaTeX ソースとして書き起こさせる。
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.messages import HumanMessage

from .llm import create_llm, load_image_b64

logger = logging.getLogger(__name__)

# ── プロンプト ────────────────────────────────────────────────
_OCR_SYSTEM = """\
You are a precise LaTeX transcription assistant.
Your task is to faithfully transcribe the mathematical expressions and text
visible in the provided image(s) into clean LaTeX source.

Rules:
- Output ONLY the LaTeX body (no \\documentclass, no \\begin{document}).
- Preserve the original structure: equations, text blocks, numbering.
- Use standard AMS-LaTeX packages (amsmath, amssymb) for math.
- Do NOT add any explanation or commentary—pure LaTeX only.
"""


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

    llm = create_llm()
    message = _build_ocr_message(image_paths, prompt_hint)

    logger.info("Running OCR on %d image(s).", len(image_paths))
    response = llm.invoke([message])

    tex = response.content.strip()
    logger.debug("OCR result (%d chars).", len(tex))
    return tex
