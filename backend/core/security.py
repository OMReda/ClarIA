from typing import Any, Dict, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from pydantic import BaseModel

from .config import get_settings

settings = get_settings()

security_scheme = HTTPBearer()

# Keycloak JWKS endpoint
jwks_url = f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"

# We set lifespan to 900 seconds (15 minutes) as explicitly requested
jwk_client = jwt.PyJWKClient(jwks_url, lifespan=900)

class User(BaseModel):
    sub: str
    email: Optional[str] = None
    name: Optional[str] = None
    preferred_username: Optional[str] = None
    roles: List[str] = []

def decode_and_validate_token(token: str) -> User:
    try:
        # Get the signing key from the JWKS cache
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        
        # Decode and validate the token.
        # We explicitly skip verifying 'aud' because Keycloak's claria-frontend
        # doesn't add an 'aud' claim by default unless we map it. Instead, we
        # verify 'azp' below.
        # For issuer validation, we check that the issuer ends with /realms/{settings.keycloak_realm}
        # so that any hostname (localhost, LAN IPs, Cloudflare Tunnels, Ngrok, etc.) is supported
        # without hardcoding hostnames, while maintaining strict cryptographic signature verification.
        unverified_payload = jwt.decode(token, options={"verify_signature": False, "verify_iss": False, "verify_aud": False})
        iss = unverified_payload.get("iss", "")
        expected_suffix = f"/realms/{settings.keycloak_realm}"
        if not iss.endswith(expected_suffix):
            raise jwt.InvalidIssuerError(f"Issuer '{iss}' does not end with '{expected_suffix}'")

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_iss": False}
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidIssuerError:
        try:
            unverified = jwt.decode(token, options={"verify_signature": False, "verify_iss": False, "verify_aud": False})
            actual_iss = unverified.get("iss", "unknown")
        except Exception:
            actual_iss = "unknown"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid issuer (got '{actual_iss}')",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError: # Catch all other JWT errors (invalid signature, malformed, etc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Verify azp (Authorized Party) instead of aud
    if payload.get("azp") != settings.keycloak_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorized party (azp)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract roles. If a user is validly authenticated in our realm but doesn't have an explicit
    # 'user' role assigned in Keycloak, we automatically grant them standard 'user' access
    # while keeping 'require_admin' strict for administrative routes.
    realm_access = payload.get("realm_access", {})
    roles = list(realm_access.get("roles", []))
    if "user" not in roles and "admin" not in roles:
        roles.append("user")

    return User(
        sub=payload.get("sub"),
        email=payload.get("email"),
        name=payload.get("name"),
        preferred_username=payload.get("preferred_username"),
        roles=roles,
    )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> User:
    token = credentials.credentials
    return decode_and_validate_token(token)

def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that requires the 'admin' role."""
    if "admin" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user
