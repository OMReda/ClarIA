import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from backend.core.security import get_current_user, settings

# Generate a test RSA key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
public_key = private_key.public_key()

private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

@pytest.fixture(autouse=True)
def mock_jwk_client():
    # Mock the JWK client to return our test public key
    with patch("backend.core.security.jwk_client") as mock_client:
        mock_key = MagicMock()
        mock_key.key = public_pem
        mock_client.get_signing_key_from_jwt.return_value = mock_key
        # Also mock PyJWKClient constructor if it gets called, though it shouldn't here
        yield mock_client

def create_test_token(
    azp: str = settings.keycloak_client_id,
    issuer: str = f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}",
    roles: list = ["user"],
    exp_delta_seconds: int = 3600
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "test-user-id",
        "email": "test@claria.local",
        "name": "Test User",
        "preferred_username": "testuser",
        "azp": azp,
        "iss": issuer,
        "realm_access": {"roles": roles},
        "exp": now + timedelta(seconds=exp_delta_seconds),
        "iat": now,
    }
    return jwt.encode(payload, private_pem, algorithm="RS256")

def test_valid_token():
    token = create_test_token()
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(creds)
    assert user.sub == "test-user-id"
    assert user.email == "test@claria.local"
    assert "user" in user.roles

def test_expired_token():
    token = create_test_token(exp_delta_seconds=-3600)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()

def test_malformed_token():
    # Not just a bad signature, a completely garbage string
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="this.is.not.a.valid.jwt")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)
    assert exc_info.value.status_code == 401
    assert "validate credentials" in exc_info.value.detail.lower()

def test_wrong_issuer():
    token = create_test_token(issuer="http://wrong-issuer.local")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)
    assert exc_info.value.status_code == 401
    assert "issuer" in exc_info.value.detail.lower()

def test_wrong_audience_azp():
    token = create_test_token(azp="wrong-client")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)
    assert exc_info.value.status_code == 401
    assert "azp" in exc_info.value.detail.lower()

def test_missing_user_role():
    """
    Design intent (security.py L87-88): any authenticated Keycloak realm user
    who has neither 'user' nor 'admin' in their roles is automatically granted
    standard 'user' access. This prevents lockout when Keycloak role assignment
    is delayed, while keeping admin routes strictly protected by require_admin.
    """
    token = create_test_token(roles=["other_role"])
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    # Should NOT raise — auto-grant applies
    user = get_current_user(creds)
    assert "user" in user.roles  # auto-granted
    assert "admin" not in user.roles

def test_require_admin_blocks_non_admin():
    """require_admin must raise 403 for any user without the 'admin' role."""
    from backend.core.security import require_admin
    token = create_test_token(roles=["user"])
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(creds)
    with pytest.raises(HTTPException) as exc_info:
        require_admin(user)
    assert exc_info.value.status_code == 403
    assert "admin" in exc_info.value.detail.lower()
