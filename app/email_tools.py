from __future__ import annotations

from urllib.parse import quote


DEFAULT_EMAIL_SUBJECT = "Uygun bir zamanda kisa bir tanisma"
DEFAULT_EMAIL_BODY = (
    "Merhaba {business_name},\n\n"
    "Firmanizin dijital tarafta neler yaptigini kisaca inceledik.\n"
    "Uygun olursa, size fayda saglayabilecegini dusundugumuz 1-2 fikri paylasmak isteriz.\n\n"
    "Ilginizi cekerse bu maile kisaca donmeniz yeterli.\n"
    "Uygun degilse haber vermeniz halinde tekrar yazmayiz.\n\n"
    "Tesekkurler."
)


def normalize_email_address(email: str | None) -> str | None:
    if not email:
        return None

    cleaned = email.strip().lower()
    if "@" not in cleaned or "." not in cleaned.split("@", 1)[-1]:
        return None

    return cleaned


def render_email_template(template: str | None, business_name: str) -> str:
    base_template = (template or DEFAULT_EMAIL_BODY).strip()
    return base_template.replace("{business_name}", business_name)


def build_mailto_url(
    email: str | None,
    subject: str | None = None,
    body: str | None = None,
) -> str | None:
    normalized_email = normalize_email_address(email)
    if not normalized_email:
        return None

    query_parts: list[str] = []
    if subject:
        query_parts.append(f"subject={quote(subject)}")
    if body:
        query_parts.append(f"body={quote(body)}")

    if query_parts:
        return f"mailto:{normalized_email}?{'&'.join(query_parts)}"

    return f"mailto:{normalized_email}"
