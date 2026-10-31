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


@pytest.mark.asyncio
async def test_group_retrieval(authenticated_client):
    client = authenticated_client["client"]
    headers = authenticated_client["headers"]

    response = await client.post(
        "/groups", headers=headers, json={"name": "test group"}
    )
    created_group = response.json()

    assert response.status_code == 201

    response = await client.get(
        "/groups",
        headers=headers,
    )

    assert response.status_code == 200

    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 1
    assert any(
        group["id"] == created_group["id"] and group["name"] == created_group["name"]
        for group in response_data
    )


@pytest.mark.asyncio
async def test_multi_group_retrieval(authenticated_client):
    client = authenticated_client["client"]
    headers = authenticated_client["headers"]
    created_groups = []

    response = await client.post(
        "/groups", headers=headers, json={"name": "test group"}
    )
    created_group = response.json()
    assert response.status_code == 201
    created_groups.append(created_group)

    response = await client.post(
        "/groups", headers=headers, json={"name": "test group 2"}
    )
    created_group = response.json()
    assert response.status_code == 201
    created_groups.append(created_group)

    response = await client.post(
        "/groups", headers=headers, json={"name": "test group 3"}
    )
    created_group = response.json()
    assert response.status_code == 201
    created_groups.append(created_group)

    response = await client.get(
        "/groups",
        headers=headers,
    )

    assert response.status_code == 200

    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 3
    returned_ids = {group["id"] for group in response_data}
    created_ids = {group["id"] for group in created_groups}
    assert returned_ids == created_ids


@pytest.mark.asyncio
async def test_user_with_no_group_retrieval(authenticated_client):
    client = authenticated_client["client"]
    headers = authenticated_client["headers"]
    response = await client.get(
        "/groups",
        headers=headers,
    )

    response_data = response.json()

    assert response.status_code == 200
    assert isinstance(response_data, list)
    assert len(response_data) == 0
    assert response_data == []


@pytest.mark.asyncio
async def test_group_membership_isolation(authenticated_client):
    client = authenticated_client["client"]
    headers = authenticated_client["headers"]

    response = await client.post(
        "/groups", headers=headers, json={"name": "test group"}
    )

    assert response.status_code == 201

    response = await client.post(
        "/auth/register",
        json={"username": "Rob", "email": "abbc@gmail.com", "password": "1234passse"},
    )

    assert response.status_code == 201

    response = await client.post(
        "/auth/login", json={"email": "abbc@gmail.com", "password": "1234passse"}
    )

    assert response.status_code == 200

    response_data = response.json()

    token = response_data["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/groups", headers=headers)
    response_data = response.json()

    assert response.status_code == 200
    assert isinstance(response_data, list)
    assert response_data == []
