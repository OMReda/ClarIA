import httpx
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class KeycloakAdminClient:
    def __init__(self):
        self.server_url = settings.keycloak_server_url
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_admin_client_id
        self.client_secret = settings.keycloak_admin_client_secret
        
        # Base URL for the admin API of our realm
        self.admin_api_base = f"{self.server_url}/admin/realms/{self.realm}"
        self._cached_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._token_lock: asyncio.Lock = asyncio.Lock()
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def get_token(self) -> str:
        """Fetch a short-lived access token for the service account with caching."""
        now = time.time()
        # Fast-path: return cached token without acquiring lock
        if self._cached_token and now < self._token_expires_at:
            return self._cached_token

        async with self._token_lock:
            # Re-check inside lock — another coroutine may have refreshed while we waited
            now = time.time()
            if self._cached_token and now < self._token_expires_at:
                return self._cached_token

            token_url = f"{self.server_url}/realms/{self.realm}/protocol/openid-connect/token"
            
            if not self.client_secret:
                raise HTTPException(status_code=500, detail="KEYCLOAK_ADMIN_CLIENT_SECRET is not set in backend config.")
                
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            client = self._get_client()
            response = await client.post(token_url, data=data)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Failed to authenticate admin client: {response.text}")
            
            res_json = response.json()
            self._cached_token = res_json["access_token"]
            expires_in = res_json.get("expires_in", 60)
            self._token_expires_at = time.time() + max(10, expires_in - 10)
            return self._cached_token

    async def list_users(self) -> List[Dict[str, Any]]:
        token = await self.get_token()
        client = self._get_client()
        response = await client.get(
            f"{self.admin_api_base}/users",
            params={"max": 500, "briefRepresentation": False},
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Failed to list users: {response.text}")
        return response.json()

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        token = await self.get_token()
        client = self._get_client()
        response = await client.get(
            f"{self.admin_api_base}/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to get user: {response.text}")
        return response.json()

    async def create_user(self, payload: Dict[str, Any]) -> str:
        token = await self.get_token()
        client = self._get_client()
        response = await client.post(
            f"{self.admin_api_base}/users",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code not in (201, 204):
            raise HTTPException(status_code=400, detail=f"Failed to create user: {response.text}")
        
        # Keycloak returns the new user's location in headers, extract ID from it
        location = response.headers.get("Location")
        if location:
            return location.split("/")[-1]
        return ""

    async def update_user(self, user_id: str, payload: Dict[str, Any]) -> None:
        token = await self.get_token()
        client = self._get_client()
        response = await client.put(
            f"{self.admin_api_base}/users/{user_id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 204:
            raise HTTPException(status_code=400, detail=f"Failed to update user: {response.text}")

    async def delete_user(self, user_id: str) -> None:
        token = await self.get_token()
        client = self._get_client()
        response = await client.delete(
            f"{self.admin_api_base}/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 204:
            raise HTTPException(status_code=400, detail=f"Failed to delete user: {response.text}")

    async def set_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        token = await self.get_token()
        payload = {
            "type": "password",
            "value": password,
            "temporary": temporary
        }
        client = self._get_client()
        response = await client.put(
            f"{self.admin_api_base}/users/{user_id}/reset-password",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 204:
            raise HTTPException(status_code=400, detail=f"Failed to set password: {response.text}")

    async def logout_user(self, user_id: str) -> None:
        token = await self.get_token()
        client = self._get_client()
        response = await client.post(
            f"{self.admin_api_base}/users/{user_id}/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code not in (200, 204):
            logger.warning(f"Failed to logout user {user_id}: {response.text}")
