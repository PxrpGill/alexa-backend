from django.test import Client, TestCase

from apps.doctors.models import Doctor


class DoctorTypographyTest(TestCase):
    """ФИО, специализации и HTML-биография врача типографируются при отдаче."""

    pass
