"""
Usage:
    python -m db.init_db
"""

import os
from pathlib import Path

from .database import engine
from .model import Base

DB_PATH = Path(
    os.getenv("DATABASE_URL", "sqlite:///./data/app.db").replace("sqlite:///", "")
)


def init_db() -> None:
    # DB ファイルが存在する場合は削除
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Dropped: {DB_PATH}")

    # 親ディレクトリがなければ作成
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)
    print(f"Created: {DB_PATH}")
    print("Tables:", list(Base.metadata.tables.keys()))


if __name__ == "__main__":
    init_db()
