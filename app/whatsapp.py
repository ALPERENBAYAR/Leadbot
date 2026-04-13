from __future__ import annotations

from urllib.parse import quote


DEFAULT_WHATSAPP_MESSAGE = "Merhaba, firmanız için sunduğumuz hizmetler hakkında kısa bir görüşme yapmak isteriz."


def normalize_whatsapp_phone(phone: str | None) -> str | None:
    if not phone:
        return None

    digits = "".join(char for char in phone if char.isdigit())
    if len(digits) < 10:
        return None

    if digits.startswith("90") and len(digits) == 12:
        return digits

    if digits.startswith("0") and len(digits) == 11:
        return f"90{digits[1:]}"

    if len(digits) == 10 and digits.startswith("5"):
        return f"90{digits}"

    if digits.startswith("90") and len(digits) > 12:
        return digits[:12]

    return digits if len(digits) >= 10 else None


def build_whatsapp_url(phone: str | None, message: str | None = None) -> str | None:
    normalized_phone = normalize_whatsapp_phone(phone)
    if not normalized_phone:
        return None

    if message:
        return f"https://wa.me/{normalized_phone}?text={quote(message)}"

    return f"https://wa.me/{normalized_phone}"


def render_message_template(template: str | None, business_name: str) -> str:
    base_template = (template or DEFAULT_WHATSAPP_MESSAGE).strip()
    return base_template.replace("{business_name}", business_name)
