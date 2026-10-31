import pytest
from src.db import GroupMember, User
from sqlalchemy import select
from uuid import UUID


@pytest.mark.asyncio
async def test_successful_create_group(authenticated_client):

    client = authenticated_client["client"]
    headers = authenticated_client["headers"]

    response = await client.post(
        "/groups",
        headers=headers,
        json={"name": "test Grp", "description": "for grp test"},
    )
    response_data = response.json()

    assert response.status_code == 201
    assert "id" in response_data
    assert "created_at" in response_data
    assert "created_by_id" in response_data
    assert response_data["name"] == "test Grp"
    assert response_data["description"] == "for grp test"


@pytest.mark.asyncio
async def test_unauthenticated_group_creation(client):
    response = await client.post(
        "/groups", json={"name": "test Grp", "description": "for grp test"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_empty_group_name(authenticated_client):

    client = authenticated_client["client"]
    headers = authenticated_client["headers"]

    response = await client.post(
        "/groups", headers=headers, json={"name": "", "description": "for grp test"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_long_group_name(authenticated_client):
    client = authenticated_client["client"]
    headers = authenticated_client["headers"]

    response = await client.post(
        "/groups",
        headers=headers,
        json={"name": "a" * 151, "description": "lalalalal!!!"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_group_without_description(authenticated_client):
    client = authenticated_client["client"]
    headers = authenticated_client["headers"]

    response = await client.post(
        "/groups", headers=headers, json={"name": "test group"}
    )
    response_data = response.json()
    assert response.status_code == 201
    assert response_data["description"] == None


@pytest.mark.asyncio
async def test_creater_is_member(authenticated_client, db_session):
    client = authenticated_client["client"]
    headers = authenticated_client["headers"]

    response = await client.post(
        "/groups", headers=headers, json={"name": "test group"}
    )

    response_data = response.json()

    assert response.status_code == 201

    group_id = UUID(response_data["id"])

    result = await db_session.execute(select(User).where(User.email == "abc@gmail.com"))
    user = result.scalar_one_or_none()

    assert user is not None

    result = await db_session.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.member_id == user.id
        )
    )
    member = result.scalar_one_or_none()

    assert member is not None
