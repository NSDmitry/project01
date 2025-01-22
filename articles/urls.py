from django.urls import path
from .views import get_feed, get_some_text

urlpatterns = [
    path('feed', get_feed, name='get_feed'),
    path('some_text', get_some_text, name='get_some_text')
]