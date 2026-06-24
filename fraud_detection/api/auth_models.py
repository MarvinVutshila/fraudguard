from pydantic import BaseModel, Field, validator
from typing import Optional
import re

class LoginRequest(BaseModel):
    username: str = Field(..., description="User's email/username")
    password: str = Field(..., description="User's password")

class UserRegister(BaseModel):
    username: str = Field(..., description="User's email/username")
    password: str = Field(..., description="User's password (min 8 chars, with uppercase, lowercase, number, special char)")
    avatar_url: Optional[str] = Field(None, description="Optional avatar URL")

    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v.lower()

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        common_passwords = ['password', '12345678', 'qwerty', 'admin123', 'password123', 
                           'letmein', 'welcome', '123456789', 'admin', 'password1']
        if v.lower() in common_passwords:
            raise ValueError('Password is too common. Please choose a stronger password')
        return v

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TwoFactorSetupRequest(BaseModel):
    code: str

class TwoFactorVerifyRequest(BaseModel):
    username: str
    code: str

class TwoFactorDisableRequest(BaseModel):
    code: str
