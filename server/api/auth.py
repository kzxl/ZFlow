"""
Authentication and Token Audit API Router.
Provides RFC 7662 OAuth 2.0 Token Introspection, Security Audit Trail,
Token Revocation, and User Authentication endpoints.
"""
from fastapi import APIRouter, Request, HTTPException, Query, Header
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from engine.auth_manager import auth_manager

router = APIRouter(tags=["Authentication & Token Audit"])


class TokenIntrospectRequest(BaseModel):
    token: Optional[str] = Field(default=None, description="The JWT access token to introspect and audit")


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username (e.g. admin, manager, staff, guest)")
    password: str = Field(..., description="Password (e.g. admin123, manager123, staff123, guest123)")
    session_id: Optional[str] = Field(default=None, description="Optional custom session ID to bind")


class RevokeRequest(BaseModel):
    token: Optional[str] = Field(default=None, description="The JWT access token to revoke")
    jti: Optional[str] = Field(default=None, description="The JWT ID (jti) to revoke")


@router.post("/api/v1/auth/introspect")
async def introspect_and_audit_token(
    request: Request,
    body: TokenIntrospectRequest = TokenIntrospectRequest(),
    authorization: Optional[str] = Header(None)
):
    """
    RFC 7662 Token Introspection & Security Audit Endpoint:
    Inspects, audits, and validates an Access Token.
    Returns token status, owner (sub), role, tier, scopes, remaining lifetime, and risk assessment.
    Records an immutable audit trail entry for compliance and security monitoring.
    """
    token_str = body.token or (authorization.replace("Bearer ", "").strip() if authorization else "")
    if not token_str:
        raise HTTPException(status_code=400, detail="Missing access token in request body or Authorization header.")

    client_ip = request.client.host if request.client else "127.0.0.1"
    audit_result = auth_manager.introspect_token(token_str, ip_address=client_ip, endpoint="/api/v1/auth/introspect")
    return audit_result


@router.get("/api/v1/auth/audit-logs")
async def get_token_audit_logs(
    limit: int = Query(50, ge=1, le=500, description="Max audit log entries to return"),
    user_id: Optional[str] = Query(None, description="Filter logs by user ID"),
    action: Optional[str] = Query(None, description="Filter logs by action (e.g. INTROSPECT, LOGIN, REVOKE)")
):
    """
    Security Audit Trail Endpoint:
    Returns the immutable security audit logs for access tokens:
    who accessed what, when, from which IP, and verification outcomes (SUCCESS, EXPIRED, TAMPERED, REVOKED).
    """
    logs = auth_manager.get_audit_logs(limit=limit, user_id=user_id, action=action)
    return {
        "status": "success",
        "total": len(logs),
        "logs": logs
    }


@router.post("/api/v1/auth/login")
async def login_for_token(
    request: Request,
    payload: LoginRequest
):
    """
    Direct Authentication Endpoint:
    Validates user credentials and issues a signed RFC 7519 JWT access token with bound session.
    """
    user_record = auth_manager.authenticate_user(payload.username, payload.password)
    client_ip = request.client.host if request.client else "127.0.0.1"

    if not user_record:
        auth_manager.log_audit_event("LOGIN", "FAILED", user_id=payload.username, ip_address=client_ip, endpoint="/api/v1/auth/login")
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token_bundle = auth_manager.issue_access_token(
        user_id=user_record["username"],
        role=user_record["role"],
        tier=user_record["tier"],
        scopes=user_record["scopes"],
        session_id=payload.session_id,
        expires_in_seconds=3600
    )

    auth_manager.log_audit_event(
        "LOGIN",
        "SUCCESS",
        user_id=user_record["username"],
        jti=token_bundle["claims"]["jti"],
        ip_address=client_ip,
        endpoint="/api/v1/auth/login"
    )

    return {
        "status": "success",
        "access_token": token_bundle["access_token"],
        "token_type": "Bearer",
        "expires_in": token_bundle["expires_in"],
        "session_id": token_bundle["session_id"],
        "user": {
            "username": user_record["username"],
            "role": user_record["role"],
            "tier": user_record["tier"],
            "scopes": user_record["scopes"]
        }
    }


@router.post("/api/v1/auth/revoke")
async def revoke_access_token(
    request: Request,
    body: RevokeRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Token Revocation Endpoint:
    Immediately revokes an access token and adds its JTI to the revocation blacklist.
    """
    token_str = body.token or (authorization.replace("Bearer ", "").strip() if authorization else "")
    jti = body.jti

    if not jti and token_str:
        _, claims, _ = auth_manager.verify_token(token_str)
        if claims and "jti" in claims:
            jti = claims["jti"]

    if not jti:
        raise HTTPException(status_code=400, detail="Missing valid token or JTI to revoke.")

    auth_manager.revoke_token(jti)
    return {
        "status": "success",
        "message": f"Token with JTI '{jti}' has been revoked successfully.",
        "jti": jti
    }


@router.get("/api/v1/auth/users")
async def list_available_users():
    """
    Returns available demo accounts and their assigned roles and tiers.
    """
    return {
        "users": auth_manager.list_users()
    }
