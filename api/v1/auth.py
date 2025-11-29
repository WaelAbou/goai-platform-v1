"""
Authentication API - Login, register, API keys.
"""

from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm
from typing import List

from core.auth import (
    auth_service,
    User, UserCreate, UserLogin, UserResponse, Token,
    APIKey, APIKeyCreate, APIKeyResponse,
    get_current_user_required, get_current_admin_user, get_current_user
)


router = APIRouter()


# ==========================================
# User Registration & Login
# ==========================================

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """
    Register a new user account.
    
    Example:
    ```
    POST /api/v1/auth/register
    {
        "email": "user@example.com",
        "username": "johndoe",
        "password": "securepassword123"
    }
    ```
    """
    try:
        user = auth_service.create_user(user_data)
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            last_login=user.last_login
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=Token)
async def login(response: Response, credentials: UserLogin):
    """
    Login with username/email and password.
    
    Returns a JWT token for authentication.
    
    Example:
    ```
    POST /api/v1/auth/login
    {
        "username": "johndoe",
        "password": "securepassword123"
    }
    ```
    """
    token = auth_service.login(credentials.username, credentials.password)
    
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    # Also set cookie for convenience
    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        max_age=token.expires_in,
        samesite="lax"
    )
    
    return token


@router.post("/token", response_model=Token)
async def login_oauth2(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible login endpoint.
    
    Accepts form data:
    - username: string
    - password: string
    """
    token = auth_service.login(form_data.username, form_data.password)
    
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        max_age=token.expires_in,
        samesite="lax"
    )
    
    return token


@router.post("/logout")
async def logout(response: Response):
    """Logout - clears the auth cookie."""
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}


# ==========================================
# Current User
# ==========================================

@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user_required)):
    """Get current authenticated user."""
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.get("/check")
async def check_auth(user: User = Depends(get_current_user)):
    """Check if user is authenticated."""
    if user:
        return {
            "authenticated": True,
            "user": user.username,
            "is_admin": user.is_admin
        }
    return {"authenticated": False}


# ==========================================
# API Keys
# ==========================================

@router.post("/api-keys", response_model=dict)
async def create_api_key(
    key_data: APIKeyCreate,
    user: User = Depends(get_current_user_required)
):
    """
    Create a new API key.
    
    ⚠️ The raw key is only shown once! Save it securely.
    
    Example:
    ```
    POST /api/v1/auth/api-keys
    {
        "name": "My Integration",
        "scopes": ["read", "write"],
        "expires_in_days": 365
    }
    ```
    """
    api_key, raw_key = auth_service.create_api_key(user.id, key_data)
    
    return {
        "key": raw_key,  # Only shown once!
        "id": api_key.id,
        "name": api_key.name,
        "prefix": api_key.prefix,
        "scopes": api_key.scopes,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "warning": "Save this key! It will not be shown again."
    }


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(user: User = Depends(get_current_user_required)):
    """List all API keys for the current user."""
    keys = auth_service.list_api_keys(user.id)
    
    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            prefix=k.prefix,
            created_at=k.created_at,
            last_used=k.last_used,
            expires_at=k.expires_at,
            is_active=k.is_active,
            scopes=k.scopes
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: User = Depends(get_current_user_required)
):
    """Revoke an API key."""
    success = auth_service.revoke_api_key(key_id, user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"message": "API key revoked"}


# ==========================================
# Admin Only
# ==========================================

@router.get("/users", response_model=List[UserResponse])
async def list_users(user: User = Depends(get_current_admin_user)):
    """List all users (admin only)."""
    return auth_service.list_users()

