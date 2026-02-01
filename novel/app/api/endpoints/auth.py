import secrets
from fastapi import APIRouter, HTTPException, Request, Depends
from app.models.schemas import UserRegister, UserLogin
from app.services.user_manager import get_users_db, save_users_db
from app.core.security import hash_password, verify_password
from app.core.config import DATA_ROOT
from app.api.deps import SESSIONS

router = APIRouter()

@router.post("/register")
async def register(user: UserRegister):
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的密码不一致")

    if len(user.username) < 3:
        raise HTTPException(status_code=400, detail="用户名太短")

    users = get_users_db()
    if user.username in users:
        raise HTTPException(status_code=400, detail="用户名已存在")

    pwd_hash, salt = hash_password(user.password)
    users[user.username] = {
        "hash": pwd_hash,
        "salt": salt,
        "group": "default"  # Assign default group
    }
    save_users_db(users)

    # 创建用户目录
    (DATA_ROOT / user.username).mkdir(parents=True, exist_ok=True)

    return {"status": "ok", "message": "注册成功，请登录"}

@router.post("/login")
async def login(user: UserLogin):
    users = get_users_db()
    if user.username not in users:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    stored = users[user.username]
    if not verify_password(stored["hash"], stored["salt"], user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 生成 Token
    token = secrets.token_hex(16)
    SESSIONS[token] = user.username

    return {"status": "ok", "token": token, "username": user.username}

@router.post("/logout")
async def logout(request: Request):
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ")[1]
        if token in SESSIONS:
            del SESSIONS[token]
    return {"status": "ok"}
