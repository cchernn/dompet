import os
import dataclasses
from .models import User
from django.shortcuts import get_object_or_404
from rest_framework import exceptions

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .models import User

from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver
from django.template.loader import render_to_string
# from django.urls import reverse

from django_rest_passwordreset.signals import reset_password_token_created

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

def get_user(username:str, email:str):
    user = get_object_or_404(User, username=username)

    if user:
        if user.email != email:
            raise exceptions.NotFound("Email does not match user.")

    return user

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param args:
    :param kwargs:
    :return:
    """
    front_end_url = os.getenv("WEB_BASE_URL")

    # send an e-mail to the user
    context = {
        'current_user': reset_password_token.user,
        'username': reset_password_token.user.username,
        'email': reset_password_token.user.email,
        'reset_password_url': "{}?token={}".format(
            # instance.request.build_absolute_uri(reverse('password_reset:reset-password-confirm')),
            f"{front_end_url}/reset-password-confirm",
            reset_password_token.key)
    }

    # render email text
    email_html_message = render_to_string('email/user_reset_password.html', context)
    email_plaintext_message = render_to_string('email/user_reset_password.txt', context)

    msg = EmailMultiAlternatives(
        # title:
        "Password Reset for {title}".format(title="Some website title"),
        # message:
        email_plaintext_message,
        # from:
        "noreply@somehost.local",
        # to:
        [reset_password_token.user.email]
    )
    msg.attach_alternative(email_html_message, "text/html")
    msg.send()