from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from .models import Article

@api_view(['GET'])
def get_feed(request):
    articles = Article.objects.all().values('id', 'title', 'description', 'rating')
    return Response(list(articles))

@api_view(['GET'])
def get_article(request, article_id):
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        return Response(
            {"error": "Not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response(article.to_json(), status=status.HTTP_200_OK)

@api_view(['POST'])
def create_artice(request):
    title = request.data.get('title')
    description = request.data.get('description')
    rating = request.data.get('rating')

    if not title or not description or not rating:
        return Response(
            {"error": "Fields title, description, rating required"},
            status = status.HTTP_400_BAD_REQUEST
        )

    article = Article.objects.create(title=title, description=description, rating=rating)

    return Response(article.to_json(), status = status.HTTP_201_CREATED)

@api_view(['DELETE'])
def delete_article(request, article_id):
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    article.delete()
    return Response({"message": "Success delete"}, status=status.HTTP_200_OK)
