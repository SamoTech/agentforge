"""Auth routes: register, login, me."""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from agentforge.db.base import get_db
from agentforge.db.models import User
from agentforge.auth.jwt import create_access_token, hash_password, verify_password
from agentforge.core.config import settings

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr; password: str; full_name: Optional[str] = None

from typing import Optional


@router.post('/register', status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if await db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(400, 'Email already registered')
    user = User(email=body.email, hashed_password=hash_password(body.password), full_name=body.full_name)
    db.add(user); await db.commit(); await db.refresh(user)
    return {'id': str(user.id), 'email': user.email, 'plan': user.plan}


@router.post('/login')
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == form.username))
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid credentials')
    token = create_access_token({'sub': str(user.id), 'email': user.email, 'plan': user.plan},
                                 expires_delta=timedelta(minutes=settings.access_token_expire_minutes))
    return {'access_token': token, 'token_type': 'bearer'}
