from django.shortcuts import render, redirect, get_object_or_404  # Добавлен get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.http import HttpResponse
from .models import Task
from .tokens import account_activation_token
from .forms import CustomUserCreationForm, TaskForm, ProfileForm


# Главная страница
def homepage(request):
    """Обработчик для отображения главной страницы."""
    return render(request, 'homepage.html')


def task_list_view(request):
    return render(request, 'task_list.html')


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            username = form.cleaned_data.get('username')

            if User.objects.filter(email=email).exists():
                messages.error(request, 'Этот email уже используется. Попробуйте другой.')
                return render(request, 'register.html', {'form': form})

            if User.objects.filter(username=username).exists():
                messages.error(request, 'Этот логин уже используется. Попробуйте другой.')
                return render(request, 'register.html', {'form': form})

            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            login(request, user)
            messages.success(request, 'Регистрация прошла успешно! Добро пожаловать!')
            return redirect('home')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = CustomUserCreationForm()

    return render(request, 'register.html', {'form': form})


def home(request):
    return render(request, 'home.html', {'message': 'Добро пожаловать на домашнюю страницу!'})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Account activated successfully!')
        return redirect('login')
    else:
        return HttpResponse('Activation link is invalid!')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'todolist/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def task_list(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            return redirect('task_list')
    else:
        form = TaskForm()

    # Сортировка задач по статусу: сначала невыполненные, потом выполненные
    tasks = Task.objects.filter(user=request.user, parent=None).order_by('completed', 'created_at')

    return render(request, 'task_list.html', {'tasks': tasks, 'form': form})

# Функция для удаления задачи
@login_required
def delete_task(request, task_id):
    task = Task.objects.get(id=task_id, user=request.user)
    task.delete()
    return redirect('task_list')


def toggle_task(request, task_id):
    """
    Переключает статус задачи (выполнено/не выполнено).
    """
    task = get_object_or_404(Task, id=task_id, user=request.user)  # Исправлено
    if request.method == "POST":
        task.completed = not task.completed
        task.save()
        # Проверяем статус родительских задач, если они есть
        if task.parent:
            task.parent.check_completion()
    return redirect('task_list')


def add_subtask(request, parent_id):
    parent_task = get_object_or_404(Task, id=parent_id, user=request.user)  # Используем get_object_or_404
    if request.method == "POST":
        title = request.POST.get("title")
        if title:
            Task.objects.create(
                title=title,
                parent=parent_task,
                user=request.user,
            )
    return redirect('task_list')


@login_required
def profile_edit(request):
    """Редактирование профиля пользователя."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен.')
            return redirect('task_list')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'profile_edit.html', {'form': form})
