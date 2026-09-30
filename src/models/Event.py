from datetime import datetime
from models.Status import (
    AttentionStatus,
    CatalogStatus
)


class Event:

    def __init__(
        self,
        identifier,
        magnitude,
        depth,
        x,
        y,
        date_time,
        revision,
        priority,
        is_populated_zone
    ):

        self.identifier = int(identifier)

        self.magnitude = float(magnitude)
        self.depth = float(depth)

        self.x = float(x)
        self.y = float(y)

        self.date_time = date_time

        self.revision = int(revision)

        self.priority = int(priority)

        self.is_populated_zone = is_populated_zone

        self.attention_status = (
            AttentionStatus.PENDING
        )

        self.catalog_status = (
            CatalogStatus.ACTIVE
        )

        self.accepted_stations = set()


    def get_key(self):

        return (
            self.priority,
            self.magnitude,
            self.identifier
        )


    def add_accepted_station(
        self,
        station_name
    ):

        self.accepted_stations.add(
            station_name
        )


    def mark_as_reviewed(self):

        self.attention_status = (
            AttentionStatus.REVIEWED
        )


    def mark_as_pending(self):

        self.attention_status = (
            AttentionStatus.PENDING
        )


    def archive(self):

        self.catalog_status = (
            CatalogStatus.ARCHIVED
        )


    def activate(self):

        self.catalog_status = (
            CatalogStatus.ACTIVE
        )


    def delete(self):

        self.catalog_status = (
            CatalogStatus.DELETED
        )


    def __str__(self):

        return (
            f"Event("
            f"SIS-{self.identifier:06d}, "
            f"K={self.get_key()}, "
            f"Revision={self.revision}"
            f")"
        )

    def to_dict(self):

        return {
            "identifier": self.identifier,
            "magnitude": self.magnitude,
            "depth": self.depth,
            "x": self.x,
            "y": self.y,
            "date_time": self.date_time,
            "revision": self.revision,
            "priority": self.priority,
            "is_populated_zone": self.is_populated_zone
        }


 