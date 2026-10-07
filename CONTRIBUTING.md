# CONTRIBUTING · 参与贡献

欢迎提交 Issue 与 PR！本仓库代码全部原创（MIT 协议），请遵守以下约定。

## 开发环境

```bash
# 后端
cd backend && python3 -m venv .venv && source .venv/bin/activate \
  && pip install -r requirements.txt && pytest tests/ -v

# 前端
cd frontend && npm install && npm run dev
```

## 提交约定

- PR 标题格式：`[模块] 简述`，如 `[chat] 修复饼图空数据异常`
- 后端改动必须附带/更新 `backend/tests/` 用例，并保证 `pytest` 全绿
- 不提交 `.env`、`.db`、`node_modules/`、`dist/`（已被 .gitignore 排除）
- 新增 API 请同步更新 `docs/产品设计.md` 中的接口说明

## 安全红线

- Text-to-SQL 相关改动不得放宽 `validate_select_sql` 的白名单（SELECT 限定、危险关键字拦截）
- 权限相关改动必须保留"不能删自己 / 至少保留 1 个 super_admin"保护策略，并补充测试
