# askdata 后端入口：FastAPI 应用装配
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import database, seed
from .routers import audit, auth, chat, export, models, schema, templates, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时建表 + 无数据则灌入演示数据
    database.init_db()
    conn = database.get_conn()
    try:
        empty = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    finally:
        conn.close()
    if empty:
        seed.seed()
    yield


app = FastAPI(title="askdata API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, chat.router, schema.router, templates.router,
          users.router, audit.router, export.router, models.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True, "app": "askdata"}
