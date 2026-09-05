from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional, List

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    photo_path: Optional[str] = None
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ValidationErrorDetail(BaseModel):
    loc: List
    msg: str
    type: str

class HTTPValidationError(BaseModel):
    detail: Optional[List[ValidationErrorDetail]] = None

class ErrorResponse(BaseModel):
    detail: str

class TagResponse(BaseModel):
    id: int
    name: str



class NewsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    subtitle: Optional[str] = None
    text: str
    image_path: Optional[str] = None
    author: UserResponse
    tags: List[TagResponse]
    created_at: datetime
    comments_count: int = 0

class NewsListResponse(BaseModel):
    items: Optional[List[NewsResponse]] = None
    total: int
    page: int
    per_page: int
    total_pages: int

class CommentResponse(BaseModel):
    id: int
    text: str
    author: UserResponse
    created_at: datetime



