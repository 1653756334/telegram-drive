from __future__ import annotations

from pydantic import BaseModel


class SendCodeRequest(BaseModel):
    phone: str


class VerifyCodeRequest(BaseModel):
    phone: str
    code: str
    phone_code_hash: str
    password: str | None = None


class UploadResult(BaseModel):
    file_id: int
    name: str
    size: int

