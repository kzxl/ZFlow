"""
Authentication & JWT Session Token Engine for ZFlow.
Implements RFC 7519 compliant JSON Web Token (HS256) signing, verification,
session binding, claims extraction, and token revocation without external dependencies.
"""
from typing import Dict, Any, Optional, Tuple, List
import hmac
import hashlib
import base64
import json
import time
import secrets
import os
import sqlite3

AUTH_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "auth_sessions.db"))
os.makedirs(os.path.dirname(AUTH_DB_PATH), exist_ok=True)


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data_str: str) -> bytes:
    padding = "=" * (4 - (len(data_str) % 4))
    return base64.urlsafe_b64decode(data_str + padding)


class AuthManager:
    """
    Sovereign Identity and JWT Token Manager.
    Handles user authentication, access token issuance, signature verification,
    claims injection, and token revocation.
    """
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or os.environ.get("ZFLOW_AUTH_SECRET", "zflow_super_secret_jwt_hmac_key_2026")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revoked_tokens (
                    jti TEXT PRIMARY KEY,
                    session_id TEXT,
                    revoked_at REAL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT,
                    role TEXT,
                    tier TEXT,
                    scopes TEXT
                )
            """)
            conn.commit()
            self._seed_default_users(conn)

    def _seed_default_users(self, conn: sqlite3.Connection):
        """Seed starter demo users if not present."""
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            default_users = [
                ("admin", self._hash_password("admin123"), "admin", "vip", "admin:all,rag:read,rag:write,code:exec"),
                ("manager", self._hash_password("manager123"), "manager", "pro", "finance:read,rag:read,orders:manage"),
                ("staff", self._hash_password("staff123"), "staff", "standard", "rag:read,chat:interact"),
                ("guest", self._hash_password("guest123"), "guest", "free", "chat:interact")
            ]
            cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?)", default_users)
            conn.commit()

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Validates username & password against database."""
        h = self._hash_password(password)
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, role, tier, scopes FROM users WHERE username = ? AND password_hash = ?", (username, h))
            row = cursor.fetchone()
            if row:
                return {
                    "username": row[0],
                    "role": row[1],
                    "tier": row[2],
                    "scopes": [s.strip() for s in row[3].split(",") if s.strip()]
                }
        return None

    def issue_access_token(
        self,
        user_id: str,
        role: str = "guest",
        tier: str = "free",
        scopes: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        expires_in_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Creates an RFC 7519 compliant JWT Access Token and Refresh Token.
        """
        now = int(time.time())
        exp = now + expires_in_seconds
        jti = secrets.token_hex(12)
        sess_id = session_id or f"sess_{secrets.token_hex(8)}"

        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "iss": "zflow-auth-engine",
            "sub": user_id,
            "session_id": sess_id,
            "role": role,
            "tier": tier,
            "scopes": scopes or ["chat:interact"],
            "iat": now,
            "exp": exp,
            "jti": jti
        }

        # Sign JWT
        header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

        sig = hmac.new(self.secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        sig_b64 = _base64url_encode(sig)

        access_token = f"{header_b64}.{payload_b64}.{sig_b64}"
        refresh_token = f"rfr_{secrets.token_urlsafe(32)}"

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": expires_in_seconds,
            "session_id": sess_id,
            "claims": payload
        }

    def verify_token(self, token_str: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Validates token signature, expiration timestamp, and revocation blacklist.
        Returns: (is_valid, claims_dict, error_reason)
        """
        if not token_str:
            return False, None, "Missing token."

        token = token_str.replace("Bearer ", "").strip()
        parts = token.split(".")
        if len(parts) != 3:
            return False, None, "Malformed JWT structure: must have 3 segments (header.payload.signature)."

        header_b64, payload_b64, sig_b64 = parts

        # Verify signature
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(self.secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        expected_sig_b64 = _base64url_encode(expected_sig)

        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return False, None, "Invalid JWT signature."

        # Parse payload
        try:
            payload = json.loads(_base64url_decode(payload_b64).decode("utf-8"))
        except Exception:
            return False, None, "Corrupted payload in JWT."

        # Check expiration
        now = time.time()
        if payload.get("exp") and now >= float(payload["exp"]):
            return False, payload, "Token has expired."

        # Check revocation blacklist
        jti = payload.get("jti")
        if jti and self.is_token_revoked(jti):
            return False, payload, "Token has been revoked."

        return True, payload, "Token verified successfully."

    def revoke_token(self, jti: str, session_id: Optional[str] = None):
        """Adds a token's JTI to the revocation blacklist."""
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO revoked_tokens (jti, session_id, revoked_at) VALUES (?, ?, ?)",
                (jti, session_id or "", time.time())
            )
            conn.commit()

    def is_token_revoked(self, jti: str) -> bool:
        """Checks if JTI is in the revocation blacklist."""
        with sqlite3.connect(AUTH_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM revoked_tokens WHERE jti = ?", (jti,))
            return cursor.fetchone() is not None


# Global singleton instance
auth_manager = AuthManager()
