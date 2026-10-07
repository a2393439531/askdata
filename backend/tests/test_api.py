# askdata 后端接口自测（pytest）
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

# 测试用独立数据库，避免污染开发库
os.environ["DB_PATH"] = "data/test_hr_insight.db"

from app import database, seed  # noqa: E402
from app.main import app  # noqa: E402

# 显式建库 + 灌入演示数据（TestClient 非上下文模式下不触发 lifespan）
_db_path = database.config.DB_PATH
if os.path.exists(_db_path):
    os.remove(_db_path)
database.init_db()
seed.seed()

from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)

ADMIN = {"username": "superadmin", "password": "Admin@2024"}


@pytest.fixture(scope="module")
def token():
    r = client.post("/api/auth/login", json=ADMIN)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_success(token):
    assert token and len(token) > 20


def test_login_fail():
    r = client.post("/api/auth/login", json={"username": "superadmin", "password": "wrong"})
    assert r.status_code == 401


def test_me(token):
    r = client.get("/api/auth/me", headers=_h(token))
    assert r.status_code == 200
    assert r.json()["username"] == "superadmin"


def test_ask_template_match(token):
    # 无 Key 时走模板匹配："各部门有多少员工？"命中模板
    r = client.post("/api/chat/ask", headers=_h(token),
                    json={"question": "各部门有多少员工？", "model": "deepseek"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "success", data
    assert data["via"] == "template"
    assert data["row_count"] == 5  # 5 个部门
    assert "department" in data["columns"]


def test_ask_reject_irrelevant(token):
    r = client.post("/api/chat/ask", headers=_h(token),
                    json={"question": "今天天气怎么样？", "model": "deepseek"})
    data = r.json()
    assert data["status"] == "error"
    assert "人力数据" in data["error"]


def test_ask_no_template_match(token):
    r = client.post("/api/chat/ask", headers=_h(token),
                    json={"question": "员工加班时长按月份统计一下", "model": "deepseek"})
    data = r.json()
    # 未配 Key 且模板未命中 → 友好提示
    assert data["status"] == "error"
    assert "模板" in data["error"] or "Key" in data["error"]


def test_template_execute(token):
    r = client.get("/api/templates", headers=_h(token))
    tid = r.json()["groups"][0]["items"][0]["id"]
    r = client.post(f"/api/templates/{tid}/execute", headers=_h(token))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "success"


def test_export_csv(token):
    # 先问一次拿到历史 id
    r = client.post("/api/chat/ask", headers=_h(token),
                    json={"question": "各部门有多少员工？", "model": "deepseek"})
    hid = r.json()["id"]
    r = client.post("/api/export/csv", headers=_h(token), json={"history_id": hid})
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    text = r.content.decode("utf-8-sig")
    assert "department" in text.splitlines()[0]


def test_audit_written(token):
    r = client.get("/api/audit?username=superadmin&action=chat",
                   headers=_h(token))
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_forbidden_for_operator():
    r = client.post("/api/auth/login",
                    json={"username": "operator01", "password": "Admin@2024"})
    tok = r.json()["access_token"]
    r = client.get("/api/users", headers=_h(tok))
    assert r.status_code == 403


def test_scope_filter_operator():
    # operator01 数据范围 own_team=研发组：问数结果应只含技术部研发组
    r = client.post("/api/auth/login",
                    json={"username": "operator01", "password": "Admin@2024"})
    tok = r.json()["access_token"]
    r = client.post("/api/chat/ask", headers=_h(tok),
                    json={"question": "各部门有多少员工？", "model": "deepseek"})
    data = r.json()
    assert data["status"] == "success"
    depts = {row[0] for row in data["rows"]}
    assert depts == {"技术部"}, depts


def test_user_self_delete_protected(token):
    me = client.get("/api/auth/me", headers=_h(token)).json()
    r = client.delete(f"/api/users/{me['id']}", headers=_h(token))
    assert r.status_code == 400
    assert "不能删除自己" in r.json()["detail"]
