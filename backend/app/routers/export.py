# CSV 导出：查询历史结果导出（UTF-8 BOM，Excel 直接打开）
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .. import database
from ..deps import client_ip, get_current_user, log_audit
from ..permissions import require_role

router = APIRouter(prefix="/export", tags=["export"])


class ExportIn(BaseModel):
    history_id: int


@router.post("/csv")
def export_csv(body: ExportIn, request: Request, user: dict = Depends(get_current_user)):
    conn = database.get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM query_history WHERE id=?", (body.history_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    row = dict(row)
    if row["user_id"] != user["id"] and not require_role(user, "super_admin"):
        raise HTTPException(status_code=403, detail="无权导出他人的查询结果")
    if row["status"] != "success":
        raise HTTPException(status_code=400, detail="该查询未成功，无数据可导出")

    conn = database.get_conn()
    try:
        # 重新执行 SQL 取全量（历史 rows 未持久化明细）
        cur = conn.execute(row["sql"])
        columns = [d[0] for d in cur.description] if cur.description else []
        data = cur.fetchall()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"导出执行失败：{e}")
    finally:
        conn.close()

    buf = io.StringIO()
    buf.write("\ufeff")  # BOM，Excel 直接识别 UTF-8
    writer = csv.writer(buf)
    writer.writerow(columns)
    writer.writerows(data)
    content = buf.getvalue().encode("utf-8")

    log_audit(user, "export_csv",
              f"导出历史 id={body.history_id}，{len(data)} 行",
              client_ip(request), 0, "成功")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=query_{body.history_id}.csv"},
    )
