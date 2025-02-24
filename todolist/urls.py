from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Главная страница для управления To-Do
    path('', views.create_todo, name='create_todo'),

    # Унифицированная страница аутентификации (логин + регистрация)
    path('auth/', views.auth_view, name='auth_view'),

    # Выход из системы
    path('logout/', views.logout_view, name='logout'),

    # Маршруты для работы с To-Do списками
    path('todolist/<int:todolist_id>/', views.task_list, name='todolist_tasks'),
    path('tasks/json/', views.get_tasks_json, name='get_tasks_json'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('toggle/<int:task_id>/', views.toggle_task, name='toggle_task'),
    path('add_subtask/<int:parent_id>/', views.add_subtask, name='add_subtask'),

    # Новый маршрут для добавления/обновления детальной информации задачи
    path('add_detail/<int:task_id>/', views.add_detail, name='add_detail'),

    # Управление To-Do списками
    path('delete_todolist/<int:todolist_id>/', views.delete_todolist, name='delete_todolist'),
    path('rename_todolist/<int:todolist_id>/', views.rename_todolist, name='rename_todolist'),

    # Редактирование профиля
    path('profile/edit/', views.profile_edit, name='profile_edit'),

    # Маршруты для сброса пароля
    path(
        'password_reset/',
        auth_views.PasswordResetView.as_view(template_name='password_reset.html'),
        name='password_reset'
    ),
    path(
        'password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'),
        name='password_reset_done'
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'),
        name='password_reset_confirm'
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'),
        name='password_reset_complete'
    ),

    # Новые маршруты для Projects и Settings
    path('projects/', views.projects, name='projects'),
    path('settings/', views.settings_view, name='settings_view'),
]
