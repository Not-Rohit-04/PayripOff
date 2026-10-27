from uuid import UUID
from fastapi import Depends, status, HTTPException, APIRouter
from decimal import Decimal, ROUND_DOWN
from ..db import User, Group, GroupMember, Expense, ExpenseShare, get_async_session
from ..dependencies import get_current_user
from ..schemas import ExpenseResponse, CreateExpense, GroupMemberBalance
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

router = APIRouter(tags=["Expenses"])


@router.post(
    "/groups/{group_id}/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_200_OK,
)
async def create_expense(
    group_id: UUID,
    expense_data: CreateExpense,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    membership_check = await session.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.member_id == current_user.id
        )
    )
    membership_check_result = membership_check.scalar_one_or_none()

    if membership_check_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )

    participant_result = await session.execute(
        select(User)
        .join(GroupMember, User.id == GroupMember.member_id)
        .where(
            GroupMember.group_id == group_id,
            User.username.in_(expense_data.participant_usernames),
        )
    )
    participants = participant_result.scalars().all()

    if len(participants) != len(set(expense_data.participant_usernames)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more usernames are invalid or not members of this group",
        )

    new_expense = Expense(
        group_id=group_id,
        paid_by_id=current_user.id,
        description=expense_data.description,
        amount=expense_data.amount,
    )

    session.add(new_expense)
    await session.flush()

    total_paise = int(expense_data.amount * 100)
    participant_count = len(participants)

    base_share, remainder = divmod(total_paise, participant_count)

    for i, participant in enumerate(participants):
        share_paise = base_share + (1 if i < remainder else 0)

        share = ExpenseShare(
            expense_id=new_expense.id,
            user_id=participant.id,
            amount_owed=Decimal(share_paise) / 100,
        )

        session.add(share)

    await session.commit()
    await session.refresh(new_expense)

    return new_expense


@router.get("/groups/{group_id}/expenses", response_model=list[ExpenseResponse])
async def get_groups_expense(
    group_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    querry_membership = await session.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.member_id == current_user.id
        )
    )
    membership_result = querry_membership.scalar_one_or_none()

    if membership_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )

    querry_for_expenses = await session.execute(
        select(Expense)
        .where(Expense.group_id == group_id)
        .order_by(Expense.created_at.desc())
    )

    expenses = querry_for_expenses.scalars().all()

    return expenses


async def calculate_group_expenses(
    group_id=UUID,
    session: AsyncSession = Depends(get_async_session),
) -> list[GroupMemberBalance]:

    querry_all_member = await session.execute(
        select(User)
        .join(GroupMember, User.id == GroupMember.member_id)
        .where(GroupMember.group_id == group_id)
    )
    members = querry_all_member.scalars().all()

    querry_total_paid = await session.execute(
        select(Expense.paid_by_id, func.sum(Expense.amount))
        .where(Expense.group_id == group_id)
        .group_by(Expense.paid_by_id)
    )
    paid_totals = dict(querry_total_paid.all())

    querry_total_owed = await session.execute(
        select(ExpenseShare.user_id, func.sum(ExpenseShare.amount_owed))
        .join(Expense, ExpenseShare.expense_id == Expense.id)
        .where(Expense.group_id == group_id)
        .group_by(ExpenseShare.user_id)
    )
    owed_totals = dict(querry_total_owed.all())

    balances = []

    for member in members:
        total_paid = paid_totals.get(member.id, Decimal("0.00"))
        total_owed = owed_totals.get(member.id, Decimal("0.00"))

        balances.append(
            GroupMemberBalance(
                user_id=member.id,
                username=member.username,
                total_paid=total_paid,
                total_owed=total_owed,
                net_balance=total_paid - total_owed,
            )
        )

    return balances

    pass


@router.get("/{group_id}/balances", response_model=list[GroupMemberBalance])
async def get_group_balance(
    group_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    querry_verify = await session.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.member_id == current_user.id
        )
    )
    querry_verify_result = querry_verify.scalar_one_or_none()

    if querry_verify_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=" Group not found"
        )
        
    balances = await calculate_group_expenses(session=session,group_id=group_id)
    
    return balances