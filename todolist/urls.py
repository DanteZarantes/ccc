from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Home view
    path('', views.create_todo, name='create_todo'),

    # Authentication-related routes
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),

    # To-Do list related routes
    path('todolist/<int:todolist_id>/', views.task_list, name='todolist_tasks'),
    path('tasks/json/', views.get_tasks_json, name='get_tasks_json'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('toggle/<int:task_id>/', views.toggle_task, name='toggle_task'),
    path('add_subtask/<int:parent_id>/', views.add_subtask, name='add_subtask'),

    # To-Do list management routes
    path('delete_todolist/<int:todolist_id>/', views.delete_todolist, name='delete_todolist'),
    path('rename_todolist/<int:todolist_id>/', views.rename_todolist, name='rename_todolist'),  # New rename feature

    # Profile-related routes
    path('profile/edit/', views.profile_edit, name='profile_edit'),
]
