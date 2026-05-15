from pydantic import BaseModel
from uuid import UUID


class UserResponse(BaseModel):
    id: UUID
    phone_number: str
    locale: str
    country: str

    class Config:
        from_attributes = True


class AuthSyncRequest(BaseModel):
    firebase_token: str


class AuthSyncResponse(BaseModel):
    user_id: UUID
    message: str
