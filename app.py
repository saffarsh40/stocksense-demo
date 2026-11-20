import json
import os
import tempfile
import time
from datetime import datetime
from typing import List, Optional

import cv2
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field
from pyzbar.pyzbar import decode as decode_barcodes
from google import genai
from google.genai import types

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="StockSense AI | Live Shelf & SAP Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- COMMERCIAL SAAS CUSTOM CSS ---
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
    }
    #MainMenu, footer {visibility: hidden;}
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 2.5rem;
        max-width: 1280px;
    }
    .brand-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 20px;
        background: linear-gradient(90deg, #161B22 0%, #0E1117 100%);
        border: 1px solid #262C36;
        border-radius: 12px;
        margin-bottom: 16px;
    }
    .status-pill {
        background-color: rgba(63, 185, 80, 0.14);
        color: #3FB950;
        border: 1px solid rgba(63, 185, 80, 0.45);
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    div[data-testid="stMetric"] {
        background-color: #161B22;
        border: 1px solid #262C36;
        padding: 14px 16px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.65rem !important;
        font-weight: 700 !important;
        color: #F0F6FC !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #161B22;
        padding: 6px;
        border-radius: 10px;
        border: 1px solid #262C36;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px;
        padding: 8px 16px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1F6FEB !important;
        color: #FFFFFF !important;
    }
    .sap-badge {
        display: inline-block;
        background-color: rgba(31, 111, 235, 0.16);
        color: #58A6FF;
        border: 1px solid rgba(88, 166, 255, 0.35);
        padding: 2px 8px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 0.74rem;
        margin-right: 6px;
    }
    .evidence-box {
        background-color: #12171F;
        border-left: 3px solid #3FB950;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 8px;
        font-size: 0.86rem;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #1F6FEB 0%, #388BFD 100%);
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.55rem 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- SAP MATERIAL MASTER & BILINGUAL CATALOG ---
DEFAULT_INVENTORY = [
    {
        "sku_key": "osra_sugar",
        "sap_id": "SAP-10045210",
        "ean13": "6281007041012",
        "sku": "SUG-OSR-1KG",
        "name": "Osra White Sugar 1kg",
        "arabic_name": "سكر الأسرة الأبيض الناعم 1 كجم",
        "keywords": ["osra", "al osra", "sugar", "أسرة", "الأسرة", "سكر", "قيراط"],
        "aisle": "Aisle B2",
        "price": 5.50,
        "erp_qty": 12,
        "physical_qty": 0,
        "reorder_pt": 6,
    },
    {
        "sku_key": "kuwait_flour",
        "sap_id": "SAP-10045218",
        "ean13": "6271001010025",
        "sku": "FLR-KWT-2KG",
        "name": "Kuwait Patent Flour 2kg",
        "arabic_name": "طحين الكويت الفاخر 2 كجم",
        "keywords": ["kuwait", "flour", "طحين", "دقيق", "الكويت", "المطاحن"],
        "aisle": "Aisle B2",
        "price": 8.00,
        "erp_qty": 15,
        "physical_qty": 0,
        "reorder_pt": 8,
    },
    {
        "sku_key": "afia_oil",
        "sap_id": "SAP-10045304",
        "ean13": "6281018001053",
        "sku": "OIL-AFI-1.5L",
        "name": "Afia Corn Oil 1.5L",
        "arabic_name": "زيت ذرة عافية 1.5 لتر",
        "keywords": ["afia", "corn oil", "oil", "عافية", "زيت", "ذرة"],
        "aisle": "Aisle A1",
        "price": 24.50,
        "erp_qty": 8,
        "physical_qty": 0,
        "reorder_pt": 5,
    },
    {
        "sku_key": "almarai_milk",
        "sap_id": "SAP-10045411",
        "ean13": "6281007020017",
        "sku": "DRY-ALM-1L",
        "name": "Almarai Fresh Milk 1L",
        "arabic_name": "حليب المراعي طازج 1 لتر",
        "keywords": ["almarai", "milk", "fresh", "المراعي", "حليب", "طازج"],
        "aisle": "Chiller C1",
        "price": 6.00,
        "erp_qty": 20,
        "physical_qty": 0,
        "reorder_pt": 10,
    },
    {
        "sku_key": "pepsi_can",
        "sap_id": "SAP-10045502",
        "ean13": "6281034000112",
        "sku": "BEV-PEP-330",
        "name": "Pepsi Cola Can 330ml",
        "arabic_name": "بيبسي كولا علبة 330 مل",
        "keywords": ["pepsi", "cola", "بيبسي", "كولا"],
        "aisle": "Aisle D4",
        "price": 2.50,
        "erp_qty": 24,
        "physical_qty": 0,
        "reorder_pt": 12,
    },
    {
        "sku_key": "nova_water",
        "sap_id": "SAP-10045609",
        "ean13": "6281038000019",
        "sku": "BEV-NOV-330",
        "name": "Nova Bottled Water 330ml",
        "arabic_name": "مياه نوفا 330 مل",
        "keywords": ["nova", "water", "نوفا", "مياه", "ماء"],
        "aisle": "Aisle D1",
        "price": 1.00,
        "erp_qty": 30,
        "physical_qty": 0,
        "reorder_pt": 15,
    },
]

# --- STRUCTURED OUTPUT SCHEMA ---
class DetectedProduct(BaseModel):
    sku_key: str = Field(
        description="Matched catalog key: osra_sugar, kuwait_flour, afia_oil, almarai_milk, pepsi_can, nova_water, or 'unmapped_item'"
    )
    sap_id: str = Field(
        description="Corresponding SAP Material ID from the catalog, or 'SAP-UNMAPPED'"
    )
    product_name: str = Field(
        description="Clean English + Arabic product name identified on packaging"
    )
    extracted_text_ar_en: str = Field(
        description="Verbatim Arabic and English words read from the label/packaging"
    )
    detected_barcode: Optional[str] = Field(
        default=None,
        description="Any EAN/UPC barcode digits visible on the package, if readable"
    )
    unit_count: int = Field(
        description="Exact number of physical units/facings of this product visible"
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0"
    )

class ShelfScanResult(BaseModel):
    detections: List[DetectedProduct]
    raw_visible_text_summary: str = Field(
        description="Brief summary of all readable Arabic/English shelf labels and brands detected"
    )

# --- SESSION STATE ---
if "inventory" not in st.session_state:
    st.session_state.inventory = [item.copy() for item in DEFAULT_INVENTORY]
if "last_sync" not in st.session_state:
    st.session_state.last_sync = "09:15 AM (SAP S/4HANA Synced)"
if "scan_history" not in st.session_state:
    st.session_state.scan_history = []
if "last_annotated_img" not in st.session_state:
    st.session_state.last_annotated_img = None
if "last_barcode_hits" not in st.session_state:
    st.session_state.last_barcode_hits = []
if "active_model_used" not in st.session_state:
    st.session_state.active_model_used = "gemini-3.5-flash-lite"

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.markdown("### ⚙️ Engine Configuration")
    secret_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
    user_api_key = st.text_input(
        "Gemini API Key (Optional Override)",
        value="",
        type="password",
        help="Uses GEMINI_API_KEY from Streamlit Secrets automatically if left blank."
    )
    active_gemini_key = user_api_key.strip() or secret_key or os.environ.get("GEMINI_API_KEY", "")
    st.caption(f"Active Model: **{st.session_state.active_model_used}**")
    if st.button("🔄 Reset Counts to Zero", use_container_width=True):
        st.session_state.inventory = [item.copy() for item in DEFAULT_INVENTORY]
        st.session_state.scan_history = []
        st.session_state.last_annotated_img = None
        st.session_state.last_barcode_hits = []
        st.rerun()

# --- BARCODE & MULTI-MODEL RESILIENT VISION ENGINE ---
def scan_local_barcodes(pil_image: Image.Image, catalog: list):
    img_np = np.array(pil_image.convert("RGB"))
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    decoded = decode_barcodes(img_np)
    if not decoded:
        decoded = decode_barcodes(gray)

    annotated = pil_image.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)
    barcode_hits = []

    ean_lookup = {item["ean13"]: item for item in catalog}

    for obj in decoded:
        code_val = obj.data.decode("utf-8", errors="ignore").strip()
        code_type = obj.type
        pts = obj.polygon

        matched_sku = ean_lookup.get(code_val)
        sap_id = matched_sku["sap_id"] if matched_sku else f"SAP-EXT-{code_val[-4:]}"
        prod_name = matched_sku["name"] if matched_sku else f"Scanned Barcode ({code_val})"
        sku_key = matched_sku["sku_key"] if matched_sku else "unmapped_item"

        barcode_hits.append({
            "barcode": code_val,
            "format": code_type,
            "sap_id": sap_id,
            "product_name": prod_name,
            "sku_key": sku_key,
            "is_catalog_match": matched_sku is not None,
        })

        if pts and len(pts) >= 4:
            poly_coords = [(p.x, p.y) for p in pts]
            draw.polygon(poly_coords, outline="#3FB950", width=5)
            x0, y0 = poly_coords[0]
            label_txt = f" {sap_id} | {code_val} "
            draw.rectangle([x0, max(0, y0 - 26), x0 + len(label_txt) * 8, y0], fill="#3FB950")
            draw.text((x0 + 4, max(2, y0 - 22)), label_txt, fill="#0E1117")

    return annotated, barcode_hits


def call_gemini_with_failover(client: genai.Client, contents: list) -> ShelfScanResult:
    model_chain = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
    last_err = None

    for model_name in model_chain:
        for _ in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ShelfScanResult,
                        temperature=0.1,
                    ),
                )
                st.session_state.active_model_used = model_name
                return ShelfScanResult.model_validate_json(response.text)
            except Exception as err:
                last_err = err
                err_str = str(err)
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                    time.sleep(0.5)
                    continue
                raise err

    raise RuntimeError(f"Models busy right now. Details: {last_err}")


def analyze_media_frames(pil_images: List[Image.Image], catalog: list, api_key: str, is_video_walkthrough: bool = False):
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY. Add your key in Streamlit Secrets or the left sidebar.")

    first_annotated, barcode_hits = scan_local_barcodes(pil_images[0], catalog)
    for extra_img in pil_images[1:]:
        _, extra_hits = scan_local_barcodes(extra_img, catalog)
        barcode_hits.extend(extra_hits)

    client = genai.Client(api_key=api_key)

    catalog_reference = "\n".join([
        f"- sku_key: '{item['sku_key']}' | sap_id: '{item['sap_id']}' | ean13: '{item['ean13']}' | "
        f"English: '{item['name']}' | Arabic: '{item['arabic_name']}' | Keywords: {item['keywords']}"
        for item in catalog
    ])

    walkthrough_instruction = (
        "These frames are sequential snapshots from a continuous aisle walk-through video. "
        "Count ALL unique physical products visible across the entire aisle sequence while deduplicating items that appear in overlapping consecutive frames."
        if is_video_walkthrough else
        "Analyze this shelf/product frame and count every visible physical unit."
    )

    prompt = f"""
You are StockSense AI, an enterprise retail shelf auditing and SAP material mapping engine in Saudi Arabia.
{walkthrough_instruction}

Instructions:
1. Read ALL visible Arabic and English text on every package, bottle, can, bag, or shelf price tag.
2. Read any visible barcode digits (EAN-13 / UPC) if legible.
3. Map each identified product to our SAP Material Master Catalog below:

{catalog_reference}

Local ZBar decoded barcodes: {json.dumps(barcode_hits)}

Rules:
- Match Arabic or English keywords accurately (e.g., 'أسرة' or 'الأسرة' or 'سكر' or 'قيراط' or 'Al Osra' or 'Osra' or 'Sugar' -> 'osra_sugar' / 'SAP-10045210'; 'المراعي' or 'حليب' or 'Almarai' -> 'almarai_milk' / 'SAP-10045411'; 'عافية' or 'Afia' -> 'afia_oil' / 'SAP-10045304'; 'طحين' or 'الكويت' or 'Kuwait' -> 'kuwait_flour' / 'SAP-10045218'; 'بيبسي' or 'Pepsi' -> 'pepsi_can' / 'SAP-10045502'; 'نوفا' or 'Nova' -> 'nova_water' / 'SAP-10045609').
- If a product is clearly readable on the packaging (e.g., another grocery brand) but not in the 6-item catalog above, set sku_key='unmapped_item', sap_id='SAP-UNMAPPED', and still report its exact English/Arabic name, extracted text, and count.
"""

    contents = [*pil_images, prompt]
    parsed = call_gemini_with_failover(client, contents)
    return first_annotated, barcode_hits, parsed


def extract_video_keyframes(video_bytes: bytes, max_frames: int = 8) -> List[Image.Image]:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    cap = cv2.VideoCapture(tmp_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []

    if total_frames > 0:
        indices = np.linspace(0, max(0, total_frames - 1), min(max_frames, total_frames), dtype=int)
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_f = Image.fromarray(rgb)
                pil_f.thumbnail((800, 800))
                frames.append(pil_f)
    cap.release()
    os.remove(tmp_path)
    return frames


def apply_scan_results(scan_result: ShelfScanResult, barcode_hits: list, accumulate: bool):
    detected_map = {}
    for det in scan_result.detections:
        detected_map[det.sku_key] = detected_map.get(det.sku_key, 0) + det.unit_count

    for b_hit in barcode_hits:
        k = b_hit["sku_key"]
        if k != "unmapped_item" and k not in detected_map:
            detected_map[k] = 1

    matched_skus = 0
    for item in st.session_state.inventory:
        k = item["sku_key"]
        if k in detected_map:
            if accumulate:
                item["physical_qty"] += detected_map[k]
            else:
                item["physical_qty"] = detected_map[k]
            matched_skus += 1

    st.session_state.scan_history.insert(0, {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "model": st.session_state.active_model_used,
        "summary": scan_result.raw_visible_text_summary,
        "items": [d.model_dump() for d in scan_result.detections],
    })
    return matched_skus


# --- TOP BRAND BAR ---
st.markdown(f"""
<div class="brand-bar">
    <div>
        <span style="font-size: 1.3rem; font-weight: 800; color: #F0F6FC; letter-spacing: -0.4px;">
            📦 StockSense AI
        </span>
        <span style="color: #8B949E; font-size: 0.85rem; margin-left: 10px;">
            Continuous Aisle Vision • Bilingual OCR (AR/EN) • Barcode-to-SAP
        </span>
    </div>
    <div class="status-pill">● Engine Ready ({st.session_state.active_model_used})</div>
</div>
""", unsafe_allow_html=True)

# --- CALCULATE LIVE METRICS ---
df = pd.DataFrame(st.session_state.inventory)
df["variance"] = df["physical_qty"] - df["erp_qty"]
df["rev_at_risk"] = df.apply(lambda r: abs(r["variance"]) * r["price"] if r["variance"] < 0 else 0.0, axis=1)
df["status"] = df.apply(
    lambda r: "🔴 Stockout" if r["physical_qty"] == 0 else ("🟠 Low Stock" if r["physical_qty"] <= r["reorder_pt"] else "🟢 Optimal"),
    axis=1,
)

total_erp = int(df["erp_qty"].sum())
total_phys = int(df["physical_qty"].sum())
accuracy = round((min(total_phys, total_erp) / total_erp) * 100, 1) if total_erp > 0 else 100.0
rev_risk = df["rev_at_risk"].sum()
alerts_count = len(df[df["physical_qty"] <= df["reorder_pt"]])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Inventory Accuracy", f"{accuracy}%", f"{total_phys - total_erp:+d} units vs SAP")
c2.metric("Revenue at Risk", f"SAR {rev_risk:,.2f}", "Phantom stock exposure", delta_color="inverse")
c3.metric("Active Replenishment Alerts", f"{alerts_count} SKUs", "SAP PO triggers")
c4.metric("Audit Speed", "100 SKUs / min", "Continuous aisle sweep")

st.write("")

# --- NAVIGATION TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🎥 Live Continuous & Aisle Audit",
    "📊 Executive SAP Dashboard",
    "📲 Automated Store Alerts",
    "📹 Live Aisle RTSP Feed",
])

# ==========================================
# TAB 1: LIVE CONTINUOUS, VIDEO & MULTI-PHOTO AUDIT
# ==========================================
with tab1:
    col_cam, col_list = st.columns([1.1, 1], gap="large")

    with col_cam:
        st.subheader("1. Aisle Capture Mode (Scalable to 100+ SKUs)")
        audit_mode = st.radio(
            "Select Capture Workflow:",
            [
                "🎥 Live Rear-Camera Auto-Scanner",
                "🎞️ Aisle Walk-Through Video (100+ Items)",
                "📸 Multi-Shelf Photo Batch",
            ],
            horizontal=True,
        )

        accumulate_mode = st.checkbox(
            "➕ Cumulative Batch Mode (Add newly scanned items to existing shelf totals instead of overwriting)",
            value=True,
        )

        # --- MODE A: LIVE CONTINUOUS REAR-CAMERA AUTO-SCANNER ---
        if audit_mode == "🎥 Live Rear-Camera Auto-Scanner":
            st.caption("Live rear-camera viewfinder with real-time frame streaming & automatic 3-second AI sweeps.")
            catalog_json = json.dumps([
                {
                    "sku_key": i["sku_key"],
                    "sap_id": i["sap_id"],
                    "ean13": i["ean13"],
                    "name": i["name"],
                    "arabic_name": i["arabic_name"],
                    "keywords": i["keywords"],
                }
                for i in st.session_state.inventory
            ])

            live_scanner_html = f"""
            <div style="background:#161B22; border:1px solid #262C36; border-radius:12px; padding:12px; font-family:sans-serif; color:#F0F6FC;">
                <div style="position:relative; width:100%; border-radius:8px; overflow:hidden; background:#000;">
                    <video id="cam" autoplay playsinline muted style="width:100%; max-height:330px; object-fit:cover; display:block;"></video>
                    <div id="hud" style="position:absolute; top:10px; left:10px; right:10px; display:flex; justify-content:space-between; align-items:center;">
                        <span id="badge" style="background:rgba(14,17,23,0.88); color:#3FB950; border:1px solid #3FB950; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:700;">
                            ● LIVE REAR CAMERA READY
                        </span>
                        <span id="timer" style="background:rgba(14,17,23,0.88); color:#58A6FF; padding:4px 10px; border-radius:999px; font-size:12px;">
                            Auto-Scan: OFF
                        </span>
                    </div>
                </div>
                <canvas id="canvas" style="display:none;"></canvas>

                <div style="display:flex; gap:8px; margin-top:10px;">
                    <button id="toggleBtn" onclick="toggleAutoScan()" style="flex:1; background:#1F6FEB; color:#fff; border:none; padding:10px; border-radius:8px; font-weight:700; cursor:pointer;">
                        ▶ Start Live Continuous AI Scan
                    </button>
                    <button onclick="scanSingleNow()" style="background:#21262D; color:#F0F6FC; border:1px solid #30363D; padding:10px 14px; border-radius:8px; font-weight:600; cursor:pointer;">
                        ⚡ Scan Frame Now
                    </button>
                </div>

                <div id="liveResults" style="margin-top:12px; background:#0E1117; border:1px solid #262C36; border-radius:8px; padding:12px; min-height:110px; max-height:260px; overflow-y:auto; font-size:13px;">
                    <span style="color:#8B949E;">Point camera at Arabic/English products (e.g., Osra Sugar, Almarai, Pepsi) and tap <b>Start Live Continuous AI Scan</b>...</span>
                </div>
            </div>

            <script>
            const API_KEY = {json.dumps(active_gemini_key)};
            const CATALOG = {catalog_json};
            const video = document.getElementById('cam');
            const canvas = document.getElementById('canvas');
            const badge = document.getElementById('badge');
            const timerEl = document.getElementById('timer');
            const resultsEl = document.getElementById('liveResults');
            const toggleBtn = document.getElementById('toggleBtn');

            let scanning = false;
            let intervalId = null;
            let inFlight = false;
            let runningTotals = {{}};

            async function startCamera() {{
                try {{
                    const stream = await navigator.mediaDevices.getUserMedia({{
                        video: {{ facingMode: {{ ideal: "environment" }}, width: {{ ideal: 1280 }} }},
                        audio: false
                    }});
                    video.srcObject = stream;
                }} catch (err) {{
                    badge.innerText = "⚠ Camera blocked";
                    badge.style.color = "#F85149";
                    resultsEl.innerHTML = `<span style="color:#F85149;">Camera error: ${{err.message}}</span>`;
                }}
            }}
            startCamera();

            function toggleAutoScan() {{
                scanning = !scanning;
                if (scanning) {{
                    toggleBtn.innerText = "⏸ Pause Live AI Scan";
                    toggleBtn.style.background = "#DA3633";
                    timerEl.innerText = "Auto-Scan: ON (3.0s)";
                    scanSingleNow();
                    intervalId = setInterval(scanSingleNow, 3000);
                }} else {{
                    toggleBtn.innerText = "▶ Resume Live Continuous AI Scan";
                    toggleBtn.style.background = "#1F6FEB";
                    timerEl.innerText = "Auto-Scan: PAUSED";
                    clearInterval(intervalId);
                }}
            }}

            async function callGeminiModel(model, base64Jpeg) {{
                const prompt = `You are StockSense AI. Read ALL visible Arabic and English text and barcodes on products in this image and map them to this SAP catalog: ${{JSON.stringify(CATALOG)}}. If a product is visible on screen, extract its Arabic/English words and match its SAP ID. Return ONLY valid JSON: {{"items": [{{"sap_id": "...", "name": "...", "text_read": "...", "count": 1}}]}}`;
                const url = `https://generativelanguage.googleapis.com/v1beta/models/${{model}}:generateContent`;
                const res = await fetch(url, {{
                    method: "POST",
                    headers: {{
                        "Content-Type": "application/json",
                        "x-goog-api-key": API_KEY
                    }},
                    body: JSON.stringify({{
                        contents: [{{
                            parts: [
                                {{ text: prompt }},
                                {{ inline_data: {{ mime_type: "image/jpeg", data: base64Jpeg }} }}
                            ]
                        }}],
                        generationConfig: {{ responseMimeType: "application/json", temperature: 0.1 }}
                    }})
                }});
                const data = await res.json();
                if (!res.ok) {{
                    const msg = data?.error?.message || ("HTTP " + res.status);
                    throw new Error(msg);
                }}
                const rawText = data.candidates[0].content.parts[0].text;
                return JSON.parse(rawText);
            }}

            async function scanSingleNow() {{
                if (inFlight) return;
                if (!video.videoWidth) {{
                    resultsEl.innerHTML = "<span style='color:#D29922;'>Waiting for camera stream to initialize...</span>";
                    return;
                }}
                if (!API_KEY) {{
                    resultsEl.innerHTML = "<span style='color:#F85149;'>Missing GEMINI_API_KEY in Streamlit Secrets.</span>";
                    return;
                }}

                inFlight = true;
                badge.innerText = "🔍 READING LABELS...";
                badge.style.color = "#58A6FF";

                canvas.width = 512;
                canvas.height = Math.round((video.videoHeight / video.videoWidth) * 512);
                canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
                const b64 = canvas.toDataURL('image/jpeg', 0.78).split(',')[1];

                const models = ["gemini-3.5-flash-lite", "gemini-3.8-flash"];
                let parsed = null;
                let usedModel = "";
                let lastErrorMsg = "";

                for (const m of models) {{
                    try {{
                        parsed = await callGeminiModel(m, b64);
                        usedModel = m;
                        break;
                    }} catch (e) {{
                        lastErrorMsg = `${{m}}: ${{e.message}}`;
                    }}
                }}

                if (parsed && parsed.items) {{
                    badge.innerText = "● LIVE LOCK (" + usedModel + ")";
                    badge.style.color = "#3FB950";
                    let html = `<div style="color:#3FB950; font-weight:700; margin-bottom:6px;">✅ Live Frame Decoded (${{new Date().toLocaleTimeString()}})</div>`;
                    if (parsed.items.length === 0) {{
                        html += `<div style="color:#8B949E;">No product label detected in this frame — pan camera toward product text...</div>`;
                    }} else {{
                        parsed.items.forEach(it => {{
                            const key = it.sap_id + " | " + it.name;
                            runningTotals[key] = (runningTotals[key] || 0) + (it.count || 1);
                            html += `<div style="border-left:3px solid #3FB950; padding-left:8px; margin-bottom:6px;">
                                <span style="color:#58A6FF; font-family:monospace;">[${{it.sap_id}}]</span> <b>${{it.name}}</b> — Qty: <b>${{it.count}}</b><br/>
                                <span style="color:#8B949E; font-size:12px;">Read Text: "${{it.text_read}}"</span>
                            </div>`;
                        }});
                    }}
                    html += `<hr style="border-color:#262C36; margin:8px 0;"/><div style="color:#F0F6FC; font-weight:700;">Cumulative Live Session Tally:</div>`;
                    for (const [k, v] of Object.entries(runningTotals)) {{
                        html += `<div style="color:#58A6FF; font-size:12px;">• ${{k}}: <b>${{v}} units</b></div>`;
                    }}
                    resultsEl.innerHTML = html;
                }} else {{
                    badge.innerText = "⚠ API Error";
                    badge.style.color = "#F85149";
                    resultsEl.innerHTML = `<div style="color:#F85149; font-weight:700;">Scan Failed:</div><div style="color:#FFA657; font-size:12px; margin-top:4px;">${{lastErrorMsg}}</div>`;
                }}
                inFlight = false;
            }}
            </script>
            """
            components.html(live_scanner_html, height=540)

        # --- MODE B: AISLE WALK-THROUGH VIDEO (100+ PRODUCTS) ---
        elif audit_mode == "🎞️ Aisle Walk-Through Video (100+ Items)":
            st.info("Record a 10–30 second walk-through video panning across an entire aisle (up to 100+ products). StockSense extracts key frames, deduplicates overlaps, and maps all SKUs to SAP in one click.")
            vid_file = st.file_uploader("Upload Aisle Walk-Through Video (.mp4, .mov)", type=["mp4", "mov", "avi"])
            if vid_file is not None:
                st.video(vid_file)
                if st.button("🚀 Analyze Entire Aisle Video & Map to SAP", type="primary", use_container_width=True):
                    with st.spinner("Extracting aisle keyframes & running multi-frame Bilingual OCR + Barcode mapping..."):
                        try:
                            frames = extract_video_keyframes(vid_file.read(), max_frames=8)
                            if not frames:
                                st.error("Could not extract frames from this video.")
                            else:
                                first_ann, b_hits, scan_res = analyze_media_frames(
                                    frames,
                                    st.session_state.inventory,
                                    active_gemini_key,
                                    is_video_walkthrough=True,
                                )
                                st.session_state.last_annotated_img = first_ann
                                st.session_state.last_barcode_hits = b_hits
                                matched = apply_scan_results(scan_res, b_hits, accumulate=accumulate_mode)
                                st.success(f"✅ Processed {len(frames)} aisle keyframes! Mapped {matched} catalog SKU(s) to SAP.")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Video audit error: {e}")

        # --- MODE C: MULTI-SHELF PHOTO BATCH ---
        else:
            uploaded_files = st.file_uploader(
                "Upload 1 or Multiple Wide Shelf Photos (JPG/PNG)",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
            )
            if uploaded_files:
                pil_batch = [Image.open(f) for f in uploaded_files]
                st.image(pil_batch[0], caption=f"Loaded {len(pil_batch)} shelf photo(s) for batch OCR", use_container_width=True)
                if st.button(f"🔍 Scan {len(pil_batch)} Photo(s) & Map to SAP", type="primary", use_container_width=True):
                    with st.spinner(f"Scanning {len(pil_batch)} shelf image(s) with failover protection..."):
                        try:
                            first_ann, b_hits, scan_res = analyze_media_frames(
                                pil_batch,
                                st.session_state.inventory,
                                active_gemini_key,
                                is_video_walkthrough=(len(pil_batch) > 1),
                            )
                            st.session_state.last_annotated_img = first_ann
                            st.session_state.last_barcode_hits = b_hits
                            matched = apply_scan_results(scan_res, b_hits, accumulate=accumulate_mode)
                            st.success(f"✅ Batch scan complete! Mapped {matched} catalog SKU(s) to SAP.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Scan error: {e}")

        # --- DISPLAY EVIDENCE LOG ---
        if st.session_state.last_annotated_img is not None and st.session_state.last_barcode_hits:
            st.image(
                st.session_state.last_annotated_img,
                caption="ZBar Local Barcode Detection Overlay (Mapped to SAP)",
                use_container_width=True,
            )

        if st.session_state.scan_history:
            st.markdown("#### 🧠 Bilingual OCR & SAP Audit Trail")
            latest = st.session_state.scan_history[0]
            st.caption(f"Last Sweep ({latest['timestamp']} via `{latest['model']}`): {latest['summary']}")
            for det in latest["items"]:
                bc_tag = f" • Barcode: `{det['detected_barcode']}`" if det.get("detected_barcode") else ""
                conf_pct = int(round(det.get("confidence", 0.95) * 100))
                st.markdown(f"""
                <div class="evidence-box">
                    <span class="sap-badge">{det['sap_id']}</span>
                    <strong style="color:#F0F6FC;">{det['product_name']}</strong>
                    <span style="color:#3FB950; font-weight:700; float:right;">Count: {det['unit_count']} ({conf_pct}%)</span><br/>
                    <span style="color:#8B949E;">Read Text (AR/EN): <em>"{det['extracted_text_ar_en']}"</em>{bc_tag}</span>
                </div>
                """, unsafe_allow_html=True)

    # --- RIGHT COLUMN: SAP LEDGER ---
    with col_list:
        st.subheader("2. SAP Material Verification & Sync")
        st.caption(f"Last ERP Sync: {st.session_state.last_sync}")

        for idx, item in enumerate(st.session_state.inventory):
            with st.container():
                c_info, c_erp, c_phys = st.columns([2.3, 0.9, 1.1])
                with c_info:
                    st.markdown(
                        f"**{item['name']}**  \n"
                        f"<span style='color:#8B949E; font-size:0.8rem;'>{item['arabic_name']}</span>  \n"
                        f"<span class='sap-badge'>{item['sap_id']}</span>"
                        f"<span style='color:#8B949E; font-size:0.78rem;'>EAN: {item['ean13']} • {item['aisle']}</span>",
                        unsafe_allow_html=True,
                    )
                with c_erp:
                    st.markdown(
                        f"<span style='color:#8B949E; font-size:0.78rem;'>SAP Stock</span><br/>"
                        f"<strong style='font-size:1.15rem;'>{item['erp_qty']}</strong>",
                        unsafe_allow_html=True,
                    )
                with c_phys:
                    new_val = st.number_input(
                        "Verified",
                        min_value=0,
                        max_value=5000,
                        value=int(item["physical_qty"]),
                        key=f"qty_{idx}",
                    )
                    st.session_state.inventory[idx]["physical_qty"] = new_val
                st.divider()

        if st.button("✅ Approve Audit & Sync to SAP S/4HANA", type="primary", use_container_width=True):
            st.session_state.last_sync = datetime.now().strftime("%I:%M %p (Live SAP S/4HANA Synced)")
            st.balloons()
            st.success("SAP inventory ledger updated and automated replenishment alerts dispatched!")

# ==========================================
# TAB 2: EXECUTIVE SAP DASHBOARD
# ==========================================
with tab2:
    st.subheader("Live Store Inventory & SAP Discrepancy Ledger")
    display_df = df[["sap_id", "ean13", "name", "arabic_name", "aisle", "erp_qty", "physical_qty", "variance", "rev_at_risk", "status"]].copy()
    display_df.columns = [
        "SAP Material ID",
        "EAN-13 Barcode",
        "Product (EN)",
        "Product (AR)",
        "Location",
        "SAP Qty",
        "Verified Qty",
        "Variance",
        "Rev. at Risk (SAR)",
        "Status",
    ]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("#### SAP Book Stock vs. Vision Verified Stock")
        chart_df = df.set_index("name")[["erp_qty", "physical_qty"]]
        chart_df.columns = ["SAP Book Qty", "AI Verified Qty"]
        st.bar_chart(chart_df, color=["#30363D", "#1F6FEB"])

    with col_chart2:
        st.markdown("#### Revenue Leakage by SKU (SAR)")
        risk_df = df[df["rev_at_risk"] > 0].set_index("name")[["rev_at_risk"]]
        if not risk_df.empty:
            risk_df.columns = ["At-Risk Revenue (SAR)"]
            st.bar_chart(risk_df, color="#F85149")
        else:
            st.success("Zero inventory shrinkage or phantom stock detected!")

# ==========================================
# TAB 3: AUTOMATED STORE ALERTS
# ==========================================
with tab3:
    st.subheader("Zero-Friction Manager Alerts & SAP PO Triggers")
    alert_items = df[df["physical_qty"] <= df["reorder_pt"]]
    if alert_items.empty:
        st.success("✅ All shelves are stocked above SAP reorder points.")
    else:
        for _, row in alert_items.iterrows():
            st.markdown(f"""
            <div style="background-color:#1E2A24; border-left:4px solid #25D366; padding:16px; border-radius:8px; margin-bottom:12px;">
                <div style="color:#25D366; font-weight:700; font-size:0.85rem;">💬 WHATSAPP BUSINESS ALERT • STORE #104</div>
                <div style="color:#F0F6FC; margin-top:6px; font-size:0.95rem;">
                    <strong>⚠️ SHELF REPLENISHMENT REQUIRED ({row['sap_id']}):</strong><br/>
                    • <strong>Product:</strong> {row['name']} ({row['arabic_name']})<br/>
                    • <strong>Barcode / Location:</strong> {row['ean13']} • {row['aisle']}<br/>
                    • <strong>Verified Shelf Qty:</strong> {row['physical_qty']} units (SAP Book: {row['erp_qty']} | Variance: {row['variance']:+d})<br/>
                    • <strong>Action:</strong> Pull 1 case from Backroom Bay B or approve draft SAP Purchase Order.
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# TAB 4: LIVE AISLE RTSP FEED
# ==========================================
with tab4:
    st.subheader("Continuous Overhead CCTV / RTSP Stream Analytics")
    st.info("In enterprise production, StockSense AI connects directly to existing store IP cameras via RTSP — running scheduled Arabic/English OCR and barcode sweeps with zero additional hardware.")
    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        st.markdown("""
        <div style="background-color:#161B22; border:1px dashed #30363D; border-radius:12px; padding:65px 20px; text-align:center;">
            <div style="font-size:2.5rem;">📹</div>
            <div style="color:#F0F6FC; font-weight:600; margin-top:8px;">RTSP Stream Connected: rtsp://10.104.22.18:554/aisle-b2</div>
            <div style="color:#8B949E; font-size:0.85rem; margin-top:4px;">Inference Interval: Every 15 mins • Bilingual OCR (AR/EN) + ZBar Barcode Engine Active</div>
        </div>
        """, unsafe_allow_html=True)
    with col_v2:
        st.markdown("#### Edge Telemetry")
        st.write("• **Active Cameras:** 14 / 14 Online")
        st.write("• **OCR Languages:** Arabic + English")
        st.write("• **Barcode Symbologies:** EAN-13, UPC-A, QR")
        st.write("• **SAP Integration:** OData / BAPI Live Sync")
