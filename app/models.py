from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

LEAD_STATUS_LABELS = {
    "new": "Yeni",
    "contacted": "Iletisim Kuruldu",
    "quoted": "Teklif Verildi",
    "follow_up": "Takip Ediliyor",
    "won": "Kazanildi",
    "lost": "Kaybedildi",
}

LEAD_STATUS_ALIASES = {
    "new": "new",
    "yeni": "new",
    "contacted": "contacted",
    "iletisim kuruldu": "contacted",
    "iletişim kuruldu": "contacted",
    "quoted": "quoted",
    "teklif verildi": "quoted",
    "follow_up": "follow_up",
    "follow-up": "follow_up",
    "takip ediliyor": "follow_up",
    "won": "won",
    "kazanildi": "won",
    "kazanıldı": "won",
    "lost": "lost",
    "kaybedildi": "lost",
}

LEAD_ACTIVITY_LABELS = {
    "called": "Arandi",
    "whatsapp_opened": "WhatsApp Acildi",
    "whatsapp_prepared": "WhatsApp Hazirlandi",
    "email_opened": "E-posta Acildi",
    "email_prepared": "E-posta Hazirlandi",
    "email_replied": "E-posta Yanitlandi",
    "email_bounced": "E-posta Bounce Oldu",
    "email_unsubscribed": "E-posta Reddi Geldi",
    "quoted": "Teklif Verildi",
    "note_added": "Not Eklendi",
}


class LeadCreate(BaseModel):
    business_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    next_contact_date: Optional[str] = None
    query_label: Optional[str] = None
    email_delivery_status: Optional[str] = None
    email_last_event_at: Optional[str] = None
    email_replied_at: Optional[str] = None
    email_bounced_at: Optional[str] = None
    email_unsubscribed_at: Optional[str] = None

    @field_validator("business_name")
    @classmethod
    def validate_business_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Isletme adi zorunludur")
        return cleaned

    @field_validator(
        "phone",
        "email",
        "website",
        "address",
        "category",
        "source",
        "status",
        "note",
        "next_contact_date",
        "query_label",
        "email_delivery_status",
        "email_last_event_at",
        "email_replied_at",
        "email_bounced_at",
        "email_unsubscribed_at",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: object) -> Optional[str]:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("status", mode="after")
    @classmethod
    def normalize_status(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_status_value(value)


class LeadUpdate(BaseModel):
    business_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    next_contact_date: Optional[str] = None
    query_label: Optional[str] = None
    email_delivery_status: Optional[str] = None
    email_last_event_at: Optional[str] = None
    email_replied_at: Optional[str] = None
    email_bounced_at: Optional[str] = None
    email_unsubscribed_at: Optional[str] = None

    @field_validator("business_name")
    @classmethod
    def validate_business_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Isletme adi zorunludur")
        return cleaned

    @field_validator(
        "phone",
        "email",
        "website",
        "address",
        "category",
        "source",
        "status",
        "note",
        "next_contact_date",
        "query_label",
        "email_delivery_status",
        "email_last_event_at",
        "email_replied_at",
        "email_bounced_at",
        "email_unsubscribed_at",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: object) -> Optional[str]:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("status", mode="after")
    @classmethod
    def normalize_status(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_status_value(value)


class Lead(LeadCreate):
    id: int
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    items: list[Lead]
    total: int
    limit: int
    offset: int


class LeadQueryOptionsResponse(BaseModel):
    items: list[str]


class FollowUpSummaryResponse(BaseModel):
    today: list[Lead]
    overdue: list[Lead]


class LeadActivity(BaseModel):
    id: int
    lead_id: int
    activity_type: str
    activity_note: Optional[str] = None
    created_at: str


class LeadActivityCreate(BaseModel):
    activity_type: str
    activity_note: Optional[str] = None

    @field_validator("activity_type")
    @classmethod
    def validate_activity_type(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized not in LEAD_ACTIVITY_LABELS:
            raise ValueError("Gecersiz aktivite secildi")
        return normalized

    @field_validator("activity_note", mode="before")
    @classmethod
    def normalize_activity_note(cls, value: object) -> Optional[str]:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None


class GoogleMapsScrapeRequest(BaseModel):
    keyword: str
    location: str
    max_results: int = Field(default=10, ge=1, le=100)

    @field_validator("keyword", "location")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Bu alan zorunludur")
        return cleaned

    @field_validator("max_results", mode="before")
    @classmethod
    def validate_max_results(cls, value: object) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Maksimum sonuc 1 ile 100 arasinda olmalidir") from exc

        if parsed < 1 or parsed > 100:
            raise ValueError("Maksimum sonuc 1 ile 100 arasinda olmalidir")

        return parsed


class GoogleMapsScrapeJobResponse(BaseModel):
    success: bool
    job_id: str
    status: str


class GoogleMapsScrapeStopResponse(BaseModel):
    success: bool
    job_id: str
    status: str
    message: str


class GoogleMapsScrapeMetaResponse(BaseModel):
    success: bool
    has_running_job: bool
    cooldown_remaining_seconds: int


class GoogleMapsScrapeStatusResponse(BaseModel):
    success: bool
    status: str
    scraped_leads: int
    saved_leads: int
    skipped_duplicates: int
    scraped_count: int
    saved_count: int
    skipped_count: int
    message: str | None = None
    error: str | None = None


class SelectedLeadExportRequest(BaseModel):
    lead_ids: list[int]

    @field_validator("lead_ids")
    @classmethod
    def validate_lead_ids(cls, value: list[int]) -> list[int]:
        cleaned = [lead_id for lead_id in value if lead_id > 0]
        if not cleaned:
            raise ValueError("Lutfen en az bir kayit secin")
        return cleaned


class BulkStatusUpdateRequest(SelectedLeadExportRequest):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = _normalize_status_value(value)
        if normalized is None:
            raise ValueError("Gecersiz durum secildi")
        return normalized


class WhatsAppPrepareRequest(SelectedLeadExportRequest):
    message_template: Optional[str] = None

    @field_validator("message_template", mode="before")
    @classmethod
    def normalize_message_template(cls, value: object) -> Optional[str]:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None


class WhatsAppPreparedContact(BaseModel):
    id: int
    business_name: str
    original_phone: Optional[str] = None
    normalized_phone: Optional[str] = None
    whatsapp_url: Optional[str] = None
    note: Optional[str] = None


class WhatsAppPrepareResponse(BaseModel):
    success: bool
    contacts: list[WhatsAppPreparedContact]


class EmailPrepareRequest(SelectedLeadExportRequest):
    subject: Optional[str] = None
    body_template: Optional[str] = None

    @field_validator("subject", "body_template", mode="before")
    @classmethod
    def normalize_optional_template_text(cls, value: object) -> Optional[str]:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None


class EmailPreparedContact(BaseModel):
    id: int
    business_name: str
    email: Optional[str] = None
    mailto_url: Optional[str] = None
    note: Optional[str] = None


class EmailPrepareResponse(BaseModel):
    success: bool
    contacts: list[EmailPreparedContact]


def _normalize_status_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    normalized = value.strip().casefold()
    if not normalized:
        return None

    if normalized not in LEAD_STATUS_ALIASES:
        raise ValueError("Gecersiz durum secildi")

    return LEAD_STATUS_ALIASES[normalized]
