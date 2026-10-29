from pydantic import BaseModel, Field, EmailStr, ConfigDict
from uuid import UUID
from datetime import datetime
from decimal import Decimal


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


class AddGroupMember(BaseModel):
    username: list[str] = Field(min_length=1)


class CreateExpense(BaseModel):
    description: str = Field(min_length=1, max_length=250)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    participant_usernames: list[str] = Field(min_length=1)


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    description: str
    amount: Decimal
    created_at: datetime


class GroupMemberBalance(BaseModel):
    user_id: UUID
    username: str
    total_paid: Decimal
    total_owed: Decimal
    net_balance: Decimal


class SettlementSuggestion(BaseModel):
    from_user: UUID
    from_username: str
    to_user: UUID
    to_username: str
    amount: Decimal


class CreateSettlement(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class SettlementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    from_user_id: UUID
    to_user_id: UUID
    amount_transferred: Decimal
    created_at: datetime


class UpdateExpense(BaseModel):
    description: str = Field(min_length=1, max_length=250)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
