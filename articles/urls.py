from django.urls import path
from .views import articles, articles_with_id

urlpatterns = [
    path('api/articles', articles, name='get_articles'), # GET, POST
    path('api/articles/<int:article_id>', articles_with_id, name="by_id"), # GET, DELETE
]