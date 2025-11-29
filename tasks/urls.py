from django.urls import path
from .views import AnalyzeTasksView, SuggestTasksView,welcome

urlpatterns = [
    path('tasks/analyze/', AnalyzeTasksView.as_view()),
    path('tasks/suggest/', SuggestTasksView.as_view()),
    path('tasks/', welcome)
]