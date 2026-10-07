# 登录 / 登出 / 当前用户
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .. import auth, database
from ..deps import client_ip, get_current_user, log_audit

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginIn, request: Request):
    conn = database.get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username=?", (body.username.strip(),)
        ).fetchone()
    finally:
        conn.close()
    ip = client_ip(request)
    if not row or not auth.verify_password(body.password, row["salt"], row["password_hash"]):
        log_audit(None, "login", f"用户名：{body.username}", ip, 0, "失败")
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    user = dict(row)
    if not user["is_active"]:
        log_audit(user, "login", "账号已禁用", ip, 0, "失败")
        raise HTTPException(status_code=403, detail="账号已禁用")
    token = auth.create_token(user["id"], user["username"])
    log_audit(user, "login", "登录成功", ip, 0, "成功")
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "data_scope": user["data_scope"],
            "employee_id": user["employee_id"],
            "is_active": bool(user["is_active"]),
        },
    }


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "data_scope": user["data_scope"],
        "employee_id": user["employee_id"],
        "is_active": bool(user["is_active"]),
    }


@router.post("/logout")
def logout(request: Request, user: dict = Depends(get_current_user)):
    log_audit(user, "logout", "登出", client_ip(request), 0, "成功")
    return {"ok": True}
