from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from models import UserDB, RegisterRequest, LoginRequest, TokenResponse
from database import get_db
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os, uuid

router = APIRouter()
pwd_ctx = CryptContext(schemes=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SECRET = os.getenv("JWT_SECRET", "supersecret")
ALGORITHM = "HS256"

def make_token(data: dict, expires_minutes: int) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload["jti"] = str(uuid.uuid4())
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)

@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(UserDB).filter(UserDB.username == req.username).first()
    if existing:
        raise HTTPException(400, "Username already exists")
    user = UserDB(
        username=req.username,
        password=pwd_ctx.hash(req.password),
        role=req.role
    )
    db.add(user)
    db.commit()
    return {"message": "User registered", "username": req.username}

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == req.username).first()
    if not user or not pwd_ctx.verify(req.password, user.password):
        raise HTTPException(401, "Invalid credentials")
    access  = make_token({"sub": user.username, "role": user.role}, expires_minutes=15)
    refresh = make_token({"sub": user.username, "type": "refresh"}, expires_minutes=60*24*7)
    return TokenResponse(access_token=access, refresh_token=refresh)

@router.post("/refresh")
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Not a refresh token")
        user = db.query(UserDB).filter(UserDB.username == payload["sub"]).first()
        if not user:
            raise HTTPException(401, "User not found")
        new_access = make_token({"sub": user.username, "role": user.role}, expires_minutes=15)
        return {"access_token": new_access, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(401, "Invalid refresh token")

@router.get("/verify")
def verify(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return {"username": payload["sub"], "role": payload.get("role", "user")}
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")