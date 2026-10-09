"""
ZFlow Ingress Security & Token Audit Interceptor.
Offloads authentication, token audit, and session resolution OUTSIDE the workflow graph.
Enforces OAuth 2.0 Token Introspection (RFC 7662), logs immutable security audit trails,
and enriches ExecutionContext with trusted identity claims before workflow execution.
"""
from fastapi import Request, HTTPException, Header
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import uuid

from engine.auth_manager import auth_manager
from engine.context import ExecutionContext


@dataclass
class IngressIdentity:
    user_id: str
    role: str
    tier: str
    scopes: List[str] = field(default_factory=list)
    session_id: str = ""
    is_authenticated: bool = False
    token: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role,
            "tier": self.tier,
            "scopes": self.scopes,
            "session_id": self.session_id,
            "is_authenticated": self.is_authenticated,
            "has_token": self.token is not None
        }


def extract_bearer_token(authorization: Any = None, request: Optional[Request] = None) -> Optional[str]:
    """Extracts raw Bearer token from header or query param."""
    if authorization and isinstance(authorization, str) and "Bearer " in authorization:
        return authorization.replace("Bearer ", "").strip()
    if request and hasattr(request, "headers"):
        auth_hdr = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_hdr and isinstance(auth_hdr, str) and "Bearer " in auth_hdr:
            return auth_hdr.replace("Bearer ", "").strip()
        if hasattr(request, "query_params"):
            query_token = request.query_params.get("token") or request.query_params.get("access_token")
            if query_token:
                return query_token.strip()
    return None


def verify_and_audit_ingress(
    request: Optional[Request] = None,
    authorization: Optional[str] = None,
    session_id: Optional[str] = None,
    require_auth: bool = False
) -> IngressIdentity:
    """
    Core Ingress Interceptor:
    1. Extracts access token.
    2. Runs RFC 7662 Token Introspection and security audit.
    3. If invalid/expired/revoked: halts request immediately with HTTP 401 (zero workflow execution overhead).
    4. If valid: binds trusted identity, resolves session_id, and records audit trail.
    5. If no token and not required: falls back to safe guest identity.
    """
    client_ip = request.client.host if (request and request.client) else "127.0.0.1"
    endpoint = request.url.path if (request and hasattr(request, "url")) else "/api/flow"
    token_str = extract_bearer_token(authorization, request)

    if token_str:
        # Perform introspection & audit
        audit_res = auth_manager.introspect_token(token_str, ip_address=client_ip, endpoint=endpoint)
        if not audit_res.get("active"):
            auth_manager.log_audit_event(
                "INGRESS_REJECTED",
                "UNAUTHORIZED",
                user_id=audit_res.get("sub", "unknown"),
                ip_address=client_ip,
                endpoint=endpoint,
                details={"reason": audit_res.get("error")}
            )
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Unauthorized",
                    "reason": audit_res.get("error", "Invalid, expired, or revoked access token."),
                    "status": audit_res.get("status", "INVALID")
                }
            )

        # Admitted authenticated request
        user_id = audit_res.get("sub", "authenticated_user")
        role = audit_res.get("role", "staff")
        tier = audit_res.get("tier", "standard")
        scopes = audit_res.get("scopes", [])
        jti = audit_res.get("jti", "")
        resolved_session = session_id or audit_res.get("session_id") or f"sess_{uuid.uuid4().hex[:12]}"

        auth_manager.log_audit_event(
            "INGRESS_ADMITTED",
            "SUCCESS",
            user_id=user_id,
            jti=jti,
            ip_address=client_ip,
            endpoint=endpoint,
            details={"role": role, "tier": tier, "session_id": resolved_session}
        )

        return IngressIdentity(
            user_id=user_id,
            role=role,
            tier=tier,
            scopes=scopes,
            session_id=resolved_session,
            is_authenticated=True,
            token=token_str
        )

    # No token provided
    if require_auth:
        auth_manager.log_audit_event(
            "INGRESS_REJECTED",
            "NO_TOKEN",
            user_id="anonymous",
            ip_address=client_ip,
            endpoint=endpoint
        )
        raise HTTPException(status_code=401, detail="Authentication token required via 'Authorization: Bearer <token>' header.")

    resolved_session = session_id or f"sess_guest_{uuid.uuid4().hex[:8]}"
    return IngressIdentity(
        user_id="guest",
        role="guest",
        tier="free",
        scopes=[],
        session_id=resolved_session,
        is_authenticated=False,
        token=None
    )


def bind_ingress_to_context(context: ExecutionContext, identity: IngressIdentity):
    """
    Enriches ExecutionContext with trusted, pre-verified identity claims and session ID.
    All downstream workflow nodes receive this trusted metadata without needing to re-authenticate.
    """
    context.session_id = identity.session_id
    context.set_variable("session_id", identity.session_id)
    context.set_variable("user_id", identity.user_id)
    context.set_variable("user_role", identity.role)
    context.set_variable("role", identity.role)
    context.set_variable("user_tier", identity.tier)
    context.set_variable("tier", identity.tier)
    context.set_variable("user_scopes", identity.scopes)
    context.set_variable("scopes", identity.scopes)
    context.set_variable("is_authenticated", identity.is_authenticated)
    if identity.token:
        context.set_variable("access_token", identity.token)
        context.set_variable("token", identity.token)
