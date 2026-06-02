"""
File access manager.

All paths are relative to DATA_ROOT (data/).
External code never constructs absolute paths directly —
always go through this module.
"""

import os
import shutil
from pathlib import Path

DATA_ROOT = Path(os.getenv("DATA_ROOT", "data"))


def _abs(relative: str | Path) -> Path:
    """Resolve a DATA_ROOT-relative path to an absolute Path."""
    return DATA_ROOT / relative


def save(relative: str | Path, data: bytes) -> Path:
    """
    Save *data* at DATA_ROOT / relative.
    Parent directories are created automatically.
    Returns the absolute path.
    """
    dest = _abs(relative)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def load(relative: str | Path) -> bytes:
    """
    Load and return raw bytes from DATA_ROOT / relative.
    Raises FileNotFoundError if the file does not exist.
    """
    src = _abs(relative)
    if not src.exists():
        raise FileNotFoundError(f"File not found: {src}")
    return src.read_bytes()


def delete(relative: str | Path) -> None:
    """
    Delete the file at DATA_ROOT / relative.
    Raises FileNotFoundError if the file does not exist.
    """
    target = _abs(relative)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {target}")
    target.unlink()


def delete_dir(relative: str | Path) -> None:
    """
    Recursively delete a directory under DATA_ROOT.
    Raises FileNotFoundError if the directory does not exist.
    """
    target = _abs(relative)
    if not target.exists():
        raise FileNotFoundError(f"Directory not found: {target}")
    shutil.rmtree(target)


def exists(relative: str | Path) -> bool:
    """Return True if DATA_ROOT / relative exists."""
    return _abs(relative).exists()


def abs_path(relative: str | Path) -> Path:
    """Return the absolute Path for a DATA_ROOT-relative path."""
    return _abs(relative)


class FileManager:
    """
    PDF ファイルの保存・パス管理を担うクラス。
    pipeline.py から使用される。
    """

    def save_pdf(self, *, session_id: str, filename: str, data: bytes) -> str:
        """
        PDF バイト列を data/sessions/{session_id}/{filename} に保存し、
        data/ 起点の相対パスを返す。
        """
        relative = f"sessions/{session_id}/{filename}"
        save(relative, data)
        return relative

    def load_pdf(self, *, session_id: str, filename: str) -> bytes:
        """
        data/sessions/{session_id}/{filename} から PDF を読み込む。
        """
        relative = f"sessions/{session_id}/{filename}"
        return load(relative)

    def delete_pdf(self, *, session_id: str, filename: str) -> None:
        """
        data/sessions/{session_id}/{filename} を削除する。
        """
        relative = f"sessions/{session_id}/{filename}"
        delete(relative)
