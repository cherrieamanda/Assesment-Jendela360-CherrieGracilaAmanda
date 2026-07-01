"""
scrape_all.py — Scrape all POPULAR_LOCATIONS from SPEEDHOME and save to sample_data.json.

Usage:
    python scrape_all.py             # skip areas already in sample_data.json
    python scrape_all.py --force     # re-scrape everything
    python scrape_all.py --area mont-kiara  # scrape a single area only
"""

import json
import re
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_FILE = Path(__file__).parent / "sample_data.json"
MAX_PAGES = 10
DELAY_BETWEEN_PAGES = 1.5   # seconds
DELAY_BETWEEN_AREAS = 2.0   # seconds
BROWSER_PROFILES = ["chrome", "chrome110", "chrome116", "chrome120", "edge101"]

POPULAR_LOCATIONS = [
    "Kuala Lumpur", "Petaling Jaya", "Shah Alam", "Cyberjaya", "Puchong",
    "Kajang", "Subang Jaya", "Bukit Jalil", "Seri Kembangan", "Cheras",
    "Ampang", "Klang", "Seremban", "Johor Bahru", "Penang", "Melaka",
    "Ipoh", "Batu Caves", "Kepong", "Mont Kiara", "Bangsar",
    "Damansara", "Sentul", "Rawang", "Semenyih", "Nilai",
    "Setapak", "Segambut", "Wangsa Maju", "Old Klang Road",
    "Sri Petaling", "Kuchai Lama", "Desa Petaling", "Bukit Bintang",
    "Titiwangsa", "Damansara Heights", "Bangsar South", "Dutamas",
    "Bayan Lepas", "Sepang", "Dengkil", "Sungai Buloh",
    "Selayang", "Gombak", "Balakong", "Bangi",
    "Ara Damansara", "Tropicana", "Kota Damansara",
    "Putrajaya", "Setia Alam", "Bukit Mertajam", "Butterworth",
]


def location_to_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


# ── Build ID ──────────────────────────────────────────────────────────────────
def get_build_id(session) -> str:
    print("  Fetching Next.js buildId...", end=" ", flush=True)
    try:
        resp = session.get("https://speedhome.com/rent/kuala-lumpur", timeout=25)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            nd = soup.find("script", id="__NEXT_DATA__")
            if nd:
                build_id = json.loads(nd.string).get("buildId", "")
                print(f"OK ({build_id[:16]}...)")
                return build_id
    except Exception as e:
        print(f"FAILED ({e})")
    return ""


# ── Scrape one area ───────────────────────────────────────────────────────────
def scrape_area_json(slug: str, build_id: str, session) -> tuple[list, int, str]:
    """Try _next/data JSON API first (faster, no HTML parsing)."""
    all_listings = []
    total = 0
    label = slug.replace("-", " ").title()

    for page in range(1, MAX_PAGES + 1):
        if page == 1:
            url = f"https://speedhome.com/_next/data/{build_id}/rent/{slug}.json"
        else:
            url = f"https://speedhome.com/_next/data/{build_id}/rent/{slug}.json?page={page}"

        for attempt, profile in enumerate(BROWSER_PROFILES[:3]):
            try:
                s = curl_requests.Session(impersonate=profile)
                resp = s.get(url, timeout=25)
                if resp.status_code != 200:
                    time.sleep(1)
                    continue

                data = resp.json()
                props = data.get("pageProps", {})
                pl = props.get("propertyList", {})
                content = pl.get("content", [])

                if not content:
                    return all_listings, total, label

                if page == 1:
                    total = pl.get("totalElements", 0)
                    meta = props.get("enhancedMetaData", {})
                    if meta.get("area"):
                        label = meta["area"]

                for item in content:
                    all_listings.append(_extract_fields(item))

                if pl.get("last", True):
                    return all_listings, total, label

                time.sleep(DELAY_BETWEEN_PAGES)
                break

            except Exception:
                time.sleep(1)

    return all_listings, total, label


def scrape_area_html(slug: str, session) -> tuple[list, int, str]:
    """HTML fallback — parse __NEXT_DATA__ from rendered page."""
    all_listings = []
    total = 0
    label = slug.replace("-", " ").title()

    for page in range(1, MAX_PAGES + 1):
        url = f"https://speedhome.com/rent/{slug}" + (f"?page={page}" if page > 1 else "")

        for profile in BROWSER_PROFILES:
            try:
                s = curl_requests.Session(impersonate=profile)
                resp = s.get(url, timeout=25)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "lxml")
                nd = soup.find("script", id="__NEXT_DATA__")
                if not nd:
                    continue

                data = json.loads(nd.string)
                props = data.get("props", {}).get("pageProps", {})
                pl = props.get("propertyList", {})
                content = pl.get("content", [])

                if not content:
                    return all_listings, total, label

                if page == 1:
                    total = pl.get("totalElements", 0)
                    meta = props.get("enhancedMetaData", {})
                    if meta.get("area"):
                        label = meta["area"]

                for item in content:
                    all_listings.append(_extract_fields(item))

                if pl.get("last", True):
                    return all_listings, total, label

                time.sleep(DELAY_BETWEEN_PAGES)
                break

            except Exception:
                continue

    return all_listings, total, label


def _extract_fields(item: dict) -> dict:
    return {
        "name":        item.get("name"),
        "address":     item.get("address"),
        "bedroom":     item.get("bedroom", 0),
        "bathroom":    item.get("bathroom", 0),
        "roomType":    item.get("roomType"),
        "price":       item.get("price", 0),
        "sqft":        item.get("sqft", 0),
        "buildUpSize": item.get("buildUpSize", 0),
        "furnishType": item.get("furnishType"),
        "type":        item.get("type"),
        "slug":        item.get("slug"),
        "ref":         item.get("ref"),
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    force = "--force" in sys.argv
    single = None
    if "--area" in sys.argv:
        idx = sys.argv.index("--area")
        if idx + 1 < len(sys.argv):
            single = sys.argv[idx + 1]

    # Load existing data
    existing: dict = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"Loaded {len(existing)} existing areas from {OUTPUT_FILE.name}")
    else:
        print(f"No existing {OUTPUT_FILE.name} — starting fresh")

    # Build slug list
    if single:
        slugs = [(single, single.replace("-", " ").title())]
    else:
        slugs = sorted(
            {(location_to_slug(loc), loc) for loc in POPULAR_LOCATIONS},
            key=lambda x: x[0],
        )

    if not force and not single:
        skip = [s for s, _ in slugs if s in existing]
        todo = [(s, n) for s, n in slugs if s not in existing]
        if skip:
            print(f"Skipping {len(skip)} already-cached areas (use --force to re-scrape all)")
        print(f"Areas to scrape: {len(todo)}")
    else:
        todo = slugs

    if not todo:
        print("Nothing to do. Run with --force to refresh all areas.")
        return

    # Get build ID once
    session = curl_requests.Session(impersonate="chrome")
    build_id = get_build_id(session)

    success, failed = 0, []

    for i, (slug, name) in enumerate(todo, 1):
        print(f"\n[{i}/{len(todo)}] {name} ({slug})", flush=True)

        # Try JSON API first
        if build_id:
            listings, total, label = scrape_area_json(slug, build_id, session)
            method = "JSON API"
        else:
            listings, total, label = [], 0, slug.replace("-", " ").title()

        # Fall back to HTML scraping
        if not listings:
            print(f"  JSON API returned nothing — trying HTML fallback...", end=" ", flush=True)
            listings, total, label = scrape_area_html(slug, session)
            method = "HTML"

        if listings:
            existing[slug] = {"listings": listings, "total": total, "label": label}
            # Save after every area so partial progress is never lost
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False)
            print(f"  {method}: {len(listings)} listings (total on site: {total}) — saved")
            success += 1
        else:
            print(f"  No data found — skipping")
            failed.append(slug)

        if i < len(todo):
            time.sleep(DELAY_BETWEEN_AREAS)

    print(f"\n{'='*60}")
    print(f"Done. {success} areas scraped successfully.")
    print(f"Total areas in {OUTPUT_FILE.name}: {len(existing)}")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed)}")


if __name__ == "__main__":
    main()
