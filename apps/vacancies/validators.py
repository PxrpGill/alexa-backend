import os
import re

from django.conf import settings

ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}

ALLOWED_RESUME_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
}

NAME_MAX_LENGTH = 255


def _digits_only(value):
    return re.sub(r"\D", "", value)


def is_valid_phone(value):
    digits = _digits_only(value)
    if len(digits) == 11 and digits[0] in ("7", "8"):
        return True
    if len(digits) == 10:
        return True
    return False


def validate_name(value, errors):
    if value is None or not str(value).strip():
        errors.setdefault("name", []).append("Введите имя.")
    elif len(value) > NAME_MAX_LENGTH:
        errors.setdefault("name", []).append(
            f"Имя не должно превышать {NAME_MAX_LENGTH} символов."
        )


def validate_phone(value, errors):
    if value is None or not str(value).strip():
        errors.setdefault("phone", []).append("Введите номер телефона.")
    elif not is_valid_phone(str(value)):
        errors.setdefault("phone", []).append("Введите корректный номер телефона.")


def _file_has_magic(fileobj, signatures):
    fileobj.seek(0)
    try:
        head = fileobj.read(max(len(sig) for sig in signatures))
    except Exception:
        return False
    finally:
        fileobj.seek(0)
    return any(head.startswith(sig) for sig in signatures)


def _human_size(num):
    for unit in ("Б", "КБ", "МБ"):
        if num < 1024:
            return f"{num:.0f} {unit}"
        num /= 1024
    return f"{num:.1f} ГБ"


def validate_resume(resume, errors):
    if resume is None or not getattr(resume, "name", ""):
        errors.setdefault("resume", []).append("Загрузите файл резюме.")
        return

    _, extension = os.path.splitext(resume.name)
    extension = extension.lstrip(".").lower()

    if extension not in ALLOWED_RESUME_EXTENSIONS:
        errors.setdefault("resume", []).append(
            "Допустимые форматы файла: PDF, DOC, DOCX."
        )
        return

    if resume.content_type not in ALLOWED_RESUME_MIME_TYPES:
        errors.setdefault("resume", []).append(
            "Недопустимый тип файла. Загрузите файл в формате PDF, DOC или DOCX."
        )
        return

    if resume.size > settings.MAX_RESUME_SIZE:
        errors.setdefault("resume", []).append(
            f"Файл слишком большой. Максимальный размер — "
            f"{_human_size(settings.MAX_RESUME_SIZE)}."
        )
        return

    signatures = {
        "pdf": (b"%PDF",),
        "doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
        "docx": (b"PK",),
    }
    if not _file_has_magic(resume, signatures[extension]):
        errors.setdefault("resume", []).append(
            "Файл повреждён или имеет недопустимое содержимое."
        )


def validate_privacy_policy_accepted(value, errors):
    if value is not True:
        errors.setdefault("privacy_policy_accepted", []).append(
            "Необходимо согласиться с политикой конфиденциальности."
        )


def validate_application(payload, resume):
    errors = {}
    validate_name(payload.name, errors)
    validate_phone(payload.phone, errors)
    validate_privacy_policy_accepted(payload.privacy_policy_accepted, errors)
    validate_resume(resume, errors)
    return errors
