from uuid import uuid4

from django.db import models

from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class User(AbstractUser):

    username = None

    email = models.EmailField(_("email address"), unique=True)

    uuid = models.CharField(max_length=36, default=uuid4, unique=True)

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email
