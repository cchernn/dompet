from django.db import models
from django.contrib.auth import models as auth_models

# Create your models here.
class UserManager(auth_models.BaseUserManager):
    def create_user(self, username:str, email:str, password:str=None, **kwargs) -> "User":
        if not username:
            raise ValueError("User must have a username")
        
        if not email:
            raise ValueError("User must have an email.")
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **kwargs)
        user.set_password(password)
        user.is_active = True
        user.save()

        return user

    def create_superuser(self, username:str, email:str, password:str=None, **kwargs) -> "User":
        kwargs.setdefault('is_staff', True)
        kwargs.setdefault('is_superuser', True)

        user = self.create_user(
            username=username,
            email=email,
            password=password,
            **kwargs,
        )

        return user

class User(auth_models.AbstractUser):
    first_name = models.CharField(verbose_name="First Name", max_length=255, blank=True)
    last_name = models.CharField(verbose_name="Last Name", max_length=255, blank=True)
    email = models.EmailField(verbose_name="Email", max_length=255, unique=True, error_messages={"unique": "A user with that email already exists."})
    username = models.CharField(verbose_name="Username", max_length=255, unique=True, error_messages={"unique": "A user with that username already exists."})

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]
