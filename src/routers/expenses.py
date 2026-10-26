from uuid import UUID
from fastapi import Depends, status, HTTPException, APIRouter
from decimal import Decimal, ROUND_DOWN
from ..db import User, Group, GroupMember, Expense, ExpenseShare, get_async_session
from ..dependencies import get_current_user
from ..schemas import ExpenseResponse, CreateExpense
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
