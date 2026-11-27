from django.contrib import admin

from ..models import landyshevaya, volkova


class SingletonModelAdmin(admin.ModelAdmin):
    """Прячет кнопку «Добавить», когда единственная запись уже создана.

    Прямой заход на /add/ тоже вернёт 403 — Django проверяет этот же метод.
    """

    def has_add_permission(self, request):
        if not super().has_add_permission(request):
            return False
        return not self.model.objects.exists()


PAGE_MODELS = (
    landyshevaya.LandyshevayaAdultConsultationModel,
    landyshevaya.LandyshevayaAdultGnathologyModel,
    landyshevaya.LandyshevayaAdultHygieneModel,
    landyshevaya.LandyshevayaAdultOrthodonticsModel,
    landyshevaya.LandyshevayaAdultOrthopedicsModel,
    landyshevaya.LandyshevayaAdultPeriodontologyModel,
    landyshevaya.LandyshevayaAdultSurgeryAndImplantationModel,
    landyshevaya.LandyshevayaAdultTherapyModel,
    landyshevaya.LandyshevayaAdultTreatmentDuringSleepModel,
    landyshevaya.LandyshevayaPediatricConsultationModel,
    landyshevaya.LandyshevayaPediatricHygieneModel,
    landyshevaya.LandyshevayaPediatricOrthodonticsModel,
    landyshevaya.LandyshevayaPediatricSurgeryAndImplantationModel,
    landyshevaya.LandyshevayaPediatricTherapyModel,
    landyshevaya.LandyshevayaPediatricTreatmentDuringSleepModel,
    volkova.VolkovaMainPageModel,
)

for model in PAGE_MODELS:
    admin.site.register(model, SingletonModelAdmin)
