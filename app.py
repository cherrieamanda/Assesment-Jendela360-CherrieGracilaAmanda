import streamlit as st
import pandas as pd
import numpy as np
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup
import json
import time
import re
from io import BytesIO
from datetime import datetime
from statistics import mode, StatisticsError

# ─── Color Palette ───────────────────────────────────────────────────────────
# Primary: #2563EB | Primary Hover: #1D4ED8 | Secondary: #06B6D4
# Accent: #10B981 | Background: #F8FAFC | Surface: #FFFFFF
# Border: #E2E8F0 | Text Primary: #0F172A | Text Secondary: #475569
# Text Muted: #94A3B8 | Success: #22C55E | Warning: #F59E0B
# Info: #3B82F6 | Error: #EF4444
# Gradient: #2563EB → #06B6D4

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Property Price Intelligence — SPEEDHOME",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp {
        background-color: #F8FAFC;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* Header */
    .main-header {
        text-align: center;
        padding: 1.8rem 1rem;
        background: linear-gradient(135deg, #2563EB 0%, #06B6D4 100%);
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 {
        font-size: 1.8rem;
        margin: 0;
        color: white;
    }
    .main-header p {
        font-size: 0.95rem;
        opacity: 0.85;
        margin: 0.3rem 0 0 0;
        color: white;
    }

    /* Overview cards */
    .overview-card {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        display: flex;
        align-items: flex-start;
        gap: 0.9rem;
        height: 100%;
    }
    .overview-icon {
        width: 44px;
        height: 44px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        font-size: 1.2rem;
    }
    .overview-icon.blue   { background: #2563EB; }
    .overview-icon.teal   { background: #06B6D4; }
    .overview-icon.green  { background: #10B981; }
    .overview-icon.purple { background: #8B5CF6; }
    .overview-text { flex: 1; }
    .overview-text .label {
        font-size: 0.8rem;
        color: #475569;
        font-weight: 600;
        margin: 0;
    }
    .overview-text .value {
        font-size: 1.6rem;
        color: #0F172A;
        font-weight: 700;
        margin: 0.1rem 0;
        line-height: 1.2;
    }
    .overview-text .sub {
        font-size: 0.75rem;
        color: #0F172A;
        margin: 0;
    }

    /* Blue index text (No + Listing Title) and center No column */
    div[data-testid="stDataFrame"] [data-testid="stDataFrameResizableContainer"]
        [role="rowgroup"] [role="row"] th {
        color: #2563EB !important;
    }
    div[data-testid="stDataFrame"] [data-testid="stDataFrameResizableContainer"]
        [role="columnheader"]:first-child {
        text-align: center !important;
    }
    div[data-testid="stDataFrame"] [data-testid="stDataFrameResizableContainer"]
        [role="rowgroup"] [role="row"] th:first-child {
        text-align: center !important;
    }

    /* Primary button */
    .stButton > button[kind="primary"] {
        background-color: #2563EB !important;
        border-color: #2563EB !important;
        color: white !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #1D4ED8 !important;
        border-color: #1D4ED8 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 2px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1.5rem;
        color: #475569;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important;
        color: white !important;
    }

    /* Info box */
    .info-box {
        background: #EFF6FF;
        border: 1px solid #3B82F6;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        font-size: 0.85rem;
        color: #1E40AF;
        margin: 0.5rem 0;
    }

    /* Section headers */
    h3 { color: #0F172A !important; }
    h4 { color: #0F172A !important; }

    /* Responsive */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .main-header h1 {
            font-size: 1.3rem;
        }
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Download buttons */
    .stDownloadButton > button {
        background-color: #10B981 !important;
        color: white !important;
        border-color: #10B981 !important;
    }
    .stDownloadButton > button:hover {
        background-color: #059669 !important;
        border-color: #059669 !important;
    }

    /* Success alert */
    div[data-testid="stAlert"] {
        border-radius: 8px;
    }

    /* Hide anchor links on headers */
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a,
    .stMarkdown a[href^="#"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Location Data ───────────────────────────────────────────────────────────
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
POPULAR_LOCATIONS = sorted(set(POPULAR_LOCATIONS))


def location_to_slug(name):
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


# ─── Scraper ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def scrape_speedhome(area_slug, max_pages=10):
    session = curl_requests.Session(impersonate="chrome")
    all_listings = []
    total_elements = 0
    area_label = area_slug.replace("-", " ").title()

    for page_num in range(1, max_pages + 1):
        if page_num == 1:
            url = f"https://speedhome.com/rent/{area_slug}"
        else:
            url = f"https://speedhome.com/rent/{area_slug}?page={page_num}"

        try:
            resp = session.get(url, timeout=20)
            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.text, "lxml")
            next_data = soup.find("script", id="__NEXT_DATA__")
            if not next_data:
                break

            data = json.loads(next_data.string)
            props = data.get("props", {}).get("pageProps", {})
            prop_list = props.get("propertyList", {})
            content = prop_list.get("content", [])

            if not content:
                break

            if page_num == 1:
                total_elements = prop_list.get("totalElements", 0)
                meta = props.get("enhancedMetaData", {})
                if meta.get("area"):
                    area_label = meta["area"]

            all_listings.extend(content)

            if prop_list.get("last", True):
                break

            time.sleep(1.5)

        except Exception as e:
            st.warning(f"Error fetching page {page_num}: {str(e)}")
            break

    return all_listings, total_elements, area_label


def parse_listings(raw_listings):
    records = []
    for item in raw_listings:
        bedroom = item.get("bedroom", 0) or 0
        room_type = item.get("roomType")

        if room_type and "STUDIO" in str(room_type).upper():
            unit_type = "Studio"
        elif room_type and "ROOM" in str(room_type).upper():
            unit_type = "Room"
        elif bedroom == 0:
            unit_type = "Studio"
        else:
            unit_type = f"{bedroom}BR"

        price = item.get("price", 0) or 0
        sqft = item.get("sqft", 0) or item.get("buildUpSize", 0) or 0
        sqft_display = f"{int(sqft):,} sqft" if sqft > 0 else "No data"

        furnish_map = {"FULL": "Fully Furnished", "PARTIAL": "Partially Furnished", "NONE": "Unfurnished"}
        furnish = furnish_map.get(item.get("furnishType", ""), item.get("furnishType", "N/A"))

        slug = item.get("slug", "")
        link = f"https://speedhome.com/rent/{slug}" if slug else ""

        records.append({
            "Listing Title": item.get("name", "N/A"),
            "Property / Area": item.get("address", "N/A"),
            "Unit Type": unit_type,
            "Bedrooms": 1 if unit_type == "Studio" else bedroom,
            "Bathrooms": item.get("bathroom", 0) or 0,
            "Price per Month (RM)": price,
            "Price per Year (RM)": price * 12 if price else 0,
            "Size (sqft)": sqft_display,
            "Furnishing": furnish,
            "Property Type": item.get("type", "N/A"),
            "Link": link,
            "Ref": item.get("ref", ""),
            "_sqft_raw": sqft,
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values("Price per Month (RM)").reset_index(drop=True)
        df.index = df.index + 1
    return df


def compute_price_summary(df):
    if df.empty:
        return pd.DataFrame()

    summary_rows = []
    unit_order = ["Studio", "Room", "1BR", "2BR", "3BR", "4BR", "5BR", "6BR"]

    def summarize_group(group, label):
        prices = group["Price per Month (RM)"]
        sqfts = group["_sqft_raw"]

        try:
            price_mode = mode(prices)
        except (StatisticsError, ValueError):
            price_mode = prices.iloc[0]

        median_price = prices.median()
        avg_price = prices.mean()
        fair_price = round((median_price + avg_price) / 2)
        valid_sqft = sqfts[sqfts > 0]
        avg_sqft = round(valid_sqft.mean()) if not valid_sqft.empty else 0

        return {
            "Unit Type": label,
            "Units Found": len(group),
            "Avg Price (RM)": round(avg_price),
            "Median Price (RM)": round(median_price),
            "Mode Price (RM)": round(price_mode),
            "Fair Price (RM)": fair_price,
            "Min Price (RM)": int(prices.min()),
            "Max Price (RM)": int(prices.max()),
            "Avg Size (sqft)": avg_sqft,
        }

    for ut in unit_order:
        group = df[df["Unit Type"] == ut]
        if not group.empty:
            summary_rows.append(summarize_group(group, ut))

    for ut in sorted(set(df["Unit Type"].unique()) - set(unit_order)):
        group = df[df["Unit Type"] == ut]
        summary_rows.append(summarize_group(group, ut))

    return pd.DataFrame(summary_rows)


def to_excel(df_listings, df_summary, area_name):
    output = BytesIO()
    export_df = df_listings.drop(columns=["_sqft_raw"], errors="ignore")
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="Price Summary", index=False)
        export_df.to_excel(writer, sheet_name="Unit Listings", index=False)
    return output.getvalue()


# ─── UI ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏠 Property Price Intelligence</h1>
    <p>Powered by SPEEDHOME.com — Malaysian Rental Market Data</p>
</div>
""", unsafe_allow_html=True)

st.markdown("### Search Property")

input_mode = st.radio(
    "Input method:",
    ["Search by Area Name", "Enter SPEEDHOME URL"],
    horizontal=True,
    label_visibility="collapsed",
)

area_slug = None
area_display = None

col_input, col_btn = st.columns([4, 1], vertical_alignment="bottom")

if input_mode == "Search by Area Name":
    with col_input:
        search_query = st.selectbox(
            "Type an area or apartment name:",
            options=[""] + POPULAR_LOCATIONS,
            index=0,
            placeholder="e.g., Mont Kiara, Bangsar, Cyberjaya...",
        )
        if search_query:
            area_slug = location_to_slug(search_query)
            area_display = search_query
else:
    with col_input:
        url_input = st.text_input(
            "Enter SPEEDHOME URL:",
            placeholder="https://speedhome.com/rent/mont-kiara",
        )
        if url_input:
            match = re.search(r"speedhome\.com/rent/([a-z0-9-]+)", url_input.lower())
            if match:
                area_slug = match.group(1)
                area_display = area_slug.replace("-", " ").title()
            else:
                st.error("Invalid URL. Please use a SPEEDHOME rental URL like: https://speedhome.com/rent/mont-kiara")

with col_btn:
    search_clicked = st.button("Search", use_container_width=True, type="primary")

# ─── Main Content ────────────────────────────────────────────────────────────

# Persist results in session state so they survive download button reruns
if search_clicked and area_slug:
    with st.spinner(f"Fetching rental data for **{area_display}** from SPEEDHOME..."):
        raw_listings, total_count, area_label = scrape_speedhome(area_slug)

    if not raw_listings:
        st.error(f"No listings found for '{area_display}'. Try a different area name or check the URL.")
        st.session_state.pop("results", None)
    else:
        df = parse_listings(raw_listings)
        summary_df = compute_price_summary(df)
        st.session_state["results"] = {
            "df": df,
            "summary_df": summary_df,
            "area_label": area_label,
            "area_slug": area_slug,
            "total_count": total_count,
        }

elif search_clicked and not area_slug:
    st.warning("Please enter an area name or SPEEDHOME URL to search.")


def make_pinned_df(source_df, columns):
    """Create a display DataFrame with No + Listing Title as a frozen MultiIndex."""
    display = source_df[columns].copy()
    display.index = pd.MultiIndex.from_arrays(
        [range(1, len(display) + 1), display["Listing Title"]],
        names=["No", "Listing Title"],
    )
    display = display.drop(columns=["Listing Title"])
    return display


if "results" in st.session_state:
    r = st.session_state["results"]
    df = r["df"]
    summary_df = r["summary_df"]
    area_label = r["area_label"]
    area_slug_saved = r["area_slug"]
    total_count = r["total_count"]

    st.success(f"Found **{len(df)}** listings in **{area_label}** (total on SPEEDHOME: {total_count})")

    st.markdown("---")
    tab_monthly, tab_yearly, tab_daily = st.tabs(["Monthly Rental", "Yearly Rental", "Daily Rental"])

    with tab_monthly:
        st.markdown("#### Price Summary — Monthly Rental")
        if not summary_df.empty:
            st.dataframe(
                summary_df.style.format({
                    "Avg Price (RM)": "RM {:,}",
                    "Median Price (RM)": "RM {:,}",
                    "Mode Price (RM)": "RM {:,}",
                    "Fair Price (RM)": "RM {:,}",
                    "Min Price (RM)": "RM {:,}",
                    "Max Price (RM)": "RM {:,}",
                    "Avg Size (sqft)": "{:,} sqft",
                }),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("#### Overview")
        avg_p = round(df["Price per Month (RM)"].mean())
        med_p = round(df["Price per Month (RM)"].median())
        valid_sqft = df[df["_sqft_raw"] > 0]["_sqft_raw"]
        avg_sq = round(valid_sqft.mean()) if not valid_sqft.empty else 0

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
            <div class="overview-card">
                <div class="overview-icon blue">
                    <svg width="22" height="22" fill="none" stroke="white" stroke-width="2" viewBox="0 0 24 24"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 14l2 2 4-4"/></svg>
                </div>
                <div class="overview-text">
                    <p class="label">Total Listings</p>
                    <p class="value">{len(df)}</p>
                    <p class="sub">in {area_label}</p>
                </div>
            </div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="overview-card">
                <div class="overview-icon teal">
                    <svg width="22" height="22" fill="none" stroke="white" stroke-width="2" viewBox="0 0 24 24"><path d="M23 6l-9.5 9.5-5-5L1 18"/><polyline points="17 6 23 6 23 12"/></svg>
                </div>
                <div class="overview-text">
                    <p class="label">Average Rent</p>
                    <p class="value">RM {avg_p:,}</p>
                    <p class="sub">per month</p>
                </div>
            </div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="overview-card">
                <div class="overview-icon green">
                    <svg width="22" height="22" fill="none" stroke="white" stroke-width="2" viewBox="0 0 24 24"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>
                </div>
                <div class="overview-text">
                    <p class="label">Median Rent</p>
                    <p class="value">RM {med_p:,}</p>
                    <p class="sub">per month</p>
                </div>
            </div>""", unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="overview-card">
                <div class="overview-icon purple">
                    <svg width="22" height="22" fill="none" stroke="white" stroke-width="2" viewBox="0 0 24 24"><path d="M17 3a2.85 2.85 0 114 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
                </div>
                <div class="overview-text">
                    <p class="label">Avg Size</p>
                    <p class="value">{avg_sq:,} sqft</p>
                    <p class="sub">average unit size</p>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Unit Listings")

        monthly_display = make_pinned_df(df, [
            "Listing Title", "Property / Area", "Unit Type",
            "Bedrooms", "Bathrooms", "Price per Month (RM)",
            "Size (sqft)", "Furnishing", "Link"
        ])

        st.dataframe(
            monthly_display,
            use_container_width=True,
            hide_index=False,
            column_config={
                "Link": st.column_config.LinkColumn("SPEEDHOME Link", display_text="View Listing"),
                "Price per Month (RM)": st.column_config.NumberColumn(format="RM %d"),
                "Size (sqft)": st.column_config.TextColumn("Size (sqft)"),
            },
        )

    with tab_yearly:
        st.markdown("#### Price Summary — Yearly Rental (Estimated)")
        st.markdown("""
        <div class="info-box">
            <strong>Note:</strong> SPEEDHOME primarily lists monthly rental prices. Yearly prices shown here are
            estimated as <strong>Monthly Price x 12</strong>. Actual yearly rental agreements may differ —
            verify directly with the landlord via the SPEEDHOME listing.
        </div>
        """, unsafe_allow_html=True)

        if not summary_df.empty:
            yearly_summary = summary_df.copy()
            for col in ["Avg Price (RM)", "Median Price (RM)", "Mode Price (RM)", "Fair Price (RM)", "Min Price (RM)", "Max Price (RM)"]:
                yearly_summary[col] = yearly_summary[col] * 12
            yearly_summary.columns = [c.replace("Price (RM)", "Price/Year (RM)") if "Price" in c else c for c in yearly_summary.columns]

            st.dataframe(
                yearly_summary.style.format({
                    "Avg Price/Year (RM)": "RM {:,}",
                    "Median Price/Year (RM)": "RM {:,}",
                    "Mode Price/Year (RM)": "RM {:,}",
                    "Fair Price/Year (RM)": "RM {:,}",
                    "Min Price/Year (RM)": "RM {:,}",
                    "Max Price/Year (RM)": "RM {:,}",
                    "Avg Size (sqft)": "{:,} sqft",
                }),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("#### Unit Listings — Yearly View")

        yearly_display = make_pinned_df(df, [
            "Listing Title", "Property / Area", "Unit Type",
            "Bedrooms", "Bathrooms", "Price per Year (RM)",
            "Size (sqft)", "Furnishing", "Link"
        ])

        st.dataframe(
            yearly_display,
            use_container_width=True,
            hide_index=False,
            column_config={
                "Link": st.column_config.LinkColumn("SPEEDHOME Link", display_text="View Listing"),
                "Price per Year (RM)": st.column_config.NumberColumn(format="RM %d"),
                "Size (sqft)": st.column_config.TextColumn("Size (sqft)"),
            },
        )

    with tab_daily:
        st.markdown("#### Daily Rental")
        st.markdown("""
        <div class="info-box">
            <strong>Not Available:</strong> SPEEDHOME does not offer daily rental listings.
            SPEEDHOME is a platform focused on <strong>monthly and yearly</strong> tenancy agreements
            (minimum rental duration is typically 6–12 months).
        </div>
        """, unsafe_allow_html=True)

    # ─── Download Section ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Download Data")

    date_str = datetime.now().strftime("%Y%m%d")
    area_file = area_slug_saved.replace("-", "_").title().replace(" ", "_")
    filename_base = f"SPEEDHOME_{area_file}_{date_str}"

    col_dl1, col_dl2, _ = st.columns([1, 1, 2])

    with col_dl1:
        excel_data = to_excel(df, summary_df, area_label)
        st.download_button(
            label="Download Excel (.xlsx)",
            data=excel_data,
            file_name=f"{filename_base}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col_dl2:
        csv_data = df.drop(columns=["_sqft_raw"]).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name=f"{filename_base}.csv",
            mime="text/csv",
            use_container_width=True,
        )

# ─── Footer ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#94A3B8; font-size:0.8rem;">'
    'Data sourced from <a href="https://speedhome.com" target="_blank" style="color:#2563EB;">SPEEDHOME.com</a>. '
    "Prices are indicative and subject to change. This tool respects SPEEDHOME's robots.txt policy."
    "</p>",
    unsafe_allow_html=True,
)
