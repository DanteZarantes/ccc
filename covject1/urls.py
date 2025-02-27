from django.contrib import admin
from django.urls import path, include
from todolist import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.homepage, name='homepage'),

    # Проекты и настройки без префикса /todolist/
    path('projects/', views.projects, name='projects'),
    path('settings/', views.settings_view, name='settings_view'),

    # Остальные маршруты приложения To-Do идут под /todolist/
    path('todolist/', include('todolist.urls')),
]

# Для работы с медиа (при DEBUG)
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
