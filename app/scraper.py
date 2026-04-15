from __future__ import annotations

import re
from random import randint
from collections.abc import Callable, Iterable
from urllib.parse import quote_plus, urljoin, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.models import LeadCreate


LISTING_SELECTORS = [
    'a[href*="/place/"]',
    'div[role="article"] a[href*="/place/"]',
    'div[role="feed"] a[href*="/place/"]',
]

EMAIL_REGEX = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
UNWANTED_EMAIL_PARTS = (
    "example@example.com",
    "test@test.com",
    "noreply@",
    "no-reply@",
)
GENERIC_EMAIL_PREFIXES = (
    "info@",
    "destek@",
    "satis@",
    "hello@",
    "contact@",
    "iletisim@",
)
CONTACT_PATHS = [
    "/iletisim",
    "/contact",
    "/iletisim.html",
    "/contact-us",
    "/about",
]
CONTACT_LINK_HINTS = ("iletişim", "iletisim", "contact", "about", "destek")
INVALID_BUSINESS_NAMES = {
    "sonuçlar",
    "sonuclar",
    "results",
    "google maps",
}
RESULT_ACTION_DELAY_RANGE = (500, 900)
SCROLL_DELAY_RANGE = (900, 1400)
BLOCK_PATTERNS = (
    "unusual traffic",
    "olağandışı trafik",
    "sorry, but your computer or network may be sending automated queries",
    "detected unusual traffic",
    "i'm not a robot",
    "ben robot değilim",
)
CONSENT_BUTTON_SELECTORS = (
    'button:has-text("Tümünü kabul et")',
    'button[aria-label="Tümünü kabul et"]',
    'button:has-text("Accept all")',
    'button[aria-label="Accept all"]',
)


class ScrapeCancelled(Exception):
    pass


def scrape_google_maps(
    keyword: str,
    location: str,
    max_results: int,
    on_lead: Callable[[LeadCreate], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[LeadCreate]:
    query = f"{keyword} {location}".strip()
    collected: list[LeadCreate] = []
    seen_keys: set[tuple[str, str | None, str | None, str | None]] = set()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            locale="tr-TR",
            timezone_id="Europe/Istanbul",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
            },
        )
        page = context.new_page()
        page.goto(
            f"https://www.google.com/maps/search/{quote_plus(query)}",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        _handle_google_consent(page)
        _raise_if_google_blocked(page)

        _wait_for_results(page)
        scroll_container = _find_scroll_container(page)

        last_count = 0
        stalled_attempts = 0

        while len(collected) < max_results and stalled_attempts < 6:
            _raise_if_should_stop(should_stop)
            cards = _get_result_cards(page)
            current_count = cards.count()

            if current_count == 0:
                break

            if current_count == last_count:
                stalled_attempts += 1
            else:
                stalled_attempts = 0
                last_count = current_count

            for index in range(current_count):
                _raise_if_should_stop(should_stop)
                if len(collected) >= max_results:
                    break

                try:
                    _raise_if_google_blocked(page)
                    card = cards.nth(index)
                    card.scroll_into_view_if_needed(timeout=5000)
                    _pause(page, *RESULT_ACTION_DELAY_RANGE)
                    card.click(timeout=5000)
                    detail = _extract_listing_details(page)
                except Exception:
                    continue

                if detail is None:
                    continue

                if detail.website:
                    _raise_if_should_stop(should_stop)
                    detail.email = _enrich_email_from_website(context, detail.website)

                dedupe_key = (
                    _normalize_text(detail.business_name) or "",
                    _normalize_text(detail.phone),
                    _normalize_text(detail.address),
                    _normalize_text(detail.website),
                )
                if dedupe_key in seen_keys:
                    continue

                seen_keys.add(dedupe_key)
                collected.append(detail)
                if on_lead is not None:
                    try:
                        on_lead(detail)
                    except Exception:
                        pass

            _scroll_results(page, scroll_container)

        context.close()
        browser.close()

    return collected


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = " ".join(value.split()).strip()
    return cleaned.casefold() if cleaned else None


def _wait_for_results(page) -> None:
    for selector in LISTING_SELECTORS:
        try:
            page.wait_for_selector(selector, timeout=15000)
            return
        except PlaywrightTimeoutError:
            _handle_google_consent(page)
            _raise_if_google_blocked(page)
            continue


def _get_result_cards(page):
    for selector in LISTING_SELECTORS:
        locator = page.locator(selector)
        try:
            if locator.count() > 0:
                return locator
        except Exception:
            continue

    return page.locator('a[href*="/place/"]')


def _find_scroll_container(page):
    candidates = [
        'div[role="feed"]',
        'div[aria-label][role="main"] div[role="feed"]',
        'div[role="main"]',
    ]
    for selector in candidates:
        locator = page.locator(selector).first
        try:
            if locator.count() > 0:
                return locator
        except Exception:
            continue

    return None


def _scroll_results(page, scroll_container) -> None:
    try:
        if scroll_container is not None:
            scroll_container.evaluate("(node) => { node.scrollBy(0, node.scrollHeight); }")
        else:
            page.mouse.wheel(0, 5000)
        _pause(page, *SCROLL_DELAY_RANGE)
    except Exception:
        _pause(page, *SCROLL_DELAY_RANGE)


def _extract_listing_details(page) -> LeadCreate | None:
    _pause(page, 700, 1000)

    name = _extract_business_name(page)
    if not name:
        return None

    phone = _extract_info_value(page, ["Phone", "Telefon", "Telefon:"])
    website = _extract_website(page)
    address = _extract_info_value(page, ["Address", "Adres", "Adres:"])
    category = _extract_category(page)

    return LeadCreate(
        business_name=name,
        phone=phone,
        website=website,
        address=address,
        category=category,
        source="google_maps",
        status="new",
    )


def _extract_info_value(page, labels: Iterable[str]) -> str | None:
    for label in labels:
        try:
            button = page.locator(
                f'button[data-item-id*="{label.lower()}"], '
                f'button[aria-label*="{label}"], '
                f'div[role="main"] button[aria-label*="{label}"]'
            ).first
            if button.count() > 0:
                text = button.inner_text(timeout=3000).strip()
                cleaned = text.replace(f"{label}:", "").strip()
                if cleaned and cleaned != text:
                    return cleaned
                if cleaned:
                    return cleaned
        except Exception:
            continue

    fallback_selectors: list[str] = []
    labels_lower = {label.lower() for label in labels}
    if "phone" in labels_lower or "telefon" in labels_lower:
        fallback_selectors.append('button[data-item-id*="phone"]')
    if "address" in labels_lower or "adres" in labels_lower:
        fallback_selectors.append('button[data-item-id*="address"]')

    for selector in fallback_selectors:
        try:
            button = page.locator(selector).first
            if button.count() > 0:
                text = button.inner_text(timeout=3000).strip()
                if text:
                    return text
        except Exception:
            continue

    return None


def _extract_website(page) -> str | None:
    selectors = [
        'a[data-item-id="authority"]',
        'a[data-item-id*="authority"]',
        'a[aria-label*="Website"]',
        'a[aria-label*="Web sitesi"]',
    ]
    for selector in selectors:
        try:
            link = page.locator(selector).first
            if link.count() > 0:
                href = link.get_attribute("href", timeout=3000)
                if href:
                    return href
        except Exception:
            continue

    return None


def _extract_category(page) -> str | None:
    selectors = [
        'button[jsaction*="pane.rating.category"]',
        'div[role="main"] button[aria-label*="Category"]',
        'div[role="main"] button[aria-label*="Kategori"]',
        'div[role="main"] span button',
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0:
                text = locator.inner_text(timeout=3000).strip()
                if text and len(text) < 120 and not text.startswith("Yorum"):
                    return text
        except Exception:
            continue

    return None


def _first_text(page, selectors: Iterable[str]) -> str:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0:
                text = " ".join(locator.inner_text(timeout=3000).split()).strip()
                if text:
                    return text
        except Exception:
            continue

    return ""


def _extract_business_name(page) -> str:
    selectors = [
        "h1.DUwDvf",
        "h1.fontHeadlineLarge",
        'div[role="main"] h1',
        "h1",
    ]

    for selector in selectors:
        name = _first_text(page, [selector])
        if _is_valid_business_name(name):
            return name

    try:
        title = page.title().strip()
    except Exception:
        title = ""

    if title:
        cleaned_title = title.split(" - Google Maps", 1)[0].strip()
        if _is_valid_business_name(cleaned_title):
            return cleaned_title

    return ""


def _is_valid_business_name(value: str) -> bool:
    normalized = _normalize_text(value)
    if not normalized:
        return False

    if normalized in INVALID_BUSINESS_NAMES:
        return False

    return len(normalized) > 2


def _enrich_email_from_website(context, website_url: str) -> str | None:
    normalized_url = _normalize_website_url(website_url)
    if not normalized_url:
        return None

    page = context.new_page()
    visited_urls: set[str] = set()
    candidate_urls = [normalized_url]

    try:
        for candidate_url in candidate_urls[:5]:
            if candidate_url in visited_urls:
                continue

            visited_urls.add(candidate_url)
            email, extra_urls = _extract_email_from_page(page, candidate_url, normalized_url)
            if email:
                return email

            for extra_url in extra_urls:
                if extra_url not in visited_urls and extra_url not in candidate_urls:
                    candidate_urls.append(extra_url)

        return None
    finally:
        page.close()


def _extract_email_from_page(page, candidate_url: str, base_url: str) -> tuple[str | None, list[str]]:
    try:
        page.goto(candidate_url, wait_until="domcontentloaded", timeout=8000)
        _pause(page, 700, 1000)
    except Exception:
        return None, []

    emails = _collect_emails_from_page(page)
    best_email = _select_best_email(emails)
    if best_email:
        return best_email, []

    follow_up_urls = _collect_candidate_links(page, base_url)
    if candidate_url == base_url:
        for path in CONTACT_PATHS:
            follow_up_url = urljoin(base_url, path)
            if follow_up_url not in follow_up_urls:
                follow_up_urls.append(follow_up_url)

    return None, follow_up_urls[:4]


def _collect_emails_from_page(page) -> set[str]:
    emails: set[str] = set()

    try:
        content = page.content()
        emails.update(_extract_emails_from_text(content))
    except Exception:
        pass

    try:
        body_text = page.locator("body").inner_text(timeout=3000)
        emails.update(_extract_emails_from_text(body_text))
    except Exception:
        pass

    try:
        links = page.locator('a[href^="mailto:"]')
        for index in range(links.count()):
            href = links.nth(index).get_attribute("href", timeout=1000)
            if href:
                email_value = href.replace("mailto:", "").split("?")[0].strip().lower()
                if _is_valid_email(email_value):
                    emails.add(email_value)
    except Exception:
        pass

    return emails


def _collect_candidate_links(page, base_url: str) -> list[str]:
    collected_links: list[str] = []
    base_domain = urlparse(base_url).netloc

    try:
        links = page.locator("a[href]")
        count = min(links.count(), 60)
    except Exception:
        return collected_links

    for index in range(count):
        try:
            link = links.nth(index)
            href = link.get_attribute("href", timeout=1000)
            text = " ".join((link.inner_text(timeout=1000) or "").split()).lower()
        except Exception:
            continue

        if not href:
            continue

        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc != base_domain:
            continue

        url_text = full_url.lower()
        if any(hint in text or hint in url_text for hint in CONTACT_LINK_HINTS):
            if full_url not in collected_links:
                collected_links.append(full_url)

    return collected_links[:4]


def _extract_emails_from_text(text: str) -> set[str]:
    return {email for email in (match.lower().strip() for match in EMAIL_REGEX.findall(text)) if _is_valid_email(email)}


def _is_valid_email(email: str) -> bool:
    if not email or " " in email:
        return False

    lowered = email.lower().strip()
    return not any(unwanted in lowered for unwanted in UNWANTED_EMAIL_PARTS)


def _select_best_email(emails: set[str]) -> str | None:
    if not emails:
        return None

    def score(email: str) -> tuple[int, int, str]:
        is_generic = any(email.startswith(prefix) for prefix in GENERIC_EMAIL_PREFIXES)
        domain = email.split("@", 1)[1]
        return (1 if is_generic else 0, len(domain), email)

    return sorted(emails, key=score)[0]


def _normalize_website_url(website_url: str) -> str | None:
    cleaned = website_url.strip()
    if not cleaned:
        return None

    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"

    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    return f"{parsed.scheme}://{parsed.netloc}"


def _pause(page, min_ms: int, max_ms: int) -> None:
    page.wait_for_timeout(randint(min_ms, max_ms))


def _handle_google_consent(page) -> None:
    if "consent.google.com" not in page.url:
        return

    for selector in CONSENT_BUTTON_SELECTORS:
        try:
            button = page.locator(selector).first
            if button.count() == 0:
                continue

            button.click(timeout=5000)
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            try:
                page.wait_for_url(lambda url: "consent.google.com" not in url, timeout=10000)
            except PlaywrightTimeoutError:
                pass
            return
        except Exception:
            continue


def _raise_if_google_blocked(page) -> None:
    try:
        if "consent.google.com" in page.url:
            return
        content = page.content().lower()
    except Exception:
        return

    if any(pattern in content for pattern in BLOCK_PATTERNS):
        raise RuntimeError(
            "Google olağandışı trafik veya doğrulama ekranı gösterdi. Riski azaltmak için tarama durduruldu."
        )


def _raise_if_should_stop(should_stop: Callable[[], bool] | None) -> None:
    if should_stop is not None and should_stop():
        raise ScrapeCancelled("Tarama kullanıcı tarafından durduruldu.")
