from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    nickname: str
    role: str
    is_active: bool
    is_admin: bool
    trial_end: datetime
    email_verified: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    role: str
    nickname: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    nickname: str
    role: str
    is_active: bool = False
    is_admin: bool = False
    is_super_admin: bool = False
    email_verified: bool = False

class UserInDB(BaseModel):
    email: str
    is_active: bool
    is_admin: bool
    trial_end: datetime
    email_verified: bool

class EmailSchema(BaseModel):
    email: EmailStr