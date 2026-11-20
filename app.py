import cv2
import requests
import base64
import numpy as np
import streamlit as st
import time
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="StockSense AI | Enterprise Shelf & Inventory Intelligence",
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
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        max-width: 1280px;
    }
    /* Brand Header */
    .brand-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 18px;
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
        letter-spacing: 0.3px;
    }
    /* KPI Cards */
    .metric-card {
        background: linear-gradient(145deg, #181D26 0%, #12161E 100%);
        border: 1px solid #262C36;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
        margin-bottom: 10px;
    }
    .metric-title {
        color: #8B949E;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .metric-value {
        color: #F0F6FC;
        font-size: 1.9rem;
        font-weight: 700;
        margin-top: 6px;
        line-height: 1.1;
    }
    .metric-delta {
        font-size: 0.8rem;
        margin-top: 6px;
        font-weight: 500;
    }
    /* Alert Cards */
    .alert-card-red {
        background: rgba(248, 81, 73, 0.09);
        border: 1px solid rgba(248, 81, 73, 0.35);
        border-left: 4px solid #F85149;
        padding: 14px 16px;
        border-radius: 10px;
        margin-bottom: 8px;
        color: #F0F6FC;
    }
    .alert-card-yellow {
        background: rgba(210, 153, 34, 0.09);
        border: 1px solid rgba(210, 153, 34, 0.35);
        border-left: 4px solid #D29922;
        padding: 14px 16px;
        border-radius: 10px;
        margin-bottom: 8px;
        color: #F0F6FC;
    }
    /* WhatsApp Chat Bubble Preview */
    .wa-container {
        background-color: #0B141A;
        border: 1px solid #262C36;
        border-radius: 12px;
        padding: 16px;
    }
    .wa-header {
        color: #8696A0;
        font-size: 0.78rem;
        margin-bottom: 10px;
        border-bottom: 1px solid #1F2C33;
        padding-bottom: 6px;
    }
    .wa-bubble {
        background-color: #005C4B;
        color: #E9EDEF;
        padding: 12px 14px;
        border-radius: 10px 10px 2px 10px;
        font-size: 0.88rem;
        line-height: 1.45;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    }
    .wa-meta {
        text-align: right;
        font-size: 0.72rem;
        color: #8696A0;
        margin-top: 6px;
    }
    /* Touch-friendly Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        min-height: 44px;
        transition: all 0.15s ease;
    }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZE SHARED MASTER INVENTORY DATABASE ---
DEFAULT_INVENTORY = [
    {"roboflow_class": "osra_sugar", "SKU": "SUG-OSR-1KG", "Product": "Osra White Sugar 1kg", "Category": "Dry Goods", "Aisle": "Aisle B2", "ERP_Expected": 12, "Visual_Count": 12, "ROP": 5, "Unit_Price_SAR": 5.50, "Last_Audit": "09:15 AM"},
    {"roboflow_class": "kuwait_flour", "SKU": "FLR-KWT-2KG", "Product": "Kuwait Patent Flour 2kg", "Category": "Baking", "Aisle": "Aisle B2", "ERP_Expected": 15, "Visual_Count": 14, "ROP": 6, "Unit_Price_SAR": 7.25, "Last_Audit": "09:15 AM"},
    {"roboflow_class": "afia_oil", "SKU": "OIL-AFI-1.5L", "Product": "Afia Corn Oil 1.5L", "Category": "Cooking Oils", "Aisle": "Aisle A1", "ERP_Expected": 8, "Visual_Count": 3, "ROP": 5, "Unit_Price_SAR": 18.00, "Last_Audit": "09:30 AM"},
    {"roboflow_class": "almarai_milk", "SKU": "DRY-ALM-1L", "Product": "Almarai Fresh Milk 1L", "Category": "Dairy", "Aisle": "Chiller C1", "ERP_Expected": 20, "Visual_Count": 20, "ROP": 8, "Unit_Price_SAR": 6.00, "Last_Audit": "10:00 AM"},
    {"roboflow_class": "pepsi_can", "SKU": "BEV-PEP-330", "Product": "Pepsi Cola Can 330ml", "Category": "Beverages", "Aisle": "Aisle D4", "ERP_Expected": 24, "Visual_Count": 6, "ROP": 10, "Unit_Price_SAR": 2.50, "Last_Audit": "10:05 AM"},
    {"roboflow_class": "nova_water", "SKU": "BEV-NOV-330", "Product": "Nova Bottled Water 330ml", "Category": "Beverages", "Aisle": "Aisle D1", "ERP_Expected": 30, "Visual_Count": 0, "ROP": 12, "Unit_Price_SAR": 1.00, "Last_Audit": "10:10 AM"},
]

if "inventory_df" not in st.session_state:
    st.session_state["inventory_df"] = pd.DataFrame(DEFAULT_INVENTORY)

if "audit_logs" not in st.session_state:
    st.session_state["audit_logs"] = [
        {"Timestamp": "10:10:14", "Location": "Aisle D1", "SKU": "BEV-NOV-330", "Product": "Nova Bottled Water 330ml", "ERP": 30, "Verified": 0, "Variance": -30, "Auditor": "Mobile App"},
        {"Timestamp": "10:05:02", "Location": "Aisle D4", "SKU": "BEV-PEP-330", "Product": "Pepsi Cola Can 330ml", "ERP": 24, "Verified": 6, "Variance": -18, "Auditor": "Mobile App"},
    ]

if "dispatched_orders" not in st.session_state:
    st.session_state["dispatched_orders"] = []

if "erp_last_sync" not in st.session_state:
    st.session_state["erp_last_sync"] = "Synced today at 10:12 AM (SAP / Odoo Connector)"

if "pending_scan_counts" not in st.session_state:
    st.session_state["pending_scan_counts"] = {}

if "pending_scan_image" not in st.session_state:
    st.session_state["pending_scan_image"] = None

if "scan_completed" not in st.session_state:
    st.session_state["scan_completed"] = False

# --- HELPER FUNCTIONS ---
def detect_objects_static(image_bgr, api_key, project_id, version, conf_thresh, nms_thresh):
    annotated = image_bgr.copy()
    h_orig, w_orig = annotated.shape[:2]

    resized = cv2.resize(annotated, (640, int(640 * h_orig / w_orig)))
    _, buffer = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    img_str = base64.b64encode(buffer.tobytes()).decode("utf-8")

    url = f"https://detect.roboflow.com/{project_id}/{version}?api_key={api_key}&confidence={int(conf_thresh * 100)}"
    response = requests.post(
        url,
        data=img_str,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=8
    )
    response.raise_for_status()
    raw_preds = response.json().get("predictions", [])

    scale_x = w_orig / resized.shape[1]
    scale_y = h_orig / resized.shape[0]

    boxes, confidences, labels = [], [], []
    for p in raw_preds:
        w = int(p["width"] * scale_x)
        h = int(p["height"] * scale_y)
        x = int(p["x"] * scale_x - w / 2)
        y = int(p["y"] * scale_y - h / 2)
        boxes.append([x, y, w, h])
        confidences.append(float(p["confidence"]))
        labels.append(p["class"])

    indices = cv2.dnn.NMSBoxes(boxes, confidences, score_threshold=conf_thresh, nms_threshold=nms_thresh)
    counts = {}

    if len(indices) > 0:
        for i in indices.flatten():
            x, y, w, h = boxes[i]
            cls_name = labels[i]
            conf_score = confidences[i]
            counts[cls_name] = counts.get(cls_name, 0) + 1

            cv2.rectangle(annotated, (x, y), (x + w, y + h), (63, 185, 80), 3)
            label_text = f"{cls_name} ({conf_score:.0%})"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (x, max(0, y - th - 10)), (x + tw + 8, y), (63, 185, 80), -1)
            cv2.putText(annotated, label_text, (x + 4, max(15, y - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (14, 17, 23), 2)

    return annotated, counts

def get_status_label(row):
    if row["Visual_Count"] == 0:
        return "🔴 Out of Stock"
    elif row["Visual_Count"] <= row["ROP"]:
        return "🟡 Low Stock"
    return "🟢 Optimal"

# --- SIDEBAR (ADMIN & ENGINE SETTINGS) ---
with st.sidebar:
    st.markdown("### :material/tune: Admin & Vision Engine")
    st.caption("Model credentials & inference tuning")
    with st.expander("Roboflow & Camera Config", expanded=False):
        API_KEY = st.text_input("Roboflow API Key", value="3MXgfSLZxnv1Qog1GH3v", type="password")
        PROJECT_ID = st.text_input("Project ID", value="stocksense")
        VERSION = st.text_input("Model Version", value="1")
        STREAM_URL = st.text_input("Local RTSP Stream URL", value="http://192.168.8.4:8080/video")
    conf_threshold = st.slider("Confidence Threshold", 0.10, 1.00, 0.50, 0.05)
    nms_threshold = st.slider("NMS Overlap Threshold", 0.05, 0.50, 0.25, 0.05)

# --- TOP SAAS HEADER ---
st.markdown("""
    <div class="brand-bar">
        <div>
            <div style="font-size:1.35rem; font-weight:700; color:#F0F6FC; letter-spacing:-0.3px;">
                📦 StockSense AI
            </div>
            <div style="font-size:0.82rem; color:#8B949E;">
                Computer Vision Shelf Auditing & Automated Replenishment Platform
            </div>
        </div>
        <div>
            <span class="status-pill">● LIVE CLOUD PROTOTYPE</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- ROLE-BASED NAVIGATION TABS ---
tab_mobile, tab_exec, tab_alerts, tab_rtsp = st.tabs([
    ":material/qr_code_scanner: Mobile Shelf Audit",
    ":material/analytics: Executive Dashboard",
    ":material/notifications_active: Alerts & Reordering",
    ":material/videocam: Live Gate Stream"
])

# ==============================================================================
# TAB 1: MOBILE AUDITOR VIEW (PROGRESSIVE DISCLOSURE & THUMB-FRIENDLY)
# ==============================================================================
with tab_mobile:
    m_col1, m_col2 = st.columns([1.05, 1], gap="large")

    with m_col1:
        with st.container(border=True):
            st.markdown("#### :material/photo_camera: Step 1 — Capture Shelf")
            selected_aisle = st.selectbox(
                "Target Zone / Aisle",
                ["All Zones", "Aisle B2", "Aisle A1", "Aisle D4", "Aisle D1", "Chiller C1"]
            )

            capture_mode = st.segmented_control(
                "Input Method",
                options=["Camera Snap", "Upload Photo", "Instant Demo Scan"],
                default="Camera Snap",
                selection_mode="single"
            )

            captured_bgr = None

            if capture_mode == "Camera Snap":
                cam_photo = st.camera_input("Align shelf items in frame and capture")
                if cam_photo is not None:
                    file_bytes = np.asarray(bytearray(cam_photo.read()), dtype=np.uint8)
                    captured_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            elif capture_mode == "Upload Photo":
                uploaded_file = st.file_uploader("Select shelf image (JPG / PNG)", type=["jpg", "jpeg", "png"])
                if uploaded_file is not None:
                    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                    captured_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            else:
                st.info("Simulates a multi-SKU AI shelf scan without requiring physical items.")
                if st.button(":material/bolt: Run Simulated Shelf Scan", use_container_width=True, type="primary"):
                    st.session_state["pending_scan_counts"] = {
                        "osra_sugar": 11,
                        "kuwait_flour": 14,
                        "afia_oil": 2,
                        "pepsi_can": 5
                    }
                    st.session_state["pending_scan_image"] = None
                    st.session_state["scan_completed"] = True
                    st.toast("Simulated AI scan complete!", icon="✅")

            if captured_bgr is not None:
                if st.button(":material/search: Run AI Shelf Detection", use_container_width=True, type="primary"):
                    with st.spinner("Analyzing shelf image..."):
                        try:
                            annotated_img, detected_counts = detect_objects_static(
                                captured_bgr, API_KEY, PROJECT_ID, VERSION, conf_threshold, nms_threshold
                            )
                            st.session_state["pending_scan_image"] = cv2.cvtColor(annotated_img, cv2.COLOR_BGR2RGB)
                            st.session_state["pending_scan_counts"] = detected_counts
                            st.session_state["scan_completed"] = True
                            if not detected_counts:
                                st.warning("No trained SKUs detected above threshold. Adjust counts manually on the right.")
                        except Exception as e:
                            st.error(f"Vision API Error: {e}")

            if st.session_state["pending_scan_image"] is not None:
                st.image(st.session_state["pending_scan_image"], caption="AI Bounding Box Verification", use_container_width=True)

    with m_col2:
        with st.container(border=True):
            h_ver1, h_ver2 = st.columns([3, 1])
            with h_ver1:
                st.markdown("#### :material/fact_check: Step 2 — Verify & Sync")
            with h_ver2:
                if st.button("Reset", use_container_width=True):
                    st.session_state["pending_scan_counts"] = {}
                    st.session_state["pending_scan_image"] = None
                    st.session_state["scan_completed"] = False
                    st.rerun()

            df_inv = st.session_state["inventory_df"]

            # Progressive disclosure: filter by selected aisle or detected scan items
            if selected_aisle != "All Zones":
                filtered_df = df_inv[df_inv["Aisle"] == selected_aisle]
            elif st.session_state["scan_completed"] and st.session_state["pending_scan_counts"]:
                detected_keys = list(st.session_state["pending_scan_counts"].keys())
                filtered_df = df_inv[df_inv["roboflow_class"].isin(detected_keys)]
            else:
                filtered_df = df_inv

            if st.button(":material/check_circle: Approve Audit & Sync ERP", use_container_width=True, type="primary"):
                now_str = datetime.now().strftime("%H:%M:%S")
                for idx in filtered_df.index:
                    cls_key = st.session_state["inventory_df"].at[idx, "roboflow_class"]
                    new_count = st.session_state.get(f"verify_{cls_key}", st.session_state["inventory_df"].at[idx, "Visual_Count"])
                    old_count = st.session_state["inventory_df"].at[idx, "Visual_Count"]
                    erp_exp = st.session_state["inventory_df"].at[idx, "ERP_Expected"]

                    st.session_state["inventory_df"].at[idx, "Visual_Count"] = new_count
                    st.session_state["inventory_df"].at[idx, "Last_Audit"] = datetime.now().strftime("%I:%M %p")

                    if new_count != old_count:
                        st.session_state["audit_logs"].insert(0, {
                            "Timestamp": now_str,
                            "Location": st.session_state["inventory_df"].at[idx, "Aisle"],
                            "SKU": st.session_state["inventory_df"].at[idx, "SKU"],
                            "Product": st.session_state["inventory_df"].at[idx, "Product"],
                            "ERP": erp_exp,
                            "Verified": new_count,
                            "Variance": new_count - erp_exp,
                            "Auditor": "Mobile Audit"
                        })
                st.toast("Audit synced to Executive Dashboard & Alert Engine!", icon="📦")
                st.success("Synced! Check Executive Dashboard or Alerts tab.")

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

            for idx, row in filtered_df.iterrows():
                cls_key = row["roboflow_class"]
                ai_detected = st.session_state["pending_scan_counts"].get(cls_key, row["Visual_Count"])

                with st.container(border=True):
                    c_name, c_erp, c_val = st.columns([2.2, 1, 1.3])
                    with c_name:
                        st.markdown(f"**{row['Product']}**")
                        st.caption(f"{row['SKU']} • {row['Aisle']}")
                    with c_erp:
                        st.metric("ERP Stock", row["ERP_Expected"])
                    with c_val:
                        st.number_input(
                            "Verified",
                            min_value=0,
                            max_value=200,
                            value=int(ai_detected),
                            key=f"verify_{cls_key}"
                        )


# ==============================================================================
# TAB 2: EXECUTIVE LAPTOP DASHBOARD
# ==============================================================================
with tab_exec:
    df_curr = st.session_state["inventory_df"].copy()
    df_curr["Variance"] = df_curr["Visual_Count"] - df_curr["ERP_Expected"]
    df_curr["Status"] = df_curr.apply(get_status_label, axis=1)

    total_expected = df_curr["ERP_Expected"].sum()
    abs_diff = df_curr["Variance"].abs().sum()
    accuracy_pct = max(0.0, (1 - (abs_diff / max(1, total_expected))) * 100)
    low_or_oos_count = len(df_curr[df_curr["Visual_Count"] <= df_curr["ROP"]])
    discrepancy_skus = len(df_curr[df_curr["Variance"] != 0])

    # Top 4 KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Shelf Inventory Accuracy</div>
            <div class="metric-value">{accuracy_pct:.1f}%</div>
            <div class="metric-delta" style="color:#3FB950;">↑ +6.4% vs manual baseline</div>
        </div>
    """, unsafe_allow_html=True)

    k2.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">SKUs With Discrepancy</div>
            <div class="metric-value">{discrepancy_skus} <span style="font-size:1rem; color:#8B949E;">/ {len(df_curr)}</span></div>
            <div class="metric-delta" style="color:#D29922;">{abs_diff} total unit variance</div>
        </div>
    """, unsafe_allow_html=True)

    k3.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Low Stock / OOS Alerts</div>
            <div class="metric-value">{low_or_oos_count} <span style="font-size:1rem; color:#F85149;">Flagged</span></div>
            <div class="metric-delta" style="color:#8B949E;">At or below Reorder Point</div>
        </div>
    """, unsafe_allow_html=True)

    k4.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Est. Audit Time Saved</div>
            <div class="metric-value">78% <span style="font-size:1rem; color:#3FB950;">Faster</span></div>
            <div class="metric-delta" style="color:#3FB950;">~4.5 hrs/week per store</div>
        </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        # Ledger Header & Actions
        e_col1, e_col2, e_col3 = st.columns([2, 1, 1])
        with e_col1:
            st.markdown("#### :material/inventory_2: Master SKU Inventory Ledger")
            st.caption(f"Connector Status: {st.session_state['erp_last_sync']}")
        with e_col2:
            if st.button(":material/sync: Reconcile ERP Stock", use_container_width=True, type="primary"):
                st.session_state["inventory_df"]["ERP_Expected"] = st.session_state["inventory_df"]["Visual_Count"]
                st.session_state["erp_last_sync"] = f"Synced at {datetime.now().strftime('%I:%M:%S %p')} (0 Discrepancies)"
                st.toast("ERP Master Ledger reconciled!", icon="🔄")
                st.rerun()
        with e_col3:
            csv_data = df_curr.drop(columns=["roboflow_class"]).to_csv(index=False).encode("utf-8")
            st.download_button(
                label=":material/download: Export Audit CSV",
                data=csv_data,
                file_name=f"StockSense_Audit_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        # Quick Search & Filter Row
        f_col1, f_col2 = st.columns([2, 1])
        with f_col1:
            search_q = st.text_input("Search by SKU, Product, or Aisle", placeholder="e.g. Pepsi, B2, OIL-AFI...")
        with f_col2:
            status_filter = st.selectbox("Filter View", ["All SKUs", "Discrepancies Only", "Low Stock / OOS Only"])

        df_filtered = df_curr.copy()
        if search_q:
            mask = (
                df_filtered["SKU"].str.contains(search_q, case=False) |
                df_filtered["Product"].str.contains(search_q, case=False) |
                df_filtered["Aisle"].str.contains(search_q, case=False)
            )
            df_filtered = df_filtered[mask]

        if status_filter == "Discrepancies Only":
            df_filtered = df_filtered[df_filtered["Variance"] != 0]
        elif status_filter == "Low Stock / OOS Only":
            df_filtered = df_filtered[df_filtered["Visual_Count"] <= df_filtered["ROP"]]

        display_cols = ["SKU", "Product", "Category", "Aisle", "ERP_Expected", "Visual_Count", "Variance", "ROP", "Status", "Last_Audit"]
        st.dataframe(
            df_filtered[display_cols],
            column_config={
                "ERP_Expected": st.column_config.NumberColumn("ERP Stock"),
                "Visual_Count": st.column_config.ProgressColumn("AI Verified", min_value=0, max_value=35, format="%d units"),
                "Variance": st.column_config.NumberColumn("Variance"),
                "ROP": st.column_config.NumberColumn("Reorder Pt"),
            },
            use_container_width=True,
            hide_index=True
        )

    # Charts & Audit Log Row
    ch1, ch2 = st.columns(2, gap="large")
    with ch1:
        with st.container(border=True):
            fig_bar = px.bar(
                df_curr,
                x="Product",
                y=["ERP_Expected", "Visual_Count"],
                barmode="group",
                title="ERP System Records vs. AI Visual Shelf Count",
                template="plotly_dark",
                color_discrete_sequence=["#58A6FF", "#3FB950"]
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="",
                yaxis_title="Units",
                legend_title=""
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with ch2:
        with st.container(border=True):
            st.markdown("#### :material/history: Recent Audit Trail")
            if st.session_state["audit_logs"]:
                st.dataframe(pd.DataFrame(st.session_state["audit_logs"]), use_container_width=True, hide_index=True)
            else:
                st.info("No audit logs recorded yet.")


# ==============================================================================
# TAB 3: AUTOMATED ALERT & REORDERING ENGINE
# ==============================================================================
with tab_alerts:
    df_alert_check = st.session_state["inventory_df"].copy()
    low_items = df_alert_check[df_alert_check["Visual_Count"] <= df_alert_check["ROP"]]

    a_col1, a_col2 = st.columns([1.35, 1], gap="large")

    with a_col1:
        with st.container(border=True):
            st.markdown("#### :material/warning: Active Shelf Threshold Alerts")
            st.caption("Automatically triggered when visual stock drops to or below Reorder Point (ROP).")

            if low_items.empty:
                st.success("All SKUs are above their Reorder Point. No replenishment needed.")
            else:
                for idx, item in low_items.iterrows():
                    is_oos = item["Visual_Count"] == 0
                    card_class = "alert-card-red" if is_oos else "alert-card-yellow"
                    severity = "CRITICAL OUT-OF-STOCK" if is_oos else "LOW STOCK WARNING"
                    suggested_qty = max(10, (item["ROP"] * 3) - item["Visual_Count"])
                    est_cost = suggested_qty * item["Unit_Price_SAR"]

                    st.markdown(f"""
                        <div class="{card_class}">
                            <div style="font-size:0.75rem; font-weight:700; letter-spacing:0.5px; opacity:0.9;">{severity}</div>
                            <div style="font-size:1.05rem; font-weight:700; margin:2px 0;">{item['Product']} ({item['SKU']})</div>
                            <div style="font-size:0.85rem; color:#C9D1D9;">
                                Zone: <b>{item['Aisle']}</b> • Remaining: <b>{item['Visual_Count']} units</b> (ROP: {item['ROP']}) • Restock: <b>+{suggested_qty} units</b> (SAR {est_cost:.2f})
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button(f":material/local_shipping: Dispatch Restock PO ({item['SKU']})", key=f"po_{item['SKU']}", use_container_width=True):
                            po_record = {
                                "PO_ID": f"PO-{int(time.time()) % 10000}",
                                "Time": datetime.now().strftime("%H:%M:%S"),
                                "SKU": item["SKU"],
                                "Product": item["Product"],
                                "Qty": suggested_qty,
                                "SAR": f"{est_cost:.2f}",
                                "Status": "Dispatched"
                            }
                            st.session_state["dispatched_orders"].insert(0, po_record)
                            st.toast(f"Restock PO dispatched for {item['Product']}!", icon="🚚")
                    with b2:
                        if st.button(f":material/chat: Preview Supervisor Alert", key=f"wa_{item['SKU']}", use_container_width=True):
                            st.session_state["last_wa_data"] = {
                                "product": item["Product"],
                                "sku": item["SKU"],
                                "aisle": item["Aisle"],
                                "count": item["Visual_Count"],
                                "qty": suggested_qty,
                                "time": datetime.now().strftime("%I:%M %p")
                            }
                            st.toast("Supervisor WhatsApp alert updated!", icon="📲")

    with a_col2:
        with st.container(border=True):
            st.markdown("#### :material/smartphone: Live Supervisor Alert Preview")
            wa = st.session_state.get("last_wa_data", {
                "product": "Nova Bottled Water 330ml",
                "sku": "BEV-NOV-330",
                "aisle": "Aisle D1",
                "count": 0,
                "qty": 36,
                "time": "10:10 AM"
            })
            st.markdown(f"""
                <div class="wa-container">
                    <div class="wa-header">WhatsApp Business API • Store Floor Supervisor</div>
                    <div class="wa-bubble">
                        <b>🚨 StockSense Replenishment Alert</b><br><br>
                        <b>Product:</b> {wa['product']} ({wa['sku']})<br>
                        <b>Location:</b> {wa['aisle']}<br>
                        <b>Shelf Count:</b> {wa['count']} units remaining<br>
                        <b>Action Required:</b> Restock <b>+{wa['qty']} units</b> from backroom storage.
                        <div class="wa-meta">{wa['time']} ✓✓</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("#### :material/receipt_long: Dispatched Restock Orders")
            if st.session_state["dispatched_orders"]:
                st.dataframe(pd.DataFrame(st.session_state["dispatched_orders"]), use_container_width=True, hide_index=True)
            else:
                st.info("Click 'Dispatch Restock PO' on any active alert to generate a purchase order.")


# ==============================================================================
# TAB 4: LIVE RTSP / GATE SENTINEL
# ==============================================================================
with tab_rtsp:
    with st.container(border=True):
        st.markdown("#### :material/videocam: Continuous RTSP Stream & Gate Line-Crossing")
        st.caption("Connects to a local IP camera stream on the same Wi-Fi network.")

        r1, r2, r3 = st.columns(3)
        with r1:
            cam_mode = st.selectbox("Tracking Mode", ["Tier 1: Static Shelf Density", "Tier 2: Gate Sentinel (Line Crossing)"])
        with r2:
            line_orientation = st.selectbox("Gate Line Orientation", ["Vertical (Left <-> Right)", "Horizontal (Top <-> Bottom)"])
        with r3:
            in_direction = st.selectbox("Entry Direction (+1)", ["Left to Right / Top to Bottom", "Right to Left / Bottom to Top"])

        activate_rtsp = st.toggle("Start Live RTSP Stream", value=False)
        rtsp_placeholder = st.empty()

        if activate_rtsp:
            cap = cv2.VideoCapture(STREAM_URL)
            if not cap.isOpened():
                st.error(f"Could not connect to RTSP stream at `{STREAM_URL}`. Ensure your IP camera is running on the same Wi-Fi network.")
            else:
                while activate_rtsp:
                    ret, frame = cap.read()
                    if not ret:
                        st.warning("Frame dropped from stream...")
                        break
                    h, w, _ = frame.shape
                    if "Gate Sentinel" in cam_mode:
                        if "Vertical" in line_orientation:
                            cv2.line(frame, (w // 2, 0), (w // 2, h), (63, 185, 80), 3)
                        else:
                            cv2.line(frame, (0, h // 2), (w, h // 2), (63, 185, 80), 3)
                    rtsp_placeholder.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB", use_container_width=True)
                    time.sleep(0.03)
                cap.release()
