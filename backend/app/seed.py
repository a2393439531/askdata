# 演示数据灌入：员工/薪资/考勤/绩效/模板/账号（确定性随机，可重复执行）
import random
from datetime import datetime

from . import auth, database

SURNAMES = ["王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴", "徐", "孙", "马", "朱", "胡"]
GIVENS = ["伟", "芳", "娜", "敏", "静", "磊", "洋", "艳", "勇", "杰", "涛", "明", "超", "雪", "晨"]
DEPTS = {
    "销售部": ["销售一组", "销售二组"],
    "技术部": ["研发组", "测试组", "运维组"],
    "人事部": ["招聘组", "薪酬组"],
    "财务部": ["会计组"],
    "市场部": ["推广组"],
}
LEVELS = ["P2", "P3", "P4", "P5", "P6", "P7", "P8", "M1", "M2", "M3"]
LEVEL_BASE = {"P2": 11000, "P3": 14000, "P4": 16500, "P5": 20000, "P6": 21000,
              "P7": 29000, "P8": 36000, "M1": 32000, "M2": 40000, "M3": 50000}
EDUS = ["大专", "本科", "硕士", "博士"]

TEMPLATES = [
    ("组织概览", "各部门员工数量", "各部门有多少员工？",
     "SELECT department, COUNT(*) AS emp_count FROM employee WHERE work_status='在职' GROUP BY department ORDER BY emp_count DESC",
     "bar"),
    ("薪酬分析", "按职级薪酬分布", "按职级统计平均薪酬",
     "SELECT e.level AS level, ROUND(AVG(s.gross_pay),2) AS avg_gross_pay, "
     "ROUND(MIN(s.gross_pay),2) AS min_gross_pay, ROUND(MAX(s.gross_pay),2) AS max_gross_pay, "
     "COUNT(DISTINCT e.id) AS emp_count FROM salary s JOIN employee e ON s.emp_id=e.id "
     "GROUP BY e.level ORDER BY avg_gross_pay DESC",
     "bar"),
    ("人员画像", "学历分布占比", "员工学历分布占比",
     "SELECT education, COUNT(*) AS emp_count FROM employee WHERE work_status='在职' GROUP BY education ORDER BY emp_count DESC",
     "pie"),
    ("风险监控", "离职风险预警", "离职风险较高的员工列表",
     "SELECT e.name, e.department, e.level, ROUND(AVG(p.kpi_score),1) AS avg_kpi, "
     "ROUND(SUM(a.overtime_hours),1) AS total_overtime FROM employee e "
     "LEFT JOIN performance p ON p.emp_id=e.id LEFT JOIN attendance_summary a ON a.emp_id=e.id "
     "WHERE e.work_status='在职' GROUP BY e.id HAVING avg_kpi < 75 OR total_overtime > 120 "
     "ORDER BY avg_kpi ASC LIMIT 50",
     "table"),
    ("绩效分析", "各部门绩效排名", "按部门统计平均 KPI 得分排名",
     "SELECT e.department AS department, ROUND(AVG(p.kpi_score),2) AS avg_kpi, "
     "COUNT(DISTINCT e.id) AS emp_count FROM performance p JOIN employee e ON p.emp_id=e.id "
     "GROUP BY e.department ORDER BY avg_kpi DESC",
     "bar"),
]

SEED_USERS = [
    # username, password, role, data_scope, department
    ("superadmin", "Admin@2024", "super_admin", "all", None),
    ("hradmin", "Admin@2024", "admin", "own_dept", "人事部"),
    ("techadmin", "Admin@2024", "admin", "own_dept", "技术部"),
    ("operator01", "Admin@2024", "operator", "own_team", "技术部"),
    ("auditor", "Admin@2024", "readonly", "self_only", None),
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def seed() -> None:
    database.init_db()
    conn = database.get_conn()
    try:
        cur = conn.cursor()
        # 已有数据则跳过（幂等）
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] > 0:
            print("数据库已有数据，跳过灌入。")
            return

        rnd = random.Random(42)
        now = _now()
        emp_ids: list[int] = []

        # ---- 员工 60 人 ----
        for i in range(60):
            dept = rnd.choice(list(DEPTS.keys()))
            sub = rnd.choice(DEPTS[dept])
            level = rnd.choices(LEVELS, weights=[8, 12, 14, 16, 12, 8, 4, 8, 6, 4])[0]
            name = rnd.choice(SURNAMES) + rnd.choice(GIVENS) + (rnd.choice(GIVENS) if rnd.random() < 0.4 else "")
            manager_id = rnd.choice(emp_ids) if emp_ids and rnd.random() < 0.7 else None
            cur.execute(
                """INSERT INTO employee(name, gender, birth_year, department, sub_department,
                   position, level, manager_id, hire_date, education, phone, email,
                   work_status, contract_type, entry_channel, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name, rnd.choice(["男", "女"]), rnd.randint(1975, 2000), dept, sub,
                 rnd.choice(["专员", "高级专员", "主管", "经理", "总监"]), level, manager_id,
                 f"{rnd.randint(2015, 2025)}-{rnd.randint(1, 12):02d}-01",
                 rnd.choices(EDUS, weights=[15, 55, 25, 5])[0],
                 f"138{rnd.randint(10000000, 99999999)}", f"user{i}@example.com",
                 "在职", "正式", rnd.choice(["社招", "校招", "内推"]), now),
            )
            emp_ids.append(cur.lastrowid)

        # ---- 薪资：近 12 个月（2025-10 ~ 2026-09）----
        months = [(2025, m) for m in range(10, 13)] + [(2026, m) for m in range(1, 10)]
        for eid in emp_ids:
            cur.execute("SELECT level FROM employee WHERE id=?", (eid,))
            base = LEVEL_BASE[cur.fetchone()[0]]
            for y, m in months:
                base_pay = round(base * rnd.uniform(0.95, 1.05), 2)
                bonus = round(base * rnd.uniform(0, 0.4), 2)
                cur.execute(
                    "INSERT INTO salary(emp_id, year, month, base_pay, bonus, gross_pay) VALUES (?,?,?,?,?,?)",
                    (eid, y, m, base_pay, bonus, round(base_pay + bonus, 2)),
                )

        # ---- 考勤汇总 ----
        for eid in emp_ids:
            for y, m in months:
                cur.execute(
                    """INSERT INTO attendance_summary(emp_id, year, month, work_days,
                       overtime_hours, leave_days, late_count) VALUES (?,?,?,?,?,?,?)""",
                    (eid, y, m, rnd.randint(20, 23), round(rnd.uniform(0, 40), 1),
                     round(rnd.uniform(0, 3), 1), rnd.randint(0, 3)),
                )

        # ---- 绩效（2025Q4 ~ 2026Q3）----
        for eid in emp_ids:
            for y, q in [(2025, 4), (2026, 1), (2026, 2), (2026, 3)]:
                score = round(rnd.uniform(60, 98), 1)
                rating = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D"
                cur.execute(
                    "INSERT INTO performance(emp_id, year, quarter, kpi_score, rating) VALUES (?,?,?,?,?)",
                    (eid, y, q, score, rating),
                )

        # ---- 账号（先插用户，模板的 created_by 依赖 users.id）----
        for username, pwd, role, scope, dept in SEED_USERS:
            h, salt = auth.hash_password(pwd)
            emp_id = None
            if scope == "self_only":
                emp_id = emp_ids[0]
            elif scope == "own_team":
                cur.execute("SELECT id FROM employee WHERE sub_department='研发组' LIMIT 1")
                row = cur.fetchone()
                emp_id = row[0] if row else None
            cur.execute(
                """INSERT INTO users(username, password_hash, salt, role, data_scope,
                   employee_id, is_active, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,1,?,?)""",
                (username, h, salt, role, scope, emp_id, now, now),
            )

        # ---- 问题模板 ----
        for group, title, question, sql, chart in TEMPLATES:
            cur.execute(
                """INSERT INTO question_template(group_name, title, question, sql, chart_type,
                   created_by, created_at, updated_at) VALUES (?,?,?,?,?,1,?,?)""",
                (group, title, question, sql, chart, now, now),
            )

        # admin 账号的部门归属（登录后按用户名映射到部门，见 USER_DEPT_MAP）
        conn.commit()
        print(f"灌入完成：员工 {len(emp_ids)} 人，账号 {len(SEED_USERS)} 个，模板 {len(TEMPLATES)} 个。")
    finally:
        conn.close()


# 用户名 -> 部门（own_dept / own_team 解析用）
USER_DEPT_MAP = {"hradmin": "人事部", "techadmin": "技术部", "operator01": "技术部"}
USER_SUB_DEPT_MAP = {"operator01": "研发组"}


if __name__ == "__main__":
    seed()
