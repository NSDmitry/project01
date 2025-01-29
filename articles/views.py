from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Article
from .serializer import ArticleSerializer

@api_view(['GET', 'POST', 'DELETE'])
def articles(request):
    if request.method == 'GET':
        return __get_all(request)
    elif request.method == 'POST':
        return __create(request)
    elif request.method == 'DELETE':
        return __delete_all(request)

@api_view(['GET', 'DELETE'])
def articles_with_id(request, article_id):
    if request.method == 'GET':
        return __get_by_id(request, article_id)
    elif request.method == 'DELETE':
        return __delete_by_id(request, article_id)

"""Возвращает список всех статей."""
def __get_all(request):
    articles = Article.objects.all()
    serializer = ArticleSerializer(articles, many=True)
    return Response(serializer.data)

"""
Создает новую статью.
Ожидает поля: title, description, rating.
"""
def __create(request):
    serializer = ArticleSerializer(data=request.data)
    if serializer.is_valid():
        article = serializer.save()
        return Response(ArticleSerializer(article).data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

"""Удаляет статью по её ID."""
def __delete_by_id(request, article_id):
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    article.delete()
    return Response({"message": "Success delete"}, status=status.HTTP_200_OK)

"""Возвращает одну статью по её ID."""
def __get_by_id(request, article_id):
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ArticleSerializer(article)
    return Response(serializer.data, status=status.HTTP_200_OK)

"""Удаление всех статей из базы данных"""
def __delete_all(request):
    try:
        objects = Article.objects.all()
    except Article.DoesNotExist:
        return Response({"message": "is empty"}, status=status.HTTP_200_OK)

    objects.delete()
    return Response({"message": "success delete all articles"}, status=status.HTTP_200_OK)