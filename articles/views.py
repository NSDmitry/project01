from django.http import JsonResponse
from .models import Article

def get_feed(request):
    articles = Article.objects.all().values('title', 'description')
    return JsonResponse(list(articles), safe=False)

def get_some_text(request):
    return JsonResponse("Hello world!", safe=False)
