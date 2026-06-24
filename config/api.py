from ninja import NinjaAPI
from apps.branches.api import router as branches_router
from apps.doctors.api import router as doctors_router

api = NinjaAPI(
    title="Alexa Dental API",
    version="1.0.0",
    docs_url="/docs",
)

api.add_router("/branches/", branches_router)
api.add_router("/doctors/", doctors_router)
