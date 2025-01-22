from django.urls import path
from .views import get_feed,  create_artice

urlpatterns = [
    path('api/feed', get_feed, name='get_feed'),
    path('api/article', create_artice, name='create_new_article')
]