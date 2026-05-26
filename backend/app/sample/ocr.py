"""
sample/ocr_llm.py

./data/sample/image.png を Vision LLM に渡して書き起こすだけ。
- スキーマなし、StrOutputParser のみ
- with_retry() で 3 回リトライ
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# ── .env 読み込み ──────────────────────────────────────────────
load_dotenv()

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
IMAGE_PATH = Path("./data/sessions/sample/image.png")


# ── 画像を base64 エンコード ───────────────────────────────────
def load_image_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


# ── チェーン構築 ───────────────────────────────────────────────
def build_chain():
    llm = ChatOpenAI(
        model="google/gemini-2.5-flash-lite",  # vision 対応モデル
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0,
    )

    chain = (llm | StrOutputParser()).with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,
    )

    return chain


# ── エントリーポイント ─────────────────────────────────────────
if __name__ == "__main__":
    image_b64 = load_image_b64(IMAGE_PATH)

    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
            },
            {
                "type": "text",
                "text": "この画像に含まれるテキストをすべて書き起こしてください。",
            },
        ]
    )

    chain = build_chain()
    result: str = chain.invoke([message])

    print(result)
