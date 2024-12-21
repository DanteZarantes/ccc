from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', views.task_list, name='task_list'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('', views.task_list, name='task_list'),
    path('toggle/<int:task_id>/', views.toggle_task, name='toggle_task'),
    path('add_subtask/<int:parent_id>/', views.add_subtask, name='add_subtask'),
]
