from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

class Task(models.Model):
    """Модель задачи."""
    title = models.CharField(max_length=200)
    detail = models.TextField(blank=True, null=True)  # <-- Поле для подробного описания
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='subtasks',
        on_delete=models.CASCADE
    )
    todolist = models.ForeignKey(
        'ToDoList',
        null=True,
        blank=True,
        related_name='tasks',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.title

    def get_numbering(self):
        """Создает иерархическую нумерацию для задач."""
        numbering = []
        task = self
        while task:
            # Смотрим, среди "братьев" какая у задачи позиция
            if task.parent:
                siblings = task.parent.subtasks.order_by('created_at')
            else:
                siblings = Task.objects.filter(parent=None, todolist=self.todolist).order_by('created_at')
            position = list(siblings).index(task) + 1
            numbering.append(position)
            task = task.parent
        return '.'.join(map(str, numbering[::-1]))  # Переворачиваем список и склеиваем

    def check_completion(self):
        """Проверяет завершение всех подзадач и обновляет статус задачи."""
        if self.subtasks.exists():
            self.completed = all(subtask.completed for subtask in self.subtasks.all())
            self.save()
        if self.parent:
            self.parent.check_completion()


class ToDoList(models.Model):
    """
    Модель для блоков To-Do List (или "Проектов").
    Добавили поле description, чтобы можно было хранить описание проекта.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)  # <-- Новое поле для описания
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    """Модель кастомного пользователя."""
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png', blank=True)
    about = models.TextField(max_length=500, blank=True, null=True, help_text="Write something about yourself.")

    def __str__(self):
        return self.username
