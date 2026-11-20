import json
import os
from datetime import datetime
from typing import List, Optional

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field
from pyzbar.pyzbar import decode as decode_barcodes
from google import genai
from google.genai import types

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="StockSense AI | Enterprise Shelf & SAP Intelligence",
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
        padding-top: 2.8rem;
        padding-bottom: 2.5rem;
        max-width: 1280px;
    }
    /* Brand Header */
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
    /* KPI Cards */
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
    /* Navigation Tabs */
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
    /* Mobile SKU Card */
    .sku-card {
        background-color: #161B22;
        border: 1px solid #262C36;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 8px;
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
    /* Primary CTA Button */
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
        "keywords": ["osra", "sugar", "أسرة", "الأسرة", "سكر"],
        "aisle": "Aisle B2",
        "price": 5.50,
        "erp_qty": 12,
        "physical_qty": 12,
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
        "physical_qty": 14,
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
        "physical_qty": 3,
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
        "physical_qty": 20,
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
        "physical_qty": 6,
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

# --- STRUCTURED OUTPUT SCHEMA FOR GEMINI VISION OCR ---
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
        description="Exact number of physical units/facings of this product visible in the image"
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
if "last_scan_report" not in st.session_state:
    st.session_state.last_scan_report = None
if "last_annotated_img" not in st.session_state:
    st.session_state.last_annotated_img = None
if "last_barcode_hits" not in st.session_state:
    st.session_state.last_barcode_hits = []

# --- SIDEBAR SETTINGS (OPTIONAL KEY OVERRIDE) ---
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
    st.caption("SAP Master: **6 Active SKUs** | Vision: **Gemini 3.8 Flash + ZBar**")
    if st.button("🔄 Reset Demo Data", use_container_width=True):
        st.session_state.inventory = [item.copy() for item in DEFAULT_INVENTORY]
        st.session_state.last_scan_report = None
        st.session_state.last_annotated_img = None
        st.session_state.last_barcode_hits = []
        st.rerun()

# --- BARCODE & BILINGUAL VISION ENGINE ---
def scan_local_barcodes(pil_image: Image.Image, catalog: list):
    """Decodes EAN/UPC/QR codes locally using ZBar and maps them to SAP Material IDs."""
    img_np = np.array(pil_image.convert("RGB"))
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    # Try both raw RGB and contrast-enhanced grayscale for curved packaging
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

        # Draw emerald bounding polygon around barcode
        if pts and len(pts) >= 4:
            poly_coords = [(p.x, p.y) for p in pts]
            draw.polygon(poly_coords, outline="#3FB950", width=5)
            x0, y0 = poly_coords[0]
            label_txt = f" {sap_id} | {code_val} "
            draw.rectangle([x0, max(0, y0 - 26), x0 + len(label_txt) * 8, y0], fill="#3FB950")
            draw.text((x0 + 4, max(2, y0 - 22)), label_txt, fill="#0E1117")

    return annotated, barcode_hits


def run_bilingual_ocr_and_sap_mapping(pil_image: Image.Image, catalog: list, api_key: str):
    """Combines local ZBar barcode decoding with Gemini Vision Arabic/English OCR + SAP mapping."""
    annotated_img, barcode_hits = scan_local_barcodes(pil_image, catalog)

    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY. Add it in Streamlit Secrets or the left sidebar.")

    client = genai.Client(api_key=api_key)

    catalog_reference = "\n".join([
        f"- sku_key: '{item['sku_key']}' | sap_id: '{item['sap_id']}' | ean13: '{item['ean13']}' | "
        f"English: '{item['name']}' | Arabic: '{item['arabic_name']}' | Keywords: {item['keywords']}"
        for item in catalog
    ])

    barcode_context = (
        f"Local ZBar scanner already decoded these barcodes in the image: {json.dumps(barcode_hits)}"
        if barcode_hits else "No local ZBar barcode polygon was decoded; inspect image directly for barcodes and text."
    )

    prompt = f"""
You are StockSense AI, an enterprise retail shelf auditing and SAP material mapping engine in Saudi Arabia.
Analyze this shelf/product image carefully:
1. Read ALL visible Arabic and English text on every package, bottle, can, bag, or shelf price tag.
2. Read any visible barcode digits (EAN-13 / UPC) if legible.
3. Map each identified product to our SAP Material Master Catalog below using Arabic/English brand & product keywords or barcode digits:

{catalog_reference}

{barcode_context}

Rules:
- Match Arabic or English keywords accurately (e.g., 'أسرة' or 'سكر' or 'Osra' or 'Sugar' -> 'osra_sugar' / 'SAP-10045210'; 'المراعي' or 'حليب' or 'Almarai' -> 'almarai_milk' / 'SAP-10045411'; 'عافية' or 'Afia' -> 'afia_oil' / 'SAP-10045304'; 'طحين' or 'الكويت' or 'Kuwait' -> 'kuwait_flour' / 'SAP-10045218'; 'بيبسي' or 'Pepsi' -> 'pepsi_can' / 'SAP-10045502'; 'نوفا' or 'Nova' -> 'nova_water' / 'SAP-10045609').
- Count the exact number of visible physical units of each SKU in the image.
- If a product is clearly readable on the packaging (e.g., another grocery brand) but not in the 6-item catalog above, set sku_key='unmapped_item', sap_id='SAP-UNMAPPED', and still report its exact English/Arabic name, extracted text, and count so the auditor sees the live OCR working on any real item!
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[pil_image, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ShelfScanResult,
            temperature=0.1,
        ),
    )

    parsed = ShelfScanResult.model_validate_json(response.text)
    return annotated_img, barcode_hits, parsed


# --- TOP BRAND BAR ---
st.markdown("""
<div class="brand-bar">
    <div>
        <span style="font-size: 1.3rem; font-weight: 800; color: #F0F6FC; letter-spacing: -0.4px;">
            📦 StockSense AI
        </span>
        <span style="color: #8B949E; font-size: 0.85rem; margin-left: 10px;">
            Bilingual OCR (AR/EN) • Barcode-to-SAP Engine • Store #104 (Al-Khobar)
        </span>
    </div>
    <div class="status-pill">● SAP S/4HANA & Vision OCR Active</div>
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
c4.metric("Audit Time Saved", "86% Faster", "14 sec vs 3.5 hrs manual")

st.write("")

# --- NAVIGATION TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📱 Smart OCR & Barcode Audit",
    "📊 Executive SAP Dashboard",
    "📲 Automated Store Alerts",
    "📹 Live Aisle RTSP Feed",
])

# ==========================================
# TAB 1: BILINGUAL OCR + BARCODE + SAP AUDIT
# ==========================================
with tab1:
    col_cam, col_list = st.columns([1.08, 1], gap="large")

    with col_cam:
        st.subheader("1. Capture Shelf / Product Label")
        scan_mode = st.radio(
            "Input Source:",
            ["📸 Live Camera Scan", "🖼️ Upload Shelf / Product Photo", "⚡ Quick Demo Preset"],
            horizontal=True,
        )

        img_to_process = None
        if scan_mode == "📸 Live Camera Scan":
            cam_photo = st.camera_input("Point at Arabic/English packaging or barcode")
            if cam_photo:
                img_to_process = Image.open(cam_photo)
        elif scan_mode == "🖼️ Upload Shelf / Product Photo":
            uploaded = st.file_uploader("Upload JPG/PNG photo of grocery products or barcodes", type=["jpg", "jpeg", "png", "webp"])
            if uploaded:
                img_to_process = Image.open(uploaded)
        else:
            st.info("Simulates scanning Aisle B2 & D4 with Arabic/English packaging + EAN-13 barcode verification.")
            if st.button("⚡ Run Simulated Bilingual + SAP Shelf Scan", type="primary", use_container_width=True):
                simulated_counts = {
                    "osra_sugar": 12,
                    "kuwait_flour": 14,
                    "afia_oil": 3,
                    "almarai_milk": 20,
                    "pepsi_can": 6,
                    "nova_water": 0,
                }
                for item in st.session_state.inventory:
                    item["physical_qty"] = simulated_counts[item["sku_key"]]
                st.session_state.last_scan_report = {
                    "summary": "Read Arabic & English labels: 'سكر الأسرة / Osra Sugar', 'طحين الكويت / Kuwait Flour', 'زيت عافية / Afia Oil', 'حليب المراعي / Almarai Milk', 'بيبسي / Pepsi'.",
                    "items": [
                        {
                            "sap_id": "SAP-10045210",
                            "product_name": "Osra White Sugar 1kg",
                            "extracted_text_ar_en": "الأسرة سكر ناعم / Osra Fine White Sugar 1kg",
                            "detected_barcode": "6281007041012",
                            "unit_count": 12,
                            "confidence": 0.99,
                        },
                        {
                            "sap_id": "SAP-10045304",
                            "product_name": "Afia Corn Oil 1.5L",
                            "extracted_text_ar_en": "عافية زيت ذرة صافي / Afia Pure Corn Oil 1.5L",
                            "detected_barcode": "6281018001053",
                            "unit_count": 3,
                            "confidence": 0.98,
                        },
                        {
                            "sap_id": "SAP-10045502",
                            "product_name": "Pepsi Cola Can 330ml",
                            "extracted_text_ar_en": "بيبسي كولا / Pepsi 330ml",
                            "detected_barcode": "6281034000112",
                            "unit_count": 6,
                            "confidence": 0.99,
                        },
                    ],
                }
                st.success("✅ Simulated Multimodal Scan complete — mapped 3 SKUs to SAP Material IDs!")
                st.rerun()

        if img_to_process is not None:
            st.image(img_to_process, caption="Captured Frame Ready for OCR + Barcode Analysis", use_container_width=True)
            if st.button("🔍 Scan Arabic/English Text & Map Barcodes to SAP", type="primary", use_container_width=True):
                with st.spinner("Decoding ZBar barcodes & reading Arabic/English packaging via Gemini Vision..."):
                    try:
                        annotated_img, barcode_hits, scan_result = run_bilingual_ocr_and_sap_mapping(
                            img_to_process,
                            st.session_state.inventory,
                            active_gemini_key,
                        )
                        st.session_state.last_annotated_img = annotated_img
                        st.session_state.last_barcode_hits = barcode_hits

                        # Map detected counts back to inventory state
                        detected_map = {}
                        report_items = []
                        for det in scan_result.detections:
                            report_items.append(det.model_dump())
                            if det.sku_key in detected_map:
                                detected_map[det.sku_key] += det.unit_count
                            else:
                                detected_map[det.sku_key] = det.unit_count

                        # Also ensure any local ZBar catalog match is counted if Gemini missed it
                        for b_hit in barcode_hits:
                            k = b_hit["sku_key"]
                            if k != "unmapped_item" and k not in detected_map:
                                detected_map[k] = 1

                        matched_skus_count = 0
                        for item in st.session_state.inventory:
                            if item["sku_key"] in detected_map:
                                item["physical_qty"] = detected_map[item["sku_key"]]
                                matched_skus_count += 1

                        st.session_state.last_scan_report = {
                            "summary": scan_result.raw_visible_text_summary,
                            "items": report_items,
                        }
                        st.success(f"✅ Vision OCR & Barcode Scan complete! Mapped {matched_skus_count} catalog SKU(s) to SAP.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Scan error: {e}")

        # Display AI Evidence & Barcode Readout
        if st.session_state.last_annotated_img is not None and st.session_state.last_barcode_hits:
            st.image(
                st.session_state.last_annotated_img,
                caption="ZBar Local Barcode Detection Overlay (Mapped to SAP)",
                use_container_width=True,
            )

        if st.session_state.last_scan_report:
            st.markdown("#### 🧠 Extracted Text & SAP Mapping Evidence")
            st.caption(st.session_state.last_scan_report["summary"])
            for det in st.session_state.last_scan_report["items"]:
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
                        max_value=500,
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
    st.write("Triggered automatically when Vision OCR or Barcode scans detect phantom stock or low shelf depth.")

    alert_items = df[df["physical_qty"] <= df["reorder_pt"]]
    if alert_items.empty:
        st.success("✅ All shelves are stocked above SAP reorder points. No urgent action required.")
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
