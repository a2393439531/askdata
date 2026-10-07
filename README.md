# askdata · 员工问数 AI 智能体

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Vue](https://img.shields.io/badge/Vue-3-42b883)
![FastAPI](https://img.shields.io/badge/FastAPI-009688)
![ECharts](https://img.shields.io/badge/ECharts-5-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

> 用中文直接问人力数据，AI 自动生成 SQL、执行并给出图表与一句话解读。
> 自然语言问数 / Text-to-SQL / 自动可视化 / 四角色权限 / 审计日志 / 问题模板 / CSV 导出。

---

## 一键启动

```bash
# 方式一：Docker（一键拉起前后端）
docker compose up -d --build
# 前端 http://localhost:3000，后端 http://localhost:8000

# 方式二：本地开发
cd backend && python3 -m venv .venv && source .venv/bin/activate \
  && pip install -r requirements.txt && cp .env.example .env \
  && uvicorn app.main:app --reload --port 8000
cd ../frontend && npm install && npm run dev   # http://localhost:5173
```

## 测试账号（密码均为 `Admin@2024`）

| 用户名 | 角色 | 数据范围 |
|---|---|---|
| superadmin | 超级管理员 | 全公司 |
| hradmin | 管理员（HR） | 本部门 |
| techadmin | 管理员（技术） | 本部门 |
| operator01 | 操作员 | 本团队 |
| auditor | 只读审计 | 仅本人 |

## 大模型 Key 配置（可选）

不配置也能跑：问数走"问题模板匹配"降级，模板/字典/历史/审计全部可用。
要启用 AI 自由问数，在 `backend/.env` 中填写（OpenAI 兼容接口）：

```bash
LLM_DEEPSEEK_API_KEY=sk-...        # https://platform.deepseek.com
LLM_QWEN_API_KEY=sk-...            # 阿里百炼 https://bailian.console.aliyun.com
```

也可在 `.env` 中改 `LLM_DEEPSEEK_BASE_URL` / `LLM_QWEN_MODEL` 等。

## 目录结构

```
askdata/
├── backend/          # FastAPI + SQLite（app/, tests/, Dockerfile）
├── frontend/         # Vue3 + Element Plus + ECharts
├── docs/             # 产品设计 / 功能与价格设计 / 实施步骤
├── docker-compose.yml
├── README.md
├── LICENSE           # MIT
└── CONTRIBUTING.md
```

详见 [docs/实施步骤.md](docs/实施步骤.md)。
