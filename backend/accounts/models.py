from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Users log in with their email address.

    A custom user model is created at the very start of the project because
    Django makes it hard to switch to one after the first migration.
    """

    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email
