"""FastAPI dependency injectors for authentication."""
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from agentforge.db.base import get_db
from agentforge.db.models import User
from agentforge.auth.jwt import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    exc = HTTPException(status.HTTP_401_UNAUTHORIZED, 'Could not validate credentials',
                        headers={'WWW-Authenticate': 'Bearer'})
    try:
        payload = decode_token(token)
        user_id = payload.get('sub')
        if not user_id:
            raise exc
    except ValueError:
        raise exc
    user = await db.get(User, uuid.UUID(user_id))
    if not user or not user.is_active:
        raise exc
    return user

async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, 'Admin access required')
    return user
