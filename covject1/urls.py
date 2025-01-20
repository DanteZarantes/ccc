from django.contrib import admin
from django.urls import path, include
from todolist import views

urlpatterns = [
    path('admin/', admin.site.urls),  # Админка
    path('', views.homepage, name='homepage'),  # Главная страница
    path('tasks/', include('todolist.urls')),  # Все маршруты To-Do List
    path('accounts/', include('todolist.urls')),  # Регистрация, вход, выход
]
