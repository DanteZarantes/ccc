from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.http import JsonResponse
from .models import Task, ToDoList
from .tokens import account_activation_token
from .forms import CustomUserCreationForm, ProfileForm
from django.views.decorators.csrf import csrf_exempt
import json

def homepage(request):
    return render(request, 'homepage.html')

@login_required
def task_list_view(request, todolist_id=None):
    if todolist_id:
        todolist = get_object_or_404(ToDoList, id=todolist_id, user=request.user)
        return render(request, 'task_list.html', {'todolist': todolist})
    return redirect('create_todo')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            username = form.cleaned_data.get('username')

            if User.objects.filter(email=email).exists():
                return render(request, 'register.html', {
                    'form': form,
                    'error': 'This email is already in use. Please try another one.'
                })
            if User.objects.filter(username=username).exists():
                return render(request, 'register.html', {
                    'form': form,
                    'error': 'This username is already in use. Please try another one.'
                })

            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('create_todo')
        else:
            return render(request, 'register.html', {
                'form': form,
                'error': 'Please fix the errors in the form.'
            })
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def home(request):
    return render(request, 'home.html')

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect('login')
    else:
        return JsonResponse({'error': 'Activation link is invalid!'}, status=400)

def login_view(request):
    if request.method == 'POST':
        # Здесь мы ожидаем, что пользователь вводит свой Email в поле "username"
        email = request.POST.get('username')
        password = request.POST.get('password')
        try:
            user_obj = User.objects.get(email=email)
            # Аутентифицируем, подставляя реальный username
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None

        if user is not None:
            login(request, user)
            return redirect('create_todo')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials.'})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        about_me = request.POST.get('about')

        if new_password and new_password == confirm_password:
            request.user.set_password(new_password)

        if about_me:
            request.user.about = about_me
            request.user.save()

        if form.is_valid():
            form.save()
            return redirect('create_todo')
    else:
        form = ProfileForm(instance=request.user)

    # Подготовка данных для статистики профиля
    tasks_completed = Task.objects.filter(user=request.user, completed=True).count()
    todo_lists = ToDoList.objects.filter(user=request.user).count()
    last_login = request.user.last_login

    context = {
        'form': form,
        'tasks_completed': tasks_completed,
        'todo_lists': todo_lists,
        'last_login': last_login,
    }
    return render(request, 'profile_edit.html', context)

@login_required
@csrf_exempt
def task_list(request, todolist_id):
    todolist = get_object_or_404(ToDoList, id=todolist_id, user=request.user)

    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        title = data.get("title")
        if title:
            Task.objects.create(title=title, todolist=todolist, user=request.user)
            return JsonResponse({"success": True}, status=201)
        return JsonResponse({"success": False, "message": "Task title is required."}, status=400)

    tasks = todolist.tasks.all().order_by("completed", "created_at")
    return render(request, 'task_list.html', {'todolist': todolist, 'tasks': tasks})

@login_required
@csrf_exempt
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == "POST":
        task.delete()
        return JsonResponse({"success": True}, status=200)
    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

@login_required
@csrf_exempt
def toggle_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == "POST":
        task.completed = not task.completed
        task.save()
        return JsonResponse({"success": True, "completed": task.completed}, status=200)
    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

@login_required
@csrf_exempt
def add_subtask(request, parent_id):
    parent_task = get_object_or_404(Task, id=parent_id, user=request.user)
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        title = data.get("title")
        if title:
            Task.objects.create(title=title, parent=parent_task, user=request.user)
            return JsonResponse({"success": True}, status=201)
        return JsonResponse({"success": False, "message": "Subtask title is required."}, status=400)

@login_required
def get_tasks_json(request):
    todolist_id = request.GET.get('todolist_id')
    if not todolist_id:
        return JsonResponse([], safe=False)

    todolist = get_object_or_404(ToDoList, id=todolist_id, user=request.user)

    def build_task_tree(task):
        return {
            "id": task.id,
            "title": task.title,
            "detail": task.detail if task.detail else "",  # Теперь возвращаем detail
            "completed": task.completed,
            "children": [build_task_tree(subtask) for subtask in task.subtasks.all()]
        }

    tasks = todolist.tasks.filter(parent=None)
    task_tree = [build_task_tree(task) for task in tasks]
    return JsonResponse(task_tree, safe=False)

@login_required
def create_todo(request):
    if request.method == "POST":
        name = request.POST.get("todolist_name")
        if name:
            ToDoList.objects.create(name=name, user=request.user)
            return redirect('create_todo')

    todolists = ToDoList.objects.filter(user=request.user)
    return render(request, 'create_todo.html', {'todolists': todolists})

@login_required
@csrf_exempt
def delete_todolist(request, todolist_id):
    if request.method == "POST":
        try:
            todolist = get_object_or_404(ToDoList, id=todolist_id, user=request.user)
            todolist.delete()
            return JsonResponse({"success": True, "message": "To-Do List deleted successfully."}, status=200)
        except Exception as e:
            print(f"Error deleting ToDoList: {e}")
            return JsonResponse({"success": False, "message": str(e)}, status=500)
    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

@login_required
@csrf_exempt
def rename_todolist(request, todolist_id):
    if request.method == "POST":
        try:
            todolist = get_object_or_404(ToDoList, id=todolist_id, user=request.user)
            try:
                data = json.loads(request.body.decode("utf-8"))
            except json.JSONDecodeError:
                return JsonResponse({"success": False, "message": "Invalid JSON."}, status=400)

            new_name = data.get("name")
            if new_name:
                todolist.name = new_name
                todolist.save()
                return JsonResponse({"success": True, "message": "To-Do List renamed successfully."}, status=200)
            return JsonResponse({"success": False, "message": "New name is required."}, status=400)
        except Exception as e:
            print(f"Error renaming ToDoList: {e}")
            return JsonResponse({"success": False, "message": str(e)}, status=500)
    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

# Новый эндпоинт для сохранения/обновления detail задачи
@login_required
@csrf_exempt
def add_detail(request, task_id):
    """
    Сохраняет или обновляет подробное описание (detail) для задачи с id=task_id.
    Требует, чтобы в модели Task было поле `detail = models.TextField(blank=True, null=True)`.
    """
    if request.method == "POST":
        try:
            task = get_object_or_404(Task, id=task_id, user=request.user)
            data = json.loads(request.body.decode("utf-8"))
            detail_text = data.get("detail", "")
            task.detail = detail_text
            task.save()
            return JsonResponse({"success": True}, status=200)
        except Task.DoesNotExist:
            return JsonResponse({"success": False, "message": "Task not found."}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)
