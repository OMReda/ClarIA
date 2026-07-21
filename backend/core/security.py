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
        # verify 'azp' below. We verify issuer.
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}",
            options={"verify_aud": False, "verify_iss": True}
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidIssuerError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid issuer",
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

    # Extract roles
    realm_access = payload.get("realm_access", {})
    roles = realm_access.get("roles", [])

    if "user" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions (missing 'user' role)",
        )

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
