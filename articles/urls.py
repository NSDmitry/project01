from django.urls import path
from .views import get_feed, create_artice, delete_article, get_article

urlpatterns = [
    path('api/feed', get_feed, name='get_feed'),
    path('api/article', create_artice, name='create_new_article'),
    path('api/article/<int:article_id>', get_article, name="get article by id"),
    path('api/article/<int:article_id>', delete_article, name='delete article by id'),
]