from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django.shortcuts import render, redirect
from .models import Task
from .tokens import account_activation_token
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, TaskForm


def task_list_view(request):
    return render(request, 'task_list.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = False  # Аккаунт будет активирован после подтверждения по почте
            user.save()

            # Отправка email для подтверждения
            current_site = get_current_site(request)
            subject = 'Activate your account'
            message = render_to_string('activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            email = EmailMessage(subject, message, to=[user.email])
            email.send()

            return HttpResponse('Please confirm your email to complete registration.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

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
            task = form.save(commit=False)  # Не сохраняем сразу
            task.user = request.user        # Устанавливаем текущего пользователя
            task.save()                     # Сохраняем задачу
            return redirect('task_list')
    else:
        form = TaskForm()

    tasks = Task.objects.filter(user=request.user, parent=None)  # Загружаем задачи только текущего пользователя
    return render(request, 'task_list.html', {'tasks': tasks, 'form': form})


def delete_task(request, task_id):
    task = Task.objects.get(id=task_id, user=request.user)  # Убедимся, что задача принадлежит пользователю
    task.delete()
    return redirect('task_list')
def logout_view(request):
    logout(request)
    return redirect('task_list')

from django.shortcuts import get_object_or_404, redirect

from django.shortcuts import get_object_or_404, redirect
from .models import Task


def toggle_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == "POST":
        # Изменяем статус текущей задачи
        task.completed = not task.completed
        task.save()

        # Проверяем статус всех родительских задач
        if task.parent:
            task.parent.check_completion()
    return redirect('task_list')



def add_subtask(request, parent_id):
    parent_task = get_object_or_404(Task, id=parent_id, user=request.user)
    if request.method == "POST":
        title = request.POST.get("title")
        if title:
            Task.objects.create(
                title=title,
                parent=parent_task,
                user=request.user,
            )
    return redirect('task_list')
