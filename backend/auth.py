"""Very small role-based auth (demo grade): admin can upload/delete, user can only ask."""
import hashlib, secrets
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from .db import get_db, User, SessionLocal

SALT = "edupolicy-demo-salt"
TOKENS: dict[str, int] = {}   # token -> user_id (in memory; restart = log in again)


def hash_pw(pw: str) -> str:
    return hashlib.sha256((SALT + pw).encode()).hexdigest()


def seed_users():
    db = SessionLocal()
    try:
        for name, pw, role in [("admin", "admin123", "admin"), ("student", "student123", "user")]:
            if not db.query(User).filter_by(username=name).first():
                db.add(User(username=name, password_hash=hash_pw(pw), role=role))
        db.commit()
    finally:
        db.close()


def login(db: Session, username: str, password: str):
    u = db.query(User).filter_by(username=username).first()
    if not u or u.password_hash != hash_pw(password):
        raise HTTPException(401, "Invalid username or password")
    token = secrets.token_hex(24)
    TOKENS[token] = u.id
    return token, u


def current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    token = (authorization or "").replace("Bearer ", "").strip()
    uid = TOKENS.get(token)
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(401, "Not logged in")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin role required")
    return user
