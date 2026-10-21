from collections.abc import AsyncGenerator
import uuid
from decimal import Decimal
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    Numeric,
    String,
    DateTime,
    ForeignKey,
    Text,
    func,
    CheckConstraint,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from datetime import datetime, timezone

database_url = "sqlite+aiosqlite:///./test.db"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_groups: Mapped[list["Group"]] = relationship(
        "Group", back_populates="creator"
    )
    paid_expenses: Mapped[list["Expense"]] = relationship(
        "Expense", back_populates="paid_by", foreign_keys="Expense.paid_by_id"
    )
    expense_shares: Mapped[list["ExpenseShare"]] = relationship(
        "ExpenseShare", back_populates="user"
    )
    group_memberships: Mapped[list["GroupMember"]] = relationship(
        "GroupMember", back_populates="user"
    )


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    creator: Mapped[User] = relationship("User", back_populates="created_groups")
    expenses: Mapped[list["Expense"]] = relationship("Expense", back_populates="group")
    memberships: Mapped[list["GroupMember"]] = relationship(
        "GroupMember", back_populates="group"
    )


class GroupMember(Base):
    __tablename__ = "group_members"
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), primary_key=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    user: Mapped[User] = relationship("User", back_populates="group_memberships")
    group: Mapped[Group] = relationship("Group", back_populates="memberships")


class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    paid_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(225), nullable=False)

    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    group: Mapped[Group] = relationship("Group", back_populates="expenses")
    paid_by: Mapped[User] = relationship(
        "User", back_populates="paid_expenses", foreign_keys=[paid_by_id]
    )
    shares: Mapped[list["ExpenseShare"]] = relationship(
        "ExpenseShare", back_populates="expense"
    )


class ExpenseShare(Base):
    __tablename__ = "expense_shares"
    expense_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expenses.id"), primary_key=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True, nullable=False
    )
    amount_owed: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        CheckConstraint("amount_owed > 0"),
        nullable=False,
    )
    user: Mapped[User] = relationship("User", back_populates="expense_shares")
    expense: Mapped[Expense] = relationship("Expense", back_populates="shares")

engin = create_async_engine(database_url)

async_session_maker = async_sessionmaker(engin,expire_on_commit=False)

async def create_db_and_table():
    async with engin.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        
async def get_async_session() -> AsyncGenerator[AsyncSession,None]:
    async with async_session_maker as session:
        yield session
        