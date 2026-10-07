# Schema 总览 / 表字段字典
from fastapi import APIRouter, Depends

from .. import database
from ..deps import get_current_user

router = APIRouter(prefix="/schema", tags=["schema"])

TABLE_COMMENTS = {
    "employee": "员工主数据",
    "salary": "薪资（按月）",
    "attendance_summary": "考勤汇总（按月）",
    "performance": "绩效（按季度）",
}


@router.get("/overview")
def overview(user: dict = Depends(get_current_user)):
    conn = database.get_conn()
    try:
        tables = []
        for name, comment in TABLE_COMMENTS.items():
            cols = conn.execute(f"PRAGMA table_info({name})").fetchall()
            tables.append({
                "name": name,
                "comment": comment,
                "column_count": len(cols),
                "columns": [
                    {"name": c["name"], "type": c["type"],
                     "pk": bool(c["pk"]), "notnull": bool(c["notnull"]),
                     "default": c["dflt_value"]}
                    for c in cols
                ],
            })
        return {"tables": tables}
    finally:
        conn.close()
