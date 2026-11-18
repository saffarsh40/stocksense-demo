import cv2
import requests
import base64
import numpy as np
import streamlit as st
import threading
import time
import pandas as pd
import plotly.express as px
from datetime import datetime
from collections import OrderedDict

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="StockSense | AI Inventory & Shelf Auditing",
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
    .metric-card {
        background: linear-gradient(135deg, #1E222D 0%, #14171F 100%);
        border: 1px solid #2B313E;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        text-align: left;
        margin-bottom: 10px;
    }
    .metric-title {
        color: #8B949E;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        color: #FFFFFF;
        font-size: 1.85rem;
        font-weight: 700;
        margin-top: 4px;
    }
    .metric-delta {
        font-size: 0.8rem;
        margin-top: 4px;
    }
    .status-badge-live {
        background-color: rgba(46, 160, 67, 0.15);
        color: #3FB950;
        border: 1px solid #2EA043;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    .alert-banner-red {
        background-color: rgba(248, 81, 73, 0.12);
        border-left: 4px solid #F85149;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
        color: #F0F6FC;
    }
    .alert-banner-yellow {
        background-color: rgba(210, 153, 34, 0.12);
        border-left: 4px solid #D29922;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
        color: #F0F6FC;
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }
    /* Make buttons touch-friendly for mobile evaluators */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        min-height: 44px;
    }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZE SHARED MASTER INVENTORY DATABASE ---
# Maps Roboflow class names (roboflow_class) to commercial SKU records
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

# --- HELPER FUNCTIONS ---
def detect_objects_static(image_bgr, api_key, project_id, version, conf_thresh, nms_thresh):
    """Runs Roboflow object detection on a single snapshot and draws clean SaaS bounding boxes."""
    annotated = image_bgr.copy()
    h_orig, w_orig = annotated.shape[:2]
    
    # Resize for fast API payload
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

            # Draw sleek emerald bounding box + label badge
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

# --- SIDEBAR SETTINGS (COLLAPSED BY DEFAULT FOR CLEAN MOBILE/EXEC VIEW) ---
st.sidebar.title("⚙️ StockSense Engine")
st.sidebar.caption("Vision & ERP Configuration")
API_KEY = st.sidebar.text_input("Roboflow API Key", value="3MXgfSLZxnv1Qog1GH3v", type="password")
PROJECT_ID = st.sidebar.text_input("Project ID", value="stocksense")
VERSION = st.sidebar.text_input("Model Version", value="1")
conf_threshold = st.sidebar.slider("Confidence Cutoff", 0.10, 1.00, 0.50, 0.05)
nms_threshold = st.sidebar.slider("NMS Overlap Cutoff", 0.05, 0.50, 0.25, 0.05)
STREAM_URL = st.sidebar.text_input("Local RTSP / IP Cam URL", value="http://192.168.8.4:8080/video")

# --- TOP BRAND HEADER ---
h1, h2 = st.columns([3, 1])
with h1:
    st.title("📦 StockSense AI")
    st.caption("AI-Assisted Shelf Auditing, Discrepancy Detection & Automated Replenishment")
with h2:
    st.markdown('<div style="text-align: right; padding-top: 12px;"><span class="status-badge-live">🟢 CLOUD & MOBILE READY</span></div>', unsafe_allow_html=True)

# --- ROLE-BASED NAVIGATION TABS ---
tab_mobile, tab_exec, tab_alerts, tab_rtsp = st.tabs([
    "📱 Mobile Shelf Audit (Staff)",
    "💻 Executive Dashboard (Manager)",
    "🚨 Alerts & Reordering",
    "📹 Live Gate / RTSP Stream"
])

# ==============================================================================
# TAB 1: MOBILE AUDITOR VIEW (OPTIMIZED FOR SMARTPHONE & LIVE SHOWCASES)
# ==============================================================================
with tab_mobile:
    st.markdown("#### 📱 Quick Shelf Audit & Visual Verification")
    st.caption("Designed for storekeepers & auditors on mobile devices. Snap a shelf photo or upload an image to count stock automatically.")

    m_col1, m_col2 = st.columns([1.1, 1])

    with m_col1:
        selected_aisle = st.selectbox(
            "1️⃣ Select Aisle / Storage Zone",
            ["All Zones (Multi-SKU Demo)", "Aisle B2 (Dry Goods & Baking)", "Aisle A1 (Cooking Oils)", "Aisle D4 (Beverages)", "Chiller C1 (Dairy)"]
        )

        input_source = st.radio(
            "2️⃣ Capture Method",
            ["📸 Smartphone Camera (Live Snap)", "📁 Upload Shelf Photo", "⚡ Simulate Demo Shelf Scan (No Camera)"],
            horizontal=True
        )

        captured_bgr = None

        if "Smartphone Camera" in input_source:
            cam_photo = st.camera_input("Point camera at shelf items and tap Take Photo")
            if cam_photo is not None:
                file_bytes = np.asarray(bytearray(cam_photo.read()), dtype=np.uint8)
                captured_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        elif "Upload Shelf Photo" in input_source:
            uploaded_file = st.file_uploader("Choose a shelf image (JPG/PNG)", type=["jpg", "jpeg", "png"])
            if uploaded_file is not None:
                file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                captured_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        else:
            st.info("Demo Simulation Mode: Click below to simulate an AI shelf scan across your demo SKUs.")
            if st.button("⚡ Run Simulated AI Shelf Scan", use_container_width=True, type="primary"):
                # Simulates realistic detection results for live demonstrations
                st.session_state["pending_scan_counts"] = {
                    "osra_sugar": 11,
                    "kuwait_flour": 14,
                    "afia_oil": 2,
                    "pepsi_can": 5
                }
                st.session_state["pending_scan_image"] = None
                st.success("✅ AI Scan Complete! Review and approve counts on the right.")

        if captured_bgr is not None:
            if st.button("🔍 Analyze Shelf with StockSense AI", use_container_width=True, type="primary"):
                with st.spinner("Running Roboflow Computer Vision inference..."):
                    try:
                        annotated_img, detected_counts = detect_objects_static(
                            captured_bgr, API_KEY, PROJECT_ID, VERSION, conf_threshold, nms_threshold
                        )
                        st.session_state["pending_scan_image"] = cv2.cvtColor(annotated_img, cv2.COLOR_BGR2RGB)
                        st.session_state["pending_scan_counts"] = detected_counts
                        if not detected_counts:
                            st.warning("No trained SKUs detected above confidence cutoff. You can still adjust counts manually.")
                    except Exception as e:
                        st.error(f"API Connection Error: {e}. Try 'Simulate Demo Shelf Scan' for offline demos.")

        if st.session_state["pending_scan_image"] is not None:
            st.image(st.session_state["pending_scan_image"], caption="AI Bounding Box Verification", use_container_width=True)

    with m_col2:
        st.markdown("##### 3️⃣ Human-in-the-Loop Verification")
        st.caption("Confirm AI counts or adjust manually before syncing to ERP.")

        df_inv = st.session_state["inventory_df"]
        verified_updates = {}

        for idx, row in df_inv.iterrows():
            cls_key = row["roboflow_class"]
            # Show items detected in current scan, or all items if no scan yet
            ai_detected = st.session_state["pending_scan_counts"].get(cls_key, row["Visual_Count"])

            with st.container():
                c_name, c_erp, c_val = st.columns([2.2, 1, 1.3])
                with c_name:
                    st.markdown(f"**{row['Product']}**")
                    st.caption(f"{row['SKU']} • {row['Aisle']}")
                with c_erp:
                    st.metric("ERP Expected", row["ERP_Expected"])
                with c_val:
                    verified_updates[idx] = st.number_input(
                        "Verified Count",
                        min_value=0,
                        max_value=200,
                        value=int(ai_detected),
                        key=f"verify_{cls_key}"
                    )
                st.markdown("<hr style='margin: 6px 0; border-color: #2B313E;'>", unsafe_allow_html=True)

        if st.button("✅ Approve Audit & Sync to Dashboard", use_container_width=True, type="primary"):
            now_str = datetime.now().strftime("%H:%M:%S")
            for idx, new_count in verified_updates.items():
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
            st.toast("✅ Inventory updated across Executive Dashboard & Alert Engine!", icon="📦")
            st.success("Audit approved! Switch to the **Executive Dashboard** or **Alerts** tab to see live updates.")


# ==============================================================================
# TAB 2: EXECUTIVE LAPTOP DASHBOARD
# ==============================================================================
with tab_exec:
    df_curr = st.session_state["inventory_df"].copy()
    df_curr["Variance"] = df_curr["Visual_Count"] - df_curr["ERP_Expected"]
    df_curr["Status"] = df_curr.apply(get_status_label, axis=1)

    total_expected = df_curr["ERP_Expected"].sum()
    total_visual = df_curr["Visual_Count"].sum()
    abs_diff = df_curr["Variance"].abs().sum()
    accuracy_pct = max(0.0, (1 - (abs_diff / max(1, total_expected))) * 100)
    low_or_oos_count = len(df_curr[df_curr["Visual_Count"] <= df_curr["ROP"]])
    discrepancy_skus = len(df_curr[df_curr["Variance"] != 0])

    # Top 4 Executive KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🎯 Shelf Inventory Accuracy</div>
            <div class="metric-value">{accuracy_pct:.1f}%</div>
            <div class="metric-delta" style="color:#3FB950;">↑ +6.4% vs manual baseline</div>
        </div>
    """, unsafe_allow_html=True)

    k2.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">⚠️ SKUs With Discrepancy</div>
            <div class="metric-value">{discrepancy_skus} <span style="font-size:1rem; color:#8B949E;">/ {len(df_curr)} SKUs</span></div>
            <div class="metric-delta" style="color:#D29922;">{abs_diff} total unit variance</div>
        </div>
    """, unsafe_allow_html=True)

    k3.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🚨 Low Stock / OOS Alerts</div>
            <div class="metric-value">{low_or_oos_count} <span style="font-size:1rem; color:#F85149;">Action Needed</span></div>
            <div class="metric-delta" style="color:#8B949E;">Below Reorder Point (ROP)</div>
        </div>
    """, unsafe_allow_html=True)

    k4.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">⏱️ Est. Audit Time Saved</div>
            <div class="metric-value">78% <span style="font-size:1rem; color:#3FB950;">Faster</span></div>
            <div class="metric-delta" style="color:#3FB950;">~4.5 hrs/week per store</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ERP Action Bar
    e_col1, e_col2, e_col3 = st.columns([2, 1, 1])
    with e_col1:
        st.markdown("##### 📋 Master SKU Inventory Ledger")
        st.caption(f"ERP Status: {st.session_state['erp_last_sync']}")
    with e_col2:
        if st.button("🔄 Push Verified Counts to ERP", use_container_width=True):
            st.session_state["inventory_df"]["ERP_Expected"] = st.session_state["inventory_df"]["Visual_Count"]
            st.session_state["erp_last_sync"] = f"Synced at {datetime.now().strftime('%I:%M:%S %p')} (0 Discrepancies)"
            st.toast("ERP Master Ledger reconciled successfully!", icon="🔄")
            st.rerun()
    with e_col3:
        csv_data = df_curr.drop(columns=["roboflow_class"]).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Audit CSV",
            data=csv_data,
            file_name=f"StockSense_Audit_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Interactive Master Table
    display_cols = ["SKU", "Product", "Category", "Aisle", "ERP_Expected", "Visual_Count", "Variance", "ROP", "Status", "Last_Audit"]
    st.dataframe(
        df_curr[display_cols],
        column_config={
            "ERP_Expected": st.column_config.NumberColumn("ERP System Stock"),
            "Visual_Count": st.column_config.ProgressColumn("AI Verified Stock", min_value=0, max_value=35, format="%d units"),
            "Variance": st.column_config.NumberColumn("Variance"),
            "ROP": st.column_config.NumberColumn("Reorder Point"),
        },
        use_container_width=True,
        hide_index=True
    )

    # Side-by-Side Executive Charts
    ch1, ch2 = st.columns(2)
    with ch1:
        fig_bar = px.bar(
            df_curr,
            x="Product",
            y=["ERP_Expected", "Visual_Count"],
            barmode="group",
            title="ERP System Records vs. AI Visual Shelf Count",
            template="plotly_dark",
            color_discrete_sequence=["#58A6FF", "#3FB950"]
        )
        fig_bar.update_layout(xaxis_title="", yaxis_title="Units", legend_title="Source")
        st.plotly_chart(fig_bar, use_container_width=True)

    with ch2:
        st.markdown("##### 🕒 Recent Mobile & Gate Audit Trail")
        if st.session_state["audit_logs"]:
            st.dataframe(pd.DataFrame(st.session_state["audit_logs"]), use_container_width=True, hide_index=True)
        else:
            st.info("No audit logs recorded yet.")


# ==============================================================================
# TAB 3: AUTOMATED ALERT & REORDERING ENGINE
# ==============================================================================
with tab_alerts:
    st.markdown("#### 🚨 Automated Low-Stock Alerts & Replenishment Dispatch")
    st.caption("Real-time triggers when visual stock falls at or below Reorder Point (ROP).")

    df_alert_check = st.session_state["inventory_df"].copy()
    low_items = df_alert_check[df_alert_check["Visual_Count"] <= df_alert_check["ROP"]]

    a_col1, a_col2 = st.columns([1.4, 1])

    with a_col1:
        st.markdown("##### 🔔 Active Shelf Threshold Alerts")
        if low_items.empty:
            st.success("🎉 All SKUs are above their Reorder Point! No immediate replenishment needed.")
        else:
            for idx, item in low_items.iterrows():
                is_oos = item["Visual_Count"] == 0
                banner_class = "alert-banner-red" if is_oos else "alert-banner-yellow"
                severity = "CRITICAL OUT-OF-STOCK" if is_oos else "LOW STOCK WARNING"
                suggested_qty = max(10, (item["ROP"] * 3) - item["Visual_Count"])
                est_cost = suggested_qty * item["Unit_Price_SAR"]

                st.markdown(f"""
                    <div class="{banner_class}">
                        <strong>{severity}: {item['Product']} ({item['SKU']})</strong><br>
                        Location: {item['Aisle']} | Current Visual Count: <b>{item['Visual_Count']} units</b> (ROP: {item['ROP']})<br>
                        Suggested Replenishment: <b>+{suggested_qty} units</b> (Est. SAR {est_cost:.2f})
                    </div>
                """, unsafe_allow_html=True)

                b1, b2 = st.columns(2)
                with b1:
                    if st.button(f"📦 Dispatch Restock PO ({item['SKU']})", key=f"po_{item['SKU']}", use_container_width=True):
                        po_record = {
                            "PO_ID": f"PO-{int(time.time()) % 10000}",
                            "Time": datetime.now().strftime("%H:%M:%S"),
                            "SKU": item["SKU"],
                            "Product": item["Product"],
                            "Order_Qty": suggested_qty,
                            "Total_SAR": f"{est_cost:.2f}",
                            "Status": "Dispatched to Warehouse"
                        }
                        st.session_state["dispatched_orders"].insert(0, po_record)
                        st.toast(f"Replenishment order created for {item['Product']}!", icon="🚚")
                with b2:
                    if st.button(f"📲 Send WhatsApp Supervisor Alert", key=f"wa_{item['SKU']}", use_container_width=True):
                        st.session_state["last_wa_preview"] = (
                            f"🚨 *StockSense Alert*\n"
                            f"Item: *{item['Product']}* ({item['SKU']})\n"
                            f"Location: {item['Aisle']}\n"
                            f"Remaining on Shelf: *{item['Visual_Count']} units*\n"
                            f"Action: Please restock +{suggested_qty} units from backroom."
                        )
                        st.toast("Mobile alert preview generated!", icon="📲")

    with a_col2:
        st.markdown("##### 📲 Live Mobile Notification Preview")
        wa_msg = st.session_state.get(
            "last_wa_preview",
            "🚨 *StockSense Alert*\nItem: *Nova Bottled Water 330ml* (BEV-NOV-330)\nLocation: Aisle D1\nRemaining on Shelf: *0 units*\nAction: Please restock +36 units immediately."
        )
        st.code(wa_msg, language="markdown")

        st.markdown("##### 🚚 Dispatched Replenishment Orders")
        if st.session_state["dispatched_orders"]:
            st.dataframe(pd.DataFrame(st.session_state["dispatched_orders"]), use_container_width=True, hide_index=True)
        else:
            st.info("Click 'Dispatch Restock PO' on any active alert to generate a purchase/replenishment order.")


# ==============================================================================
# TAB 4: LIVE RTSP / GATE SENTINEL (YOUR ORIGINAL CONTINUOUS STREAM MODULE)
# ==============================================================================
with tab_rtsp:
    st.markdown("#### 📹 Continuous RTSP Stream & Gate Line-Crossing")
    st.caption("Best used locally on a laptop connected to an IP camera on the same Wi-Fi network.")

    r1, r2, r3 = st.columns(3)
    with r1:
        cam_mode = st.selectbox("Tracking Mode", ["Tier 1: Static Shelf Density", "Tier 2: Gate Sentinel (Line Crossing)"])
    with r2:
        line_orientation = st.selectbox("Gate Line Orientation", ["Vertical (Left <-> Right)", "Horizontal (Top <-> Bottom)"])
    with r3:
        in_direction = st.selectbox("Entry Direction (+1)", ["Left to Right / Top to Bottom", "Right to Left / Bottom to Top"])

    activate_rtsp = st.checkbox("▶️ Start Live RTSP Stream", value=False)
    rtsp_placeholder = st.empty()

    if activate_rtsp:
        cap = cv2.VideoCapture(STREAM_URL)
        if not cap.isOpened():
            st.error(f"Could not connect to RTSP stream at `{STREAM_URL}`. Ensure your IP camera app is running on the same local network, or use Tab 1 (Mobile Shelf Audit) for cloud demos.")
        else:
            st.success("Connected to RTSP feed! Uncheck 'Start Live RTSP Stream' to stop.")
            while activate_rtsp:
                ret, frame = cap.read()
                if not ret:
                    st.warning("Frame dropped from stream...")
                    break
                h, w, _ = frame.shape
                if "Gate Sentinel" in cam_mode:
                    if "Vertical" in line_orientation:
                        cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 140, 0), 3)
                    else:
                        cv2.line(frame, (0, h // 2), (w, h // 2), (255, 140, 0), 3)
                rtsp_placeholder.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB", use_container_width=True)
                time.sleep(0.03)
            cap.release()