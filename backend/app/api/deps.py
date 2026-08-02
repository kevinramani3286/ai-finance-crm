from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from ..core.security import decode_token
from ..database import get_db
from ..models.entities import Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user = db.query(User).filter(User.email == payload.get("sub"), User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Inactive or missing user")
    return user

def require_roles(*roles: Role):
    def checker(user: User = Depends(current_user)) -> User:
        if roles and user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker
