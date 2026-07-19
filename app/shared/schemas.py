from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, field_serializer

MOSCOW_TIMEZONE = ZoneInfo("Europe/Moscow")


class ResponseSchema(BaseModel):
    """Базовая схема ответа с сериализацией времени по Москве."""

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_datetime(self, value: object) -> object:
        """Преобразует все datetime-поля ответа в московский часовой пояс."""

        if isinstance(value, datetime):
            return value.astimezone(MOSCOW_TIMEZONE)

        return value
