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
    detail = models.TextField(blank=True, null=True)  # Detailed description

    is_completed = models.BooleanField(default=False)

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
            all_subs_done = all(subtask.is_completed for subtask in self.subtasks.all())
            self.is_completed = all_subs_done
            if all_subs_done:
                self.status = 'done'
                if not self.completed_at:
                    self.completed_at = timezone.now()
            else:
                self.status = 'todo'
                self.completed_at = None
            self.save()
        if self.parent:
            self.parent.check_completion()


class ToDoList(models.Model):
    """
    Model for a to-do list.
    Includes a name, optional description, and a reference to the user.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Project(models.Model):
    """
    Autonomous Project model.
    This model is independent from To-Do lists and can be used to manage projects separately.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
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
    ACCOUNT_TYPE_CHOICES = (
        ('free', 'Free'),
        ('business', 'Business'),
        ('premium', 'Premium'),
    )
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default='free'
    )

    def __str__(self):
        return self.username


class Subscription(models.Model):
    """
    Model to store user subscriptions (paid plans).
    """
    PLAN_CHOICES = (
        ('business', 'Business'),
        ('premium', 'Premium'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.plan}"


class Payment(models.Model):
    """
    Model to store payment transactions (e.g., for Stripe).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    plan = models.CharField(max_length=20)
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, null=True)
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Paid" if self.paid else "Not Paid"
        return f"{self.user.username} - {self.plan} - {status}"


class Message(models.Model):
    """
    Model to store direct messages between users.
    """
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.recipient.username}"
