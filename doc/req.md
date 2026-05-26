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


project/
├── docker-compose.yml
├── .env
│
├── frontend/
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── index.css
│   │   ├── App.tsx
│   │   ├── routes/
│   │   │   ├── Home.tsx
│   │   │   └── Diff.tsx
│   │   ├── components/
│   │   │   ├── LatexRenderer.tsx
│   │   │   └── DiffViewer.tsx
│   │   └── lib/
│   │       └── katexConfig.ts
│   └── package.json
│
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── main.py
        ├── database.py
        ├── models.py
        └── routers/
            └── latex.py