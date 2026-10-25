import uuid

from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import Group, GroupMember, get_async_session, User
from ..schemas import CreateGroup, GroupResponse, AddGroupMember
from ..dependencies import get_current_user

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_data: CreateGroup,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    new_group = Group(
        name=group_data.name,
        description=group_data.description,
        created_by_id=current_user.id,
    )

    session.add(new_group)
    await session.flush()

    membership = GroupMember(group_id=new_group.id, member_id=current_user.id)

    session.add(membership)

    await session.commit()
    await session.refresh(new_group)

    return new_group


@router.get("", response_model=list[GroupResponse], status_code=status.HTTP_200_OK)
async def get_gropus(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    querry = (
        select(Group)
        .join(GroupMember, Group.id == GroupMember.group_id)
        .where(GroupMember.member_id == current_user.id)
    )

    result = await session.execute(querry)

    groups = result.scalars().all()

    return groups


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):

    querry = (
        select(Group)
        .join(GroupMember, Group.id == GroupMember.group_id)
        .where(Group.id == group_id, GroupMember.member_id == current_user.id)
    )

    result = await session.execute(querry)

    group = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found."
        )

    return group


@router.post("/{group_id}/members", status_code=status.HTTP_200_OK)
async def add_group_member(
    group_id: uuid.UUID,
    member_data: AddGroupMember,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    membership_result = await session.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.member_id == current_user.id
        )
    )
    membership = membership_result.scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not Found"
        )

    user_result = await session.execute(
        select(User).where(User.username == member_data.username)
    )

    user_to_add = user_result.scalar_one_or_none()

    if user_to_add is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    existing__user = await session.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.member_id == user_to_add.id
        )
    )

    existing_result = existing__user.scalar_one_or_none()

    if existing_result is not None:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists in the group.",
        )

    new_member = GroupMember(group_id=group_id, member_id=user_to_add.id)

    session.add(new_member)
    await session.commit()

    return {"message": f"{user_to_add.username} added to the group"}
