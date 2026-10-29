from uuid import UUID
from fastapi import Depends, status, HTTPException, APIRouter
from decimal import Decimal, ROUND_DOWN
from ..db import (
    User,
    Group,
    GroupMember,
    Expense,
    ExpenseShare,
    Settlement,
    get_async_session,
)
from ..dependencies import get_current_user
from ..schemas import (
    ExpenseResponse,
    CreateExpense,
    GroupMemberBalance,
    SettlementSuggestion,
    SettlementResponse,
    CreateSettlement,
)
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
    group_id: UUID,
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

    querry_settlements_sent = await session.execute(
        select(Settlement.from_user_id, func.sum(Settlement.amount_transferred))
        .where(Settlement.group_id == group_id)
        .group_by(Settlement.from_user_id)
    )
    settlements_sent = dict(querry_settlements_sent.all())

    querry_settlements_recieved = await session.execute(
        select(Settlement.to_user_id, func.sum(Settlement.amount_transferred))
        .where(Settlement.group_id == group_id)
        .group_by(Settlement.to_user_id)
    )

    settlements_recieved = dict(querry_settlements_recieved.all())
    balances = []

    for member in members:
        total_paid = paid_totals.get(member.id, Decimal("0.00"))
        total_owed = owed_totals.get(member.id, Decimal("0.00"))
        total_sent = settlements_sent.get(member.id, Decimal("0.00"))
        total_recieved = settlements_recieved.get(member.id, Decimal("0.00"))

        balances.append(
            GroupMemberBalance(
                user_id=member.id,
                username=member.username,
                total_paid=total_paid,
                total_owed=total_owed,
                net_balance=total_paid - total_owed + total_sent - total_recieved,
            )
        )

    return balances


@router.get("/groups/{group_id}/balances", response_model=list[GroupMemberBalance])
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

    balances = await calculate_group_expenses(session=session, group_id=group_id)

    return balances


@router.get("/groups/{group_id}/settlements", response_model=list[SettlementSuggestion])
async def get_group_settlements(
    group_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    querry_verify_user = await session.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.member_id == current_user.id
        )
    )
    result_verify_user = querry_verify_user.scalar_one_or_none()

    if result_verify_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )

    balances = await calculate_group_expenses(session=session, group_id=group_id)

    creditors = [member for member in balances if member.net_balance > 0]
    debtors = [member for member in balances if member.net_balance < 0]

    settlements = []

    debtor_index = 0
    creditor_index = 0
    remaining_debts = {member.user_id: abs(member.net_balance) for member in debtors}
    remaining_credits = {member.user_id: member.net_balance for member in creditors}

    while debtor_index < len(debtors) and creditor_index < len(creditors):
        creditor = creditors[creditor_index]
        debtor = debtors[debtor_index]

        transfer_amt = min(
            remaining_debts[debtor.user_id], remaining_credits[creditor.user_id]
        )

        settlements.append(
            SettlementSuggestion(
                from_user=debtor.user_id,
                from_username=debtor.username,
                to_user=creditor.user_id,
                to_username=creditor.username,
                amount=transfer_amt,
            )
        )

        remaining_debts[debtor.user_id] -= transfer_amt
        remaining_credits[creditor.user_id] -= transfer_amt

        if remaining_debts[debtor.user_id] == Decimal("0.00"):
            debtor_index += 1

        if remaining_credits[creditor.user_id] == Decimal("0.00"):
            creditor_index += 1

    return settlements


@router.post(
    "/groups/{group_id}/settlements/{to_user_id}",
    response_model=SettlementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_settlement(
    group_id: UUID,
    to_user_id: UUID,
    settelment_data: CreateSettlement,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    check_users_querry = await session.execute(
        select(GroupMember.member_id).where(
            GroupMember.group_id == group_id,
            GroupMember.member_id.in_([current_user.id, to_user_id]),
        )
    )
    members_ids = set(check_users_querry.scalars().all())
    if current_user.id == to_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Can't settle with yourself"
        )
    if members_ids != {current_user.id, to_user_id}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both users must belong to the group",
        )
    balances = await calculate_group_expenses(session=session, group_id=group_id)
    sender_balance = next(
        (balance for balance in balances if balance.user_id == current_user.id), None
    )
    reciver_balance = next(
        (balance for balance in balances if balance.user_id == to_user_id), None
    )

    if sender_balance is None or reciver_balance is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not find both users' balances in this group",
        )
    if sender_balance.net_balance >= 0 or reciver_balance.net_balance <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sender must owe money and recipient must be owed money",
        )

    if (
        settelment_data.amount > abs(sender_balance.net_balance)
        or settelment_data.amount > reciver_balance.net_balance
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Settlement amount exceeds the outstanding balance",
        )

    new_settlement = Settlement(
        group_id=group_id,
        from_user_id=current_user.id,
        to_user_id=to_user_id,
        amount_transferred=settelment_data.amount,
    )

    session.add(new_settlement)
    await session.commit()
    await session.refresh(new_settlement)

    return new_settlement


@router.get(
    "/groups/{group_id}/expenses/{expense_id}",
    response_model=ExpenseResponse,
    status_code=status.HTTP_200_OK,
)
async def get_expense(
    group_id: UUID,
    expense_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    querry_membership = await session.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id, current_user.id == GroupMember.member_id
        )
    )
    result_querry_membership = querry_membership.scalar_one_or_none()

    if result_querry_membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )

    querry_expenses_verify = await session.execute(
        select(Expense).where(Expense.group_id == group_id, Expense.id == expense_id)
    )
    result_expense_verify = querry_expenses_verify.scalar_one_or_none()

    if result_expense_verify is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not in the group "
        )

    return result_expense_verify
