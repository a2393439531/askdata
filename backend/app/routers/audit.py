# 审计日志查询（super_admin / admin）
from fastapi import APIRouter, Depends, HTTPException, Query

from .. import database
from ..deps import get_current_user
from ..permissions import require_role

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(username: str = Query("", description="按用户名筛选"),
               action: str = Query(""),
               page: int = Query(1, ge=1),
               page_size: int = Query(20, ge=1, le=100),
               user: dict = Depends(get_current_user)):
    if not require_role(user, "admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    where, params = [], []
    if username.strip():
        where.append("username LIKE ?")
        params.append(f"%{username.strip()}%")
    if action.strip():
        where.append("action = ?")
        params.append(action.strip())
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    conn = database.get_conn()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM audit_log{clause}", params).fetchone()[0]
        rows = conn.execute(
            f"""SELECT id, username, action, detail, ip, elapsed_ms, result, created_at
                FROM audit_log{clause} ORDER BY id DESC LIMIT ? OFFSET ?""",
            params + [page_size, (page - 1) * page_size],
        ).fetchall()
        return {"total": total, "items": [dict(r) for r in rows]}
    finally:
        conn.close()
