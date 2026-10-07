# 大模型列表（是否已配置 Key）
from fastapi import APIRouter, Depends

from .. import config
from ..deps import get_current_user
from ..services.text2sql import model_configured

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def list_models(user: dict = Depends(get_current_user)):
    return [
        {"id": key, "name": cfg["name"], "configured": model_configured(key)}
        for key, cfg in config.LLM_CONFIG.items()
    ]
