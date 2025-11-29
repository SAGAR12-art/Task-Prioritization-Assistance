from django.db import models

# Create your models here.
class task(models.Model):
    title=models.CharField(max_length=255)
    due_date=models.DateField(null=True,blank=True)
    estimated_hours=models.FloatField(null=True,blank=True)
    importance=models.IntegerField(default=5)
    dependencies=models.JSONField(default=list,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return self.title