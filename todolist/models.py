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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    parent = models.ForeignKey(
        'self', null=True, blank=True, related_name='subtasks', on_delete=models.CASCADE
    )

    def __str__(self):
        return self.title

    def get_numbering(self):
        """Генерация иерархической нумерации задачи."""
        numbering = []
        task = self
        while task:
            siblings = (
                task.parent.subtasks.order_by('created_at') if task.parent
                else Task.objects.filter(parent=None).order_by('created_at')
            )
            position = list(siblings).index(task) + 1
            numbering.append(position)
            task = task.parent
        return '.'.join(map(str, numbering[::-1]))

    def check_completion(self):
        """Проверяет, выполнены ли все подзадачи (на всех уровнях), и обновляет статус задачи."""
        if self.subtasks.exists():
            # Если у задачи есть подзадачи, проверяем, все ли они выполнены
            self.completed = all(subtask.completed for subtask in self.subtasks.all())
            self.save()
        # Если у текущей задачи есть родительская задача, проверяем её статус
        if self.parent:
            self.parent.check_completion()
