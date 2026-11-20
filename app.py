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
    st.session_state.active_model_used = "gemini-3.8-flash"

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
