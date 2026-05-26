# セットアップ手順書

## ディレクトリ構成

```
project/
├── frontend/
├── backend/
├── .env
└── docker-compose.yml
```

---

## 1. プロジェクト初期化

```bash
mkdir project && cd project
```

---

## 2. Frontend — React + Vite + Tailwind v4 + daisyUI

### 2-1. Vite プロジェクト作成

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

### 2-2. React Router

```bash
npm install react-router
```

### 2-3. Tailwind CSS v4

```bash
npm install tailwindcss @tailwindcss/vite
```

**編集: `frontend/vite.config.ts`**
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
})
```

**編集: `frontend/src/index.css`**（全内容を置換）
```css
@import "tailwindcss";
```

### 2-4. daisyUI

```bash
npm install daisyui
```

**編集: `frontend/src/index.css`**
```css
@import "tailwindcss";
@plugin "daisyui";
```

### 2-5. LaTeX レンダリング

```bash
# KaTeX（軽量・高速）
npm install katex react-katex
npm install -D @types/katex

# latex-diff 描画用（差分ハイライト）
# latex-diff 自体は Python 側で処理し、フロントは差分済みソースを受け取る
# または latexdiff-wasm を使う場合:
npm install @matejmazur/react-katex
```

> **方針:** `latex-diff` の出力（`\DIFadd{}`/`\DIFdel{}` マクロ付き LaTeX）を
> バックエンドで生成し、フロント側は KaTeX カスタムマクロで色分けレンダリングする。

**編集: `frontend/src/lib/katexConfig.ts`**（新規作成）
```ts
export const KATEX_MACROS = {
  "\\DIFadd": "\\textcolor{green}{#1}",
  "\\DIFdel": "\\textcolor{red}{\\sout{#1}}",
}
```

---

## 3. Backend — FastAPI + SQLAlchemy + SQLite

### 3-1. ディレクトリ作成

```bash
cd ../
mkdir -p backend/app
```

### 3-2. `backend/requirements.txt`（新規作成）

```
fastapi>=0.115
uvicorn[standard]>=0.30
sqlalchemy>=2.0
alembic>=1.13
python-dotenv>=1.0
latexdiff          # latex-diff CLI ラッパー（または subprocess で直接呼ぶ）
```

### 3-3. `backend/app/main.py`（新規作成）

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}
```

### 3-4. `backend/app/database.py`（新規作成）

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass
```

### 3-5. `backend/Dockerfile`（新規作成）

```dockerfile
FROM python:3.12-slim

# latexdiff は texlive に同梱
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-extra-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

---

## 4. .env（プロジェクトルートに新規作成）

```env
DATABASE_URL=sqlite:///./data/app.db
```

---

## 5. docker-compose.yml（プロジェクトルートに新規作成）

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./backend/data:/app/data
    env_file:
      - .env
    restart: unless-stopped

  frontend:
    image: node:22-alpine
    working_dir: /app
    volumes:
      - ./frontend:/app
    ports:
      - "5173:5173"
    command: sh -c "npm install && npm run dev -- --host"
    environment:
      - VITE_API_URL=http://localhost:8000
    restart: unless-stopped
```

---

## 6. 起動

```bash
# プロジェクトルートで
docker compose up --build
```

| サービス | URL |
|---|---|
| Frontend (Vite) | http://localhost:5173 |
| Backend (FastAPI) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

## 7. latex-diff エンドポイント追加方針

`latexdiff` コマンドは `texlive-extra-utils` に含まれる。

**`backend/app/routers/latex.py`（スケルトン）**
```python
import subprocess, tempfile, os
from fastapi import APIRouter

router = APIRouter(prefix="/latex")

@router.post("/diff")
def latex_diff(old: str, new: str):
    with tempfile.NamedTemporaryFile("w", suffix=".tex", delete=False) as f1, \
         tempfile.NamedTemporaryFile("w", suffix=".tex", delete=False) as f2:
        f1.write(old); f2.write(new)
        f1_path, f2_path = f1.name, f2.name

    result = subprocess.run(
        ["latexdiff", f1_path, f2_path],
        capture_output=True, text=True
    )
    os.unlink(f1_path); os.unlink(f2_path)
    return {"diff": result.stdout}
```

フロント側は受け取った diff LaTeX 文字列を KaTeX + `\DIFadd`/`\DIFdel` マクロで描画する。

---

## 技術スタック一覧

| レイヤー | 技術 | バージョン目安 |
|---|---|---|
| Frontend フレームワーク | React | 19 |
| ビルドツール | Vite | 6 |
| ルーティング | React Router | 7 |
| スタイリング | Tailwind CSS | v4 |
| UI コンポーネント | daisyUI | 5 |
| LaTeX レンダリング | KaTeX | 0.16 |
| Backend フレームワーク | FastAPI | 0.115 |
| ORM | SQLAlchemy | 2.0 |
| DB | SQLite | — |
| LaTeX diff | latexdiff (texlive) | — |
| コンテナ | Docker Compose | v2 |