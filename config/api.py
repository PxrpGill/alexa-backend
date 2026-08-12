from ninja import NinjaAPI
from apps.doctors.api import router as doctors_router
from apps.blog.api import router as blog_router
from apps.promotions.api import router as promotions_router
from apps.appointments.api import router as appointments_router
from apps.dms.api import router as dms_router

api = NinjaAPI(
    title="API стоматологической клиники Алекса",
    description="Публичный REST API для получения информации о филиалах, врачах, услугах, акциях и блоге клиники Алекса. Запись на приём — POST /appointments/.",
    version="1.0.0",
    docs_url="/docs",
)

api.add_router("/doctors/", doctors_router)
api.add_router("/blog/", blog_router)
api.add_router("/promotions/", promotions_router)
api.add_router("/appointments/", appointments_router)
api.add_router("/dms/", dms_router)