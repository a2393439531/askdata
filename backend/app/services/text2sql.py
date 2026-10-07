# Text-to-SQL 服务：大模型生成 SQL（OpenAI 兼容接口）+ 安全校验 + 无 Key 降级
import json
import re
import time
import urllib.request

from .. import config
from ..permissions import apply_data_scope, extract_tables, validate_select_sql

# 数据意图关键词：问题命中任一才允许走 SQL 生成，否则视为无关问题
INTENT_KEYWORDS = [
    "员工", "部门", "人数", "多少人", "薪资", "薪酬", "工资", "平均",
    "统计", "分布", "占比", "排名", "绩效", "kpi", "考勤", "加班",
    "请假", "迟到", "离职", "风险", "学历", "年龄", "性别", "职级",
    "岗位", "入职", "名单", "列表", "最高", "最低", "总数", "合计",
]

SCHEMA_DESC = """
表 employee（员工）: id, name, gender, birth_year, department, sub_department,
  position, level, manager_id, hire_date, education, phone, email
表 salary（薪资）: id, emp_id, year, month, base_pay, bonus, gross_pay
表 attendance_summary（考勤）: id, emp_id, year, month, work_days,
  overtime_hours, leave_days, late_count
表 performance（绩效）: id, emp_id, year, quarter, kpi_score, rating
关联：salary.emp_id=employee.id，attendance_summary.emp_id=employee.id，
  performance.emp_id=employee.id，employee.manager_id=employee.id
""".strip()

SYSTEM_PROMPT = """你是 HR 数据问答助手。根据用户中文问题和下面的数据库结构，
生成一条 SQLite 可执行的 SELECT 查询语句。

数据库结构：
{schema}

规则（必须严格遵守）：
1. 只输出一条 SELECT 语句，不要输出解释、前缀、markdown 代码块之外的任何文字。
2. 只能查询上述四张表，禁止查询其他表。
3. 聚合统计必须带 GROUP BY；需要排序时加 ORDER BY；默认 LIMIT 200。
4. 中文问题里的时间词（如"近12个月"）用 SQLite 日期函数表达。
5. 表别名使用 e(employee)、s(salary)、a(attendance_summary)、p(performance)。
"""


def has_data_intent(question: str) -> bool:
    return any(k in question for k in INTENT_KEYWORDS)


def _extract_sql(text: str) -> str:
    """从模型回复中提取 SQL（去 markdown fence）"""
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text.strip()


def _call_llm(model_key: str, question: str) -> str:
    """调用 OpenAI 兼容接口，返回原始文本"""
    cfg = config.LLM_CONFIG[model_key]
    body = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.format(schema=SCHEMA_DESC)},
            {"role": "user", "content": question},
        ],
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        cfg["base_url"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def model_configured(model_key: str) -> bool:
    return bool(config.LLM_CONFIG.get(model_key, {}).get("api_key"))


def match_template(question: str, templates: list[dict]) -> dict | None:
    """无 Key 降级：问题与模板 question 做包含/相似度匹配"""
    import difflib

    q = question.strip()
    for t in templates:
        tq = (t.get("question") or "").strip()
        if tq and (tq in q or q in tq):
            return t
    # 相似度兜底：防止"按月份统计"误命中"按职级统计"这类形近句
    best, best_ratio = None, 0.0
    for t in templates:
        tq = (t.get("question") or "").strip()
        if not tq:
            continue
        ratio = difflib.SequenceMatcher(None, q, tq).ratio()
        if ratio > best_ratio:
            best, best_ratio = t, ratio
    return best if best_ratio >= 0.55 else None


def detect_chart_type(question: str, sql: str, columns: list[str]) -> str:
    q = question
    s = sql.lower()
    if any(k in q for k in ["趋势", "每月", "近", "时间", "月份"]) or "month_label" in s or "quarter" in s:
        return "line"
    if any(k in q for k in ["占比", "分布", "比例"]) and "group by" in s:
        return "pie"
    if "group by" in s or "count(" in s or "avg(" in s or "sum(" in s:
        return "bar"
    return "table"


def build_interpretation(question: str, columns: list[str], rows: list, row_count: int) -> str:
    if row_count == 0:
        return "查询成功，但没有符合条件的数据。"
    if len(columns) >= 2:
        try:
            vals = [float(r[1]) for r in rows if r[1] is not None]
            if vals:
                return f"共 {row_count} 行；{columns[1]}最高 {max(vals):,.2f}，最低 {min(vals):,.2f}。"
        except (ValueError, TypeError, IndexError):
            pass
    return f"共查到 {row_count} 行数据。"


def generate(
    question: str,
    user: dict,
    allowed_tables: list[str],
    templates: list[dict],
    model_key: str = "deepseek",
    user_dept: str | None = None,
    user_sub_dept: str | None = None,
) -> dict:
    """
    问数主流程，返回 dict：
    {ok, sql, chart_type, error, via: 'llm'|'template'|'rejected'}
    """
    t0 = time.time()
    if not has_data_intent(question):
        return {
            "ok": False,
            "sql": None,
            "chart_type": "table",
            "via": "rejected",
            "error": "抱歉，我只能回答与人力数据相关的问题（如人数、薪酬、绩效、考勤等），请换个问法试试。",
            "elapsed_ms": int((time.time() - t0) * 1000),
        }

    via, sql, chart_type, error = "template", None, "table", None
    if model_configured(model_key):
        try:
            raw = _call_llm(model_key, question)
            sql = _extract_sql(raw)
            via = "llm"
        except Exception as e:  # noqa: BLE001 - 降级为模板匹配
            error = f"大模型调用失败：{e}，已尝试用问题模板匹配。"
            sql = None

    if not sql:
        tpl = match_template(question, templates)
        if tpl:
            sql = tpl["sql"]
            chart_type = tpl.get("chart_type") or "table"
            via = "template"
        else:
            return {
                "ok": False,
                "sql": None,
                "chart_type": "table",
                "via": "template",
                "error": (error + " " if error else "")
                + "当前未配置大模型 Key，且没有命中任何问题模板。建议：① 在设置中配置 DeepSeek/Qwen 的 API Key；② 或点击下方快捷模板直接查询。",
                "elapsed_ms": int((time.time() - t0) * 1000),
            }

    # 安全校验 + 作用域注入
    ok, reason = validate_select_sql(sql, allowed_tables)
    if not ok:
        return {
            "ok": False, "sql": sql, "chart_type": "table", "via": via,
            "error": f"SQL 安全校验未通过：{reason}",
            "elapsed_ms": int((time.time() - t0) * 1000),
        }
    sql = apply_data_scope(sql, user, user_dept, user_sub_dept)
    return {
        "ok": True, "sql": sql, "chart_type": chart_type, "via": via, "error": error,
        "elapsed_ms": int((time.time() - t0) * 1000),
    }
