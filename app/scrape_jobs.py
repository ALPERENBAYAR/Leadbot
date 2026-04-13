from __future__ import annotations

from dataclasses import dataclass
from threading import Lock, Thread
from time import time
from uuid import uuid4

from app.db import insert_lead_if_new, save_scrape_query
from app.models import GoogleMapsScrapeRequest, LeadCreate
from app.scraper import ScrapeCancelled, scrape_google_maps


@dataclass
class ScrapeJobState:
    status: str = "pending"
    scraped_leads: int = 0
    saved_leads: int = 0
    skipped_duplicates: int = 0
    error: str | None = None
    cancel_requested: bool = False


_jobs: dict[str, ScrapeJobState] = {}
_jobs_lock = Lock()
_last_job_started_at = 0.0
SCRAPE_COOLDOWN_SECONDS = 20


def create_scrape_job(payload: GoogleMapsScrapeRequest) -> str:
    global _last_job_started_at
    job_id = uuid4().hex

    with _jobs_lock:
        if any(job.status == "running" for job in _jobs.values()):
            raise ValueError("Zaten devam eden bir tarama var. Lütfen mevcut taramanın bitmesini bekleyin.")

        now = time()
        if now - _last_job_started_at < SCRAPE_COOLDOWN_SECONDS:
            remaining_seconds = int(SCRAPE_COOLDOWN_SECONDS - (now - _last_job_started_at))
            raise ValueError(
                f"Google Maps için kısa bir bekleme uygulanıyor. Lütfen {remaining_seconds} saniye sonra tekrar deneyin."
            )

        _jobs[job_id] = ScrapeJobState(status="running")
        _last_job_started_at = now

    save_scrape_query(f"{payload.keyword.strip()} - {payload.location.strip()}")

    worker = Thread(target=_run_scrape_job, args=(job_id, payload), daemon=True)
    worker.start()
    return job_id


def get_scrape_job(job_id: str) -> ScrapeJobState | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def get_scrape_meta() -> tuple[bool, int]:
    with _jobs_lock:
        has_running_job = any(job.status in {"running", "stopping"} for job in _jobs.values())
        elapsed = time() - _last_job_started_at
        cooldown_remaining_seconds = max(0, int(SCRAPE_COOLDOWN_SECONDS - elapsed))

    return has_running_job, cooldown_remaining_seconds


def stop_scrape_job(job_id: str) -> ScrapeJobState | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return None

        if job.status == "running":
            job.cancel_requested = True
            job.status = "stopping"

        return job


def _run_scrape_job(job_id: str, payload: GoogleMapsScrapeRequest) -> None:
    query_label = f"{payload.keyword.strip()} - {payload.location.strip()}"

    def should_stop() -> bool:
        with _jobs_lock:
            job = _jobs.get(job_id)
            return bool(job and job.cancel_requested)

    def handle_lead(lead: LeadCreate) -> None:
        if should_stop():
            raise ScrapeCancelled("Tarama kullanıcı tarafından durduruldu.")

        lead.query_label = query_label
        saved = insert_lead_if_new(lead)

        with _jobs_lock:
            job = _jobs[job_id]
            job.scraped_leads += 1
            if saved:
                job.saved_leads += 1
            else:
                job.skipped_duplicates += 1

    try:
        scrape_google_maps(
            keyword=payload.keyword,
            location=payload.location,
            max_results=payload.max_results,
            on_lead=handle_lead,
            should_stop=should_stop,
        )
        with _jobs_lock:
            if _jobs[job_id].cancel_requested:
                _jobs[job_id].status = "cancelled"
                _jobs[job_id].error = "Tarama kullanıcı tarafından durduruldu."
            else:
                _jobs[job_id].status = "completed"
    except ScrapeCancelled as exc:
        with _jobs_lock:
            job = _jobs[job_id]
            job.status = "cancelled"
            job.error = str(exc)
    except Exception as exc:
        with _jobs_lock:
            job = _jobs[job_id]
            job.status = "failed"
            job.error = f"Google Maps taraması başarısız oldu: {exc}"
