from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  # Уникальный email для всех пользователей
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # Дополнительное поле
    date_of_birth = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.username

class Task(models.Model):
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Используем AUTH_USER_MODEL

    def __str__(self):
        return self.title