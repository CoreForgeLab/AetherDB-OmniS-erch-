"""
权限依赖注入模块

支持从请求头 X-API-Key 或查询参数 api_key 读取密钥。
管理员密钥优先使用环境变量 ADMIN_API_KEY/ADMIN_API_KEY（和原有 NOVEL_ADMIN_KEY/NOVEL_API_KEY 兼容）。
"""

import os
import secrets
from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader, APIKeyQuery

# ── 密钥读取（兼容新旧环境变量名） ──
ADMIN_API_KEY = (
    os.environ.get("ADMIN_API_KEY")
    or os.environ.get("NOVEL_ADMIN_KEY")
    or "nvk_admin_" + secrets.token_hex(16)
)

USER_API_KEY = (
    os.environ.get("USER_API_KEY")
    or os.environ.get("NOVEL_API_KEY")
    or "nvk_" + secrets.token_hex(16)
)

# 全部有效密钥映射
VALID_KEYS: dict[str, str] = {
    ADMIN_API_KEY: "admin",
    USER_API_KEY: "user",
}


def resolve_api_key(request: Request) -> str | None:
    """从请求头或查询参数中提取 API Key（不抛异常）。"""
    # 优先请求头
    header_key = request.headers.get("x-api-key")
    if header_key and header_key in VALID_KEYS:
        return header_key

    # 回退查询参数
    query_key = request.query_params.get("api_key")
    if query_key and query_key in VALID_KEYS:
        return query_key

    # URL 路径中嵌入 ?api_key=… 的兼容场景
    return None


async def get_current_user_role(request: Request) -> str:
    """依赖注入：返回当前用户的角色 "admin" | "user"。

    从 X-API-Key 请求头或 api_key 查询参数读取。
    无效或缺失时抛出 401。
    """
    api_key = resolve_api_key(request)
    if api_key is None:
        raise HTTPException(status_code=401, detail="缺少或无效的 API 密钥")
    return VALID_KEYS[api_key]


async def require_admin(role: str = Depends(get_current_user_role)) -> None:
    """依赖注入守卫：仅管理员可访问。

    如果当前角色不是 admin，抛出 403。
    """
    if role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
