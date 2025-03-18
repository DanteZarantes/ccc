from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.http import JsonResponse
from .models import Task, ToDoList
from .tokens import account_activation_token
from .forms import CustomUserCreationForm, ProfileForm
from django.views.decorators.csrf import csrf_exempt
import json
import datetime
from django.utils import timezone

# =============== НОВОЕ: импорт для GPT ===============
import openai
from django.conf import settings
# =====================================================

User = get_user_model()

def homepage(request):
    return render(request, 'homepage.html')


@login_required
def task_list_view(request, todolist_id=None):
    """
    Renders the task list page for a specific To-Do List.
    """
    if todolist_id:
        todolist = get_object_or_404(ToDoList, id=todolist_id, user=request.user)
        return render(request, 'task_list.html', {'todolist': todolist})
    return redirect('create_todo')


def auth_view(request):
    """
    Unified authentication page for login and registration.
    """
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'login':
            # Login using email
            email = request.POST.get('email')
            password = request.POST.get('password')
            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

            if user is not None:
                login(request, user)
                return redirect('create_todo')
            else:
                return render(request, 'auth.html', {'error_login': 'Invalid email or password'})
        elif form_type == 'register':
            form = CustomUserCreationForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data.get('email')
                username = form.cleaned_data.get('username')

                if User.objects.filter(email=email).exists():
                    return render(request, 'auth.html', {'error_register': 'Email already in use'})
                if User.objects.filter(username=username).exists():
                    return render(request, 'auth.html', {'error_register': 'Username already in use'})

                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()
                login(request, user)
                return redirect('create_todo')
            else:
                return render(request, 'auth.html', {'error_register': 'Please fix the errors in the form'})

    return render(request, 'auth.html')


@login_required
def home(request):
    return render(request, 'home.html')


def activate(request, uidb64, token):
    """
    Activates a user's account if the token is valid.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect('auth_view')
    else:
        return JsonResponse({'error': 'Activation link is invalid!'}, status=400)


def logout_view(request):
    logout(request)
    return redirect('auth_view')


@login_required
def profile_edit(request):
    """
    Allows the user to edit their profile.
    """
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

    tasks_completed = Task.objects.filter(user=request.user, is_completed=True).count()
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
    """
    Handles GET and POST requests for tasks within a specific To-Do List.
    For POST, creates a new task with the provided title.
    """
    todolist = get_object_or_404(ToDoList, id=todolist_id, user=request.user)
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        title = data.get("title")
        if title:
            Task.objects.create(title=title, todolist=todolist, user=request.user)
            return JsonResponse({"success": True}, status=201)
        return JsonResponse({"success": False, "message": "Task title is required."}, status=400)
    tasks = todolist.tasks.all().order_by("is_completed", "created_at")
    return render(request, 'task_list.html', {'todolist': todolist, 'tasks': tasks})


@login_required
@csrf_exempt
def delete_task(request, task_id):
    """
    Deletes a task specified by task_id.
    """
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == "POST":
        task.delete()
        return JsonResponse({"success": True}, status=200)
    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)


@login_required
@csrf_exempt
def toggle_task(request, task_id):
    """
    Toggles the completion status of a task.
    """
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == "POST":
        task.is_completed = not task.is_completed
        task.save()
        return JsonResponse({"success": True, "is_completed": task.is_completed}, status=200)
    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)


@login_required
@csrf_exempt
def add_subtask(request, parent_id):
    """
    Creates a subtask under a given parent task.
    """
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
    """
    Returns a JSON representation of tasks for a given To-Do List.
    """
    todolist_id = request.GET.get('todolist_id')
    if not todolist_id:
        return JsonResponse([], safe=False)
    todolist = get_object_or_404(ToDoList, id=todolist_id, user=request.user)

    def build_task_tree(task):
        return {
            "id": task.id,
            "title": task.title,
            "detail": task.detail or '',
            "is_completed": task.is_completed,
            "children": [build_task_tree(subtask) for subtask in task.subtasks.all()]
        }
    tasks = todolist.tasks.filter(parent=None)
    task_tree = [build_task_tree(task) for task in tasks]
    return JsonResponse(task_tree, safe=False)


@login_required
def create_todo(request):
    """
    Creates a new To-Do List (project) and displays existing ones.
    """
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
    """
    Deletes a To-Do List.
    """
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
    """
    Updates the name (and optionally description) of a To-Do List.
    Expects JSON with "name" and optional "description".
    """
    if request.method == "POST":
        try:
            todolist = get_object_or_404(ToDoList, id=todolist_id, user=request.user)
            try:
                data = json.loads(request.body.decode("utf-8"))
            except json.JSONDecodeError:
                return JsonResponse({"success": False, "message": "Invalid JSON."}, status=400)

            new_name = data.get("name")
            new_description = data.get("description")

            if new_name:
                todolist.name = new_name
            if new_description is not None:
                todolist.description = new_description

            todolist.save()
            return JsonResponse({"success": True, "message": "To-Do List updated successfully."}, status=200)
        except Exception as e:
            print(f"Error renaming ToDoList: {e}")
            return JsonResponse({"success": False, "message": str(e)}, status=500)
    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)


@login_required
@csrf_exempt
def add_detail(request, task_id):
    """
    Saves or updates the task's detail description.
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


# ===============================
# New views for Dashboard, Kanban, and Task Filter
# ===============================

@login_required
def dashboard_view(request):
    """
    Displays a dashboard with a bar chart showing the number of completed tasks
    for the last 7 days.
    """
    today = timezone.now().date()
    labels = []
    data_for_chart = []
    for i in range(7):
        day = today - datetime.timedelta(days=i)
        count_tasks = Task.objects.filter(
            user=request.user,
            is_completed=True,
            completed_at__date=day
        ).count()
        labels.append(day.strftime('%Y-%m-%d'))
        data_for_chart.append(count_tasks)
    labels.reverse()
    data_for_chart.reverse()
    context = {'labels': labels, 'data_for_chart': data_for_chart}
    return render(request, 'dashboard.html', context)


@login_required
def kanban_view(request):
    """
    Displays a Kanban board with tasks separated into columns based on status.
    """
    tasks_todo = Task.objects.filter(user=request.user, status='todo')
    tasks_in_progress = Task.objects.filter(user=request.user, status='in_progress')
    tasks_done = Task.objects.filter(user=request.user, status='done')
    context = {
        'tasks_todo': tasks_todo,
        'tasks_in_progress': tasks_in_progress,
        'tasks_done': tasks_done,
    }
    return render(request, 'kanban.html', context)


@login_required
def task_filter_view(request):
    """
    Displays tasks filtered by tag. Uses the GET parameter 'tag' for filtering.
    """
    selected_tag = request.GET.get('tag', '')
    tasks = Task.objects.filter(user=request.user)
    if selected_tag:
        tasks = tasks.filter(tags__icontains=selected_tag)
    context = {'tasks': tasks, 'selected_tag': selected_tag}
    return render(request, 'task_filter.html', context)


# ===============================
# End of new views
# ===============================

@login_required
@csrf_exempt
def update_task_status(request):
    """
    Updates the status of a task via AJAX.
    Expects JSON with 'task_id' and 'status'.
    """
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        task_id = data.get('task_id')
        new_status = data.get('status')
        try:
            task = Task.objects.get(pk=task_id, user=request.user)
            task.status = new_status
            if new_status == 'done':
                task.is_completed = True
                if not task.completed_at:
                    task.completed_at = timezone.now()
            else:
                task.is_completed = False
                task.completed_at = None
            task.save()
            return JsonResponse({'success': True})
        except Task.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Task not found'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@login_required
def projects(request):
    """
    Displays the projects page (To-Do Lists as projects).
    If POST, creates a new project.
    """
    if request.method == "POST":
        project_name = request.POST.get("project_name")
        project_description = request.POST.get("project_description", "")
        if project_name:
            ToDoList.objects.create(
                name=project_name,
                user=request.user,
                description=project_description
            )
        return redirect('projects')

    projects_list = ToDoList.objects.filter(user=request.user).order_by('-id')
    return render(request, 'projects.html', {'projects': projects_list})


@login_required
def settings_view(request):
    return render(request, 'settings.html')


@login_required
def change_theme(request):
    """
    Switches the site theme (light, dark, or gradient) by saving it in the session.
    """
    if request.method == 'POST':
        chosen_theme = request.POST.get('theme')
        if chosen_theme in ['light', 'dark', 'gradient']:
            request.session['theme'] = chosen_theme
        return redirect('settings_view')
    else:
        return redirect('settings_view')


def password_instructions(request):
    """
    Displays the password instructions page.
    """
    return render(request, 'password_instructions.html')


# ===============================
# NEW PAGES: Terms of Service, Privacy Policy, Contact Support
# ===============================

def terms_of_service(request):
    return render(request, 'terms_of_service.html')

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def contact_support(request):
    """
    Renders a contact form or handles submission.
    For now, just a static page.
    """
    if request.method == 'POST':
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        # Здесь можно добавить логику: отправить письмо, сохранить в БД, etc.
        # return redirect(...)  # после успешной отправки
    return render(request, 'contact_support.html')


# ===============================
# НОВОЕ: GPT-ассистент (chat_api + тестовая страница)
# ===============================

@login_required
@csrf_exempt
def chat_api(request):
    """
    Принимает POST с полем 'message' и возвращает ответ GPT в JSON.
    Хранит историю в сессии, чтобы GPT "помнил" контекст.
    """
    if request.method == "POST":
        user_message = request.POST.get("message", "")
        if not user_message:
            return JsonResponse({"error": "No message provided."}, status=400)

        # Инициируем или берём историю чата из сессии
        conversation_history = request.session.get("gpt_history", [])
        if not conversation_history:
            # Пример system-промпта: можно описать роль ассистента
            conversation_history = [
                {"role": "system", "content": "You are a helpful assistant that helps with tasks."}
            ]

        # Добавляем новое сообщение
        conversation_history.append({"role": "user", "content": user_message})

        # Указываем ключ
        openai.api_key = settings.OPENAI_API_KEY

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Или 'gpt-4', если есть доступ
                messages=conversation_history,
                max_tokens=512,
                temperature=0.7,
            )
            gpt_answer = response.choices[0].message["content"]
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        # Сохраняем ответ ассистента
        conversation_history.append({"role": "assistant", "content": gpt_answer})
        request.session["gpt_history"] = conversation_history

        return JsonResponse({"answer": gpt_answer}, status=200)
    else:
        return JsonResponse({"error": "Only POST method allowed."}, status=405)


@login_required
def chat_page(request):
    """
    Тестовая страница для чата GPT.
    """
    return render(request, 'chat_page.html')
