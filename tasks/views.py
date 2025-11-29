from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .scoring import score_tasks
from django.shortcuts import render

class AnalyzeTasksView(APIView):
    def post(self, request):
        strategy = request.data.get('strategy', 'smart_balance')
        tasks_data = request.data.get('tasks', [])

        # basic validation
        if not isinstance(tasks_data, list):
            return Response({"error": "tasks must be a list"}, status=status.HTTP_400_BAD_REQUEST)

        # convert to serializer style + ensure id field
        normalized = []
        for idx, t in enumerate(tasks_data):
            t = dict(t)
            t.setdefault('id', idx + 1)
            normalized.append(t)

        scored = score_tasks(normalized, strategy=strategy)
        return Response({"strategy": strategy, "tasks": scored})

class SuggestTasksView(APIView):
    def post(self, request):  
        strategy = request.data.get('strategy', 'smart_balance')
        tasks_data = request.data.get('tasks', [])
        normalized = []
        for idx, t in enumerate(tasks_data):
            t = dict(t)
            t.setdefault('id', idx + 1)
            normalized.append(t)

        scored = score_tasks(normalized, strategy=strategy)
        return Response({"strategy": strategy, "tasks": scored[:3]})
    
def welcome(request):
    return render(request, "index.html")
