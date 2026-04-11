"""Auth routes — register, login, refresh."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from agentforge.db.base import get_db
from agentforge.db.models import User
from agentforge.auth.jwt import hash_password, verify_password, create_access_token
from agentforge.auth.deps import get_current_user
from agentforge.core.config import settings
from sqlalchemy import select
from datetime import timedelta

router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'

@router.post('/register', response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(409, 'Email already registered')
    user = User(email=body.email, hashed_password=hash_password(body.password), full_name=body.full_name)
    db.add(user)
    await db.commit()
    token = create_access_token({'sub': str(user.id)}, timedelta(minutes=settings.access_token_expire_minutes))
    return TokenResponse(access_token=token)

@router.post('/login', response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid credentials')
    token = create_access_token({'sub': str(user.id)}, timedelta(minutes=settings.access_token_expire_minutes))
    return TokenResponse(access_token=token)

@router.get('/me')
async def me(user: User = Depends(get_current_user)):
    return {'id': str(user.id), 'email': user.email, 'full_name': user.full_name, 'plan': user.plan}
