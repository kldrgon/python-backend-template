from dataclasses import dataclass


@dataclass
class Address:
    province: str | None = None
    city: str | None = None
    district: str | None = None
