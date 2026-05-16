from fastapi import APIRouter, HTTPException, Header, Depends
from models import UserProfileDB, UserProfile, UpdateProfileRequest
from database import get_db
from sqlalchemy.orm import Session
from typing import Optional

router = APIRouter()

@router.get("/profile/{username}", response_model=UserProfile)
def get_profile(username: str, db: Session = Depends(get_db)):
    profile = db.query(UserProfileDB).filter(UserProfileDB.username == username).first()
    if not profile:
        return UserProfile(username=username)
    return UserProfile(username=profile.username, email=profile.email, full_name=profile.full_name)

@router.put("/profile/{username}", response_model=UserProfile)
def update_profile(username: str, req: UpdateProfileRequest, db: Session = Depends(get_db), x_user: Optional[str] = Header(None)):
    if x_user != username:
        raise HTTPException(403, "Cannot update another user's profile")
    profile = db.query(UserProfileDB).filter(UserProfileDB.username == username).first()
    if not profile:
        profile = UserProfileDB(username=username)
        db.add(profile)
    if req.email:
        profile.email = req.email
    if req.full_name:
        profile.full_name = req.full_name
    db.commit()
    db.refresh(profile)
    return UserProfile(username=profile.username, email=profile.email, full_name=profile.full_name)

@router.get("/users")
def list_users(db: Session = Depends(get_db), x_role: Optional[str] = Header(None)):
    if x_role != "admin":
        raise HTTPException(403, "Admin only")
    profiles = db.query(UserProfileDB).all()
    return [{"username": p.username, "email": p.email, "full_name": p.full_name} for p in profiles]