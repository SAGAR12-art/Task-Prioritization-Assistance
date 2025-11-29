from rest_framework import serializers
from .models import task

class taskSerializer(serializers.ModelSerializer):
    score=serializers.FloatField(read_only=True)
    explaination=serializers.CharField(read_only=True)

    class Meta:
        model=task
        fields=['id','title','due_date','estimated_hours','importance','dependencies','created_at','score','explaination']