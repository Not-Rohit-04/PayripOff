from pydantic import BaseModel, Field, EmailStr, ConfigDict
from uuid import UUID
from datetime import datetime


class CreateUser(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    created_at: datetime


class UserLogin(BaseModel):

    email: EmailStr
    password: str


class CreateGroup(BaseModel):

    name: str = Field(min_length=1, max_length=150)
    description: str | None = None


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_by_id: UUID
    created_at: datetime
