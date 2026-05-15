from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from autoscout.db.session import get_db
from autoscout.db.models import User
from autoscout.auth.firebase import verify_token


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Verify Firebase token and return decoded token claims."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        token = authorization.replace("Bearer ", "")
        decoded = verify_token(token)
        if not decoded:
            raise HTTPException(status_code=401, detail="Invalid token")
        return decoded
    except Exception as e:
        raise HTTPException(status_code=401, detail="Unauthorized")


def get_db_user(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """Resolve Firebase claims to a User ORM object."""
    user = db.query(User).filter(User.phone_number == current_user.get("phone_number")).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
