# 依赖项：当前用户解析（JWT）+ 审计日志写入
from datetime import datetime

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import auth, database
from .seed import USER_DEPT_MAP, USER_SUB_DEPT_MAP

_bearer = HTTPBearer(auto_error=False)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if not creds:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = auth.decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    conn = database.get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE id=?", (int(payload["sub"]),)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="用户不存在")
    user = dict(row)
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="账号已禁用")
    # 请求对象上挂用户名，供审计使用
    request.state.username = user["username"]
    return user


def log_audit(
    user: dict | None,
    action: str,
    detail: str = "",
    ip: str = "",
    elapsed_ms: int = 0,
    result: str = "成功",
) -> None:
    conn = database.get_conn()
    try:
        conn.execute(
            """INSERT INTO audit_log(user_id, username, action, detail, ip,
               elapsed_ms, result, created_at) VALUES (?,?,?,?,?,?,?,?)""",
            (user["id"] if user else None, user["username"] if user else "",
             action, detail, ip, elapsed_ms, result, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def scope_dept(user: dict) -> tuple[str | None, str | None]:
    """返回 (部门, 二级部门)，用于 own_dept / own_team 解析"""
    username = user["username"]
    return USER_DEPT_MAP.get(username), USER_SUB_DEPT_MAP.get(username)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""
