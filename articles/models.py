from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    rating = models.FloatField(default=0.0)

    def __str__(self):
        return self.title
