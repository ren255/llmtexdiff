

backend/app/
├── main.py
├── routers/
│   ├── sessions.py       # POST/GET/DELETE /api/sessions
│   ├── questions.py      # POST /api/sessions/{id}/question
│   └── files.py          # GET /api/files/{session_id}/{filename}
├── db/
│   ├── database.py       # engine, SessionLocal, get_db
│   ├── model.py          # Session, Question, Answer
│   └── init_db.py        # create_all
├── schemas/
│   └── session.py        # Pydantic models (SessionCreate, AnswerOut, etc.)
├── logic/
│   ├── llm.py            # LLM呼び出し → tex生成
│   ├── image.py          # base64 → ファイル保存（拡張子判定含む）
│   └── diff.py           # latexdiff処理
└── core/
    └── config.py         # DATA_DIR等の設定値

    エンドポイント一覧
Sessions
POST /api/sessions
新しいセッションを作成する

body: { title?: string }
response: Session object

GET /api/sessions
セッション一覧を取得する

response: Session[]（created_at降順）

GET /api/sessions/{session_id}
セッション詳細（Question・Answerも含む）を取得する

response: Session + Question + Answer（ネスト）

DELETE /api/sessions/{session_id}
セッションを削除する（cascade）

Questions & Answers（セッション配下）
POST /api/sessions/{session_id}/question
Questionを作成してLLMに投げ、Answerを生成・保存して返す
プロトタイプなので1Session=1Questionの制約はそのまま守る

body: { prompt: string, images?: base64[] }
response: { question: Question, answer: Answer }
処理: LLM呼び出し → tex_transcribed / tex_correct / diff_latex を生成してDB保存

GET /api/sessions/{session_id}/answer
既存のAnswerを取得する（再表示用）

response: Answer object

ファイル配信
GET /api/files/{session_id}/{filename}
data/sessions/{session_id}/ 以下のファイルを返す
PDFなど生成済みファイルの配信用

response: FileResponse