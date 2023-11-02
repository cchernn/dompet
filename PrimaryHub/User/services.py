import dataclasses
import datetime
import jwt
from .models import User
from django.conf import settings

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .models import User

@dataclasses.dataclass
class UserDataClass:
    username: str
    email: str
    id: int = None
    password: str = None
    first_name: str = ""
    last_name: str = ""

    @classmethod
    def from_instance(cls, user: "User") -> "UserDataClass":
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
        )

def create_user(userdc: "UserDataClass") -> "UserDataClass":
    instance = User(
        username=userdc.username,
        email=userdc.email,
        first_name=userdc.first_name,
        last_name=userdc.last_name,
    )

    if userdc.password is not None:
        instance.set_password(userdc.password)

    instance.save()

    return UserDataClass.from_instance(user=instance)
