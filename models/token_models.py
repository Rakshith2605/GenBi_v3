from datetime import datetime, timezone, timedelta
from typing import ClassVar
from pydantic import BaseModel

class TokenPayload(BaseModel):
    iss: str
    aud: str
    auth_time: int
    user_id: str
    sub: str
    iat: int
    exp: int
    email: str
    email_verified: bool

    @property
    def issued_at(self) -> datetime:
        return datetime.fromtimestamp(self.iat, tz=timezone.utc)

    @property
    def expires_at(self) -> datetime:
        return datetime.fromtimestamp(self.exp, tz=timezone.utc)

class LocalTokenPayload(TokenPayload):
    # Annotate LOCAL_OFFSET as a ClassVar so Pydantic ignores it as a model field.
    LOCAL_OFFSET: ClassVar[timedelta] = timedelta(hours=2)

    @property
    def issued_at_local(self) -> datetime:
        return self.issued_at.astimezone(timezone(self.LOCAL_OFFSET))

    @property
    def expires_at_local(self) -> datetime:
        return self.expires_at.astimezone(timezone(self.LOCAL_OFFSET))
