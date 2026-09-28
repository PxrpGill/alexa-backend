import os

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404

from .models import Application


@staff_member_required
def download_resume(request, application_id):
    """Выдаёт резюме отклика только сотрудникам.

    Каталог /media/vacancies/resumes/ помечен в nginx как ``internal``, поэтому
    прямые ссылки на файл извне недоступны: отдача идёт через X-Accel-Redirect
    после проверки прав. В dev (без nginx) файл стримится самим Django.
    """
    application = get_object_or_404(Application, pk=application_id)

    if not application.resume:
        raise Http404('У отклика нет файла резюме')

    extension = os.path.splitext(application.resume.name)[1]
    filename = f'resume-{application.pk}{extension}'

    if getattr(settings, 'USE_X_ACCEL_REDIRECT', False):
        response = HttpResponse(status=200)
        del response['Content-Type']  # Content-Type выставит nginx
        response['X-Accel-Redirect'] = f'{settings.MEDIA_URL}{application.resume.name}'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    return FileResponse(
        application.resume.open('rb'), as_attachment=True, filename=filename
    )
