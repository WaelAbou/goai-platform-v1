"""
Authentication Service - JWT, password hashing, session management with SQLite persistence.
"""

import os
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import jwt, JWTError

from .models import User, UserCreate, UserResponse, Token, APIKey, APIKeyCreate

# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/users.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the user database."""
    conn = get_db()
    
    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    """)
    
    # API Keys table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            key_prefix TEXT NOT NULL,
            scopes TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            last_used TEXT,
            expires_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Sessions table (for tracking active sessions)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
    
    conn.commit()
    conn.close()


# Initialize on module load
init_db()


class AuthService:
    """
    Authentication service with SQLite persistence.
    """
    
    def __init__(self):
        self._ensure_admin()
    
    def _ensure_admin(self):
        """Ensure default admin user exists."""
        conn = get_db()
        admin = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            ("admin",)
        ).fetchone()
        
        if not admin:
            admin_id = "admin_001"
            now = datetime.now().isoformat()
            conn.execute("""
                INSERT INTO users (id, email, username, hashed_password, is_active, is_admin, created_at)
                VALUES (?, ?, ?, ?, 1, 1, ?)
            """, (admin_id, "admin@goai.local", "admin", self.hash_password("admin123"), now))
            conn.commit()
        
        conn.close()
    
    # ==========================================
    # Password Utilities
    # ==========================================
    
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return f"{salt}${hashed}"
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, stored_hash = hashed_password.split("$")
            computed_hash = hashlib.sha256(f"{salt}{plain_password}".encode()).hexdigest()
            return computed_hash == stored_hash
        except ValueError:
            return False
    
    # ==========================================
    # User Management
    # ==========================================
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        conn = get_db()
        
        # Check if email/username already exists
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ? OR username = ?",
            (user_data.email, user_data.username)
        ).fetchone()
        
        if existing:
            conn.close()
            raise ValueError("Email or username already taken")
        
        user_id = f"user_{secrets.token_hex(8)}"
        now = datetime.now().isoformat()
        
        conn.execute("""
            INSERT INTO users (id, email, username, hashed_password, is_active, is_admin, created_at)
            VALUES (?, ?, ?, ?, 1, 0, ?)
        """, (user_id, user_data.email, user_data.username, self.hash_password(user_data.password), now))
        conn.commit()
        conn.close()
        
        return User(
            id=user_id,
            email=user_data.email,
            username=user_data.username,
            hashed_password="[hidden]",
            is_active=True,
            is_admin=False,
            created_at=datetime.fromisoformat(now)
        )
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_user(row)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username or email."""
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username, username)
        ).fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_user(row)
    
    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert database row to User model."""
        return User(
            id=row["id"],
            email=row["email"],
            username=row["username"],
            hashed_password=row["hashed_password"],
            is_active=bool(row["is_active"]),
            is_admin=bool(row["is_admin"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None
        )
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/email and password."""
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        
        # Update last login
        conn = get_db()
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (now, user.id)
        )
        conn.commit()
        conn.close()
        
        user.last_login = datetime.fromisoformat(now)
        return user
    
    def list_users(self) -> List[UserResponse]:
        """List all users."""
        conn = get_db()
        rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        conn.close()
        
        return [
            UserResponse(
                id=row["id"],
                email=row["email"],
                username=row["username"],
                is_active=bool(row["is_active"]),
                is_admin=bool(row["is_admin"]),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None
            )
            for row in rows
        ]
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[User]:
        """Update user fields."""
        conn = get_db()
        
        allowed_fields = {"email", "username", "is_active"}
        valid_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not valid_updates:
            conn.close()
            return self.get_user(user_id)
        
        set_clause = ", ".join(f"{k} = ?" for k in valid_updates.keys())
        values = list(valid_updates.values()) + [user_id]
        
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()
        
        return self.get_user(user_id)
    
    def change_password(self, user_id: str, new_password: str) -> bool:
        """Change user password."""
        conn = get_db()
        conn.execute(
            "UPDATE users SET hashed_password = ? WHERE id = ?",
            (self.hash_password(new_password), user_id)
        )
        conn.commit()
        affected = conn.total_changes
        conn.close()
        return affected > 0
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user (soft delete by deactivating)."""
        conn = get_db()
        conn.execute(
            "UPDATE users SET is_active = 0 WHERE id = ?",
            (user_id,)
        )
        conn.commit()
        affected = conn.total_changes
        conn.close()
        return affected > 0
    
    # ==========================================
    # JWT Token Management
    # ==========================================
    
    def create_access_token(self, user: User, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        expires = datetime.utcnow() + (expires_delta or timedelta(hours=JWT_EXPIRATION_HOURS))
        
        payload = {
            "sub": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "exp": expires,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError:
            return None
    
    def get_user_from_token(self, token: str) -> Optional[User]:
        """Get user from a valid JWT token."""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        return self.get_user(user_id)
    
    def login(self, username: str, password: str) -> Optional[Token]:
        """Login and return token."""
        user = self.authenticate_user(username, password)
        if not user:
            return None
        
        access_token = self.create_access_token(user)
        
        return Token(
            access_token=access_token,
            expires_in=JWT_EXPIRATION_HOURS * 3600,
            user=UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                is_active=user.is_active,
                is_admin=user.is_admin,
                created_at=user.created_at,
                last_login=user.last_login
            )
        )
    
    # ==========================================
    # API Key Management
    # ==========================================
    
    def create_api_key(self, user_id: str, key_data: APIKeyCreate) -> tuple[APIKey, str]:
        """Create a new API key for a user."""
        api_key, raw_key = APIKey.generate(
            user_id=user_id,
            name=key_data.name,
            scopes=key_data.scopes
        )
        
        if key_data.expires_in_days:
            api_key.expires_at = datetime.now() + timedelta(days=key_data.expires_in_days)
        
        conn = get_db()
        conn.execute("""
            INSERT INTO api_keys (id, user_id, name, key_hash, key_prefix, scopes, is_active, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (
            api_key.id,
            user_id,
            api_key.name,
            api_key.key_hash,
            api_key.key_prefix,
            ",".join(api_key.scopes),
            api_key.created_at.isoformat(),
            api_key.expires_at.isoformat() if api_key.expires_at else None
        ))
        conn.commit()
        conn.close()
        
        return api_key, raw_key
    
    def verify_api_key(self, raw_key: str) -> Optional[tuple[APIKey, User]]:
        """Verify an API key and return the key and user."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1",
            (key_hash,)
        ).fetchone()
        
        if not row:
            conn.close()
            return None
        
        # Check expiration
        if row["expires_at"]:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at < datetime.now():
                conn.close()
                return None
        
        # Update last used
        conn.execute(
            "UPDATE api_keys SET last_used = ? WHERE id = ?",
            (datetime.now().isoformat(), row["id"])
        )
        conn.commit()
        conn.close()
        
        api_key = APIKey(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            key_hash=row["key_hash"],
            key_prefix=row["key_prefix"],
            scopes=row["scopes"].split(",") if row["scopes"] else [],
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None,
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
        )
        
        user = self.get_user(api_key.user_id)
        if not user or not user.is_active:
            return None
        
        return api_key, user
    
    def list_api_keys(self, user_id: str) -> List[APIKey]:
        """List API keys for a user."""
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        conn.close()
        
        return [
            APIKey(
                id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                key_hash=row["key_hash"],
                key_prefix=row["key_prefix"],
                scopes=row["scopes"].split(",") if row["scopes"] else [],
                is_active=bool(row["is_active"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None,
                expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
            )
            for row in rows
        ]
    
    def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """Revoke an API key."""
        conn = get_db()
        conn.execute(
            "UPDATE api_keys SET is_active = 0 WHERE id = ? AND user_id = ?",
            (key_id, user_id)
        )
        conn.commit()
        affected = conn.total_changes
        conn.close()
        return affected > 0


# Singleton instance
auth_service = AuthService()
