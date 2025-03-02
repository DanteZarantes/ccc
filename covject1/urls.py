from django.contrib import admin
from django.urls import path, include
from todolist import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Main page (home) – using the 'homepage' view
    path('', views.homepage, name='homepage'),

    # New routes for additional functionality
    path('dashboard/', views.dashboard_view, name='dashboard_view'),
    path('kanban/', views.kanban_view, name='kanban_view'),
    path('tasks/filter/', views.task_filter_view, name='task_filter_view'),

    # Projects and settings without the /todolist/ prefix
    path('projects/', views.projects, name='projects'),
    path('settings/', views.settings_view, name='settings_view'),

    # All other To-Do routes under /todolist/
    path('todolist/', include('todolist.urls')),
]

# Serving media files in DEBUG mode
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
