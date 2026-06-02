webサイト作成。

要件:

* docker compose ベース
* latex renderが必須
- 学習サイト系でただLLMの出力を描画できればいい
- プロトタイプ。
- ただし、"https://3142.nl/latex-diff/"系列のlatex render diffの描画なども必要だ。

案件:
- react (ts)+ vite(react route) + tailwindv4 + daisyUI 
- FastAPI + sqlalchemy + sqlite

> tree backend
backend
├── app
│   ├── db
│   │   ├── database.py
│   │   ├── file_manager.py
│   │   ├── init_db.py
│   │   ├── __init__.py
│   │   ├── model.py
│   │   └── __pycache__
│   │       ├── database.cpython-314.pyc
│   │       ├── file_manager.cpython-314.pyc
│   │       ├── __init__.cpython-314.pyc
│   │       ├── init_db.cpython-314.pyc
│   │       └── model.cpython-314.pyc
│   ├── logic
│   │   └── llm.py
│   ├── main.py
│   ├── __pycache__
│   │   ├── database.cpython-312.pyc
│   │   └── main.cpython-312.pyc
│   ├── routers
│   │   └── latex.py
│   └── sample
│       ├── db_run.py
│       ├── file_run.py
│       ├── __init__.py
│       ├── llm.py
│       ├── ocr.py
│       ├── __pycache__
│       │   ├── db_run.cpython-314.pyc
│       │   ├── file_run.cpython-314.pyc
│       │   ├── __init__.cpython-314.pyc
│       │   ├── llm.cpython-314.pyc
│       │   ├── ocr.cpython-314.pyc
│       │   └── tex_pdf.cpython-314.pyc
│       └── tex_pdf.py
├── data
│   ├── app.db
│   └── sessions
│       ├── 3ec9ff67-fb43-43e7-9350-b0f23fa25cea
│       │   └── transcribed.pdf
│       └── sample
│           ├── image.png
│           └── images
├── Dockerfile
└── requirements.txt
