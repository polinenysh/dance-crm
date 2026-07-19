from httpx import AsyncClient


async def test_health_check(client: AsyncClient) -> None:
    """Проверяет доступность приложения."""

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_database_health_check(client: AsyncClient) -> None:
    """Проверяет подключение приложения к тестовой базе."""

    response = await client.get("/health/database")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "available",
    }