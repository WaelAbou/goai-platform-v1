"""
Authentication Module.
"""

from .models import User, UserCreate, UserLogin, UserResponse, Token, APIKey, APIKeyCreate, APIKeyResponse
from .service import auth_service
from .dependencies import (
    get_current_user,
    get_current_user_required,
    get_current_active_user,
    get_current_admin_user,
    get_user_id,
    get_user_id_required,
    get_user_id_flexible,
    get_api_key_user,
    get_current_user_or_api_key
)

__all__ = [
    "User",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "APIKey",
    "APIKeyCreate",
    "APIKeyResponse",
    "auth_service",
    "get_current_user",
    "get_current_user_required",
    "get_current_active_user",
    "get_current_admin_user",
    "get_user_id",
    "get_user_id_required",
    "get_user_id_flexible",
    "get_api_key_user",
    "get_current_user_or_api_key"
]
