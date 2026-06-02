from django.urls import path
from . import views

app_name = 'kb'

urlpatterns = [
    path('manage/', views.kb_management, name='management'),
    path('create/', views.article_create, name='create'),
    path('<int:pk>/edit/', views.article_edit, name='edit'),
    path('<int:pk>/submit-review/', views.article_submit_review, name='submit_review'),
    path('<int:pk>/publish/', views.article_publish, name='publish'),
    path('<int:pk>/archive/', views.article_archive, name='archive'),
]