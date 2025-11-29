"""
Authentication Models - Users, API Keys, Sessions.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
import hashlib
import secrets


class User(BaseModel):
    """User account."""
    id: str
    email: str
    username: str
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation request."""
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    """User login request."""
    username: str  # Can be username or email
    password: str


class UserResponse(BaseModel):
    """User response (without password)."""
    id: str
    email: str
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class APIKey(BaseModel):
    """API key for programmatic access."""
    id: str
    user_id: str
    name: str
    key_hash: str
    prefix: str  # First 8 chars for identification
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    scopes: List[str] = ["read", "write"]
    
    @classmethod
    def generate(cls, user_id: str, name: str, scopes: List[str] = None) -> tuple["APIKey", str]:
        """Generate a new API key. Returns (APIKey, raw_key)."""
        raw_key = f"goai_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key = cls(
            id=secrets.token_hex(8),
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            prefix=raw_key[:12],
            scopes=scopes or ["read", "write"]
        )
        
        return api_key, raw_key


class APIKeyCreate(BaseModel):
    """API key creation request."""
    name: str
    scopes: List[str] = ["read", "write"]
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    """API key response (without hash)."""
    id: str
    name: str
    prefix: str
    created_at: datetime
    last_used: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool
    scopes: List[str]


class Session(BaseModel):
    """User session."""
    id: str
    user_id: str
    token_hash: str
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

