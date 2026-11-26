from typing import Optional
from uuid import UUID

from ninja import Schema

from apps.common.schemas import PictureFormatSchema, build_picture_format


class AboutDoctorTabSchema(Schema):
    tabKey: str
    tabTitle: Optional[str] = None


class AboutDoctorContentItemSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    year: Optional[int] = None


class AboutDoctorTabContentSchema(Schema):
    title: Optional[str] = None
    content: list[AboutDoctorContentItemSchema] = []


class AboutDoctorSchema(Schema):
    tabs: list[AboutDoctorTabSchema] = []
    content: dict[str, AboutDoctorTabContentSchema] = {}


def build_tab_key(tab):
    """Ключ раздела для фронтенда: слаг, а если он не задан — id раздела."""
    return tab.slug or str(tab.pk)


def build_about_employee(doctor):
    """Собирает «О сотруднике» в форму контракта: tabs + content по tabKey.

    Разделы без пунктов не отдаются — фронтенд строит навигацию по tabs
    и ищет данные по тому же ключу в content. Возвращает None, если
    разделов нет совсем, чтобы не отдавать пустой блок.
    """
    tabs = []
    content = {}

    for tab in sorted(doctor.doctor_informations.all(), key=lambda item: item.pk):
        items = [
            {
                "title": item.title,
                "description": item.description,
                "year": item.year,
            }
            for item in sorted(tab.tab_contents.all(), key=lambda item: item.pk)
        ]
        if not items:
            continue

        key = build_tab_key(tab)
        tabs.append({"tabKey": key, "tabTitle": tab.title})
        content[key] = {"title": tab.title, "content": items}

    if not tabs:
        return None

    return {"tabs": tabs, "content": content}


class DoctorSchema(Schema):
    id: UUID
    poster: Optional[PictureFormatSchema] = None
    fullname: str
    position: Optional[str] = None
    accreditation: list[PictureFormatSchema] = []
    aboutEmployee: Optional[AboutDoctorSchema] = None

    @staticmethod
    def resolve_poster(obj):
        return build_picture_format(obj.photo, obj.photo_mobile)

    @staticmethod
    def resolve_fullname(obj):
        return obj.full_name

    @staticmethod
    def resolve_accreditation(obj):
        pictures = (
            build_picture_format(item.photo, item.photo_mobile)
            for item in sorted(obj.doctor_accreditation.all(), key=lambda item: item.pk)
        )
        return [picture for picture in pictures if picture]

    @staticmethod
    def resolve_aboutEmployee(obj):
        return build_about_employee(obj)
