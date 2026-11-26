from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from config.api import api

# Стоковый admin: джазмин брендинг берёт из JAZZMIN_SETTINGS, здесь — только фолбэк.
if not getattr(settings, "USE_JAZZMIN", True):
    admin.site.site_header = "Стоматология Алекса"
    admin.site.site_title = "Алекса"
    admin.site.index_title = "Панель управления"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', api.urls),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('staff/vacancies/', include('apps.vacancies.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
