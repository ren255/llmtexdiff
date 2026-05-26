from __future__ import annotations

import os
import time  # 応答時間を計測するために追加
from typing import Optional

from dotenv import load_dotenv
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# ── .env 読み込み ──────────────────────────────────────────────
load_dotenv()

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]


# ── Pydantic スキーマ ──────────────────────────────────────────
class AnswerSchema(BaseModel):
    """LLM の回答スキーマ"""

    answer: str = Field(description="回答本文")
    confidence: float = Field(
        description="回答の確信度 (0.0 〜 1.0)",
        ge=0.0,
        le=1.0,
    )


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


# ── 疎通確認用（シンプルに "hello" を送信） ────────────────────
def check_connection(llm):
    print("【1/2】" + "=" * 52)
    print("疎通確認: 'hello' を送信中...")
    print("=" * 60)

    start_time = time.time()
    # invokeに直接文字列を渡して、RAWテキストで応答を受け取る
    response = llm.invoke("hello")
    elapsed_time = time.time() - start_time

    print(f"応答: {response.content.strip()}")
    print(f"応答時間: {elapsed_time:.2f} 秒")
    print("=" * 60 + "\n")


# ── メインチェーン構築 ─────────────────────────────────────────
def build_chain(llm):
    parser = PydanticOutputParser(pydantic_object=AnswerSchema)

    prompt = PromptTemplate(
        template=(
            "あなたは数学・LaTeX の専門家です。\n"
            "以下の質問に日本語で答えてください。\n\n"
            "質問: {question}\n\n"
            "{format_instructions}\n\n"
            "必ず上記 JSON 形式のみで返答してください。"
        ),
        input_variables=["question"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # すでにリトライ設定済みの llm を結合
    chain = prompt | llm | parser
    return chain


# ── エントリーポイント ─────────────────────────────────────────
if __name__ == "__main__":
    # 共通のLLMインスタンスを作成
    llm = create_llm()

    # 1. 最初にシンプルな疎通確認を実行
    check_connection(llm)

    # 2. 本番の構造化リクエストを実行
    sample_question = "二次方程式 3*sqrt(x) = 4 の解の公式を教えてください。"

    print("【2/2】" + "=" * 52)
    print(f"構造化質問: {sample_question}")
    print("=" * 60)

    chain = build_chain(llm)

    start_time = time.time()
    answer: AnswerSchema = chain.invoke({"question": sample_question})
    elapsed_time = time.time() - start_time

    print("\n── 回答 ──────────────────────────────────────")
    print(f"answer     : {answer.answer}")
    print(f"confidence : {answer.confidence}")
    print(f"処理時間   : {elapsed_time:.2f} 秒")
    print("=" * 60)
