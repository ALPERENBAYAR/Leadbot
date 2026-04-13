from __future__ import annotations

import hmac
import os
from pathlib import Path
from datetime import date

from fastapi import FastAPI, Form, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.db import (
    bulk_set_next_contact_date,
    bulk_update_lead_status,
    clear_all_leads,
    count_all_leads,
    create_activities_for_leads,
    create_lead_activity,
    delete_lead,
    get_follow_up_summary,
    get_all_leads,
    get_lead_activities,
    get_leads_by_ids,
    get_query_labels,
    init_db,
    insert_lead,
    mark_lead_contacted,
    update_lead,
)
from app.email_tools import (
    DEFAULT_EMAIL_BODY,
    DEFAULT_EMAIL_SUBJECT,
    build_mailto_url,
    normalize_email_address,
    render_email_template,
)
from app.exporters import build_csv, build_excel, create_export_filename
from app.models import (
    BulkStatusUpdateRequest,
    EmailPrepareRequest,
    EmailPrepareResponse,
    EmailPreparedContact,
    GoogleMapsScrapeJobResponse,
    GoogleMapsScrapeMetaResponse,
    GoogleMapsScrapeRequest,
    GoogleMapsScrapeStatusResponse,
    GoogleMapsScrapeStopResponse,
    FollowUpSummaryResponse,
    Lead,
    LeadActivity,
    LeadActivityCreate,
    LeadCreate,
    LeadListResponse,
    LeadQueryOptionsResponse,
    LeadUpdate,
    SelectedLeadExportRequest,
    WhatsAppPrepareRequest,
    WhatsAppPrepareResponse,
    WhatsAppPreparedContact,
)
from app.scrape_jobs import create_scrape_job, get_scrape_job, get_scrape_meta, stop_scrape_job
from app.whatsapp import (
    DEFAULT_WHATSAPP_MESSAGE,
    build_whatsapp_url,
    normalize_whatsapp_phone,
    render_message_template,
)


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
AUTH_SESSION_KEY = "is_authenticated"
LOGIN_USERNAME = os.getenv("LEADBOT_USERNAME", "admin")
LOGIN_PASSWORD = os.getenv("LEADBOT_PASSWORD", "leadbot123")
SESSION_SECRET = os.getenv("LEADBOT_SESSION_SECRET", "leadbot-local-secret")

app = FastAPI(title="LeadBot")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax", https_only=False)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def render_dashboard(request: Request, active_view: str) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "page_title": "LeadBot",
            "active_view": active_view,
            "logged_in_username": request.session.get("username", LOGIN_USERNAME),
        },
    )


def render_login(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "page_title": "LeadBot Giriş",
            "login_error": message,
        },
    )


def is_authenticated(request: Request) -> bool:
    return bool(request.session.get(AUTH_SESSION_KEY))


def require_page_auth(request: Request) -> RedirectResponse | None:
    if is_authenticated(request):
        return None

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


def require_api_auth(request: Request) -> None:
    if is_authenticated(request):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Oturum süresi doldu. Lütfen yeniden giriş yapın.",
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else None
    message = "Geçersiz istek."

    if first_error:
        message = first_error.get("msg", message)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": message},
    )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    return render_login(request)


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
) -> Response:
    normalized_username = username.strip()
    if hmac.compare_digest(normalized_username, LOGIN_USERNAME) and hmac.compare_digest(password, LOGIN_PASSWORD):
        request.session[AUTH_SESSION_KEY] = True
        request.session["username"] = LOGIN_USERNAME
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    return render_login(request, message="Kullanıcı adı veya şifre hatalı.")


@app.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    auth_redirect = require_page_auth(request)
    if auth_redirect is not None:
        return auth_redirect
    return render_dashboard(request, active_view="overview")


@app.get("/leads", response_class=HTMLResponse)
def leads_page(request: Request) -> HTMLResponse:
    auth_redirect = require_page_auth(request)
    if auth_redirect is not None:
        return auth_redirect
    return render_dashboard(request, active_view="leads")


@app.get("/outreach", response_class=HTMLResponse)
def outreach_page(request: Request) -> HTMLResponse:
    auth_redirect = require_page_auth(request)
    if auth_redirect is not None:
        return auth_redirect
    return render_dashboard(request, active_view="communication")


@app.get("/api/leads", response_model=LeadListResponse)
def get_leads(
    request: Request,
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    next_contact_date: str | None = Query(default=None),
    query_labels: list[str] | None = Query(default=None, alias="query_label"),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> LeadListResponse:
    require_api_auth(request)
    items = get_all_leads(
        search=search,
        category=category,
        status=status_filter,
        next_contact_date=next_contact_date,
        query_labels=query_labels,
        limit=limit,
        offset=offset,
    )
    total = count_all_leads(
        search=search,
        category=category,
        status=status_filter,
        next_contact_date=next_contact_date,
        query_labels=query_labels,
    )

    return LeadListResponse(items=items, total=total, limit=limit, offset=offset)


@app.get("/api/leads/query-options", response_model=LeadQueryOptionsResponse)
def get_lead_query_options(request: Request) -> LeadQueryOptionsResponse:
    require_api_auth(request)
    return LeadQueryOptionsResponse(items=get_query_labels())


@app.post("/api/leads/by-ids", response_model=list[Lead])
def get_selected_leads(request: Request, payload: SelectedLeadExportRequest) -> list[Lead]:
    require_api_auth(request)
    return get_leads_by_ids(payload.lead_ids)


@app.get("/api/leads/follow-up-summary", response_model=FollowUpSummaryResponse)
def get_lead_follow_up_summary(request: Request) -> FollowUpSummaryResponse:
    require_api_auth(request)
    today, overdue = get_follow_up_summary()
    return FollowUpSummaryResponse(today=today, overdue=overdue)


@app.get("/api/leads/{lead_id}/activities", response_model=list[LeadActivity])
def get_lead_activity_history(request: Request, lead_id: int) -> list[LeadActivity]:
    require_api_auth(request)
    return get_lead_activities(lead_id)


@app.post("/api/leads/{lead_id}/activities", response_model=LeadActivity, status_code=status.HTTP_201_CREATED)
def create_lead_activity_route(request: Request, lead_id: int, payload: LeadActivityCreate) -> LeadActivity:
    require_api_auth(request)
    created = create_lead_activity(lead_id, payload)
    if created is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead bulunamadı.")

    return created


@app.post("/api/leads/{lead_id}/mark-contacted", response_model=Lead)
def mark_lead_contacted_route(request: Request, lead_id: int) -> Lead:
    require_api_auth(request)
    updated = mark_lead_contacted(lead_id)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead bulunamadı.")

    return updated


@app.delete("/api/leads")
def delete_all_leads(request: Request) -> dict[str, int | bool]:
    require_api_auth(request)
    deleted_count = clear_all_leads()
    return {"success": True, "deleted_count": deleted_count}


@app.delete("/api/leads/{lead_id}")
def delete_lead_route(request: Request, lead_id: int) -> dict[str, int | bool]:
    require_api_auth(request)
    deleted_count = delete_lead(lead_id)
    if deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead bulunamadÄ±.")

    return {"success": True, "deleted_count": deleted_count, "lead_id": lead_id}


@app.post("/api/leads/bulk-status")
def update_bulk_lead_status(request: Request, payload: BulkStatusUpdateRequest) -> dict[str, int | bool | str]:
    require_api_auth(request)
    updated_count = bulk_update_lead_status(payload.lead_ids, payload.status)
    if updated_count > 0 and payload.status == "quoted":
        create_activities_for_leads(payload.lead_ids, "quoted")
    return {"success": True, "updated_count": updated_count, "status": payload.status}


@app.post("/api/leads/schedule-today")
def schedule_selected_leads_for_today(request: Request, payload: SelectedLeadExportRequest) -> dict[str, int | bool | str]:
    require_api_auth(request)
    today_value = date.today().isoformat()
    updated_count = bulk_set_next_contact_date(payload.lead_ids, today_value)
    if updated_count > 0:
        create_activities_for_leads(
            payload.lead_ids,
            "note_added",
            "Sonraki iletişim tarihi bugüne çekildi.",
        )
    return {
        "success": True,
        "updated_count": updated_count,
        "next_contact_date": today_value,
    }


@app.post("/api/leads", response_model=Lead, status_code=status.HTTP_201_CREATED)
def create_lead(request: Request, payload: LeadCreate) -> Lead:
    require_api_auth(request)
    return insert_lead(payload)


@app.put("/api/leads/{lead_id}", response_model=Lead)
def update_lead_route(request: Request, lead_id: int, payload: LeadUpdate) -> Lead:
    require_api_auth(request)
    updated = update_lead(lead_id, payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead bulunamadı.")

    return updated


@app.post("/api/scrape/google-maps", response_model=GoogleMapsScrapeJobResponse)
def start_google_maps_scrape(request: Request, payload: GoogleMapsScrapeRequest) -> GoogleMapsScrapeJobResponse:
    require_api_auth(request)
    try:
        job_id = create_scrape_job(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    return GoogleMapsScrapeJobResponse(success=True, job_id=job_id, status="running")


@app.get("/api/scrape/google-maps/meta", response_model=GoogleMapsScrapeMetaResponse)
def get_google_maps_scrape_meta(request: Request) -> GoogleMapsScrapeMetaResponse:
    require_api_auth(request)
    has_running_job, cooldown_remaining_seconds = get_scrape_meta()
    return GoogleMapsScrapeMetaResponse(
        success=True,
        has_running_job=has_running_job,
        cooldown_remaining_seconds=cooldown_remaining_seconds,
    )


@app.get("/api/scrape/google-maps/{job_id}", response_model=GoogleMapsScrapeStatusResponse)
def get_google_maps_scrape_status(request: Request, job_id: str) -> GoogleMapsScrapeStatusResponse:
    require_api_auth(request)
    job = get_scrape_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarama işi bulunamadı.")

    message: str | None = None
    if job.status == "running":
        message = (
            f"Tarama devam ediyor... {job.scraped_leads} sonuç bulundu, "
            f"{job.saved_leads} kayıt eklendi, {job.skipped_duplicates} kayıt tekrar olduğu için atlandı."
        )
    elif job.status == "stopping":
        message = "Tarama durduruluyor. Lütfen bekleyin..."
    elif job.status == "completed":
        message = (
            f"Tarama tamamlandı. {job.scraped_leads} sonuç bulundu, "
            f"{job.saved_leads} kayıt eklendi, {job.skipped_duplicates} kayıt tekrar olduğu için atlandı."
        )
    elif job.status == "cancelled":
        message = "Tarama durduruldu."
    elif job.status == "failed" and job.error:
        message = job.error

    return GoogleMapsScrapeStatusResponse(
        success=job.status != "failed",
        status=job.status,
        scraped_leads=job.scraped_leads,
        saved_leads=job.saved_leads,
        skipped_duplicates=job.skipped_duplicates,
        scraped_count=job.scraped_leads,
        saved_count=job.saved_leads,
        skipped_count=job.skipped_duplicates,
        message=message,
        error=job.error,
    )


@app.post("/api/scrape/google-maps/{job_id}/stop", response_model=GoogleMapsScrapeStopResponse)
def stop_google_maps_scrape(request: Request, job_id: str) -> GoogleMapsScrapeStopResponse:
    require_api_auth(request)
    job = stop_scrape_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarama işi bulunamadı.")

    return GoogleMapsScrapeStopResponse(
        success=True,
        job_id=job_id,
        status=job.status,
        message="Tarama durdurma isteği alındı.",
    )


@app.post("/api/whatsapp/prepare-selected", response_model=WhatsAppPrepareResponse)
def prepare_selected_whatsapp(request: Request, payload: WhatsAppPrepareRequest) -> WhatsAppPrepareResponse:
    require_api_auth(request)
    leads = get_leads_by_ids(payload.lead_ids)
    prepared_contacts: list[WhatsAppPreparedContact] = []

    for lead in leads:
        normalized_phone = normalize_whatsapp_phone(lead.phone)
        if not normalized_phone:
            continue

        message = render_message_template(payload.message_template, lead.business_name)
        prepared_contacts.append(
            WhatsAppPreparedContact(
                id=lead.id,
                business_name=lead.business_name,
                original_phone=lead.phone,
                normalized_phone=normalized_phone,
                whatsapp_url=build_whatsapp_url(lead.phone, message),
                note="Hazır",
            )
        )

    if prepared_contacts:
        create_activities_for_leads(
            [contact.id for contact in prepared_contacts],
            "whatsapp_prepared",
        )

    return WhatsAppPrepareResponse(success=True, contacts=prepared_contacts)


@app.post("/api/email/prepare-selected", response_model=EmailPrepareResponse)
def prepare_selected_email(request: Request, payload: EmailPrepareRequest) -> EmailPrepareResponse:
    require_api_auth(request)
    leads = get_leads_by_ids(payload.lead_ids)
    prepared_contacts: list[EmailPreparedContact] = []

    for lead in leads:
        normalized_email = normalize_email_address(lead.email)
        if not normalized_email:
            continue

        subject = payload.subject or DEFAULT_EMAIL_SUBJECT
        body = render_email_template(payload.body_template or DEFAULT_EMAIL_BODY, lead.business_name)
        prepared_contacts.append(
            EmailPreparedContact(
                id=lead.id,
                business_name=lead.business_name,
                email=normalized_email,
                mailto_url=build_mailto_url(normalized_email, subject=subject, body=body),
                note="Hazır",
            )
        )

    if prepared_contacts:
        create_activities_for_leads(
            [contact.id for contact in prepared_contacts],
            "email_prepared",
        )

    return EmailPrepareResponse(success=True, contacts=prepared_contacts)


@app.get("/api/export/csv")
def export_all_csv(request: Request) -> Response:
    require_api_auth(request)
    leads = get_all_leads()
    content = build_csv(leads)
    filename = create_export_filename("csv")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/export/excel")
def export_all_excel(request: Request) -> Response:
    require_api_auth(request)
    leads = get_all_leads()
    content = build_excel(leads)
    filename = create_export_filename("xlsx")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/export/selected/csv")
def export_selected_csv(request: Request, payload: SelectedLeadExportRequest) -> Response:
    require_api_auth(request)
    leads = get_leads_by_ids(payload.lead_ids)
    content = build_csv(leads)
    filename = create_export_filename("csv", selected=True)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/export/selected/excel")
def export_selected_excel(request: Request, payload: SelectedLeadExportRequest) -> Response:
    require_api_auth(request)
    leads = get_leads_by_ids(payload.lead_ids)
    content = build_excel(leads)
    filename = create_export_filename("xlsx", selected=True)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
