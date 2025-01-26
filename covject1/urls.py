from django.contrib import admin
from django.urls import path, include
from todolist import views

urlpatterns = [
    path('admin/', admin.site.urls),  # Админка
    path('', views.homepage, name='homepage'),  # Главная страница
    path('tasks/', include('todolist.urls')),  # Все маршруты To-Do List
    path('accounts/', include('todolist.urls')),  # Регистрация, вход, выход
]

# Добавляем обработку медиа-файлов
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
