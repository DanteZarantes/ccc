from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser


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
        """Generates hierarchical numbering for tasks."""
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
        return '.'.join(map(str, numbering[::-1]))  # Reverses numbering

    def check_completion(self):
        """Checks if all subtasks are completed and updates the task status."""
        if self.subtasks.exists():
            self.completed = all(subtask.completed for subtask in self.subtasks.all())
            self.save()
        if self.parent:
            self.parent.check_completion()

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png', blank=True)

    def __str__(self):
        return self.username