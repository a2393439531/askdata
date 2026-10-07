# 权限：角色判定 + 数据范围 SQL 注入 + 白名单校验
import json
import re

# 问数允许查询的业务表（权限表默认不可被问数）
QUERYABLE_TABLES = ["employee", "salary", "attendance_summary", "performance"]

# 角色等级（数字越大权限越高）
ROLE_RANK = {"readonly": 1, "operator": 2, "admin": 3, "super_admin": 4}


def require_role(user: dict, min_role: str) -> bool:
    return ROLE_RANK.get(user["role"], 0) >= ROLE_RANK[min_role]


def user_allowed_tables(user: dict) -> list[str]:
    """用户可问的表：先取 QUERYABLE_TABLES，再与用户白名单取交集"""
    raw = user.get("allowed_tables")
    if raw:
        try:
            white = set(json.loads(raw))
        except Exception:
            white = set()
        return [t for t in QUERYABLE_TABLES if t in white]
    return list(QUERYABLE_TABLES)


def extract_tables(sql: str) -> set[str]:
    """从 SQL 中提取 FROM/JOIN 后的表名（小写）"""
    tables = set()
    for m in re.finditer(r"(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", sql, re.IGNORECASE):
        tables.add(m.group(1).lower())
    return tables


_DANGEROUS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|attach|detach"
    r"|vacuum|pragma|replace|merge|call|execute)\b",
    re.IGNORECASE,
)


def validate_select_sql(sql: str, allowed_tables: list[str]) -> tuple[bool, str]:
    """
    安全校验：只允许单条 SELECT。
    返回 (通过?, 原因)。
    """
    s = sql.strip().rstrip(";").strip()
    if not s:
        return False, "SQL 为空"
    # 去掉行注释与块注释后再检查
    no_comment = re.sub(r"--.*?$", "", s, flags=re.MULTILINE)
    no_comment = re.sub(r"/\*.*?\*/", "", no_comment, flags=re.DOTALL)
    if ";" in no_comment:
        return False, "只允许单条查询语句"
    if not re.match(r"(?is)^\s*(select|with)\b", no_comment):
        return False, "只允许 SELECT 查询"
    if _DANGEROUS.search(no_comment):
        return False, "检测到危险关键字，仅允许 SELECT 查询"
    tables = extract_tables(no_comment)
    if not tables:
        return False, "未能识别查询的表"
    bad = [t for t in tables if t not in allowed_tables]
    if bad:
        return False, f"无权查询表：{', '.join(bad)}"
    return True, ""


def _employee_alias(sql: str) -> str | None:
    """识别 employee 表的别名（无别名则返回表名本身）"""
    m = re.search(
        r"(?:from|join)\s+employee(?:\s+(?:as\s+)?([a-zA-Z_][a-zA-Z0-9_]*))?",
        sql,
        re.IGNORECASE,
    )
    if not m:
        return None
    alias = m.group(1)
    if alias and alias.lower() in ("where", "join", "on", "group", "order", "limit", "left", "right", "inner", "outer"):
        return "employee"
    return alias or "employee"


def apply_data_scope(sql: str, user: dict, user_dept: str | None, user_sub_dept: str | None) -> str:
    """
    按 data_scope 给 SQL 追加行级过滤。
    scope=all 直接返回；其余 scope 仅在 SQL 引用 employee 表时注入条件。
    注意：实现为朴素的字符串注入，适用于单层简单查询（本产品生成的 SQL 均为此形态），
    复杂嵌套 SQL 的作用域控制以后端白名单校验兜底。
    """
    scope = user.get("data_scope", "self_only")
    if scope == "all":
        return sql
    alias = _employee_alias(sql)
    if not alias:
        return sql  # 未引用 employee 表，无需注入

    if scope == "own_dept" and user_dept:
        cond = f"{alias}.department = '{user_dept}'"
    elif scope == "own_team" and user_sub_dept:
        cond = f"{alias}.sub_department = '{user_sub_dept}'"
    elif scope == "self_only" and user.get("employee_id"):
        cond = f"{alias}.id = {int(user['employee_id'])}"
    else:
        return sql

    # 在顶层 WHERE 后追加 AND；无 WHERE 则在 GROUP BY/ORDER BY/LIMIT 前插入 WHERE
    pattern_where = re.compile(r"\bwhere\b", re.IGNORECASE)
    m = pattern_where.search(sql)
    if m:
        return sql[: m.end()] + f" ({cond}) AND" + sql[m.end() :]
    pattern_clause = re.compile(r"\b(group\s+by|order\s+by|limit)\b", re.IGNORECASE)
    m2 = pattern_clause.search(sql)
    if m2:
        return sql[: m2.start()] + f" WHERE {cond} " + sql[m2.start() :]
    return sql.rstrip().rstrip(";") + f" WHERE {cond}"
