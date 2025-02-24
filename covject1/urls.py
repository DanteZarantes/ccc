from django.contrib import admin
from django.urls import path, include
from todolist import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.homepage, name='homepage'),

    # Если нужно, чтобы Projects/Settings были без /todolist/
    path('projects/', views.projects, name='projects'),
    path('settings/', views.settings_view, name='settings_view'),

    # Остальные маршруты приложения To-Do
    path('todolist/', include('todolist.urls')),
]

# Добавляем обработку медиа-файлов (для DEBUG)
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
