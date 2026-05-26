from __future__ import annotations

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pathlib import Path
import base64

# ── .env 読み込み ──────────────────────────────────────────────
load_dotenv()

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]


# ── LLM インスタンス生成 ────────────────────────────────────────
def create_llm():
    return ChatOpenAI(
        model="google/gemini-2.5-flash-lite",
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.7,
    ).with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,  # 指数バックオフ＋ジッター
    )


def load_image_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()
