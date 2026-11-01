import enum


class UserRole(str, enum.Enum):
    customer = "customer"
    organizer = "organizer"
    admin = "admin"


class EventStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    rejected = "rejected"
    suspended = "suspended"


class SeatStatus(str, enum.Enum):
    available = "available"
    reserved = "reserved"
    sold = "sold"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    cancelled = "cancelled"
    expired = "expired"
    refunded = "refunded"


class TicketStatus(str, enum.Enum):
    reserved = "reserved"
    valid = "valid"
    cancelled = "cancelled"
