# 自然语言问数：提问 / 历史 / 收藏 / 重问 / 删除
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .. import database
from ..deps import client_ip, get_current_user, log_audit, scope_dept
from ..permissions import user_allowed_tables
from ..services import text2sql

router = APIRouter(prefix="/chat", tags=["chat"])

MAX_LIMIT = 2000


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    model: str = "deepseek"
    chart: str = "auto"  # auto/bar/line/pie/table
    limit: int = 200


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_templates() -> list[dict]:
    conn = database.get_conn()
    try:
        rows = conn.execute(
            "SELECT id, group_name, title, question, sql, chart_type FROM question_template ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _execute_sql(sql: str, limit: int) -> tuple[list[str], list[list], int]:
    """执行 SELECT，返回 (列名, 行, 耗时ms)"""
    conn = database.get_conn()
    try:
        t0 = time.time()
        # 强制 LIMIT 上限，防止大结果集
        limited = sql.rstrip().rstrip(";")
        if "limit" not in limited.lower():
            limited += f" LIMIT {min(limit, MAX_LIMIT)}"
        cur = conn.execute(limited)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = [list(r) for r in cur.fetchall()]
        elapsed = int((time.time() - t0) * 1000)
        return columns, rows, elapsed
    finally:
        conn.close()


def _save_history(user_id: int, question: str, model: str, sql: str | None,
                 row_count: int, chart_type: str, elapsed_ms: int,
                 status: str, error_msg: str = "") -> int:
    conn = database.get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO query_history(user_id, question, model, sql, row_count,
               chart_type, elapsed_ms, status, error_msg, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (user_id, question, model, sql, row_count, chart_type,
             elapsed_ms, status, error_msg, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _run_ask(user: dict, question: str, model: str, chart: str, limit: int,
             request: Request) -> dict:
    t0 = time.time()
    allowed = user_allowed_tables(user)
    dept, sub_dept = scope_dept(user)
    templates = _load_templates()

    gen = text2sql.generate(question, user, allowed, templates, model, dept, sub_dept)
    elapsed = int((time.time() - t0) * 1000)

    if not gen["ok"]:
        hid = _save_history(user["id"], question, model, gen["sql"], 0,
                            gen["chart_type"], elapsed, "error", gen["error"])
        log_audit(user, "chat", f"问题：{question}；失败：{gen['error']}",
                  client_ip(request), elapsed, "失败")
        return {"id": hid, "question": question, "sql": gen["sql"], "model": model,
                "row_count": 0, "columns": [], "rows": [],
                "chart_type": gen["chart_type"], "interpretation": "",
                "elapsed_ms": elapsed, "status": "error", "error": gen["error"],
                "via": gen["via"], "is_favorite": False}

    try:
        columns, rows, _ = _execute_sql(gen["sql"], limit)
    except Exception as e:  # noqa: BLE001
        err = f"SQL 执行失败：{e}"
        hid = _save_history(user["id"], question, model, gen["sql"], 0,
                            gen["chart_type"], elapsed, "error", err)
        log_audit(user, "chat", f"问题：{question}；{err}", client_ip(request), elapsed, "失败")
        return {"id": hid, "question": question, "sql": gen["sql"], "model": model,
                "row_count": 0, "columns": [], "rows": [],
                "chart_type": gen["chart_type"], "interpretation": "",
                "elapsed_ms": elapsed, "status": "error", "error": err, "via": gen["via"],
                "is_favorite": False}

    chart_type = chart if chart != "auto" else (
        gen["chart_type"] if gen["via"] == "template"
        else text2sql.detect_chart_type(question, gen["sql"], columns)
    )
    interpretation = text2sql.build_interpretation(question, columns, rows, len(rows))
    hid = _save_history(user["id"], question, model, gen["sql"], len(rows),
                        chart_type, elapsed, "success")
    log_audit(user, "chat", f"问题：{question}；行数：{len(rows)}",
              client_ip(request), elapsed, "成功")
    return {"id": hid, "question": question, "sql": gen["sql"], "model": model,
            "row_count": len(rows), "columns": columns, "rows": rows,
            "chart_type": chart_type, "interpretation": interpretation,
            "elapsed_ms": elapsed, "status": "success", "via": gen["via"],
            "is_favorite": False}


@router.post("/ask")
def ask(body: AskIn, request: Request, user: dict = Depends(get_current_user)):
    model = body.model if body.model in ("deepseek", "qwen") else "deepseek"
    return _run_ask(user, body.question.strip(), model, body.chart,
                    max(1, min(body.limit, MAX_LIMIT)), request)


@router.get("/history")
def history(favorite_only: bool = Query(False), limit: int = Query(50, le=200),
            user: dict = Depends(get_current_user)):
    conn = database.get_conn()
    try:
        sql = """SELECT id, question, model, row_count, chart_type, elapsed_ms,
                        status, is_favorite, created_at FROM query_history
                 WHERE user_id=?"""
        params: list = [user["id"]]
        if favorite_only:
            sql += " AND is_favorite=1"
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/history/{hid}/rerun")
def rerun(hid: int, request: Request, user: dict = Depends(get_current_user)):
    conn = database.get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM query_history WHERE id=? AND user_id=?", (hid, user["id"])
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return _run_ask(user, row["question"], row["model"] or "deepseek", "auto", 200, request)


@router.patch("/history/{hid}/favorite")
def favorite(hid: int, user: dict = Depends(get_current_user)):
    conn = database.get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM query_history WHERE id=? AND user_id=?", (hid, user["id"])
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="历史记录不存在")
        new_val = 0 if row["is_favorite"] else 1
        conn.execute("UPDATE query_history SET is_favorite=? WHERE id=?", (new_val, hid))
        conn.commit()
        return {"is_favorite": bool(new_val)}
    finally:
        conn.close()


@router.delete("/history/{hid}")
def delete_history(hid: int, request: Request, user: dict = Depends(get_current_user)):
    from ..permissions import require_role
    conn = database.get_conn()
    try:
        row = conn.execute("SELECT * FROM query_history WHERE id=?", (hid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="历史记录不存在")
        # super_admin 可删任意，普通用户只能删自己的
        if row["user_id"] != user["id"] and not require_role(user, "super_admin"):
            raise HTTPException(status_code=403, detail="无权删除他人的历史记录")
        conn.execute("DELETE FROM query_history WHERE id=?", (hid,))
        conn.commit()
    finally:
        conn.close()
    log_audit(user, "history_delete", f"删除历史记录 id={hid}", client_ip(request), 0, "成功")
    return {"ok": True}
