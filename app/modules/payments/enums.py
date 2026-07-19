from enum import StrEnum


class PaymentMethod(StrEnum):
    """Способ оплаты."""

    CASH = "cash"
    QR_CODE = "qr_code"


class PaymentStatus(StrEnum):
    """Статус оплаты."""

    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"