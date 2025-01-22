from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from .models import Article

@api_view(['GET'])
def get_feed(request):
    articles = Article.objects.all().values('title', 'description', 'rating')
    return Response(list(articles))

@api_view(['POST'])
def create_artice(request):
    title = request.data.get('title')
    description = request.data.get('description')
    rating = request.data.get('rating')

    if not title or not description or not rating:
        return Response({"error": "Поля title, description, rating обязательны"}, status = status.HTTP_400_BAD_REQUEST)

    article = Article.objects.create(title=title, description=description, rating=rating)

    return Response({
        "id": article.id,
        "title": article.title,
        "description": article.description,
        "rating": article.rating,
    }, status = status.HTTP_201_CREATED)

