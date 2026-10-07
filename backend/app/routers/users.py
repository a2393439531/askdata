# 用户管理（仅 super_admin）：增删改查 / 启用禁用
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .. import auth, database
from ..deps import client_ip, get_current_user, log_audit
from ..permissions import require_role

router = APIRouter(prefix="/users", tags=["users"])

VALID_ROLES = ("super_admin", "admin", "operator", "readonly")
VALID_SCOPES = ("all", "own_dept", "own_team", "self_only")


class UserIn(BaseModel):
    username: str
    password: str | None = None
    role: str = "readonly"
    data_scope: str = "self_only"
    employee_id: int | None = None
    allowed_tables: list[str] | None = None
    allowed_columns: dict | None = None
    is_active: bool = True


class StatusIn(BaseModel):
    is_active: bool


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _guard_admin(user: dict):
    if not require_role(user, "super_admin"):
        raise HTTPException(status_code=403, detail="需要超级管理员权限")


def _public(u: dict) -> dict:
    return {
        "id": u["id"], "username": u["username"], "role": u["role"],
        "data_scope": u["data_scope"], "employee_id": u["employee_id"],
        "allowed_tables": json.loads(u["allowed_tables"]) if u["allowed_tables"] else None,
        "allowed_columns": json.loads(u["allowed_columns"]) if u["allowed_columns"] else None,
        "is_active": bool(u["is_active"]), "created_at": u["created_at"],
    }


@router.get("")
def list_users(user: dict = Depends(get_current_user)):
    _guard_admin(user)
    conn = database.get_conn()
    try:
        rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        return [_public(dict(r)) for r in rows]
    finally:
        conn.close()


@router.post("")
def create_user(body: UserIn, request: Request, user: dict = Depends(get_current_user)):
    _guard_admin(user)
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="角色不合法")
    if body.data_scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail="数据范围不合法")
    if not body.password or len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    conn = database.get_conn()
    try:
        exists = conn.execute("SELECT id FROM users WHERE username=?",
                              (body.username.strip(),)).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="用户名已存在")
        h, salt = auth.hash_password(body.password)
        cur = conn.execute(
            """INSERT INTO users(username, password_hash, salt, role, data_scope,
               employee_id, allowed_tables, allowed_columns, is_active, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (body.username.strip(), h, salt, body.role, body.data_scope, body.employee_id,
             json.dumps(body.allowed_tables) if body.allowed_tables else None,
             json.dumps(body.allowed_columns) if body.allowed_columns else None,
             1 if body.is_active else 0, _now(), _now()),
        )
        conn.commit()
        uid = cur.lastrowid
    finally:
        conn.close()
    log_audit(user, "user_create", f"新增用户：{body.username}（{body.role}）",
              client_ip(request), 0, "成功")
    return {"id": uid}


@router.put("/{uid}")
def update_user(uid: int, body: UserIn, request: Request,
                user: dict = Depends(get_current_user)):
    _guard_admin(user)
    if body.role not in VALID_ROLES or body.data_scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail="角色或数据范围不合法")
    conn = database.get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        target = dict(row)
        # 保护：不能把自己从 super_admin 降级（至少保留一个的另一半由删除保护）
        if target["id"] == user["id"] and target["role"] == "super_admin" \
                and body.role != "super_admin":
            raise HTTPException(status_code=400, detail="不能降级自己的超级管理员角色")
        sets = ["role=?", "data_scope=?", "employee_id=?", "allowed_tables=?",
                "allowed_columns=?", "is_active=?", "updated_at=?"]
        params: list = [body.role, body.data_scope, body.employee_id,
                        json.dumps(body.allowed_tables) if body.allowed_tables else None,
                        json.dumps(body.allowed_columns) if body.allowed_columns else None,
                        1 if body.is_active else 0, _now()]
        if body.password:
            if len(body.password) < 6:
                raise HTTPException(status_code=400, detail="密码至少 6 位")
            h, salt = auth.hash_password(body.password)
            sets += ["password_hash=?", "salt=?"]
            params += [h, salt]
        params.append(uid)
        conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", params)
        conn.commit()
    finally:
        conn.close()
    log_audit(user, "user_update", f"编辑用户 id={uid}", client_ip(request), 0, "成功")
    return {"ok": True}


@router.patch("/{uid}/status")
def toggle_status(uid: int, body: StatusIn, request: Request,
                  user: dict = Depends(get_current_user)):
    _guard_admin(user)
    conn = database.get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        target = dict(row)
        if target["id"] == user["id"] and not body.is_active:
            raise HTTPException(status_code=400, detail="不能禁用自己")
        conn.execute("UPDATE users SET is_active=?, updated_at=? WHERE id=?",
                     (1 if body.is_active else 0, _now(), uid))
        conn.commit()
    finally:
        conn.close()
    log_audit(user, "user_status", f"用户 id={uid} 启用={body.is_active}",
              client_ip(request), 0, "成功")
    return {"ok": True}


@router.delete("/{uid}")
def delete_user(uid: int, request: Request, user: dict = Depends(get_current_user)):
    _guard_admin(user)
    conn = database.get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        target = dict(row)
        # 保护策略 1：不能删除自己
        if target["id"] == user["id"]:
            raise HTTPException(status_code=400, detail="不能删除自己")
        # 保护策略 2：至少保留 1 个启用的 super_admin
        if target["role"] == "super_admin":
            cnt = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role='super_admin' AND is_active=1 AND id!=?",
                (uid,)).fetchone()[0]
            if cnt < 1:
                raise HTTPException(status_code=400, detail="系统至少保留 1 个启用的超级管理员")
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
    finally:
        conn.close()
    log_audit(user, "user_delete", f"删除用户：{target['username']}",
              client_ip(request), 0, "成功")
    return {"ok": True}
