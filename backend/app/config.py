# 应用配置：从环境变量读取（支持 .env 文件）
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _load_dotenv() -> None:
    """极简 .env 加载（不引入第三方依赖）"""
    path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

JWT_SECRET = _env("JWT_SECRET", "change-me-to-a-long-random-secret")
JWT_EXPIRE_HOURS = int(_env("JWT_EXPIRE_HOURS", "8"))
DB_PATH = os.path.join(BASE_DIR, _env("DB_PATH", "data/hr_insight.db"))

# 大模型配置（OpenAI 兼容接口）
LLM_CONFIG = {
    "deepseek": {
        "name": "DeepSeek",
        "api_key": _env("LLM_DEEPSEEK_API_KEY"),
        "base_url": _env("LLM_DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        "model": _env("LLM_DEEPSEEK_MODEL", "deepseek-chat"),
    },
    "qwen": {
        "name": "通义千问",
        "api_key": _env("LLM_QWEN_API_KEY"),
        "base_url": _env("LLM_QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "model": _env("LLM_QWEN_MODEL", "qwen-plus"),
    },
}
