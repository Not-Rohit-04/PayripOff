import uuid

from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import Group, GroupMember, get_async_session, User
from ..schemas import CreateGroup, GroupResponse
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


@router.get(
    "/{group_id}",response_model=GroupResponse
)
async def get_group(
    group_id : uuid.UUID,
    session : AsyncSession = Depends(get_async_session),
    current_user : User = Depends(get_current_user)
):
    
    querry = (
        select(Group).join(
            GroupMember , Group.id == GroupMember.group_id
        ).where(
            Group.id == group_id,
            GroupMember.member_id == current_user.id
        )
    )
    
    result = await session.execute(querry)
    
    group = result.scalar_one_or_none()
    
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Group not found.'
        )
        
    return group