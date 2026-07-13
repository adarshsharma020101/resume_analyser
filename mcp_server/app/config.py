"""MCP server configuration."""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    BACKEND_URL: str = "http://backend:8000"
    MCP_HTTP_PORT: int = 8001
    MCP_HTTP_SECRET: str = "CHANGE_ME_MCP_SECRET"
    SECRET_KEY: str = "CHANGE_ME_use_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    BLOCK_EXTERNAL_NETWORK: bool = True


@lru_cache
def get_mcp_settings() -> MCPSettings:
    return MCPSettings()
