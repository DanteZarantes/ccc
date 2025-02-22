from django.contrib import admin
from django.urls import path, include
from todolist import views

urlpatterns = [
    path('admin/', admin.site.urls),        # Админка
    path('', views.homepage, name='homepage'),  # Главная страница

    # Маршруты To-Do List (включают в себя всё, что относится к задачам,
    # а также маршрут для auth_view, если вы его объявили в todolist/urls)
    path('todolist/', include('todolist.urls')),
]

# Добавляем обработку медиа-файлов
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
