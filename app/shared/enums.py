from enum import IntEnum, StrEnum


class UserRole(StrEnum):
    """Роли сотрудников CRM."""

    OWNER = "owner"
    BRANCH_ADMIN = "branch_admin"


class StudentStatus(StrEnum):
    """Статусы ученика."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class Weekday(IntEnum):
    """Дни недели в формате Python datetime.weekday()."""

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class LessonStatus(StrEnum):
    """Статусы конкретного занятия."""

    PLANNED = "planned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SubscriptionStatus(StrEnum):
    """Вычисляемые статусы абонемента ученика."""

    UPCOMING = "upcoming"
    ACTIVE = "active"
    EXPIRED = "expired"
