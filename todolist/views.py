from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.http import JsonResponse
from django.db.models import Q
from .models import Task, ToDoList, Project, Subscription, Payment, Message  # добавлена модель Message
from .tokens import account_activation_token
from .forms import CustomUserCreationForm, ProfileForm
from django.views.decorators.csrf import csrf_exempt
import json
import datetime
from django.utils import timezone
import openai
from django.conf import settings

# Stripe import
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

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
        if form.is_valid():
            user = form.save(commit=False)
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            about_me = request.POST.get('about')
            if new_password and new_password == confirm_password:
                user.set_password(new_password)
            if about_me:
                user.about = about_me
            user.save()
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
    Additionally syncs 'status' with 'is_completed' for Kanban and Dashboard consistency.
    """
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == "POST":
        if not task.is_completed:
            task.is_completed = True
            task.status = 'done'
            if not task.completed_at:
                task.completed_at = timezone.now()
        else:
            task.is_completed = False
            task.status = 'todo'
            task.completed_at = None
        task.save()
        return JsonResponse({"success": True, "is_completed": task.is_completed}, status=200)
    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)


@login_required
@csrf_exempt
def complete_task(request, task_id):
    """
    Toggles a task's completion:
    - If the task is already completed, uncomplete it.
    - If the task is incomplete, check that all subtasks are completed; if not, return an error.
    """
    if request.method == "POST":
        task = get_object_or_404(Task, id=task_id, user=request.user)
        if task.is_completed:
            task.is_completed = False
            task.status = 'todo'
            task.completed_at = None
            task.save()
            return JsonResponse({"success": True, "is_completed": False}, status=200)
        else:
            if not all_subtasks_completed(task):
                return JsonResponse({
                    "success": False,
                    "error": "Cannot complete this task because one or more subtasks are incomplete."
                }, status=400)
            task.is_completed = True
            task.status = 'done'
            if not task.completed_at:
                task.completed_at = timezone.now()
            task.save()
            if task.parent:
                task.parent.check_completion()
            return JsonResponse({"success": True, "is_completed": True}, status=200)
    return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)


def all_subtasks_completed(task):
    """
    Recursively checks that all subtasks (and their subtasks) are completed.
    """
    for sub in task.subtasks.all():
        if not sub.is_completed:
            return False
        if not all_subtasks_completed(sub):
            return False
    return True


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
    This data is used by the D3 tree to color branches for completed/incomplete tasks.
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
    for the last 7 days. We use is_completed and completed_at to track them.
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
    Completed tasks (status 'done') appear in the 'Done' column.
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
    Displays tasks filtered by tag, search query, and sorted by a given field.
    Accepts the following GET parameters:
      - tag: Filter tasks by tag (case-insensitive substring match).
      - sort_by: Order tasks by 'title', 'status', or 'created' (created_at).
      - q: A search query to filter tasks by title.
    """
    selected_tag = request.GET.get('tag', '')
    sort_by = request.GET.get('sort_by', 'created')
    query = request.GET.get('q', '')

    tasks = Task.objects.filter(user=request.user)
    if selected_tag:
        tasks = tasks.filter(tags__icontains=selected_tag)
    if query:
        tasks = tasks.filter(title__icontains=query)

    if sort_by == 'title':
        tasks = tasks.order_by('title')
    elif sort_by == 'status':
        tasks = tasks.order_by('status')
    elif sort_by == 'created':
        tasks = tasks.order_by('-created_at')

    context = {
        'tasks': tasks,
        'selected_tag': selected_tag,
        'sort_by': sort_by,
        'q': query
    }
    return render(request, 'task_filter.html', context)


# ===============================
# End of new views
# ===============================

@login_required
@csrf_exempt
def update_task_status(request):
    """
    Updates the status of a task via AJAX (for drag-and-drop in Kanban, etc.).
    If status is set to 'done', we also set is_completed=True and completed_at.
    Otherwise, is_completed=False.
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


# ===============================
# Autonomous Projects (not linked to To-Do lists)
# ===============================

@login_required
def projects(request):
    """
    Displays the projects page with autonomous project management.
    If POST, creates a new project.
    """
    if request.method == "POST":
        project_name = request.POST.get("project_name")
        project_description = request.POST.get("project_description", "")
        if project_name:
            # Create a new Project instance (ensure you have defined Project in models.py)
            Project.objects.create(
                name=project_name,
                user=request.user,
                description=project_description
            )
        return redirect('projects')
    projects_list = Project.objects.filter(user=request.user).order_by('-id')
    return render(request, 'projects.html', {'projects': projects_list})


@login_required
@csrf_exempt
def delete_project(request, project_id):
    """
    Deletes a project.
    """
    project = get_object_or_404(Project, id=project_id, user=request.user)
    if request.method == "POST":
        project.delete()
        return JsonResponse({"success": True, "message": "Project deleted successfully."}, status=200)
    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)


@login_required
@csrf_exempt
def rename_project(request, project_id):
    """
    Updates the name (and optionally description) of a project.
    Expects JSON with "name" and optional "description".
    """
    if request.method == "POST":
        project = get_object_or_404(Project, id=project_id, user=request.user)
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Invalid JSON."}, status=400)
        new_name = data.get("name")
        new_description = data.get("description")
        if new_name:
            project.name = new_name
        if new_description is not None:
            project.description = new_description
        project.save()
        return JsonResponse({"success": True, "message": "Project updated successfully."}, status=200)
    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)


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
        # Additional logic to send email or save in DB, etc.
    return render(request, 'contact_support.html')


# ===============================
# GPT Assistant (chat_api + test page)
# ===============================

@login_required
@csrf_exempt
def chat_api(request):
    """
    Accepts POST with 'message' and returns GPT response as JSON.
    Maintains conversation history in session.
    """
    if request.method == "POST":
        user_message = request.POST.get("message", "")
        if not user_message:
            return JsonResponse({"error": "No message provided."}, status=400)
        conversation_history = request.session.get("gpt_history", [])
        if not conversation_history:
            conversation_history = [
                {"role": "system", "content": "You are a helpful assistant that helps with tasks."}
            ]
        conversation_history.append({"role": "user", "content": user_message})
        openai.api_key = settings.OPENAI_API_KEY
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation_history,
                max_tokens=512,
                temperature=0.7,
            )
            gpt_answer = response.choices[0].message["content"]
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        conversation_history.append({"role": "assistant", "content": gpt_answer})
        request.session["gpt_history"] = conversation_history
        return JsonResponse({"answer": gpt_answer}, status=200)
    else:
        return JsonResponse({"error": "Only POST method allowed."}, status=405)


@login_required
def chat_page(request):
    """
    Test page for GPT chat.
    """
    return render(request, 'chat_page.html')


# ===============================
# Payment Integration (Stripe)
# ===============================

@login_required
def start_payment(request, plan):
    """
    Creates a Stripe Checkout Session for the selected plan.
    """
    if plan not in ['business', 'premium']:
        return redirect('subscription_plans')
    price_map = {
        'business': 49900,
        'premium': 99900,
    }
    amount = price_map[plan]
    payment = Payment.objects.create(
        user=request.user,
        plan=plan,
    )
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'rub',
                'product_data': {
                    'name': f"{plan.capitalize()} Plan",
                },
                'unit_amount': amount,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri('/payment/success/?session_id={CHECKOUT_SESSION_ID}'),
        cancel_url=request.build_absolute_uri('/payment/cancel/'),
        client_reference_id=str(payment.id),
    )
    payment.stripe_checkout_session_id = session.id
    payment.save()
    return redirect(session.url, code=303)


@login_required
def payment_success(request):
    """
    Page shown after a successful payment.
    """
    session_id = request.GET.get('session_id', '')
    if not session_id:
        return render(request, 'payment_failed.html', {"error": "No session ID provided."})
    session = stripe.checkout.Session.retrieve(session_id)
    payment_id = session.client_reference_id
    payment = Payment.objects.get(id=payment_id)
    payment.paid = True
    payment.save()
    plan = payment.plan
    sub, created = Subscription.objects.get_or_create(
        user=request.user,
        plan=plan,
        defaults={
            'is_active': True,
            'start_date': timezone.now(),
            'end_date': timezone.now() + datetime.timedelta(days=30),
        }
    )
    if not created:
        sub.is_active = True
        sub.end_date = timezone.now() + datetime.timedelta(days=30)
        sub.save()
    request.user.account_type = plan
    request.user.save()
    return render(request, 'payment_success.html', {"plan": plan})


@login_required
def payment_cancel(request):
    """
    Page shown if the user cancels the payment.
    """
    return render(request, 'payment_cancel.html')


# -------------------------
# Intermediate Payment Page
# -------------------------

@login_required
def payment_options(request, plan):
    """
    Intermediate page where the user confirms the selected plan and chooses the payment method.
    """
    if plan not in ['business', 'premium']:
        return redirect('subscription_plans')
    return render(request, 'payment_options.html', {'plan': plan})


@login_required
def process_payment(request):
    """
    Processes the payment options form submission.
    """
    if request.method == "POST":
        plan = request.POST.get("plan")
        payment_method = request.POST.get("payment_method", "stripe")
        if plan not in ['business', 'premium']:
            return redirect('subscription_plans')
        if payment_method == "stripe":
            return redirect('start_payment', plan=plan)
        return redirect('subscription_plans')
    else:
        return redirect('subscription_plans')


# ===============================
# Subscription and Business-Only Views
# ===============================

from functools import wraps

def subscription_required(allowed_plans=('business', 'premium')):
    """
    Checks if the user has one of the allowed subscription plans.
    If not, redirects to subscription_plans.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.account_type not in allowed_plans:
                return redirect('subscription_plans')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required
def subscription_plans(request):
    """
    Page showing available plans: free, business, premium.
    """
    active_sub = Subscription.objects.filter(user=request.user, is_active=True).order_by('-start_date').first()
    return render(request, 'subscription_plans.html', {'active_sub': active_sub})


@login_required
def upgrade_account_view(request, plan):
    """
    Demonstration logic for upgrading an account.
    """
    if plan not in ['business', 'premium']:
        return redirect('subscription_plans')
    return redirect('payment_options', plan=plan)


@login_required
@subscription_required(allowed_plans=('business', 'premium'))
def business_only_view(request):
    """
    Example of a view only accessible to business/premium users.
    """
    return render(request, 'business_only.html', {})


# ===============================
# New Views for User Search and Chat
# ===============================

@login_required
def user_search(request):
    """
    Allows users to search for other users by username.
    """
    query = request.GET.get('q', '')
    users_found = []
    if query:
        users_found = User.objects.filter(username__icontains=query).exclude(id=request.user.id)
    return render(request, 'user_search.html', {'users_found': users_found, 'query': query})


@login_required
def chat_view(request, username):
    """
    Displays the chat (direct messaging) between the current user and the user with the given username.
    """
    other_user = get_object_or_404(User, username=username)
    if other_user == request.user:
        return redirect('user_search')
    messages = Message.objects.filter(
        Q(sender=request.user, recipient=other_user) |
        Q(sender=other_user, recipient=request.user)
    ).order_by('timestamp')
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(
                sender=request.user,
                recipient=other_user,
                content=content
            )
        return redirect('chat_view', username=other_user.username)
    return render(request, 'chat_view.html', {'messages': messages, 'other_user': other_user})


@login_required
def chat_list(request):
    """
    Displays a list of users with whom the current user has had conversations.
    """
    sent_to_ids = request.user.sent_messages.values_list('recipient_id', flat=True)
    received_from_ids = request.user.received_messages.values_list('sender_id', flat=True)
    user_ids = set(sent_to_ids).union(set(received_from_ids))
    if request.user.id in user_ids:
        user_ids.remove(request.user.id)
    chat_users = User.objects.filter(id__in=user_ids)
    return render(request, 'chat_list.html', {'chat_users': chat_users})