from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Literal


ServiceType = Literal["standard", "deep", "move-in-out", "airbnb"]
Frequency = Literal["one-time", "weekly", "biweekly", "monthly"]

VALID_ADDONS = {
    "inside_fridge",
    "inside_oven",
    "interior_windows",
    "laundry",
    "cabinets",
}

SERVICE_TYPE_LABELS: dict[str, str] = {
    "standard": "Standard Clean",
    "deep": "Deep Clean",
    "move-in-out": "Move-in / Move-out Clean",
    "airbnb": "Airbnb Turnover Clean",
}

FREQUENCY_LABELS: dict[str, str] = {
    "one-time": "One-time",
    "monthly": "Monthly",
    "biweekly": "Bi-weekly",
    "weekly": "Weekly",
}


class ServiceInfo(BaseModel):
    serviceType: ServiceType
    beds: int | None = None
    baths: float | None = None
    sqft: int | None = None
    frequency: Frequency
    addons: list[str] | None = None
    notes: str | None = None

    @field_validator("addons")
    @classmethod
    def validate_addons(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        invalid = [a for a in v if a not in VALID_ADDONS]
        if invalid:
            raise ValueError(
                f"Unknown add-ons: {invalid}. Valid options: {sorted(VALID_ADDONS)}"
            )
        return v

    @field_validator("beds")
    @classmethod
    def validate_beds(cls, v: int | None) -> int | None:
        if v is not None and (v < 0 or v > 20):
            raise ValueError("Beds must be between 0 and 20.")
        return v

    @field_validator("baths")
    @classmethod
    def validate_baths(cls, v: float | None) -> float | None:
        if v is not None and (v < 0 or v > 20):
            raise ValueError("Baths must be between 0 and 20.")
        return v
