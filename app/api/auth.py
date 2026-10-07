from fastapi import APIRouter, HTTPException, Depends, Request, Response
from app.schemas.schemas import LoginRequest, LoginResponse
from app.services.repository import repo
from app.security.security import verify_password, create_access_token, verify_access_token, rate_limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])

def get_current_admin(request: Request):
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "miliconfig_token" in request.cookies:
        token = request.cookies.get("miliconfig_token")

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    admin = repo.get_admin_by_username(payload.get("sub", ""))
    if not admin:
        raise HTTPException(status_code=401, detail="Admin account not found")
    return admin

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # Rate limit by IP: max 5 login attempts per minute
    if not rate_limiter.is_allowed(f"login_{client_ip}", max_requests=5, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please wait a minute.")

    admin = repo.get_admin_by_username(req.username)
    if not admin or not verify_password(req.password, admin.password_hash):
        repo.log_audit("LOGIN_FAILED", f"Failed login attempt for user: {req.username}", ip=client_ip)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": admin.username, "role": admin.role})
    response.set_cookie(
        key="miliconfig_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # Can be True in HTTPS production
        max_age=86400
    )
    repo.log_audit("LOGIN_SUCCESS", f"Admin {admin.username} logged in successfully", admin_id=admin.id, ip=client_ip)
    return LoginResponse(access_token=token, token_type="bearer", role=admin.role)

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("miliconfig_token")
    return {"message": "Successfully logged out"}

@router.get("/me")
async def get_me(admin = Depends(get_current_admin)):
    return {"id": admin.id, "username": admin.username, "role": admin.role}
