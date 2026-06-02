import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Session(Base):
    """
    ユーザーの一連の作業単位。
    1 Session = 1 Question + 1 Answer（プロトタイプ制約）。
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # 1:1 (cascade で Session 削除時に子も消える)
    question: Mapped[Optional["Question"]] = relationship(
        "Question",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id!r} title={self.title!r}>"


class Question(Base):
    """
    ユーザーが投げる問い。
    - prompt : テキスト部分
    - image_paths : data/ 以下の相対パスのリスト
                    例: ["sessions/{id}/images/0.png", "sessions/{id}/images/1.png"]
    """

    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON 配列: 画像ファイルの相対パス（data/ 起点）
    image_paths: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["Session"] = relationship("Session", back_populates="question")
    answer: Mapped[Optional["Answer"]] = relationship(
        "Answer", back_populates="question", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Question id={self.id!r} session_id={self.session_id!r}>"


class Answer(Base):
    """
    LLM が生成する回答。
    - tex_transcribed : 画像から書き起こした .tex テキスト
    - tex_correct     : 正解の .tex テキスト
    - diff_latex      : latexdiff の出力（\\DIFadd / \\DIFdel マクロ付き）
                        KaTeX でのブラウザ描画にも使い回す
    - *_path          : data/ 以下の相対パス
                        例: "sessions/{id}/transcribed.pdf"
    """

    __tablename__ = "answers"
    __table_args__ = (
        # question との 1:1 を DB レベルで保証
        UniqueConstraint("question_id", name="uq_answers_question_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )

    # --- LaTeX テキスト本体（短いのでDB直保存） ---
    tex_transcribed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # OCR
    tex_correct: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 答え
    diff_latex: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # 直接LLMで差分込み

    # --- 生成ファイルの相対パス（data/ 起点） ---
    pdf_transcribed_path: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )
    pdf_correct_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    pdf_diff_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    question: Mapped["Question"] = relationship("Question", back_populates="answer")

    def __repr__(self) -> str:
        return f"<Answer id={self.id!r} question_id={self.question_id!r}>"
