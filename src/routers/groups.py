from fastapi import Depends, APIRouter, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import Group, GroupMember, get_async_session, User
from ..schemas import CreateGroup, GroupResponse
from ..dependencies import get_current_user

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
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
