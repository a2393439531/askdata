# 问题模板：分组查询 / 执行 / 增删改（admin+）
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .. import database
from ..deps import client_ip, get_current_user, log_audit, scope_dept
from ..permissions import apply_data_scope, require_role, user_allowed_tables, validate_select_sql
from ..services import text2sql
from .chat import _execute_sql, _save_history

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateIn(BaseModel):
    group: str
    title: str
    question: str
    sql: str
    chart_type: str = "table"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@router.get("")
def list_templates(user: dict = Depends(get_current_user)):
    conn = database.get_conn()
    try:
        rows = conn.execute(
            "SELECT id, group_name, title, question, chart_type FROM question_template ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(r["group_name"], []).append(dict(r))
    return {"groups": [{"group": g, "items": items} for g, items in groups.items()]}


@router.post("/{tid}/execute")
def execute(tid: int, request: Request, user: dict = Depends(get_current_user)):
    conn = database.get_conn()
    try:
        tpl = conn.execute(
            "SELECT * FROM question_template WHERE id=?", (tid,)
        ).fetchone()
    finally:
        conn.close()
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    tpl = dict(tpl)

    allowed = user_allowed_tables(user)
    ok, reason = validate_select_sql(tpl["sql"], allowed)
    if not ok:
        raise HTTPException(status_code=403, detail=f"模板 SQL 未通过安全校验：{reason}")
    dept, sub_dept = scope_dept(user)
    sql = apply_data_scope(tpl["sql"], user, dept, sub_dept)

    try:
        columns, rows, elapsed = _execute_sql(sql, 2000)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"模板执行失败：{e}")
    interpretation = text2sql.build_interpretation(tpl["question"], columns, rows, len(rows))
    hid = _save_history(user["id"], tpl["question"], "template", sql, len(rows),
                        tpl["chart_type"], elapsed, "success")
    log_audit(user, "template_execute",
              f"模板：{tpl['title']}；行数：{len(rows)}",
              client_ip(request), elapsed, "成功")
    return {"id": hid, "question": tpl["question"], "sql": sql, "model": "template",
            "row_count": len(rows), "columns": columns, "rows": rows,
            "chart_type": tpl["chart_type"], "interpretation": interpretation,
            "elapsed_ms": elapsed, "status": "success", "via": "template",
            "is_favorite": False}


@router.post("")
def create(body: TemplateIn, request: Request, user: dict = Depends(get_current_user)):
    if not require_role(user, "admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    ok, reason = validate_select_sql(body.sql, user_allowed_tables(user))
    if not ok:
        raise HTTPException(status_code=400, detail=f"SQL 未通过安全校验：{reason}")
    conn = database.get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO question_template(group_name, title, question, sql, chart_type,
               created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)""",
            (body.group, body.title, body.question, body.sql.strip(),
             body.chart_type, user["id"], _now(), _now()),
        )
        conn.commit()
        tid = cur.lastrowid
    finally:
        conn.close()
    log_audit(user, "template_create", f"新增模板：{body.title}", client_ip(request), 0, "成功")
    return {"id": tid}


@router.put("/{tid}")
def update(tid: int, body: TemplateIn, request: Request,
           user: dict = Depends(get_current_user)):
    if not require_role(user, "admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    ok, reason = validate_select_sql(body.sql, user_allowed_tables(user))
    if not ok:
        raise HTTPException(status_code=400, detail=f"SQL 未通过安全校验：{reason}")
    conn = database.get_conn()
    try:
        row = conn.execute("SELECT id FROM question_template WHERE id=?", (tid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="模板不存在")
        conn.execute(
            """UPDATE question_template SET group_name=?, title=?, question=?, sql=?,
               chart_type=?, updated_at=? WHERE id=?""",
            (body.group, body.title, body.question, body.sql.strip(),
             body.chart_type, _now(), tid),
        )
        conn.commit()
    finally:
        conn.close()
    log_audit(user, "template_update", f"编辑模板 id={tid}：{body.title}",
              client_ip(request), 0, "成功")
    return {"ok": True}


@router.delete("/{tid}")
def delete(tid: int, request: Request, user: dict = Depends(get_current_user)):
    if not require_role(user, "admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    conn = database.get_conn()
    try:
        row = conn.execute("SELECT id FROM question_template WHERE id=?", (tid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="模板不存在")
        conn.execute("DELETE FROM question_template WHERE id=?", (tid,))
        conn.commit()
    finally:
        conn.close()
    log_audit(user, "template_delete", f"删除模板 id={tid}", client_ip(request), 0, "成功")
    return {"ok": True}
