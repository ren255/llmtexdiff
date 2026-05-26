"""
Usage:
    python -m app.sample.db_run
"""

from app.db.database import SessionLocal
from app.db.model import Answer, Question, Session


def create_sample(db) -> Session:
    session = Session(title="サンプルセッション")
    db.add(session)
    db.flush()  # session.id を確定

    question = Question(
        session_id=session.id,
        prompt="この数式を書き起こしてください。",
        image_paths=[
            f"sessions/{session.id}/images/0.png",
        ],
    )
    db.add(question)
    db.flush()

    answer = Answer(
        question_id=question.id,
        tex_transcribed=r"E = mc^2",
        tex_correct=r"E = mc^{2}",
        diff_latex=r"\DIFdel{mc^2}\DIFadd{mc^{2}}",
        pdf_transcribed_path=f"sessions/{session.id}/transcribed.pdf",
        pdf_correct_path=f"sessions/{session.id}/correct.pdf",
        pdf_diff_path=f"sessions/{session.id}/diff.pdf",
    )
    db.add(answer)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(db) -> None:
    sessions = db.query(Session).all()
    if not sessions:
        print("  (no sessions)")
        return
    for s in sessions:
        print(f"  Session  id={s.id}  title={s.title!r}  created={s.created_at}")
        q = s.question
        if q:
            print(f"    Question id={q.id}  prompt={q.prompt!r}")
            print(f"             images={q.image_paths}")
            a = q.answer
            if a:
                print(f"    Answer   id={a.id}")
                print(f"             tex_transcribed={a.tex_transcribed!r}")
                print(f"             tex_correct    ={a.tex_correct!r}")
                print(f"             diff_latex     ={a.diff_latex!r}")


def delete_session(db, session_id: str) -> None:
    s = db.get(Session, session_id)
    if s is None:
        print(f"  Session {session_id!r} not found.")
        return
    db.delete(s)
    db.commit()
    print(f"  Deleted session {session_id!r}")


def main() -> None:
    db = SessionLocal()
    try:
        # --- 追加 ---
        print("=== CREATE ===")
        s = create_sample(db)
        print(f"  Created session {s.id!r}")

        # --- 一覧 ---
        print("\n=== LIST ===")
        list_sessions(db)

        # --- 削除 ---
        print("\n=== DELETE ===")
        delete_session(db, s.id)

        # --- 削除後の一覧 ---
        print("\n=== LIST (after delete) ===")
        list_sessions(db)

    finally:
        db.close()


if __name__ == "__main__":
    main()
