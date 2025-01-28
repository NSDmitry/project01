from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from .models import Article
from .serializer import ArticleSerializer

@api_view(['GET'])
def get_articles(request):
    """Возвращает список всех статей."""
    articles = Article.objects.all()
    serializer = ArticleSerializer(articles, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_article(request, article_id):
    """Возвращает одну статью по её ID."""
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ArticleSerializer(article)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
def create_artice(request):
    """
    Создает новую статью.
    Ожидает поля: title, description, rating.
    """
    serializer = ArticleSerializer(data=request.data)
    if serializer.is_valid():
        article = serializer.save()
        return Response(ArticleSerializer(article).data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def delete_article(request, article_id):
    """Удаляет статью по её ID."""
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    article.delete()
    return Response({"message": "Success delete"}, status=status.HTTP_200_OK)
