from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.schemas import UserCreate, UserUpdate, UserResponse, ShadowSocksCreate, ShadowSocksResponse
from app.services.repository import repo
from app.api.auth import get_current_admin

router = APIRouter(prefix="/api/admin/users", tags=["users"])

@router.get("", response_model=List[UserResponse])
async def list_users(admin = Depends(get_current_admin)):
    users = repo.list_users()
    return [UserResponse(**u.to_dict()) for u in users]

@router.post("", response_model=UserResponse)
async def create_user(req: UserCreate, admin = Depends(get_current_admin)):
    existing = repo.get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = repo.create_user(
        username=req.username,
        display_name=req.display_name,
        traffic_limit=req.traffic_limit,
        device_limit=req.device_limit,
        expires_at=req.expires_at,
        custom_uuid=req.custom_uuid
    )
    repo.log_audit("USER_CREATE", f"Created user {user.username} (ID: {user.id})", admin_id=admin.id)
    return UserResponse(**user.to_dict())

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, admin = Depends(get_current_admin)):
    user = repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user.to_dict())

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, req: UserUpdate, admin = Depends(get_current_admin)):
    user = repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_dict = {k: v for k, v in req.dict().items() if v is not None}
    updated = repo.update_user(user_id, **update_dict)
    repo.log_audit("USER_UPDATE", f"Updated user {user.username} (ID: {user.id})", admin_id=admin.id)
    return UserResponse(**updated.to_dict())

@router.delete("/{user_id}")
async def delete_user(user_id: int, admin = Depends(get_current_admin)):
    user = repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    repo.delete_user(user_id)
    repo.log_audit("USER_DELETE", f"Deleted user {user.username} (ID: {user.id})", admin_id=admin.id)
    return {"message": f"User {user.username} successfully deleted"}

@router.post("/{user_id}/reset-uuid")
async def reset_uuid(user_id: int, admin = Depends(get_current_admin)):
    user = repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_uuid = repo.reset_user_uuid(user_id)
    repo.log_audit("USER_RESET_UUID", f"Reset UUID for user {user.username}", admin_id=admin.id)
    return {"uuid": new_uuid}

@router.post("/{user_id}/reset-token")
async def reset_token(user_id: int, admin = Depends(get_current_admin)):
    user = repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_token = repo.reset_user_sub_token(user_id)
    repo.log_audit("USER_RESET_TOKEN", f"Reset subscription token for user {user.username}", admin_id=admin.id)
    return {"subscription_token": new_token}

@router.get("/{user_id}/shadowsocks", response_model=Optional[ShadowSocksResponse])
async def get_user_shadowsocks(user_id: int, admin = Depends(get_current_admin)):
    ss_cred = repo.get_ss_by_user_id(user_id)
    if not ss_cred:
        return None
    return ShadowSocksResponse(**ss_cred.to_dict())

@router.post("/{user_id}/shadowsocks", response_model=ShadowSocksResponse)
async def update_user_shadowsocks(user_id: int, req: ShadowSocksCreate, admin = Depends(get_current_admin)):
    user = repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ss_cred = repo.create_or_update_ss(
        user_id=user_id,
        password=req.password,
        method=req.method,
        port=req.port,
        server=req.server,
        udp=req.udp
    )
    repo.log_audit("USER_UPDATE_SS", f"Updated ShadowSocks for user {user.username}", admin_id=admin.id)
    return ShadowSocksResponse(**ss_cred.to_dict())
