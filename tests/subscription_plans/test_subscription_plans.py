from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.branches.model import Branch
from app.modules.subscription_plans.model import SubscriptionPlan


async def test_owner_can_create_subscription_plan(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan_payload: dict[str, Any],
    branch: Branch,
) -> None:
    """Проверяет создание типа абонемента руководителем."""

    response = await client.post(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        json=subscription_plan_payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] > 0
    assert data["name"] == (subscription_plan_payload["name"].strip().lower())
    assert data["lessons_count"] == subscription_plan_payload["lessons_count"]
    assert data["price"] == subscription_plan_payload["price"]
    assert data["is_active"] is True

    assert data["branch"]["id"] == branch.id
    assert data["branch"]["name"] == branch.name
    assert data["branch"]["address"] == branch.address

    assert "branch_id" not in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_branch_admin_cannot_create_subscription_plan(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    subscription_plan_payload: dict[str, Any],
) -> None:
    """Проверяет запрет создания типа абонемента администратором."""

    response = await client.post(
        "/api/v1/subscription-plans",
        headers=branch_admin_headers,
        json=subscription_plan_payload,
    )

    assert response.status_code == 403


async def test_create_subscription_plan_without_authorization(
    client: AsyncClient,
    subscription_plan_payload: dict[str, Any],
) -> None:
    """Проверяет защиту создания типа абонемента."""

    response = await client.post(
        "/api/v1/subscription-plans",
        json=subscription_plan_payload,
    )

    assert response.status_code == 401


async def test_cannot_create_plan_for_nonexistent_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan_payload: dict[str, Any],
) -> None:
    """Проверяет создание типа абонемента для отсутствующего филиала."""

    subscription_plan_payload["branch_id"] = 999999

    response = await client.post(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        json=subscription_plan_payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Филиал не найден"


async def test_cannot_create_plan_for_inactive_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan_payload: dict[str, Any],
    branch: Branch,
    session: AsyncSession,
) -> None:
    """Проверяет запрет создания типа абонемента для неактивного филиала."""

    branch.is_active = False
    await session.commit()

    response = await client.post(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        json=subscription_plan_payload,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Нельзя создать тип абонемента для неактивного филиала")


async def test_lessons_count_must_be_positive(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan_payload: dict[str, Any],
) -> None:
    """Проверяет положительное количество занятий."""

    subscription_plan_payload["lessons_count"] = 0

    response = await client.post(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        json=subscription_plan_payload,
    )

    assert response.status_code == 422


async def test_lessons_count_cannot_be_negative(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan_payload: dict[str, Any],
) -> None:
    """Проверяет запрет отрицательного количества занятий."""

    subscription_plan_payload["lessons_count"] = -8

    response = await client.post(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        json=subscription_plan_payload,
    )

    assert response.status_code == 422


async def test_price_cannot_be_negative(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan_payload: dict[str, Any],
) -> None:
    """Проверяет запрет отрицательной стоимости."""

    subscription_plan_payload["price"] = -1

    response = await client.post(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        json=subscription_plan_payload,
    )

    assert response.status_code == 422


async def test_zero_price_is_allowed(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan_payload: dict[str, Any],
) -> None:
    """Проверяет возможность создания бесплатного типа абонемента."""

    subscription_plan_payload["price"] = 0

    response = await client.post(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        json=subscription_plan_payload,
    )

    assert response.status_code == 201
    assert response.json()["price"] == 0


async def test_cannot_create_duplicate_plan_in_same_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет уникальность названия внутри одного филиала."""

    response = await client.post(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        json={
            "branch_id": subscription_plan.branch_id,
            "name": subscription_plan.name,
            "lessons_count": 10,
            "price": 8000,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Тип абонемента с таким названием уже существует в филиале")


async def test_plan_name_uniqueness_is_case_insensitive(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет запрет дубликата с другим регистром."""

    response = await client.post(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        json={
            "branch_id": subscription_plan.branch_id,
            "name": f"  {subscription_plan.name.upper()}  ",
            "lessons_count": 10,
            "price": 8000,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Тип абонемента с таким названием уже существует в филиале")


async def test_same_plan_name_allowed_in_different_branches(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
    second_branch: Branch,
) -> None:
    """Проверяет одинаковые названия в разных филиалах."""

    response = await client.post(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        json={
            "branch_id": second_branch.id,
            "name": subscription_plan.name.upper(),
            "lessons_count": subscription_plan.lessons_count,
            "price": 7500,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["branch"]["id"] == second_branch.id
    assert data["name"] == subscription_plan.name.lower()


async def test_owner_can_get_subscription_plans(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
    second_subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет получение списка типов абонементов руководителем."""

    response = await client.get(
        "/api/v1/subscription-plans",
        headers=owner_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert {item["id"] for item in data} == {
        subscription_plan.id,
        second_subscription_plan.id,
    }


async def test_branch_admin_sees_only_own_branch_plans(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
    other_branch_subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет ограничение списка филиалом администратора."""

    response = await client.get(
        "/api/v1/subscription-plans",
        headers=branch_admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == subscription_plan.id
    assert data[0]["branch"]["id"] == subscription_plan.branch_id


async def test_branch_admin_cannot_override_branch_filter(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
    other_branch_subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет игнорирование чужого branch_id администратором."""

    response = await client.get(
        "/api/v1/subscription-plans",
        headers=branch_admin_headers,
        params={
            "branch_id": other_branch_subscription_plan.branch_id,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == subscription_plan.id


async def test_get_subscription_plans_without_authorization(
    client: AsyncClient,
) -> None:
    """Проверяет защиту списка типов абонементов."""

    response = await client.get(
        "/api/v1/subscription-plans",
    )

    assert response.status_code == 401


async def test_filter_subscription_plans_by_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
    other_branch_subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет фильтрацию типов абонементов по филиалу."""

    response = await client.get(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        params={
            "branch_id": subscription_plan.branch_id,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == subscription_plan.id


async def test_filter_only_active_subscription_plans(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
    inactive_subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет получение только активных типов абонементов."""

    response = await client.get(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        params={
            "active_only": True,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == subscription_plan.id
    assert data[0]["is_active"] is True


async def test_subscription_plans_are_ordered(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
    second_subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет сортировку типов абонементов по числу занятий."""

    response = await client.get(
        "/api/v1/subscription-plans",
        headers=owner_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert [item["lessons_count"] for item in data] == [8, 12]


async def test_owner_can_get_subscription_plan_by_id(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет получение типа абонемента по идентификатору."""

    response = await client.get(
        f"/api/v1/subscription-plans/{subscription_plan.id}",
        headers=owner_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == subscription_plan.id
    assert data["name"] == subscription_plan.name
    assert data["lessons_count"] == subscription_plan.lessons_count
    assert data["price"] == subscription_plan.price
    assert data["branch"]["id"] == subscription_plan.branch_id


async def test_get_nonexistent_subscription_plan(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет запрос отсутствующего типа абонемента."""

    response = await client.get(
        "/api/v1/subscription-plans/999999",
        headers=owner_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Тип абонемента не найден"


async def test_branch_admin_can_get_own_branch_plan(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет просмотр типа абонемента своего филиала."""

    response = await client.get(
        f"/api/v1/subscription-plans/{subscription_plan.id}",
        headers=branch_admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == subscription_plan.id


async def test_branch_admin_cannot_get_other_branch_plan(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    other_branch_subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет запрет просмотра типа абонемента чужого филиала."""

    response = await client.get(
        ("/api/v1/subscription-plans/" f"{other_branch_subscription_plan.id}"),
        headers=branch_admin_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Нет доступа к этому филиалу"


async def test_owner_can_update_subscription_plan(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет обновление типа абонемента руководителем."""

    response = await client.patch(
        f"/api/v1/subscription-plans/{subscription_plan.id}",
        headers=owner_headers,
        json={
            "name": "  8 ЗАНЯТИЙ ОБНОВЛЁННЫЙ  ",
            "lessons_count": 10,
            "price": 8000,
            "is_active": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "8 занятий обновлённый"
    assert data["lessons_count"] == 10
    assert data["price"] == 8000
    assert data["is_active"] is False


async def test_partial_update_preserves_other_fields(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет частичное обновление типа абонемента."""

    response = await client.patch(
        f"/api/v1/subscription-plans/{subscription_plan.id}",
        headers=owner_headers,
        json={
            "price": 7500,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["price"] == 7500
    assert data["name"] == subscription_plan.name
    assert data["lessons_count"] == subscription_plan.lessons_count
    assert data["is_active"] is True


async def test_branch_admin_cannot_update_subscription_plan(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет запрет обновления типа абонемента администратором."""

    response = await client.patch(
        f"/api/v1/subscription-plans/{subscription_plan.id}",
        headers=branch_admin_headers,
        json={
            "price": 8000,
        },
    )

    assert response.status_code == 403


async def test_update_plan_with_duplicate_name(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
    second_subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет запрет установки занятого названия."""

    response = await client.patch(
        f"/api/v1/subscription-plans/{subscription_plan.id}",
        headers=owner_headers,
        json={
            "name": f"  {second_subscription_plan.name.upper()}  ",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Тип абонемента с таким названием уже существует в филиале")


async def test_update_plan_with_same_name_is_allowed(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет обновление с тем же нормализованным названием."""

    response = await client.patch(
        f"/api/v1/subscription-plans/{subscription_plan.id}",
        headers=owner_headers,
        json={
            "name": f"  {subscription_plan.name.upper()}  ",
            "price": 7100,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == subscription_plan.name.lower()
    assert data["price"] == 7100


async def test_owner_can_move_plan_to_another_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
    second_branch: Branch,
) -> None:
    """Проверяет перенос типа абонемента в другой филиал."""

    response = await client.patch(
        f"/api/v1/subscription-plans/{subscription_plan.id}",
        headers=owner_headers,
        json={
            "branch_id": second_branch.id,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["branch"]["id"] == second_branch.id
    assert data["name"] == subscription_plan.name


async def test_cannot_move_plan_to_nonexistent_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
) -> None:
    """Проверяет перенос типа абонемента в отсутствующий филиал."""

    response = await client.patch(
        f"/api/v1/subscription-plans/{subscription_plan.id}",
        headers=owner_headers,
        json={
            "branch_id": 999999,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Филиал не найден"


async def test_cannot_move_plan_to_inactive_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan: SubscriptionPlan,
    second_branch: Branch,
    session: AsyncSession,
) -> None:
    """Проверяет перенос типа абонемента в неактивный филиал."""

    second_branch.is_active = False
    await session.commit()

    response = await client.patch(
        f"/api/v1/subscription-plans/{subscription_plan.id}",
        headers=owner_headers,
        json={
            "branch_id": second_branch.id,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Нельзя создать тип абонемента для неактивного филиала")


async def test_plan_name_is_normalized_on_create(
    client: AsyncClient,
    owner_headers: dict[str, str],
    subscription_plan_payload: dict[str, Any],
) -> None:
    """Проверяет нормализацию названия при создании."""

    subscription_plan_payload["name"] = "  16 ЗАНЯТИЙ  "

    response = await client.post(
        "/api/v1/subscription-plans",
        headers=owner_headers,
        json=subscription_plan_payload,
    )

    assert response.status_code == 201
    assert response.json()["name"] == "16 занятий"
