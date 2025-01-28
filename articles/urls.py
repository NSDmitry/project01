from django.urls import path
from .views import get_articles, create_artice, delete_article, get_article

urlpatterns = [
    path('api/articles', get_articles, name='get articles'),
    path('api/article', create_artice, name='create article'),
    path('api/article/<int:article_id>', get_article, name="get article by id"),
    path('api/article/<int:article_id>', delete_article, name='delete article by id'),
]