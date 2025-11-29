"""
FastAPI dependencies for authentication.
"""

from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from .service import auth_service
from .models import User, UserResponse

# Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_token_from_header(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    authorization: Optional[str] = Header(None)
) -> Optional[str]:
    """Extract token from Authorization header."""
    if credentials:
        return credentials.credentials
    
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    
    return None


async def get_current_user(token: Optional[str] = Depends(get_token_from_header)) -> Optional[User]:
    """
    Get current user from JWT token. Returns None if not authenticated.
    Use this for optional authentication.
    """
    if not token:
        return None
    
    user = auth_service.get_user_from_token(token)
    return user


async def get_current_user_required(token: Optional[str] = Depends(get_token_from_header)) -> User:
    """
    Get current user from JWT token. Raises 401 if not authenticated.
    Use this for required authentication.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = auth_service.get_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_active_user(user: User = Depends(get_current_user_required)) -> User:
    """Get current active user."""
    return user


async def get_current_admin_user(user: User = Depends(get_current_user_required)) -> User:
    """Get current admin user. Raises 403 if not admin."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


async def get_user_id(user: Optional[User] = Depends(get_current_user)) -> str:
    """
    Get user ID from token, or return 'default' for unauthenticated requests.
    This allows gradual migration to multi-user.
    """
    if user:
        return user.id
    return "default"


async def get_user_id_required(user: User = Depends(get_current_user_required)) -> str:
    """Get user ID, requiring authentication."""
    return user.id


# API Key authentication
async def get_api_key_user(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[User]:
    """Authenticate via API key header."""
    if not x_api_key:
        return None
    
    result = auth_service.verify_api_key(x_api_key)
    if not result:
        return None
    
    api_key, user = result
    return user


async def get_current_user_or_api_key(
    token_user: Optional[User] = Depends(get_current_user),
    api_key_user: Optional[User] = Depends(get_api_key_user)
) -> Optional[User]:
    """Get user from either JWT token or API key."""
    return token_user or api_key_user


async def get_user_id_flexible(
    token_user: Optional[User] = Depends(get_current_user),
    api_key_user: Optional[User] = Depends(get_api_key_user)
) -> str:
    """
    Get user ID from JWT token, API key, or default to 'default'.
    Most flexible option for backward compatibility.
    """
    user = token_user or api_key_user
    return user.id if user else "default"
