from pydantic import BaseModel, EmailStr, field_validator
import re


class Lead(BaseModel):
    fullName: str
    email: str | None = None
    phone: str
    address: str
    zip: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) < 10:
            raise ValueError("Phone number must have at least 10 digits.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email address.")
        return v.lower().strip()
