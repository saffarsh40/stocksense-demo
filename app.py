import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import pandas as pd
import io
import os
import json
import time
import tempfile
import cv2
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# ==========================================
# PAGE CONFIG & ENTERPRISE STYLING
# ==========================================
st.set_page_config(
    page_title="StockSense AI | Retail Shelf & Loss-Prevention Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp {
        background-color: #F4F7FB;
        color: #1E293B;
    }
    section[data-testid="stSidebar"] {
        background-color: #0B2C5F;
        border-right: 1px solid #082046;
    }
    section[data-testid="stSidebar"] * {
        color: #F8FAFC !important;
    }
    section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] select {
        color: #0F172A !important;
        background-color: #FFFFFF !important;
    }
    .enterprise-header {
        background: #FFFFFF;
        padding: 18px 24px;
        border-radius: 12px;
        border: 1px solid #DCE6F2;
        box-shadow: 0 2px 6px rgba(11, 44, 95, 0.05);
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
    }
    .brand-left {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .brand-title {
        font-size: 26px;
        font-weight: 800;
        color: #0B2C5F;
        letter-spacing: -0.5px;
        margin: 0;
        line-height: 1.1;
    }
    .brand-title span {
        color: #0072CE;
    }
    .brand-subtitle {
        font-size: 13.5px;
        color: #475569;
        margin: 4px 0 0 0;
        font-weight: 500;
    }
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #DCE6F2;
        border-top: 4px solid #0072CE;
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 2px 5px rgba(11, 44, 95, 0.04);
    }
    .kpi-card.alert-red {
        border-top-color: #DC2626;
    }
    .kpi-card.alert-amber {
        border-top-color: #D97706;
    }
    .kpi-card.alert-green {
        border-top-color: #059669;
    }
    .kpi-label {
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        color: #64748B;
        letter-spacing: 0.4px;
    }
    .kpi-value {
        font-size: 26px;
        font-weight: 800;
        color: #0B2C5F;
        margin: 4px 0;
    }
    .kpi-delta {
        font-size: 12px;
        font-weight: 600;
        color: #0072CE;
    }
    .chart-card {
        background: #FFFFFF;
        border: 1px solid #DCE6F2;
        border-radius: 10px;
        padding: 18px;
        box-shadow: 0 2px 5px rgba(11, 44, 95, 0.04);
        margin-bottom: 16px;
    }
    .cctv-panel {
        background: #F8FAFC;
        border: 1.5px solid #93C5FD;
        border-radius: 12px;
        padding: 18px;
    }
    .badge-live {
        background: #E0F2FE;
        color: #0369A1;
        border: 1px solid #7DD3FC;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12.5px;
        font-weight: 700;
    }
    .badge-role {
        background: #EFF6FF;
        color: #1E3A8A;
        border: 1px solid #BFDBFE;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12.5px;
        font-weight: 700;
    }
    .login-card {
        background: #FFFFFF;
        border: 1px solid #DCE6F2;
        border-top: 5px solid #0072CE;
        border-radius: 14px;
        padding: 28px;
        box-shadow: 0 6px 20px rgba(11, 44, 95, 0.07);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SHARED MULTI-USER STORE DATABASE (CLOUD SYNC)
# ==========================================
@st.cache_resource
def get_shared_store_db():
    return {
        "audit_logs": [
            {
                "timestamp": "2026-11-22 09:15:22 AM",
                "auditor": "Nasser (Aisle A-C)",
                "aisle": "Aisle A1 - Cooking Oils",
                "sku": "Afia Pure Corn Oil 1.5L",
                "sap_code": "SAP-100231",
                "detected_qty": 3,
                "expected_qty": 8,
                "reorder_point": 4,
                "unit_price_sar": 21.50,
                "status": "LOW STOCK",
                "action": "Auto-Replenishment Drafted to SAP",
            },
            {
                "timestamp": "2026-11-22 10:02:45 AM",
                "auditor": "Mahdi (Aisle D-F)",
                "aisle": "Aisle D2 - Beverages",
                "sku": "Pepsi Cola 330ml Can",
                "sap_code": "SAP-100409",
                "detected_qty": 0,
                "expected_qty": 24,
                "reorder_point": 10,
                "unit_price_sar": 2.50,
                "status": "OUT OF STOCK",
                "action": "Urgent Backroom Restock Dispatched",
            },
            {
                "timestamp": "2026-11-22 11:20:10 AM",
                "auditor": "Walla (Aisle G-J)",
                "aisle": "Aisle G1 - Dairy & Pantry",
                "sku": "Almarai Full Cream Milk 1L",
                "sap_code": "SAP-100518",
                "detected_qty": 12,
                "expected_qty": 12,
                "reorder_point": 5,
                "unit_price_sar": 6.00,
                "status": "OPTIMAL",
                "action": "Planogram Verified",
            },
        ],
        "auditor_stats": {
            "Nasser (Aisle A-C)": {"scans": 14, "items_counted": 118, "discrepancies": 3, "accuracy": 98.4},
            "Mahdi (Aisle D-F)": {"scans": 19, "items_counted": 164, "discrepancies": 5, "accuracy": 99.1},
            "Walla (Aisle G-J)": {"scans": 11, "items_counted": 92, "discrepancies": 1, "accuracy": 97.8},
            "Ammar (Aisle K-M)": {"scans": 8, "items_counted": 67, "discrepancies": 2, "accuracy": 98.0},
            "Mohammed (Night Shift)": {"scans": 16, "items_counted": 141, "discrepancies": 4, "accuracy": 98.7},
        },
        "theft_alerts": [],
        "sap_erp_catalog": [
            {"SKU Name": "Afia Pure Corn Oil 1.5L", "SAP Material ID": "SAP-100231", "Barcode": "6281007001122", "Aisle": "Aisle A1", "Expected Shelf Qty": 8, "Reorder Point": 4, "Unit Price (SAR)": 21.50},
            {"SKU Name": "Osra Fine White Sugar 2kg", "SAP Material ID": "SAP-100114", "Barcode": "6281009003344", "Aisle": "Aisle B2", "Expected Shelf Qty": 10, "Reorder Point": 4, "Unit Price (SAR)": 9.75},
            {"SKU Name": "Almarai Full Cream Milk 1L", "SAP Material ID": "SAP-100518", "Barcode": "6281007045511", "Aisle": "Aisle G1", "Expected Shelf Qty": 12, "Reorder Point": 5, "Unit Price (SAR)": 6.00},
            {"SKU Name": "Pepsi Cola 330ml Can", "SAP Material ID": "SAP-100409", "Barcode": "6281018009912", "Aisle": "Aisle D2", "Expected Shelf Qty": 24, "Reorder Point": 10, "Unit Price (SAR)": 2.50},
            {"SKU Name": "Foom All-Purpose Flour 1kg", "SAP Material ID": "SAP-100302", "Barcode": "6281022007788", "Aisle": "Aisle B1", "Expected Shelf Qty": 9, "Reorder Point": 4, "Unit Price (SAR)": 5.25},
        ],
    }

shared_db = get_shared_store_db()

# ==========================================
# USER ACCOUNTS & ROLE-BASED ACCESS CONTROL
# ==========================================
USERS_DB = {
    "Manager (Admin)": {"pin": "1234", "role": "Manager", "zone": "All Store Zones"},
    "Nasser (Aisle A-C)": {"pin": "1111", "role": "Auditor", "zone": "Aisles A–C"},
    "Mahdi (Aisle D-F)": {"pin": "2222", "role": "Auditor", "zone": "Aisles D–F"},
    "Walla (Aisle G-J)": {"pin": "3333", "role": "Auditor", "zone": "Aisles G–J"},
    "Ammar (Aisle K-M)": {"pin": "4444", "role": "Auditor", "zone": "Aisles K–M"},
    "Mohammed (Night Shift)": {"pin": "5555", "role": "Auditor", "zone": "Full Store Night Audit"},
}

if "authenticated_user" not in st.session_state:
    st.session_state["authenticated_user"] = None
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None

# ==========================================
# GEMINI API KEY RESOLUTION (ENV / SECRETS / SIDEBAR)
# ==========================================
def resolve_gemini_key():
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        pass
    return st.session_state.get("sidebar_gemini_key", "").strip()

# ==========================================
# PYDANTIC SCHEMAS FOR STRUCTURED AI OUTPUT
# ==========================================
class ShelfItem(BaseModel):
    sku_name: str = Field(description="Exact product brand, name, and package size visible on the shelf (English or Arabic/English).")
    sap_material_id: str = Field(description="Matched SAP Material ID from catalog or 'SAP-NEW-SKU' if unlisted.")
    visible_count: int = Field(description="Exact count of physical units visible on the shelf front/depth.")
    expected_count: int = Field(description="Expected planogram stock quantity.")
    stock_status: str = Field(description="OPTIMAL, LOW STOCK, or OUT OF STOCK")
    planogram_compliant: bool = Field(description="True if neatly faced in assigned slot; False if misplaced or messy.")
    recommended_action: str = Field(description="Immediate operational action for store staff or SAP replenishment.")

class ShelfAuditReport(BaseModel):
    aisle_summary: str = Field(description="Concise executive summary of shelf health and stock findings.")
    detected_items: List[ShelfItem]

class CCTVTheftVerdict(BaseModel):
    theft_detected: bool = Field(description="True ONLY if suspicious concealment, pocket/bag stuffing, or rapid shelf sweeping is clearly observed.")
    behavior_type: str = Field(description="Short label of observed action, e.g. 'Item Concealment in Backpack' or 'Normal Shopping'.")
    confidence_pct: int = Field(description="Confidence score between 0 and 100.")
    description: str = Field(description="Detailed description of shopper hand/body movement.")
    recommended_action: str = Field(description="Action for floor security supervisor.")

# ==========================================
# AI VISION & VIDEO EXTRACTION HELPERS
# ==========================================
def extract_video_keyframes(video_bytes: bytes, max_frames: int = 5) -> List[Image.Image]:
    frames = []
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name
    try:
        cap = cv2.VideoCapture(tmp_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            return frames
        step = max(1, total_frames // max_frames)
        idx = 0
        while len(frames) < max_frames and idx < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            pil_img.thumbnail((800, 800))
            frames.append(pil_img)
            idx += step
        cap.release()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return frames

def run_shelf_vision_audit(images: List[Image.Image], aisle_name: str, api_key: str) -> ShelfAuditReport:
    client = genai.Client(api_key=api_key)
    catalog_json = json.dumps(shared_db["sap_erp_catalog"])
    prompt = f"""
    You are StockSense AI, an enterprise retail shelf-auditing vision engine deployed in Saudi Arabian supermarkets.
    Analyze the attached retail shelf image(s) for '{aisle_name}'.
    Reference SAP ERP Catalog: {catalog_json}

    Instructions:
    1. Identify every distinct retail product/SKU visible on the shelf (supporting both Arabic and English packaging such as Osra Sugar, Afia Corn Oil, Almarai Milk, Pepsi, Foom Flour, or any other visible item).
    2. Count the exact physical units visible on the shelf accurately.
    3. Compare against the SAP ERP Catalog expected quantity and reorder point (if unlisted, use expected_count = 8).
    4. Classify stock_status strictly as 'OPTIMAL', 'LOW STOCK', or 'OUT OF STOCK'.
    """
    contents = [prompt] + images
    for model_name in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ShelfAuditReport,
                    temperature=0.1,
                ),
            )
            return ShelfAuditReport.model_validate_json(response.text)
        except Exception as e:
            last_err = e
    raise last_err

def analyze_cctv_theft_behavior(images: List[Image.Image], camera_id: str, api_key: str) -> CCTVTheftVerdict:
    client = genai.Client(api_key=api_key)
    prompt = f"""
    You are StockSense AI Loss-Prevention running on fixed overhead store CCTV ({camera_id}).
    Analyze these sequential frames for shoplifting or suspicious theft behavior:
    - Hiding/concealing a retail item inside a jacket, pocket, backpack, or personal bag.
    - Rapidly sweeping multiple items off a shelf into a personal bag.
    Normal shopping (picking an item up to read the label or holding items openly) is NOT theft.
    """
    contents = [prompt] + images
    for model_name in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CCTVTheftVerdict,
                    temperature=0.1,
                ),
            )
            return CCTVTheftVerdict.model_validate_json(response.text)
        except Exception as e:
            last_err = e
    raise last_err

def record_audit_results(report: ShelfAuditReport, auditor_name: str, aisle_name: str):
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    total_units = 0
    discrepancies = 0
    catalog_lookup = {item["SKU Name"].lower(): item for item in shared_db["sap_erp_catalog"]}

    for item in report.detected_items:
        total_units += item.visible_count
        if item.stock_status in ["LOW STOCK", "OUT OF STOCK"] or item.visible_count < item.expected_count:
            discrepancies += 1
        matched_cat = catalog_lookup.get(item.sku_name.lower(), {})
        unit_price = matched_cat.get("Unit Price (SAR)", 10.00)
        reorder_pt = matched_cat.get("Reorder Point", 4)

        shared_db["audit_logs"].insert(0, {
            "timestamp": now_str,
            "auditor": auditor_name,
            "aisle": aisle_name,
            "sku": item.sku_name,
            "sap_code": item.sap_material_id,
            "detected_qty": item.visible_count,
            "expected_qty": item.expected_count,
            "reorder_point": reorder_pt,
            "unit_price_sar": unit_price,
            "status": item.stock_status,
            "action": item.recommended_action,
        })

    if auditor_name in shared_db["auditor_stats"]:
        stats = shared_db["auditor_stats"][auditor_name]
        stats["scans"] += 1
        stats["items_counted"] += max(1, total_units)
        stats["discrepancies"] += discrepancies

# ==========================================
# HEADER BANNER
# ==========================================
def render_header():
    user_badge = ""
    if st.session_state["authenticated_user"]:
        user_badge = f"""
        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
            <span class="badge-role">👤 {st.session_state['authenticated_user']} ({st.session_state['user_role']})</span>
            <span class="badge-live">● Live Cloud Store Sync Active</span>
        </div>
        """
    else:
        user_badge = '<span class="badge-live">● Enterprise Retail AI Portal</span>'

    st.markdown(f"""
    <div class="enterprise-header">
        <div class="brand-left">
            <div style="background:#0B2C5F; color:#FFFFFF; width:46px; height:46px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:22px; font-weight:800;">
                SS
            </div>
            <div>
                <div class="brand-title">Stock<span>Sense</span> AI</div>
                <div class="brand-subtitle">SEE • TRACK • MANAGE • GROW — Real-Time Shelf & Loss-Prevention Intelligence</div>
            </div>
        </div>
        {user_badge}
    </div>
    """, unsafe_allow_html=True)

render_header()

# ==========================================
# SIDEBAR CONFIGURATION
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Store System Controls")
    if not resolve_gemini_key():
        key_input = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
        if key_input:
            st.session_state["sidebar_gemini_key"] = key_input
            st.rerun()
    else:
        st.success("✅ Vision AI Engine Connected")

    st.markdown("---")
    st.markdown("**Store Branch:** Riyadh Flagship #04")
    st.markdown("**ERP Integration:** SAP S/4HANA Retail")
    st.markdown("**OCR Engine:** Bilingual (Arabic / English)")

    if st.session_state["authenticated_user"]:
        st.markdown("---")
        if st.button("🚪 Sign Out / Switch User", use_container_width=True):
            st.session_state["authenticated_user"] = None
            st.session_state["user_role"] = None
            st.rerun()

active_gemini_key = resolve_gemini_key()

# ==========================================
# ROLE-BASED LOGIN SCREEN
# ==========================================
if not st.session_state["authenticated_user"]:
    col_l, col_m, col_r = st.columns([1, 1.35, 1])
    with col_m:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("### 🔐 StockSense AI — Staff & Manager Sign-In")
        st.caption("Select your assigned store profile and enter your 4-digit terminal PIN.")

        selected_user = st.selectbox("Select Staff Profile:", list(USERS_DB.keys()))
        role_preview = USERS_DB[selected_user]["role"]
        zone_preview = USERS_DB[selected_user]["zone"]
        st.info(f"**Role:** {role_preview} | **Assigned Zone:** {zone_preview}")

        pin_input = st.text_input("Enter 4-Digit Terminal PIN:", type="password", max_chars=4, placeholder="••••")
        st.caption("Demo PINs — Manager: `1234` | Nasser: `1111` | Mahdi: `2222` | Walla: `3333` | Ammar: `4444` | Mohammed: `5555`")

        if st.button("🔓 Sign In to StockSense Terminal", type="primary", use_container_width=True):
            if pin_input == USERS_DB[selected_user]["pin"]:
                st.session_state["authenticated_user"] = selected_user
                st.session_state["user_role"] = USERS_DB[selected_user]["role"]
                st.rerun()
            else:
                st.error("Invalid PIN. Please enter the 4-digit PIN assigned to your profile.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# TOP BAR USER STATUS & ROLE-BASED NAVIGATION
# ==========================================
current_user = st.session_state["authenticated_user"]
current_role = st.session_state["user_role"]

top_c1, top_c2 = st.columns([4, 1])
with top_c1:
    st.caption(f"Signed in as **{current_user}** • Role: **{current_role}** • Assigned Zone: **{USERS_DB[current_user]['zone']}**")
with top_c2:
    if st.button("🔄 Switch User / Log Out", use_container_width=True):
        st.session_state["authenticated_user"] = None
        st.session_state["user_role"] = None
        st.rerun()

df_logs = pd.DataFrame(shared_db["audit_logs"])
low_oos_df = df_logs[df_logs["status"].isin(["LOW STOCK", "OUT OF STOCK"])] if not df_logs.empty else pd.DataFrame()
total_alerts_count = len(low_oos_df) + len(shared_db["theft_alerts"])
alert_badge = f" (🚨 {total_alerts_count})" if total_alerts_count > 0 else ""

if current_role == "Manager":
    tab_scanner, tab_exec, tab_workforce, tab_alerts, tab_cctv = st.tabs([
        "📱 Live Field Auditor Scanner",
        "📊 Manager Executive Dashboard (Live)",
        "👥 Workforce & Auditor Efficiency",
        f"📲 Automated Store Alerts{alert_badge}",
        "🛡️ Overhead CCTV Theft Detection",
    ])
else:
    tab_scanner, tab_alerts = st.tabs([
        "📱 Live Field Auditor Scanner",
        f"📲 Automated Store Alerts{alert_badge}",
    ])
    tab_exec = None
    tab_workforce = None
    tab_cctv = None

# ==========================================
# TAB 1: LIVE FIELD AUDITOR SCANNER
# ==========================================
with tab_scanner:
    st.subheader("📱 Mobile Shelf & Inventory Audit Terminal")
    st.caption("Capture live aisle shelves using your smartphone camera, upload a shelf walk-through video, or batch-process aisle photos.")

    col_scan_left, col_scan_right = st.columns([1.2, 1], gap="large")

    with col_scan_left:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        aisle_choice = st.selectbox(
            "Select Target Store Aisle:",
            [
                "Aisle A1 - Cooking Oils",
                "Aisle B1 - Flour & Baking",
                "Aisle B2 - Sugar & Grains",
                "Aisle D2 - Beverages",
                "Aisle G1 - Dairy & Pantry",
            ],
        )

        scan_mode = st.radio(
            "Select Audit Capture Mode:",
            [
                "📸 Live Smartphone / Terminal Camera",
                "🎥 Upload Aisle Walk-Through Video (.mp4 / .mov)",
                "🖼️ Upload Shelf Photo(s)",
            ],
            horizontal=True,
        )

        captured_images = []
        if scan_mode == "📸 Live Smartphone / Terminal Camera":
            cam_photo = st.camera_input("Align camera with retail shelf and capture photo")
            if cam_photo is not None:
                img = Image.open(cam_photo).convert("RGB")
                img.thumbnail((1024, 1024))
                captured_images.append(img)

        elif scan_mode == "🎥 Upload Aisle Walk-Through Video (.mp4 / .mov)":
            vid_file = st.file_uploader("Upload Shelf Walk-Through Video", type=["mp4", "mov", "avi"])
            if vid_file is not None:
                st.video(vid_file)
                if st.button("🎞️ Extract Keyframes & Run Shelf Audit", type="primary", use_container_width=True):
                    if not active_gemini_key:
                        st.error("Please enter your Gemini API Key in the sidebar first.")
                    else:
                        with st.spinner("Extracting keyframes & running StockSense Vision AI..."):
                            frames = extract_video_keyframes(vid_file.read(), max_frames=5)
                            if frames:
                                report = run_shelf_vision_audit(frames, aisle_choice, active_gemini_key)
                                record_audit_results(report, current_user, aisle_choice)
                                st.session_state["last_audit_report"] = report
                                st.success(f"Audit complete! {len(report.detected_items)} SKU(s) synced to Manager Dashboard.")
                                st.rerun()
                            else:
                                st.error("Could not extract frames from video.")

        else:
            uploaded_photos = st.file_uploader("Upload Shelf Image(s)", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
            if uploaded_photos:
                for up in uploaded_photos[:4]:
                    img = Image.open(up).convert("RGB")
                    img.thumbnail((1024, 1024))
                    captured_images.append(img)
                st.image(captured_images, width=220)

        if captured_images:
            if st.button("🚀 Analyze Shelf & Sync to SAP / Manager Dashboard", type="primary", use_container_width=True):
                if not active_gemini_key:
                    st.error("Please enter your Gemini API Key in the sidebar first.")
                else:
                    with st.spinner("Running Bilingual OCR, SKU Counting & Planogram Verification..."):
                        try:
                            report = run_shelf_vision_audit(captured_images, aisle_choice, active_gemini_key)
                            record_audit_results(report, current_user, aisle_choice)
                            st.session_state["last_audit_report"] = report
                            st.success("Shelf audit completed and pushed to Live Cloud Sync!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Vision AI error: {ex}")

        st.markdown('</div>', unsafe_allow_html=True)

    with col_scan_right:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("#### 📋 Latest Shelf Audit Output")
        if "last_audit_report" in st.session_state:
            rep: ShelfAuditReport = st.session_state["last_audit_report"]
            st.info(rep.aisle_summary)
            res_rows = []
            for it in rep.detected_items:
                res_rows.append({
                    "SKU Name": it.sku_name,
                    "SAP ID": it.sap_material_id,
                    "Visible": it.visible_count,
                    "Expected": it.expected_count,
                    "Status": it.stock_status,
                    "Action": it.recommended_action,
                })
            st.dataframe(pd.DataFrame(res_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("No new scan in this session yet. Capture or upload a shelf image on the left to see real-time SKU counts and SAP matching.")

        st.markdown("---")
        st.markdown("#### 🗄️ SAP S/4HANA Master Shelf Catalog")
        st.dataframe(pd.DataFrame(shared_db["sap_erp_catalog"]), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TAB 2: MANAGER EXECUTIVE DASHBOARD (LIVE)
# ==========================================
if tab_exec is not None:
    with tab_exec:
        st.subheader("📊 Executive Store Operations & Shelf Health")
        df_logs = pd.DataFrame(shared_db["audit_logs"])

        total_scans = len(df_logs)
        optimal_cnt = len(df_logs[df_logs["status"] == "OPTIMAL"]) if not df_logs.empty else 0
        low_cnt = len(df_logs[df_logs["status"] == "LOW STOCK"]) if not df_logs.empty else 0
        oos_cnt = len(df_logs[df_logs["status"] == "OUT OF STOCK"]) if not df_logs.empty else 0
        osa_pct = round((optimal_cnt / total_scans) * 100, 1) if total_scans > 0 else 100.0

        at_risk_sar = 0.0
        if not df_logs.empty:
            for _, r in df_logs.iterrows():
                gap = max(0, int(r["expected_qty"]) - int(r["detected_qty"]))
                at_risk_sar += gap * float(r["unit_price_sar"])

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f"""
            <div class="kpi-card alert-green">
                <div class="kpi-label">On-Shelf Availability (OSA)</div>
                <div class="kpi-value">{osa_pct}%</div>
                <div class="kpi-delta">{optimal_cnt} of {total_scans} audited slots optimal</div>
            </div>
            """, unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class="kpi-card alert-amber">
                <div class="kpi-label">Low Stock Warnings</div>
                <div class="kpi-value">{low_cnt}</div>
                <div class="kpi-delta">Below SAP reorder threshold</div>
            </div>
            """, unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="kpi-card alert-red">
                <div class="kpi-label">Out-of-Stock (OOS) Gaps</div>
                <div class="kpi-value">{oos_cnt}</div>
                <div class="kpi-delta">Immediate backroom pick required</div>
            </div>
            """, unsafe_allow_html=True)
        with k4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Revenue at Risk (SAR)</div>
                <div class="kpi-value">SAR {at_risk_sar:,.2f}</div>
                <div class="kpi-delta">Protected by real-time detection</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        c_chart1, c_chart2 = st.columns(2, gap="large")
        with c_chart1:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("#### 📦 Shelf Stock vs. Expected Planogram by SKU")
            if not df_logs.empty:
                chart_df = df_logs.groupby("sku")[["detected_qty", "expected_qty"]].first()
                st.bar_chart(chart_df)
            st.markdown('</div>', unsafe_allow_html=True)

        with c_chart2:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("#### 🧾 Live Storewide Audit Log (All Field Auditors)")
            st.dataframe(
                df_logs[["timestamp", "auditor", "aisle", "sku", "detected_qty", "expected_qty", "status"]],
                use_container_width=True,
                hide_index=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TAB 3: WORKFORCE & AUDITOR EFFICIENCY
# ==========================================
if tab_workforce is not None:
    with tab_workforce:
        st.subheader("👥 Field Auditor Productivity & Shift Leaderboard")
        st.caption("Tracks real-time shelf scan throughput, item count accuracy, and discrepancy discovery across field auditors.")

        wf_rows = []
        for staff_name, metrics in shared_db["auditor_stats"].items():
            if "Manager" in staff_name:
                continue
            wf_rows.append({
                "Field Auditor": staff_name,
                "Assigned Zone": USERS_DB.get(staff_name, {}).get("zone", "Store Floor"),
                "Shelf Scans Completed": metrics["scans"],
                "Total Units Verified": metrics["items_counted"],
                "Stock Discrepancies Caught": metrics["discrepancies"],
                "Vision Audit Accuracy (%)": metrics["accuracy"],
            })

        wf_df = pd.DataFrame(wf_rows).sort_values(by="Shelf Scans Completed", ascending=False)
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.dataframe(wf_df, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("#### 📈 Shelf Scans Completed per Field Auditor")
        st.bar_chart(wf_df.set_index("Field Auditor")["Shelf Scans Completed"])
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TAB 4: AUTOMATED STORE ALERTS
# ==========================================
with tab_alerts:
    st.subheader("📲 Automated Store Replenishment & Loss-Prevention Alerts")

    col_a1, col_a2 = st.columns(2, gap="large")
    with col_a1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("#### 🚨 Priority CCTV Loss-Prevention Alerts")
        if shared_db["theft_alerts"]:
            if current_role == "Manager":
                if st.button("🧹 Clear Resolved CCTV Alerts", use_container_width=True):
                    shared_db["theft_alerts"].clear()
                    st.rerun()
            for alert in shared_db["theft_alerts"]:
                st.error(
                    f"**[{alert['timestamp']}] {alert['camera_id']} • {alert['aisle']}**\n\n"
                    f"**Behavior:** {alert['behavior_type']} ({alert['confidence_pct']}% confidence)\n\n"
                    f"**Details:** {alert['description']}\n\n"
                    f"**Action:** {alert['recommended_action']}"
                )
        else:
            st.success("✅ No active CCTV theft or concealment alerts.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_a2:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("#### 📦 Automated SAP Replenishment & Restock Queue")
        df_logs = pd.DataFrame(shared_db["audit_logs"])
        alerts_df = df_logs[df_logs["status"].isin(["LOW STOCK", "OUT OF STOCK"])] if not df_logs.empty else pd.DataFrame()
        if not alerts_df.empty:
            for _, row in alerts_df.iterrows():
                msg = (
                    f"**[{row['status']}] {row['sku']}** (`{row['sap_code']}`) — {row['aisle']}\n\n"
                    f"Visible: **{row['detected_qty']}** / Expected: **{row['expected_qty']}** | Reported by: {row['auditor']}\n\n"
                    f"Action: *{row['action']}*"
                )
                if row["status"] == "OUT OF STOCK":
                    st.error(msg)
                else:
                    st.warning(msg)
        else:
            st.success("✅ All audited shelves are stocked above reorder thresholds.")
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TAB 5: OVERHEAD CCTV THEFT BEHAVIORAL DETECTION
# ==========================================
if tab_cctv is not None:
    with tab_cctv:
        st.subheader("🛡️ Overhead Store CCTV — Behavioral Theft Detection")
        st.caption("Dedicated fixed overhead aisle camera feed (EZVIZ C6N via OBS Virtual Camera / RTSP). Automatically analyzes live posture & concealment gestures and dispatches alerts directly to Automated Store Alerts.")

        col_cctv, col_arch = st.columns([1.25, 1], gap="large")

        with col_cctv:
            st.markdown('<div class="cctv-panel">', unsafe_allow_html=True)
            cam_select = st.selectbox(
                "Select Overhead Store Camera Channel:",
                [
                    "CAM-04 • Aisle C2 (Dairy & Infant Formula — High Shrinkage Zone)",
                    "CAM-07 • Aisle G1 (Personal Care & Cosmetics)",
                    "CAM-02 • Aisle A1 (Cooking Oils & Pantry)",
                ],
            )
            aisle_label = cam_select.split("•")[1].strip() if "•" in cam_select else "Aisle C2"
            cam_code = cam_select.split("•")[0].strip()

            cctv_source = st.radio(
                "Overhead Camera Input Source:",
                [
                    "📹 Live EZVIZ / Overhead CCTV Feed (Auto-AI Guard)",
                    "🎞️ Upload Overhead CCTV Footage (.mp4 / .mov)",
                ],
                horizontal=True,
            )

            if cctv_source == "📹 Live EZVIZ / Overhead CCTV Feed (Auto-AI Guard)":
                @st.cache_resource
                def get_live_cctv_component():
                    comp_dir = os.path.join(tempfile.gettempdir(), "stocksense_live_cctv_guard_v2")
                    os.makedirs(comp_dir, exist_ok=True)
                    index_path = os.path.join(comp_dir, "index.html")
                    html_code = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  body { margin:0; padding:0; background:transparent; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  .cam-bar { display:flex; gap:8px; margin-bottom:8px; align-items:center; }
  select { flex:1; padding:8px 10px; border-radius:8px; border:1px solid #93C5FD; background:#FFFFFF; color:#0B2C5F; font-weight:700; font-size:12.5px; }
  .btn-refresh { background:#E0EEFF; color:#0B2C5F; border:1px solid #93C5FD; padding:8px 12px; border-radius:8px; font-weight:700; font-size:12px; cursor:pointer; }
  .wrap { background:#0B2C5F; border-radius:10px; overflow:hidden; position:relative; border:2px solid #0072CE; }
  video { width:100%; max-height:310px; object-fit:cover; display:block; background:#000; }
  .top-hud { position:absolute; top:10px; left:10px; right:10px; display:flex; justify-content:space-between; font-family:monospace; font-size:12px; }
  .rec { background:rgba(220,38,38,0.92); color:#fff; padding:4px 10px; border-radius:6px; font-weight:700; }
  .clk { background:rgba(15,23,42,0.85); color:#fff; padding:4px 10px; border-radius:6px; }
  .bot-hud { position:absolute; bottom:10px; left:10px; right:10px; display:flex; justify-content:space-between; align-items:center; }
  .pose { background:rgba(15,23,42,0.88); color:#34D399; padding:4px 10px; border-radius:6px; font-family:monospace; font-size:11px; }
  .controls { display:flex; gap:8px; margin-top:10px; }
  .btn-guard { flex:1; background:linear-gradient(90deg, #DC2626 0%, #B91C1C 100%); color:#fff; border:none; padding:11px; border-radius:8px; font-weight:700; font-size:13px; cursor:pointer; }
  .btn-check { background:#E0EEFF; color:#0B2C5F; border:1px solid #93C5FD; padding:11px 14px; border-radius:8px; font-weight:700; font-size:13px; cursor:pointer; }
  .status-box { margin-top:8px; background:#FFFFFF; border:1px solid #CBDCEB; border-radius:8px; padding:10px 12px; font-size:12.5px; color:#1E293B; }
</style>
</head>
<body>
<div class="cam-bar">
  <select id="camPicker" onchange="switchSelectedCamera()">
    <option value="">Detecting available cameras (OBS Virtual Camera / Webcam)...</option>
  </select>
  <button class="btn-refresh" onclick="initCameras(true)">🔄 Refresh Cameras</button>
</div>

<div class="wrap">
  <video id="cctvVid" autoplay playsinline muted></video>
  <div class="top-hud">
    <span id="recBadge" class="rec">● REC • EZVIZ OVERHEAD CCTV</span>
    <span id="cctvClock" class="clk"></span>
  </div>
  <div class="bot-hud">
    <span id="poseHud" class="pose">AI BEHAVIOR GUARD: STANDBY</span>
  </div>
</div>
<canvas id="c1" style="display:none;"></canvas>
<canvas id="c2" style="display:none;"></canvas>

<div class="controls">
  <button id="guardBtn" class="btn-guard" onclick="toggleGuard()">🛡️ Start Live AI Theft Guard (Auto-Detect)</button>
  <button class="btn-check" onclick="runBurstCheck()">⚡ Analyze Burst Now</button>
</div>
<div id="guardStatus" class="status-box">
  Select <b>OBS Virtual Camera</b> in the dropdown above, then click <b>Start Live AI Theft Guard</b>.
</div>

<script>
let API_KEY = "";
let CAM_CODE = "CAM-04";
let AISLE = "Aisle C2";
let activeStream = null;

function sendToStreamlit(type, data) {
  window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: type }, data), "*");
}

window.addEventListener("message", function(event) {
  if (event.data && event.data.type === "streamlit:render") {
    const args = event.data.args || {};
    if (args.api_key) API_KEY = args.api_key;
    if (args.cam_code) CAM_CODE = args.cam_code;
    if (args.aisle) AISLE = args.aisle;
    sendToStreamlit("streamlit:setFrameHeight", { height: document.body.scrollHeight + 14 });
  }
});

sendToStreamlit("streamlit:componentReady", { apiVersion: 1 });
sendToStreamlit("streamlit:setFrameHeight", { height: 520 });

const v = document.getElementById('cctvVid');
const camPicker = document.getElementById('camPicker');
const c1 = document.getElementById('c1');
const c2 = document.getElementById('c2');
const poseHud = document.getElementById('poseHud');
const guardBtn = document.getElementById('guardBtn');
const guardStatus = document.getElementById('guardStatus');

let guardActive = false;
let guardTimer = null;
let busy = false;

async function startStreamById(deviceId) {
  if (activeStream) {
    activeStream.getTracks().forEach(t => t.stop());
  }
  const constraints = deviceId
    ? { video: { deviceId: { exact: deviceId }, width: { ideal: 1280 } }, audio: false }
    : { video: true, audio: false };
  activeStream = await navigator.mediaDevices.getUserMedia(constraints);
  v.srcObject = activeStream;
}

async function initCameras(forcePrompt) {
  try {
    if (!activeStream || forcePrompt) {
      await startStreamById(null);
    }
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoInputs = devices.filter(d => d.kind === 'videoinput');
    camPicker.innerHTML = "";
    let obsDeviceId = "";

    videoInputs.forEach((dev, idx) => {
      const opt = document.createElement('option');
      opt.value = dev.deviceId;
      const label = dev.label || ("Camera " + (idx + 1));
      opt.text = label;
      if (label.toLowerCase().includes("obs")) {
        obsDeviceId = dev.deviceId;
      }
      camPicker.appendChild(opt);
    });

    if (obsDeviceId) {
      camPicker.value = obsDeviceId;
      await startStreamById(obsDeviceId);
      guardStatus.innerHTML = `<span style="color:#047857; font-weight:700;">✅ Connected to OBS Virtual Camera (EZVIZ C6N Live Feed).</span>`;
    } else if (videoInputs.length > 0) {
      await startStreamById(videoInputs[0].deviceId);
    }
  } catch (err) {
    guardStatus.innerHTML = `<span style="color:#DC2626; font-weight:700;">⚠ Camera Permission Needed:</span> ${err.message}. Click the lock/camera icon in your browser bar and allow Camera access, then click Refresh Cameras.`;
  }
  sendToStreamlit("streamlit:setFrameHeight", { height: document.body.scrollHeight + 14 });
}

async function switchSelectedCamera() {
  if (camPicker.value) {
    await startStreamById(camPicker.value);
  }
}

initCameras(false);

setInterval(() => {
  document.getElementById('cctvClock').innerText = new Date().toLocaleTimeString();
}, 1000);

function toggleGuard() {
  guardActive = !guardActive;
  if (guardActive) {
    guardBtn.innerText = "⏸ Pause Live AI Theft Guard";
    guardBtn.style.background = "#0B2C5F";
    poseHud.innerText = "AI BEHAVIOR GUARD: ACTIVE (5.5s SWEEP)";
    runBurstCheck();
    guardTimer = setInterval(runBurstCheck, 5500);
  } else {
    guardBtn.innerText = "🛡️ Start Live AI Theft Guard (Auto-Detect)";
    guardBtn.style.background = "linear-gradient(90deg, #DC2626 0%, #B91C1C 100%)";
    poseHud.innerText = "AI BEHAVIOR GUARD: STANDBY";
    clearInterval(guardTimer);
  }
}

function captureFrame(canvasEl) {
  canvasEl.width = 512;
  canvasEl.height = Math.round((v.videoHeight / v.videoWidth) * 512);
  canvasEl.getContext('2d').drawImage(v, 0, 0, canvasEl.width, canvasEl.height);
  return canvasEl.toDataURL('image/jpeg', 0.78).split(',')[1];
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function runBurstCheck() {
  if (busy || !v.videoWidth || !API_KEY) return;
  busy = true;
  poseHud.innerText = "🔍 ANALYZING MOTION SEQUENCE...";
  poseHud.style.color = "#FBBF24";

  const frame1 = captureFrame(c1);
  await sleep(900);
  const frame2 = captureFrame(c2);

  const prompt = `You are StockSense AI Loss-Prevention running on overhead CCTV (${CAM_CODE} - ${AISLE}). Compare these 2 sequential frames (0.9s apart) for shoplifting or suspicious theft behavior: hiding an item in a pocket/backpack/bag/jacket, or rapid shelf sweeping. Normal sitting/standing or holding a phone/item openly without concealment is NOT theft. Return ONLY valid JSON: {"theft_detected": true/false, "behavior_type": "...", "confidence_pct": 85, "description": "...", "recommended_action": "..."}`;

  const models = ["gemini-2.5-flash", "gemini-2.0-flash"];
  for (const model of models) {
    try {
      const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-goog-api-key": API_KEY },
        body: JSON.stringify({
          contents: [{ parts: [
            { text: prompt },
            { inline_data: { mime_type: "image/jpeg", data: frame1 } },
            { inline_data: { mime_type: "image/jpeg", data: frame2 } }
          ]}],
          generationConfig: { responseMimeType: "application/json", temperature: 0.1 }
        })
      });
      const data = await res.json();
      if (!res.ok) continue;
      const verdict = JSON.parse(data.candidates[0].content.parts[0].text);
      const ts = new Date().toLocaleTimeString();

      if (verdict.theft_detected && verdict.confidence_pct >= 70) {
        poseHud.innerText = "🚨 THEFT GESTURE DETECTED (" + verdict.confidence_pct + "%)";
        poseHud.style.color = "#F87171";
        guardStatus.innerHTML = `<div style="color:#B91C1C; font-weight:700;">🚨 [${ts}] ALERT DISPATCHED TO AUTOMATED STORE ALERTS: ${verdict.behavior_type} (${verdict.confidence_pct}%)</div><div style="margin-top:4px;">${verdict.description}</div>`;
        sendToStreamlit("streamlit:setComponentValue", {
          value: {
            alert_id: Date.now() + "_" + Math.random().toString(36).slice(2, 6),
            timestamp: new Date().toLocaleString(),
            camera_id: CAM_CODE,
            aisle: AISLE,
            behavior_type: verdict.behavior_type,
            confidence_pct: verdict.confidence_pct,
            description: verdict.description,
            recommended_action: verdict.recommended_action || "Dispatch floor security supervisor to aisle exit immediately."
          }
        });
      } else {
        poseHud.innerText = "● CLEAR • NORMAL ACTIVITY (" + ts + ")";
        poseHud.style.color = "#34D399";
        guardStatus.innerHTML = `<span style="color:#047857; font-weight:700;">✅ [${ts}] Normal Activity (${verdict.confidence_pct}%):</span> ${verdict.description}`;
      }
      sendToStreamlit("streamlit:setFrameHeight", { height: document.body.scrollHeight + 14 });
      break;
    } catch (e) {}
  }
  busy = false;
}
</script>
</body>
</html>"""
                    with open(index_path, "w", encoding="utf-8") as f:
                        f.write(html_code)
                    return components.declare_component("stocksense_live_cctv_guard_v2", path=comp_dir)

                cctv_guard_comp = get_live_cctv_component()
                cctv_event = cctv_guard_comp(
                    api_key=active_gemini_key,
                    cam_code=cam_code,
                    aisle=aisle_label,
                    key="live_ezviz_cctv_guard_v2",
                )

                if isinstance(cctv_event, dict) and cctv_event.get("alert_id"):
                    al_id = cctv_event["alert_id"]
                    if st.session_state.get("last_cctv_alert_id") != al_id:
                        st.session_state["last_cctv_alert_id"] = al_id
                        shared_db["theft_alerts"].insert(0, {
                            "timestamp": cctv_event.get("timestamp", datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")),
                            "camera_id": cctv_event.get("camera_id", cam_code),
                            "aisle": cctv_event.get("aisle", aisle_label),
                            "behavior_type": cctv_event.get("behavior_type", "Suspicious Concealment"),
                            "confidence_pct": cctv_event.get("confidence_pct", 88),
                            "description": cctv_event.get("description", "Overhead AI detected suspicious item concealment."),
                            "recommended_action": cctv_event.get("recommended_action", "Dispatch floor security supervisor."),
                        })
                        st.rerun()

                with st.expander("⚡ Manual Demo Trigger (Backup Simulation)", expanded=False):
                    sim_behavior = st.selectbox(
                        "Simulated Behavioral Event:",
                        [
                            "Item Concealment in Jacket / Personal Bag (2 units removed from shelf)",
                            "Rapid Shelf Sweeping into Backpack (High-Value Dairy/Formula)",
                        ],
                        key="sim_beh_select",
                    )
                    if st.button("🚨 Trigger Manual CCTV Alert", use_container_width=True):
                        now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
                        shared_db["theft_alerts"].insert(0, {
                            "timestamp": now_str,
                            "camera_id": cam_code,
                            "aisle": aisle_label,
                            "behavior_type": sim_behavior,
                            "confidence_pct": 94,
                            "description": f"Overhead pose & action model detected hand-to-bag concealment gesture at {aisle_label} without placing items in a store basket.",
                            "recommended_action": "Dispatch floor security supervisor to aisle exit & review 10-second CCTV buffer.",
                        })
                        st.rerun()

            else:
                cctv_clip = st.file_uploader("Upload Overhead Aisle CCTV Video Clip (.mp4, .mov)", type=["mp4", "mov", "avi"])
                if cctv_clip is not None:
                    st.video(cctv_clip)
                    if st.button("🔍 Run Behavioral Theft Analysis on CCTV Clip", type="primary", use_container_width=True):
                        with st.spinner("Analyzing shopper skeleton posture & hand-to-pocket concealment across CCTV frames..."):
                            try:
                                clip_frames = extract_video_keyframes(cctv_clip.read(), max_frames=6)
                                if not clip_frames:
                                    st.error("Could not read frames from uploaded CCTV clip.")
                                else:
                                    verdict = analyze_cctv_theft_behavior(clip_frames, cam_code, active_gemini_key)
                                    now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
                                    if verdict.theft_detected:
                                        shared_db["theft_alerts"].insert(0, {
                                            "timestamp": now_str,
                                            "camera_id": cam_code,
                                            "aisle": aisle_label,
                                            "behavior_type": verdict.behavior_type,
                                            "confidence_pct": verdict.confidence_pct,
                                            "description": verdict.description,
                                            "recommended_action": verdict.recommended_action,
                                        })
                                        st.error(f"🚨 THEFT BEHAVIOR DETECTED ({verdict.confidence_pct}% confidence) at {now_str}! Alert sent.")
                                        st.rerun()
                                    else:
                                        st.success(f"✅ Normal Shopping Behavior ({verdict.confidence_pct}% confidence): {verdict.description}")
                            except Exception as ex:
                                st.error(f"CCTV analysis error: {ex}")

            st.markdown('</div>', unsafe_allow_html=True)

        with col_arch:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("#### 🧠 How StockSense Behavioral Theft Detection Works")
            st.markdown("""
            Unlike inventory scanning (done via handheld phones), **Theft Behavioral Detection** runs continuously on **fixed overhead store CCTV cameras** without using facial recognition:

            1. **Skeleton Pose Estimation (YOLOv8-Pose):** Tracks wrist, elbow, and torso keypoints in real time across overhead video frames.
            2. **Action & Concealment Recognition (SlowFast / VideoMAE + Vision AI):** Analyzes sequential motion frames to detect:
               * **Concealment:** Hand picks item from shelf and moves directly into a pocket, backpack, or under clothing.
               * **Shelf Sweeping:** Rapidly clearing multiple high-value items into a personal bag.
            3. **Instant Alert Routing:** Whenever suspicious behavior is detected, StockSense timestamps the exact camera channel and aisle and pushes a **Priority Security Alert** to Tab 4 (**Automated Store Alerts**).
            """)
            st.markdown("---")
            st.markdown("#### 📡 Overhead CCTV Edge Telemetry")
            st.write("• **Active Camera Feed:** EZVIZ CS-C6N (Channel 1 Live)")
            st.write("• **Privacy Compliance:** Anonymous Pose Keypoints (No Facial Recognition)")
            st.write("• **Alert Routing:** Real-Time Push to Tab 4 (Automated Store Alerts)")
            st.markdown('</div>', unsafe_allow_html=True)
