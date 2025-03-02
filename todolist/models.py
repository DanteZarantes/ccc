from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

# Possible status choices for tasks
STATUS_CHOICES = (
    ('todo', 'To-Do'),
    ('in_progress', 'In Progress'),
    ('done', 'Done'),
)


class Task(models.Model):
    """
    Task model representing an individual to-do item.
    Supports hierarchical (parent-child) relationships, status, tags, and more.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    todolist = models.ForeignKey(
        'ToDoList',
        null=True,
        blank=True,
        related_name='tasks',
        on_delete=models.CASCADE
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='subtasks',
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=200)
    detail = models.TextField(blank=True, null=True)  # Detailed field for task description

    # Renamed from "completed" to "is_completed"
    is_completed = models.BooleanField(default=False)

    # New fields for status, tags, and completed date
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='todo'
    )
    tags = models.CharField(max_length=200, blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def get_numbering(self):
        """
        Creates a hierarchical numbering (e.g., 1, 1.1, 1.1.1) based on parent-child relationships.
        """
        numbering = []
        task = self
        while task:
            if task.parent:
                siblings = task.parent.subtasks.order_by('created_at')
            else:
                siblings = Task.objects.filter(parent=None, todolist=self.todolist).order_by('created_at')
            position = list(siblings).index(task) + 1
            numbering.append(position)
            task = task.parent
        return '.'.join(map(str, numbering[::-1]))

    def check_completion(self):
        """
        Checks if all subtasks are completed, then updates this task's is_completed field.
        Also updates the parent task(s) recursively.
        """
        if self.subtasks.exists():
            # If any subtask is not completed, the parent is not fully completed
            all_subs_done = all(subtask.is_completed for subtask in self.subtasks.all())
            self.is_completed = all_subs_done

            if all_subs_done:
                self.status = 'done'
                if not self.completed_at:
                    self.completed_at = timezone.now()
            else:
                # If not all subtasks are completed, reset to 'todo' or 'in_progress' as needed
                # Here we simply set it back to 'todo'
                self.status = 'todo'
                self.completed_at = None

            self.save()

        # Propagate completion check up the chain
        if self.parent:
            self.parent.check_completion()


class ToDoList(models.Model):
    """
    Model for a to-do list or "project" block.
    Includes a name, optional description, and a reference to the user.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)  # Field for project description
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    """
    Custom user model with additional fields such as phone_number, date_of_birth, and avatar.
    """
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png', blank=True)
    about = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Write something about yourself."
    )

    def __str__(self):
        return self.username
