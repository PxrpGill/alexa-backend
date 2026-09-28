from django.urls import path

from . import views

urlpatterns = [
    path(
        'resume/<int:application_id>/',
        views.download_resume,
        name='vacancy_resume_download',
    ),
]
