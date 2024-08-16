import datetime
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    role: str
    nickname: str
    
class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    nickname: str
    role: str
    is_active: bool
    is_admin: bool
    trial_end: datetime
    email_verified: bool

    class Config:
        orm_mode = True    
    
class TokenData(BaseModel):
    email: str | None = None

class UserInDB(BaseModel):
    email: str
    is_active: bool
    is_admin: bool
    trial_end: datetime
    email_verified: bool

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    nickname: str
    role: str

class EmailSchema(BaseModel):
    email: str
