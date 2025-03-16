from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Main page for managing the To-Do list
    path('', views.create_todo, name='create_todo'),

    # Unified authentication page (login + registration)
    path('auth/', views.auth_view, name='auth_view'),

    # Logout
    path('logout/', views.logout_view, name='logout'),

    # Old routes
    path('todolist/<int:todolist_id>/', views.task_list, name='todolist_tasks'),
    path('tasks/json/', views.get_tasks_json, name='get_tasks_json'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('toggle/<int:task_id>/', views.toggle_task, name='toggle_task'),
    path('add_subtask/<int:parent_id>/', views.add_subtask, name='add_subtask'),

    # Task detail update
    path('add_detail/<int:task_id>/', views.add_detail, name='add_detail'),

    # To-Do list management
    path('delete_todolist/<int:todolist_id>/', views.delete_todolist, name='delete_todolist'),
    path('rename_todolist/<int:todolist_id>/', views.rename_todolist, name='rename_todolist'),

    # Profile editing
    path('profile/edit/', views.profile_edit, name='profile_edit'),

    # Password reset routes
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'),
         name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'),
         name='password_reset_complete'),

    # New route for theme switching
    path('change_theme/', views.change_theme, name='change_theme'),

    # New route for password instructions page
    path('password_instructions/', views.password_instructions, name='password_instructions'),

    # Projects and settings
    path('projects/', views.projects, name='projects'),
    path('settings/', views.settings_view, name='settings_view'),

    # For the "Open" button
    path('tasks/<int:todolist_id>/', views.task_list_view, name='task_list_view'),

    # NEW: route for updating task status via AJAX
    path('update-task-status/', views.update_task_status, name='update_task_status'),

    # Dashboard, Kanban, Task Filter
    path('dashboard/', views.dashboard_view, name='dashboard_view'),
    path('kanban/', views.kanban_view, name='kanban_view'),
    path('task_filter/', views.task_filter_view, name='task_filter_view'),

    # NEW PAGES: Terms of Service, Privacy Policy, Contact Support
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('contact-support/', views.contact_support, name='contact_support'),
]
