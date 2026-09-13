import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select

from backend.core.security import require_admin, User
from backend.core.database import get_async_session
from backend.core.config import get_settings
from backend.services.keycloak_admin import KeycloakAdminClient
from backend.models.file import File
from backend.models.prompt import Prompt
from backend.models.chart import Chart

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()
kc_client = KeycloakAdminClient()

def validate_password_complexity(v: str) -> str:
    errors = []
    if len(v) < 8:
        errors.append("au moins 8 caractères")
    if not re.search(r"[A-Z]", v):
        errors.append("au moins une lettre majuscule")
    if not re.search(r"[a-z]", v):
        errors.append("au moins une lettre minuscule")
    if not re.search(r"\d", v):
        errors.append("au moins un chiffre")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
        errors.append("au moins un caractère spécial")
        
    if errors:
        raise ValueError("Le mot de passe doit contenir : " + ", ".join(errors) + ".")
    return v

class UserCreate(BaseModel):
    username: str
    email: str
    firstName: str = ""
    lastName: str = ""
    password: str

    @field_validator("password")
    @classmethod
    def validate_pwd(cls, v):
        return validate_password_complexity(v)

class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    firstName: str | None = None
    lastName: str | None = None
    enabled: bool | None = None

class PasswordUpdate(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def validate_pwd(cls, v):
        return validate_password_complexity(v)

@router.get("/users")
async def list_users(admin: User = Depends(require_admin)):
    return await kc_client.list_users()

@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, admin: User = Depends(require_admin)):
    # Create user in Keycloak
    payload = {
        "username": user.username,
        "email": user.email,
        "firstName": user.firstName,
        "lastName": user.lastName,
        "enabled": True,
        "emailVerified": True
    }
    user_id = await kc_client.create_user(payload)
    
    # Set password if user was created successfully
    if user_id and user.password:
        await kc_client.set_password(user_id, user.password, temporary=False)
        
    return {"id": user_id, "message": "User created successfully"}

@router.put("/users/{user_id}")
async def update_user(user_id: str, user: UserUpdate, admin: User = Depends(require_admin)):
    if user_id == admin.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot edit your own profile from the admin panel."
        )
        
    try:
        target_user = await kc_client.get_user(user_id)
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé.")
        raise
        
    is_target_admin = target_user.get("username") in ("adminuser", "admin") or "admin" in target_user.get("realmRoles", [])
    
    payload = {
        "email": target_user.get("email"),
        "firstName": target_user.get("firstName", ""),
        "lastName": target_user.get("lastName", ""),
        "enabled": target_user.get("enabled", True),
    }
    if user.email is not None:
        payload["email"] = user.email
    if user.firstName is not None:
        payload["firstName"] = user.firstName
    if user.lastName is not None:
        payload["lastName"] = user.lastName
        
    if user.username is not None and user.username != target_user.get("username"):
        if is_target_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nom d'utilisateur d'un administrateur ne peut pas être modifié."
            )
        payload["username"] = user.username
        
    if user.enabled is not None:
        if is_target_admin and not user.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le compte administrateur ne peut pas être désactivé."
            )
        payload["enabled"] = user.enabled
        
    await kc_client.update_user(user_id, payload)
    if payload.get("enabled") is False:
        await kc_client.logout_user(user_id)
    return {"message": "User updated successfully"}

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_async_session)):
    if user_id == admin.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot delete your own admin account."
        )
    users = await kc_client.list_users()
    non_admins = [u for u in users if u.get("username") not in ("adminuser", "admin") and "admin" not in u.get("realmRoles", [])]
    if len(non_admins) <= 1 and any(u.get("id") == user_id for u in non_admins):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer : la plateforme doit posséder au moins un utilisateur (non-administrateur)."
        )
    # 1. Collect files to delete
    result = await db.execute(select(File).where(File.owner_id == user_id))
    files = result.scalars().all()
    file_ids = [f.id for f in files]

    # 2. Delete from Keycloak FIRST. If this fails, it raises an exception and aborts.
    await kc_client.delete_user(user_id)
    
    # 3. Keycloak deletion succeeded. Now cascade-delete local DB data explicitly.
    try:
        if file_ids:
            # Find all prompt IDs for these files to delete charts
            prompt_result = await db.execute(select(Prompt.id).where(Prompt.file_id.in_(file_ids)))
            prompt_ids = prompt_result.scalars().all()
            
            if prompt_ids:
                await db.execute(delete(Chart).where(Chart.prompt_id.in_(prompt_ids)))
            
            await db.execute(delete(Prompt).where(Prompt.file_id.in_(file_ids)))
            await db.execute(delete(File).where(File.id.in_(file_ids)))
            await db.commit()
            
            # 4. DB commit succeeded. Now cascade-delete physical files from storage.
            # We iterate over the file IDs to delete each file's specific storage directory.
            for file_id in file_ids:
                storage_dir = Path(settings.storage_path) / str(file_id)
                if storage_dir.exists() and storage_dir.is_dir():
                    shutil.rmtree(storage_dir, ignore_errors=True)
                    
    except Exception as e:
        logger.error(f"Failed to cascade delete DB files for {user_id}: {e}")
        # Even if DB deletion fails, the user is gone from Keycloak.

@router.put("/users/{user_id}/password")
async def set_password(user_id: str, data: PasswordUpdate, admin: User = Depends(require_admin)):
    if user_id == admin.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot change your own password from the admin panel."
        )
    await kc_client.set_password(user_id, data.password, temporary=False)
    return {"message": "Password updated successfully"}
