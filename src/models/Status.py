from enum import Enum


class AttentionStatus(Enum):

    PENDING = "PENDING"
    REVIEWED = "REVIEWED"


class CatalogStatus(Enum):

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"
