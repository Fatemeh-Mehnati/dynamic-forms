from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model. Extra fields (phone) are added in A5."""
    pass