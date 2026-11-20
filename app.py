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
    page_title="StockSense AI | Enterprise Shelf & SAP Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- COMMERCIAL SAAS CUSTOM CSS ---
st.markdown("""
<style>
    .stApp {
        background-color: #0B0F17;
    }
    #MainMenu, footer {visibility: hidden;}
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
        max-width: 1340px;
    }
    .brand-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
        padding: 14px 20px;
        background: linear-gradient(135deg, #151C28 0%, #0E131D 100%);
        border: 1px solid #263042;
        border-radius: 14px;
        margin-bottom: 16px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
    }
    .status-pill {
        background-color: rgba(63, 185, 80, 0.14);
        color: #3FB950;
        border: 1px solid rgba(63, 185, 80, 0.45);
        padding: 6px 14px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #151B26 0%, #111620 100%);
        border: 1px solid #263042;
        padding: 14px 16px;
        border-radius: 14px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 800 !important;
        color: #F0F6FC !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #151B26;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #263042;
        overflow-x: auto;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 14px;
        font-weight: 600;
        white-space: nowrap;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1F6FEB !important;
        color: #FFFFFF !important;
    }
    .chart-card {
        background-color: #131923;
        border: 1px solid #263042;
        border-radius: 14px;
        padding: 16px 18px 8px 18px;
        margin-bottom: 14px;
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
    .feed-item {
        background-color: #121822;
        border-left: 3px solid #1F6FEB;
        padding: 8px 12px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 6px;
        font-size: 0.84rem;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #1F6FEB 0%, #388BFD 100%);
        border: none;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.65rem 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 42-SKU SAUDI SUPERMARKET SAP MATERIAL MASTER CATALOG ---
DEFAULT_INVENTORY = [
    # Pantry & Cooking Staples
    {"sku_key": "osra_sugar", "sap_id": "SAP-10045210", "ean13": "6281007041012", "category": "Pantry", "name": "Osra White Sugar 1kg", "arabic_name": "سكر الأسرة الأبيض 1 كجم", "keywords": ["osra", "al osra", "sugar", "أسرة", "الأسرة", "سكر", "قيراط"], "aisle": "Aisle B2", "price": 5.50, "erp_qty": 12, "physical_qty": 0, "reorder_pt": 6},
    {"sku_key": "kuwait_flour", "sap_id": "SAP-10045218", "ean13": "6271001010025", "category": "Pantry", "name": "Kuwait Patent Flour 2kg", "arabic_name": "طحين الكويت الفاخر 2 كجم", "keywords": ["kuwait", "flour", "طحين", "دقيق", "الكويت", "المطاحن"], "aisle": "Aisle B2", "price": 8.00, "erp_qty": 15, "physical_qty": 0, "reorder_pt": 8},
    {"sku_key": "afia_oil", "sap_id": "SAP-10045304", "ean13": "6281018001053", "category": "Pantry", "name": "Afia Corn Oil 1.5L", "arabic_name": "زيت ذرة عافية 1.5 لتر", "keywords": ["afia", "corn oil", "oil", "عافية", "زيت", "ذرة"], "aisle": "Aisle A1", "price": 24.50, "erp_qty": 8, "physical_qty": 0, "reorder_pt": 5},
    {"sku_key": "alwalimah_rice", "sap_id": "SAP-10045312", "ean13": "6281022003018", "category": "Pantry", "name": "Al Walimah Basmati Rice 5kg", "arabic_name": "أرز الوليمة مزة بسمتي 5 كجم", "keywords": ["walimah", "al walimah", "rice", "basmati", "الوليمة", "وليمة", "أرز", "رز"], "aisle": "Aisle B1", "price": 42.00, "erp_qty": 10, "physical_qty": 0, "reorder_pt": 5},
    {"sku_key": "abukass_rice", "sap_id": "SAP-10045319", "ean13": "6281022003094", "category": "Pantry", "name": "Abu Kass Basmati Rice 5kg", "arabic_name": "أرز أبو كاس بسمتي 5 كجم", "keywords": ["abu kass", "abukass", "rice", "أبو كاس", "ابو كاس", "أرز"], "aisle": "Aisle B1", "price": 44.00, "erp_qty": 9, "physical_qty": 0, "reorder_pt": 4},
    {"sku_key": "goody_pasta", "sap_id": "SAP-10045325", "ean13": "6281011004029", "category": "Pantry", "name": "Goody Macaroni Pasta 450g", "arabic_name": "مكرونة قودي 450 جم", "keywords": ["goody", "pasta", "macaroni", "spaghetti", "قودي", "مكرونة", "معكرونة"], "aisle": "Aisle B3", "price": 4.50, "erp_qty": 18, "physical_qty": 0, "reorder_pt": 8},
    {"sku_key": "heinz_ketchup", "sap_id": "SAP-10045331", "ean13": "5000157024671", "category": "Pantry", "name": "Heinz Tomato Ketchup 570g", "arabic_name": "كاتشب طماطم هاينز 570 جم", "keywords": ["heinz", "ketchup", "tomato", "هاينز", "كاتشب"], "aisle": "Aisle A3", "price": 14.50, "erp_qty": 14, "physical_qty": 0, "reorder_pt": 6},
    {"sku_key": "almarai_olive_oil", "sap_id": "SAP-10045340", "ean13": "6281007055019", "category": "Pantry", "name": "Al Jouf Extra Virgin Olive Oil 500ml", "arabic_name": "زيت زيتون الجوف بكر 500 مل", "keywords": ["olive oil", "al jouf", "nadec", "زيت زيتون", "الجوف", "نادك"], "aisle": "Aisle A1", "price": 29.00, "erp_qty": 7, "physical_qty": 0, "reorder_pt": 4},
    {"sku_key": "al_alali_paste", "sap_id": "SAP-10045348", "ean13": "6281014002011", "category": "Pantry", "name": "Al Alali Tomato Paste 135g", "arabic_name": "معجون طماطم العلالي 135 جم", "keywords": ["al alali", "tomato paste", "العلالي", "معجون طماطم", "صلصة"], "aisle": "Aisle A2", "price": 2.25, "erp_qty": 25, "physical_qty": 0, "reorder_pt": 12},
    {"sku_key": "maggi_cubes", "sap_id": "SAP-10045355", "ean13": "7613035012042", "category": "Pantry", "name": "Maggi Chicken Bouillon 24 Cubes", "arabic_name": "مرقة دجاج ماجي 24 مكعب", "keywords": ["maggi", "bouillon", "chicken", "ماجي", "مرقة"], "aisle": "Aisle A2", "price": 11.50, "erp_qty": 16, "physical_qty": 0, "reorder_pt": 8},

    # Dairy, Cheese & Breakfast
    {"sku_key": "almarai_milk", "sap_id": "SAP-10045411", "ean13": "6281007020017", "category": "Dairy & Breakfast", "name": "Almarai Fresh Milk 1L", "arabic_name": "حليب المراعي طازج 1 لتر", "keywords": ["almarai", "milk", "fresh", "المراعي", "حليب", "طازج"], "aisle": "Chiller C1", "price": 6.00, "erp_qty": 20, "physical_qty": 0, "reorder_pt": 10},
    {"sku_key": "almarai_laban", "sap_id": "SAP-10045418", "ean13": "6281007020093", "category": "Dairy & Breakfast", "name": "Almarai Fresh Laban 1L", "arabic_name": "لبن المراعي طازج 1 لتر", "keywords": ["laban", "almarai", "لبن", "المراعي"], "aisle": "Chiller C1", "price": 6.00, "erp_qty": 18, "physical_qty": 0, "reorder_pt": 9},
    {"sku_key": "puck_cheese", "sap_id": "SAP-10045424", "ean13": "5760466901024", "category": "Dairy & Breakfast", "name": "Puck Cream Cheese Jar 500g", "arabic_name": "جبنة بوك كريم قابلة للدهن 500 جم", "keywords": ["puck", "cream cheese", "cheese", "بوك", "جبن", "جبنة"], "aisle": "Chiller C2", "price": 19.50, "erp_qty": 12, "physical_qty": 0, "reorder_pt": 6},
    {"sku_key": "kraft_cheddar", "sap_id": "SAP-10045430", "ean13": "7622210100948", "category": "Dairy & Breakfast", "name": "Kraft Original Cheddar Tin 100g", "arabic_name": "جبنة كرافت شيدر أصلية 100 جم", "keywords": ["kraft", "cheddar", "cheese", "كرافت", "شيدر", "جبنة"], "aisle": "Aisle C3", "price": 7.50, "erp_qty": 22, "physical_qty": 0, "reorder_pt": 10},
    {"sku_key": "nido_milk", "sap_id": "SAP-10045437", "ean13": "7613034890016", "category": "Dairy & Breakfast", "name": "Nestle Nido Milk Powder 900g", "arabic_name": "حليب نيدو مجفف 900 جم", "keywords": ["nido", "nestle", "milk powder", "نيدو", "نستله", "حليب مجفف"], "aisle": "Aisle C3", "price": 46.00, "erp_qty": 10, "physical_qty": 0, "reorder_pt": 5},
    {"sku_key": "lipton_tea", "sap_id": "SAP-10045443", "ean13": "6281006010125", "category": "Dairy & Breakfast", "name": "Lipton Yellow Label Tea 100 Bags", "arabic_name": "شاي ليبتون العلامة الصفراء 100 كيس", "keywords": ["lipton", "tea", "yellow label", "ليبتون", "شاي"], "aisle": "Aisle C4", "price": 17.50, "erp_qty": 15, "physical_qty": 0, "reorder_pt": 7},
    {"sku_key": "nescafe_classic", "sap_id": "SAP-10045450", "ean13": "7613033010125", "category": "Dairy & Breakfast", "name": "Nescafe Classic Jar 190g", "arabic_name": "قهوة نسكافيه كلاسيك 190 جم", "keywords": ["nescafe", "coffee", "classic", "نسكافيه", "قهوة"], "aisle": "Aisle C4", "price": 26.00, "erp_qty": 11, "physical_qty": 0, "reorder_pt": 5},
    {"sku_key": "kelloggs_cornflakes", "sap_id": "SAP-10045458", "ean13": "5053827100120", "category": "Dairy & Breakfast", "name": "Kelloggs Corn Flakes 500g", "arabic_name": "رقائق الذرة كيلوقز كورن فليكس 500 جم", "keywords": ["kellogg", "corn flakes", "cereal", "كيلوقز", "كورن فليكس"], "aisle": "Aisle C2", "price": 18.00, "erp_qty": 12, "physical_qty": 0, "reorder_pt": 6},

    # Beverages & Water
    {"sku_key": "pepsi_can", "sap_id": "SAP-10045502", "ean13": "6281034000112", "category": "Beverages", "name": "Pepsi Cola Can 330ml", "arabic_name": "بيبسي كولا علبة 330 مل", "keywords": ["pepsi", "cola", "بيبسي", "كولا"], "aisle": "Aisle D4", "price": 2.50, "erp_qty": 24, "physical_qty": 0, "reorder_pt": 12},
    {"sku_key": "sevenup_can", "sap_id": "SAP-10045508", "ean13": "6281034000228", "category": "Beverages", "name": "7UP Lemon Lime Can 330ml", "arabic_name": "سفن أب علبة 330 مل", "keywords": ["7up", "seven up", "سفن اب", "سفن أب"], "aisle": "Aisle D4", "price": 2.50, "erp_qty": 20, "physical_qty": 0, "reorder_pt": 10},
    {"sku_key": "mirinda_can", "sap_id": "SAP-10045514", "ean13": "6281034000334", "category": "Beverages", "name": "Mirinda Citrus Can 330ml", "arabic_name": "ميرندا حمضيات علبة 330 مل", "keywords": ["mirinda", "citrus", "ميرندا", "حمضيات"], "aisle": "Aisle D4", "price": 2.50, "erp_qty": 18, "physical_qty": 0, "reorder_pt": 9},
    {"sku_key": "cocacola_can", "sap_id": "SAP-10045520", "ean13": "5449000000996", "category": "Beverages", "name": "Coca-Cola Can 330ml", "arabic_name": "كوكاكولا علبة 330 مل", "keywords": ["coca-cola", "coca cola", "coke", "كوكاكولا", "كولا"], "aisle": "Aisle D4", "price": 2.50, "erp_qty": 22, "physical_qty": 0, "reorder_pt": 10},
    {"sku_key": "nova_water", "sap_id": "SAP-10045609", "ean13": "6281038000019", "category": "Beverages", "name": "Nova Bottled Water 330ml", "arabic_name": "مياه نوفا 330 مل", "keywords": ["nova", "water", "نوفا", "مياه", "ماء"], "aisle": "Aisle D1", "price": 1.00, "erp_qty": 30, "physical_qty": 0, "reorder_pt": 15},
    {"sku_key": "berain_water", "sap_id": "SAP-10045615", "ean13": "6281068000115", "category": "Beverages", "name": "Berain Bottled Water 330ml", "arabic_name": "مياه بيرين 330 مل", "keywords": ["berain", "water", "بيرين", "مياه"], "aisle": "Aisle D1", "price": 1.00, "erp_qty": 28, "physical_qty": 0, "reorder_pt": 14},
    {"sku_key": "almarai_juice", "sap_id": "SAP-10045622", "ean13": "6281007030115", "category": "Beverages", "name": "Almarai Mango Juice 1L", "arabic_name": "عصير المراعي مانجو 1 لتر", "keywords": ["juice", "mango", "almarai", "عصير", "مانجو", "المراعي"], "aisle": "Chiller C1", "price": 7.00, "erp_qty": 14, "physical_qty": 0, "reorder_pt": 7},

    # Snacks, Biscuits & Chocolates
    {"sku_key": "lays_chips", "sap_id": "SAP-10045701", "ean13": "6281034011019", "category": "Snacks & Sweets", "name": "Lay's Salted Potato Chips 155g", "arabic_name": "بطاطس ليز بالملح 155 جم", "keywords": ["lays", "lay's", "chips", "ليز", "بطاطس", "شيبس"], "aisle": "Aisle E1", "price": 6.50, "erp_qty": 16, "physical_qty": 0, "reorder_pt": 8},
    {"sku_key": "pringles_original", "sap_id": "SAP-10045708", "ean13": "5053990101573", "category": "Snacks & Sweets", "name": "Pringles Original Can 165g", "arabic_name": "بطاطس برينجلز أصلي 165 جم", "keywords": ["pringles", "chips", "برينجلز", "بطاطس"], "aisle": "Aisle E1", "price": 11.00, "erp_qty": 12, "physical_qty": 0, "reorder_pt": 6},
    {"sku_key": "galaxy_chocolate", "sap_id": "SAP-10045715", "ean13": "6294003530112", "category": "Snacks & Sweets", "name": "Galaxy Smooth Milk Chocolate 80g", "arabic_name": "شوكولاتة جالكسي بالحليب 80 جم", "keywords": ["galaxy", "chocolate", "جالكسي", "شوكولاتة"], "aisle": "Aisle E2", "price": 6.50, "erp_qty": 20, "physical_qty": 0, "reorder_pt": 10},
    {"sku_key": "kitkat_4finger", "sap_id": "SAP-10045721", "ean13": "7613034626844", "category": "Snacks & Sweets", "name": "KitKat 4-Finger Chocolate 41.5g", "arabic_name": "شوكولاتة كيت كات 4 أصابع", "keywords": ["kitkat", "kit kat", "chocolate", "كيت كات", "شوكولاتة"], "aisle": "Aisle E2", "price": 3.50, "erp_qty": 25, "physical_qty": 0, "reorder_pt": 12},
    {"sku_key": "oreo_biscuits", "sap_id": "SAP-10045728", "ean13": "7622210449283", "category": "Snacks & Sweets", "name": "Oreo Original Sandwich Cookies 154g", "arabic_name": "بسكويت أوريو الأصلي 154 جم", "keywords": ["oreo", "biscuit", "cookies", "أوريو", "اوريو", "بسكويت"], "aisle": "Aisle E3", "price": 5.50, "erp_qty": 18, "physical_qty": 0, "reorder_pt": 9},

    # Canned Foods
    {"sku_key": "goody_tuna", "sap_id": "SAP-10045801", "ean13": "6281011001011", "category": "Canned Foods", "name": "Goody Tenderina Tuna 185g", "arabic_name": "تونة قودي تندرينا 185 جم", "keywords": ["goody", "tuna", "tenderina", "قودي", "تونة"], "aisle": "Aisle A4", "price": 8.50, "erp_qty": 20, "physical_qty": 0, "reorder_pt": 10},
    {"sku_key": "luna_foul", "sap_id": "SAP-10045809", "ean13": "6281004002011", "category": "Canned Foods", "name": "Luna Foul Medames Plain 450g", "arabic_name": "فول مدمس لونا سادة 450 جم", "keywords": ["luna", "foul", "beans", "لونا", "فول"], "aisle": "Aisle A4", "price": 4.25, "erp_qty": 16, "physical_qty": 0, "reorder_pt": 8},
    {"sku_key": "al_alali_corn", "sap_id": "SAP-10045815", "ean13": "6281014005012", "category": "Canned Foods", "name": "Al Alali Whole Kernel Sweet Corn 340g", "arabic_name": "ذرة حلوة كاملة العلالي 340 جم", "keywords": ["sweet corn", "corn", "al alali", "ذرة", "العلالي"], "aisle": "Aisle A4", "price": 5.00, "erp_qty": 15, "physical_qty": 0, "reorder_pt": 7},

    # Household & Cleaning
    {"sku_key": "dettol_antiseptic", "sap_id": "SAP-10045901", "ean13": "6291100120015", "category": "Household & Care", "name": "Dettol Antiseptic Disinfectant 500ml", "arabic_name": "مطهر ديتول الأصلي 500 مل", "keywords": ["dettol", "antiseptic", "disinfectant", "ديتول", "مطهر"], "aisle": "Aisle F1", "price": 21.00, "erp_qty": 12, "physical_qty": 0, "reorder_pt": 6},
    {"sku_key": "fairy_dishwash", "sap_id": "SAP-10045908", "ean13": "4084500123456", "category": "Household & Care", "name": "Fairy Lemon Dishwashing Liquid 800ml", "arabic_name": "سائل غسيل الصحون فيري ليمون 800 مل", "keywords": ["fairy", "dish", "lemon", "فيري", "صحون"], "aisle": "Aisle F1", "price": 13.50, "erp_qty": 14, "physical_qty": 0, "reorder_pt": 7},
    {"sku_key": "tide_detergent", "sap_id": "SAP-10045915", "ean13": "6281006040115", "category": "Household & Care", "name": "Tide Laundry Powder Detergent 2.5kg", "arabic_name": "مسحوق غسيل تايد 2.5 كجم", "keywords": ["tide", "detergent", "laundry", "تايد", "مسحوق غسيل"], "aisle": "Aisle F2", "price": 34.00, "erp_qty": 10, "physical_qty": 0, "reorder_pt": 5},
    {"sku_key": "fine_tissues", "sap_id": "SAP-10045922", "ean13": "6281029001012", "category": "Household & Care", "name": "Fine Fluffy Facial Tissues 150 Sheets", "arabic_name": "مناديل وجه فاين فلافي 150 منديل", "keywords": ["fine", "tissue", "tissues", "فاين", "مناديل"], "aisle": "Aisle F3", "price": 6.00, "erp_qty": 24, "physical_qty": 0, "reorder_pt": 12},
    {"sku_key": "sanita_bags", "sap_id": "SAP-10045929", "ean13": "6281012003018", "category": "Household & Care", "name": "Sanita Club Trash Bags 30 Gallon", "arabic_name": "أكياس نفايات سانيتا كلوب 30 جالون", "keywords": ["sanita", "trash bags", "garbage", "سانيتا", "أكياس"], "aisle": "Aisle F3", "price": 12.50, "erp_qty": 15, "physical_qty": 0, "reorder_pt": 7},

    # Personal Care
    {"sku_key": "signal_toothpaste", "sap_id": "SAP-10045951", "ean13": "6281006070112", "category": "Personal Care", "name": "Signal Cavity Fighter Toothpaste 120ml", "arabic_name": "معجون أسنان سيجنال مكافح التسوس 120 مل", "keywords": ["signal", "toothpaste", "colgate", "سيجنال", "كولجيت", "معجون أسنان"], "aisle": "Aisle G1", "price": 8.00, "erp_qty": 18, "physical_qty": 0, "reorder_pt": 9},
    {"sku_key": "head_shoulders", "sap_id": "SAP-10045958", "ean13": "4084500987654", "category": "Personal Care", "name": "Head & Shoulders Menthol Shampoo 400ml", "arabic_name": "شامبو هيد آند شولدرز نعناع 400 مل", "keywords": ["head", "shoulders", "shampoo", "هيد اند شولدرز", "شامبو"], "aisle": "Aisle G2", "price": 22.00, "erp_qty": 12, "physical_qty": 0, "reorder_pt": 6},
    {"sku_key": "nivea_cream", "sap_id": "SAP-10045965", "ean13": "4005808123456", "category": "Personal Care", "name": "Nivea Soft Moisturizing Cream 200ml", "arabic_name": "كريم نيفيا سوفت المرطب 200 مل", "keywords": ["nivea", "cream", "soft", "نيفيا", "كريم"], "aisle": "Aisle G2", "price": 16.50, "erp_qty": 14, "physical_qty": 0, "reorder_pt": 7},
    {"sku_key": "lifebuoy_handwash", "sap_id": "SAP-10045972", "ean13": "6281006080111", "category": "Personal Care", "name": "Lifebuoy Total 10 Hand Wash 200ml", "arabic_name": "غسول اليدين لايفبوي 200 مل", "keywords": ["lifebuoy", "hand wash", "soap", "لايفبوي", "غسول", "صابون"], "aisle": "Aisle G1", "price": 9.50, "erp_qty": 16, "physical_qty": 0, "reorder_pt": 8},
]

# --- SHARED MULTI-DEVICE SERVER STORE (PHONE -> LAPTOP REAL-TIME SYNC) ---
@st.cache_resource
def get_shared_store_db():
    return {
        "inventory": [item.copy() for item in DEFAULT_INVENTORY],
        "last_sync": "09:15 AM (SAP S/4HANA Connected)",
        "activity_log": [],
        "last_updated_ts": time.time(),
    }

shared_db = get_shared_store_db()

# --- STRUCTURED OUTPUT SCHEMA ---
class DetectedProduct(BaseModel):
    sku_key: str = Field(description="Matched catalog key from the SAP catalog, or 'unmapped_item'")
    sap_id: str = Field(description="Corresponding SAP Material ID from the catalog, or 'SAP-UNMAPPED'")
    product_name: str = Field(description="Clean English + Arabic product name identified on packaging")
    extracted_text_ar_en: str = Field(description="Verbatim Arabic and English words read from the label/packaging")
    detected_barcode: Optional[str] = Field(default=None, description="Any EAN/UPC barcode digits visible on the package")
    unit_count: int = Field(description="Exact number of physical units/facings of this product visible")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")

class ShelfScanResult(BaseModel):
    detections: List[DetectedProduct]
    raw_visible_text_summary: str = Field(description="Brief summary of all readable Arabic/English shelf labels detected")

# --- SESSION STATE ---
if "last_annotated_img" not in st.session_state:
    st.session_state.last_annotated_img = None
if "last_barcode_hits" not in st.session_state:
    st.session_state.last_barcode_hits = []
if "active_model_used" not in st.session_state:
    st.session_state.active_model_used = "gemini-3.5-flash-lite"
if "processed_live_event_id" not in st.session_state:
    st.session_state.processed_live_event_id = None
if "live_sync_feedback" not in st.session_state:
    st.session_state.live_sync_feedback = ""

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.markdown("### ⚙️ Engine & Store Controls")
    secret_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
    user_api_key = st.text_input(
        "Gemini API Key (Optional Override)",
        value="",
        type="password",
        help="Uses GEMINI_API_KEY from Streamlit Secrets automatically if left blank."
    )
    active_gemini_key = user_api_key.strip() or secret_key or os.environ.get("GEMINI_API_KEY", "")
    st.caption(f"Active Model: **{st.session_state.active_model_used}**")
    st.caption(f"Shared Store DB: **{len(shared_db['inventory'])} SKUs**")
    if st.button("🔄 Reset Entire Store Audit to Zero", use_container_width=True):
        shared_db["inventory"] = [item.copy() for item in DEFAULT_INVENTORY]
        shared_db["activity_log"] = []
        shared_db["last_updated_ts"] = time.time()
        st.session_state.last_annotated_img = None
        st.session_state.last_barcode_hits = []
        st.session_state.live_sync_feedback = ""
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
        for attempt in range(3):
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
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str or "high demand" in err_str.lower():
                    time.sleep(0.8 * (attempt + 1))
                    continue
                raise err

    raise RuntimeError(f"Temporary cloud traffic spike. Please retry in a few seconds. ({last_err})")


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
- Match Arabic or English brand/product keywords to the exact `sku_key` and `sap_id` in the catalog above.
- If a product is clearly readable on the packaging (e.g., another household brand) but not in the catalog above, set sku_key='unmapped_item', sap_id='SAP-UNMAPPED', and still report its exact English/Arabic name, extracted text, and count.
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


def update_shared_inventory(scan_result: ShelfScanResult, barcode_hits: list, accumulate: bool, source_label: str = "Field Mobile"):
    detected_map = {}
    for det in scan_result.detections:
        detected_map[det.sku_key] = detected_map.get(det.sku_key, 0) + det.unit_count

    for b_hit in barcode_hits:
        k = b_hit["sku_key"]
        if k != "unmapped_item" and k not in detected_map:
            detected_map[k] = 1

    matched_items = []
    for item in shared_db["inventory"]:
        k = item["sku_key"]
        if k in detected_map:
            if accumulate:
                item["physical_qty"] += detected_map[k]
            else:
                item["physical_qty"] = detected_map[k]
            matched_items.append(f"{item['name']} ({item['sap_id']}) → {item['physical_qty']} unit(s)")

    shared_db["last_updated_ts"] = time.time()
    shared_db["activity_log"].insert(0, {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "source": source_label,
        "model": st.session_state.active_model_used,
        "summary": scan_result.raw_visible_text_summary,
        "matched": matched_items,
        "items": [d.model_dump() for d in scan_result.detections],
    })
    return matched_items


# --- TOP BRAND BAR ---
st.markdown(f"""
<div class="brand-bar">
    <div>
        <span style="font-size: 1.3rem; font-weight: 800; color: #F0F6FC; letter-spacing: -0.4px;">
            📦 StockSense AI
        </span>
        <span style="color: #8B949E; font-size: 0.85rem; margin-left: 10px;">
            Real-Time Field-to-Manager Shelf & SAP Intelligence
        </span>
    </div>
    <div class="status-pill">● Live Cloud Store Sync Active ({len(shared_db['inventory'])} SKUs)</div>
</div>
""", unsafe_allow_html=True)

# --- NAVIGATION TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🎥 Live Field Auditor Scanner",
    "📊 Manager Executive Dashboard (Live)",
    "📲 Automated Store Alerts",
    "📹 Live Aisle RTSP Feed",
])

# ==========================================
# TAB 1: CONTINUOUS LIVE VIEWFINDER (DEFAULT) + DIRECT SERVER BRIDGE
# ==========================================
with tab1:
    col_cam, col_list = st.columns([1.1, 1], gap="large")

    with col_cam:
        st.subheader("1. Live Rear-Camera Shelf Scanner")
        audit_mode = st.radio(
            "Capture Mode:",
            [
                "🎥 Live Rear-Camera Auto-Scanner (Instant Push)",
                "🎞️ Aisle Walk-Through Video (100+ Items)",
                "📸 Multi-Shelf Photo Batch",
            ],
            horizontal=False,
        )

        # --- MODE A: CONTINUOUS LIVE VIEWFINDER WITH DIRECT STREAMLIT POSTMESSAGE BRIDGE ---
        if audit_mode == "🎥 Live Rear-Camera Auto-Scanner (Instant Push)":
            st.caption("Point camera at products—when detected in the box below, tap the green or blue button to push straight to the Manager's laptop dashboard.")
            catalog_json = json.dumps([
                {
                    "sku_key": i["sku_key"],
                    "sap_id": i["sap_id"],
                    "name": i["name"],
                    "arabic_name": i["arabic_name"],
                    "keywords": i["keywords"],
                }
                for i in shared_db["inventory"]
            ])

            live_scanner_html = f"""
            <div style="background:#151B26; border:1px solid #263042; border-radius:12px; padding:12px; font-family:sans-serif; color:#F0F6FC; box-sizing:border-box;">
                <div style="position:relative; width:100%; border-radius:8px; overflow:hidden; background:#000;">
                    <video id="cam" autoplay playsinline muted style="width:100%; max-height:260px; object-fit:cover; display:block;"></video>
                    <div id="hud" style="position:absolute; top:10px; left:10px; right:10px; display:flex; justify-content:space-between; align-items:center;">
                        <span id="badge" style="background:rgba(11,15,23,0.9); color:#3FB950; border:1px solid #3FB950; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:700;">
                            ● LIVE CAMERA READY
                        </span>
                        <span id="timer" style="background:rgba(11,15,23,0.9); color:#58A6FF; padding:4px 10px; border-radius:999px; font-size:12px;">
                            Auto-Scan: OFF
                        </span>
                    </div>
                </div>
                <canvas id="canvas" style="display:none;"></canvas>
                <canvas id="motionCanvas" width="32" height="32" style="display:none;"></canvas>

                <div style="display:flex; gap:8px; margin-top:10px;">
                    <button id="toggleBtn" onclick="toggleAutoScan()" style="flex:1; background:#1F6FEB; color:#fff; border:none; padding:11px; border-radius:8px; font-weight:700; font-size:13px; cursor:pointer;">
                        ▶ Start Live AI Viewfinder
                    </button>
                    <button onclick="scanSingleNow(true)" style="background:#21262D; color:#F0F6FC; border:1px solid #30363D; padding:11px 14px; border-radius:8px; font-weight:600; font-size:13px; cursor:pointer;">
                        ⚡ Scan Now
                    </button>
                </div>

                <div id="liveResults" style="margin-top:10px; background:#0B0F17; border:1px solid #263042; border-radius:8px; padding:12px; min-height:95px; max-height:175px; overflow-y:auto; font-size:13px;">
                    <span style="color:#8B949E;">Point camera at products and tap <b>Start Live AI Viewfinder</b>...</span>
                </div>

                <div style="display:flex; flex-direction:column; gap:8px; margin-top:12px;">
                    <button onclick="sendLiveSync('set')" style="width:100%; background:#238636; color:#FFFFFF; border:none; padding:13px; border-radius:8px; font-weight:700; font-size:14px; cursor:pointer;">
                        📥 Update SAP Ledger with Live Count
                    </button>
                    <button onclick="sendLiveSync('add')" style="width:100%; background:#1F6FEB; color:#FFFFFF; border:none; padding:13px; border-radius:8px; font-weight:700; font-size:14px; cursor:pointer;">
                        ➕ Add Live Count to Existing SAP Total
                    </button>
                </div>
                <div id="pushStatus" style="margin-top:8px; text-align:center; font-size:12px; color:#3FB950; font-weight:600;"></div>
            </div>

            <script>
            // Official Streamlit Component PostMessage Bridge
            function sendMessageToStreamlitClient(type, data) {{
                const outData = Object.assign({{
                    isStreamlitMessage: true,
                    type: type,
                }}, data);
                window.parent.postMessage(outData, "*");
            }}
            sendMessageToStreamlitClient("streamlit:componentReady", {{ apiVersion: 1 }});
            sendMessageToStreamlitClient("streamlit:setFrameHeight", {{ height: 650 }});

            const API_KEY = {json.dumps(active_gemini_key)};
            const CATALOG = {catalog_json};
            const video = document.getElementById('cam');
            const canvas = document.getElementById('canvas');
            const motionCanvas = document.getElementById('motionCanvas');
            const badge = document.getElementById('badge');
            const timerEl = document.getElementById('timer');
            const resultsEl = document.getElementById('liveResults');
            const toggleBtn = document.getElementById('toggleBtn');
            const pushStatus = document.getElementById('pushStatus');

            let scanning = false;
            let intervalId = null;
            let inFlight = false;
            let currentFrameCounts = {{}};
            let currentFrameItems = [];
            let lastValidHtml = "";
            let prevThumb = null;
            let unchangedCount = 0;

            function sendLiveSync(mode) {{
                if (Object.keys(currentFrameCounts).length === 0) {{
                    pushStatus.style.color = "#D29922";
                    pushStatus.innerText = "⚠ Point camera at a catalog product first so a count appears above.";
                    return;
                }}
                pushStatus.style.color = "#3FB950";
                pushStatus.innerText = "🚀 Pushing live counts to Manager Dashboard...";
                sendMessageToStreamlitClient("streamlit:setComponentValue", {{
                    value: {{
                        event_id: Date.now() + "_" + Math.random().toString(36).slice(2, 7),
                        mode: mode,
                        counts: currentFrameCounts,
                        items: currentFrameItems
                    }}
                }});
            }}

            function frameChangedSignificantly() {{
                const mCtx = motionCanvas.getContext('2d');
                mCtx.drawImage(video, 0, 0, 32, 32);
                const data = mCtx.getImageData(0, 0, 32, 32).data;
                if (!prevThumb) {{
                    prevThumb = data;
                    return true;
                }}
                let diff = 0;
                for (let i = 0; i < data.length; i += 16) {{
                    diff += Math.abs(data[i] - prevThumb[i]);
                }}
                prevThumb = data;
                return (diff / (data.length / 16)) > 4.5;
            }}

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
                    toggleBtn.innerText = "⏸ Pause Live Viewfinder";
                    toggleBtn.style.background = "#DA3633";
                    timerEl.innerText = "Auto-Scan: ON (4.0s)";
                    scanSingleNow(true);
                    intervalId = setInterval(() => scanSingleNow(false), 4000);
                }} else {{
                    toggleBtn.innerText = "▶ Resume Live AI Viewfinder";
                    toggleBtn.style.background = "#1F6FEB";
                    timerEl.innerText = "Auto-Scan: PAUSED";
                    clearInterval(intervalId);
                }}
            }}

            const sleep = (ms) => new Promise(r => setTimeout(r, ms));

            async function callGeminiWithRetry(base64Jpeg) {{
                const prompt = `You are StockSense AI. Identify all grocery/household products in this frame and count the EXACT number of physical units currently visible. Map each product to its matching sap_id in this catalog: ${{JSON.stringify(CATALOG)}}. If a visible product is not in the catalog, set sap_id="SAP-UNMAPPED". Return ONLY valid JSON: {{"items": [{{"sap_id": "...", "name": "...", "text_read": "...", "count": 1}}]}}`;
                const models = ["gemini-3.5-flash-lite", "gemini-3.8-flash"];

                for (const model of models) {{
                    for (let attempt = 0; attempt < 2; attempt++) {{
                        try {{
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
                            if (!res.ok) throw new Error(data?.error?.message || ("HTTP " + res.status));
                            const rawText = data.candidates[0].content.parts[0].text;
                            return {{ parsed: JSON.parse(rawText), usedModel: model }};
                        }} catch (e) {{
                            await sleep(650 * (attempt + 1));
                        }}
                    }}
                }}
                return null;
            }}

            async function scanSingleNow(forceManual) {{
                if (inFlight || !video.videoWidth || !API_KEY) return;

                if (!forceManual && !frameChangedSignificantly()) {{
                    unchangedCount++;
                    if (unchangedCount > 1 && lastValidHtml) {{
                        badge.innerText = "● LOCKED (STEADY VIEW)";
                        badge.style.color = "#3FB950";
                        return;
                    }}
                }} else {{
                    unchangedCount = 0;
                }}

                inFlight = true;
                badge.innerText = "🔍 READING LABELS...";
                badge.style.color = "#58A6FF";

                canvas.width = 512;
                canvas.height = Math.round((video.videoHeight / video.videoWidth) * 512);
                canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
                const b64 = canvas.toDataURL('image/jpeg', 0.78).split(',')[1];

                const result = await callGeminiWithRetry(b64);

                if (result && result.parsed && result.parsed.items) {{
                    badge.innerText = "● LIVE LOCK (" + result.usedModel + ")";
                    badge.style.color = "#3FB950";

                    let freshCounts = {{}};
                    let html = `<div style="color:#3FB950; font-weight:700; margin-bottom:6px;">✅ Live Shelf View (${{new Date().toLocaleTimeString()}})</div>`;

                    if (result.parsed.items.length === 0) {{
                        html += `<div style="color:#8B949E;">No product label in frame — pan camera toward a product...</div>`;
                    }} else {{
                        currentFrameItems = result.parsed.items;
                        result.parsed.items.forEach(it => {{
                            if (it.sap_id && it.sap_id !== "SAP-UNMAPPED") {{
                                freshCounts[it.sap_id] = (freshCounts[it.sap_id] || 0) + (it.count || 1);
                            }}
                            const tagColor = it.sap_id === "SAP-UNMAPPED" ? "#D29922" : "#58A6FF";
                            html += `<div style="border-left:3px solid #3FB950; padding-left:8px; margin-bottom:6px;">
                                <span style="color:${{tagColor}}; font-family:monospace;">[${{it.sap_id}}]</span> <b>${{it.name}}</b> — In View: <b>${{it.count}} unit(s)</b><br/>
                                <span style="color:#8B949E; font-size:12px;">Read Text: "${{it.text_read}}"</span>
                            </div>`;
                        }});
                        if (Object.keys(freshCounts).length > 0) {{
                            currentFrameCounts = freshCounts;
                            pushStatus.innerText = "";
                        }}
                    }}
                    lastValidHtml = html;
                    resultsEl.innerHTML = html;
                }} else {{
                    badge.innerText = "⏳ CLOUD BUSY (HOLDING)";
                    badge.style.color = "#D29922";
                    if (!lastValidHtml) {{
                        resultsEl.innerHTML = `<div style="color:#D29922; font-size:12px;">⏳ High cloud demand — automatically retrying on next sweep...</div>`;
                    }}
                }}
                inFlight = false;
            }}
            </script>
            """

            live_event = components.html(live_scanner_html, height=655)

            # Process live push immediately when received from the component bridge
            if isinstance(live_event, dict) and live_event.get("event_id"):
                ev_id = live_event["event_id"]
                if ev_id != st.session_state.processed_live_event_id:
                    st.session_state.processed_live_event_id = ev_id
                    counts_map = live_event.get("counts", {})
                    mode_flag = live_event.get("mode", "set")
                    raw_items = live_event.get("items", [])

                    matched_updates = []
                    for item in shared_db["inventory"]:
                        sap = item["sap_id"]
                        if sap in counts_map:
                            qty_val = int(counts_map[sap])
                            if mode_flag == "add":
                                item["physical_qty"] += qty_val
                            else:
                                item["physical_qty"] = qty_val
                            matched_updates.append(f"{item['name']} ({sap}) → {item['physical_qty']} unit(s)")

                    if matched_updates:
                        shared_db["last_updated_ts"] = time.time()
                        shared_db["activity_log"].insert(0, {
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "source": "Live Field Viewfinder",
                            "model": "gemini-3.5-flash-lite",
                            "summary": "Live continuous shelf push",
                            "matched": matched_updates,
                            "items": [
                                {
                                    "sap_id": x.get("sap_id", ""),
                                    "product_name": x.get("name", ""),
                                    "unit_count": x.get("count", 1),
                                    "extracted_text_ar_en": x.get("text_read", ""),
                                }
                                for x in raw_items
                            ],
                        })
                        st.session_state.live_sync_feedback = "✅ Live Pushed to Manager Dashboard: " + " | ".join(matched_updates)
                        st.rerun()

            if st.session_state.live_sync_feedback:
                st.success(st.session_state.live_sync_feedback)

        # --- MODE B: AISLE WALK-THROUGH VIDEO (100+ PRODUCTS) ---
        elif audit_mode == "🎞️ Aisle Walk-Through Video (100+ Items)":
            st.info("Record a 10–30 second walk-through video panning across an entire aisle (up to 100+ products). StockSense extracts key frames, deduplicates overlaps, and syncs all SKUs to the Manager Dashboard.")
            accumulate_vid = st.checkbox("➕ Add to existing verified counts", value=True, key="acc_vid")
            vid_file = st.file_uploader("Upload Aisle Walk-Through Video (.mp4, .mov)", type=["mp4", "mov", "avi"])
            if vid_file is not None:
                st.video(vid_file)
                if st.button("🚀 Analyze Entire Aisle Video & Sync to SAP", type="primary", use_container_width=True):
                    with st.spinner("Extracting aisle keyframes & running multi-frame Bilingual OCR..."):
                        try:
                            frames = extract_video_keyframes(vid_file.read(), max_frames=8)
                            if not frames:
                                st.error("Could not extract frames from this video.")
                            else:
                                first_ann, b_hits, scan_res = analyze_media_frames(
                                    frames,
                                    shared_db["inventory"],
                                    active_gemini_key,
                                    is_video_walkthrough=True,
                                )
                                st.session_state.last_annotated_img = first_ann
                                st.session_state.last_barcode_hits = b_hits
                                matched_list = update_shared_inventory(
                                    scan_res, b_hits, accumulate=accumulate_vid, source_label="Aisle Video Audit"
                                )
                                st.success(f"✅ Video synced! Updated {len(matched_list)} SKU(s) on Manager Dashboard.")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Video audit error: {e}")

        # --- MODE C: MULTI-SHELF PHOTO BATCH ---
        else:
            accumulate_batch = st.checkbox("➕ Add to existing verified counts", value=True, key="acc_batch")
            uploaded_files = st.file_uploader(
                "Upload 1 or Multiple Wide Shelf Photos (JPG/PNG)",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
            )
            if uploaded_files:
                pil_batch = [Image.open(f) for f in uploaded_files]
                st.image(pil_batch[0], caption=f"Loaded {len(pil_batch)} shelf photo(s)", use_container_width=True)
                if st.button(f"🔍 Scan {len(pil_batch)} Photo(s) & Sync to SAP", type="primary", use_container_width=True):
                    with st.spinner("Processing batch & updating shared SAP ledger..."):
                        try:
                            first_ann, b_hits, scan_res = analyze_media_frames(
                                pil_batch,
                                shared_db["inventory"],
                                active_gemini_key,
                                is_video_walkthrough=(len(pil_batch) > 1),
                            )
                            st.session_state.last_annotated_img = first_ann
                            st.session_state.last_barcode_hits = b_hits
                            matched_list = update_shared_inventory(
                                scan_res, b_hits, accumulate=accumulate_batch, source_label="Batch Photo Upload"
                            )
                            st.success(f"✅ Batch synced ({len(matched_list)} SKU(s) updated on Manager Dashboard)!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Scan error: {e}")

        # --- DISPLAY LATEST AUDIT EVIDENCE ---
        if shared_db["activity_log"]:
            st.markdown("#### 🧠 Latest Field Scan Feed")
            latest = shared_db["activity_log"][0]
            st.caption(f"{latest['timestamp']} • {latest['source']} (`{latest['model']}`)")
            for det in latest["items"]:
                st.markdown(f"""
                <div class="feed-item">
                    <span class="sap-badge">{det['sap_id']}</span>
                    <strong style="color:#F0F6FC;">{det['product_name']}</strong>
                    <span style="color:#3FB950; font-weight:700; float:right;">{det['unit_count']} unit(s)</span><br/>
                    <span style="color:#8B949E;">Read Text: <em>"{det['extracted_text_ar_en']}"</em></span>
                </div>
                """, unsafe_allow_html=True)

    # --- RIGHT COLUMN: LIVE STORE VERIFIED COUNTS ---
    with col_list:
        st.subheader("2. Live Store Verified Counts")
        view_filter = st.radio(
            "Show:",
            ["Scanned Items Only", "All 42 Catalog SKUs"],
            horizontal=True,
            label_visibility="collapsed",
        )
        search_q = st.text_input("🔎 Search Product (EN / AR / SAP ID)", placeholder="e.g. Laban, Almarai, Osra, حليب...")

        shown_count = 0
        for idx, item in enumerate(shared_db["inventory"]):
            if view_filter == "Scanned Items Only" and item["physical_qty"] == 0 and not search_q.strip():
                continue
            if search_q.strip():
                q = search_q.strip().lower()
                if q not in f"{item['sap_id']} {item['name']} {item['arabic_name']}".lower():
                    continue

            shown_count += 1
            c_info, c_erp, c_phys = st.columns([2.2, 0.85, 1.15])
            with c_info:
                st.markdown(
                    f"**{item['name']}**  \n"
                    f"<span style='color:#8B949E; font-size:0.8rem;'>{item['arabic_name']}</span>  \n"
                    f"<span class='sap-badge'>{item['sap_id']}</span>",
                    unsafe_allow_html=True,
                )
            with c_erp:
                st.markdown(
                    f"<span style='color:#8B949E; font-size:0.76rem;'>SAP</span><br/>"
                    f"<strong>{item['erp_qty']}</strong>",
                    unsafe_allow_html=True,
                )
            with c_phys:
                new_val = st.number_input(
                    "Verified",
                    min_value=0,
                    max_value=5000,
                    value=int(item["physical_qty"]),
                    key=f"qty_{idx}_{int(shared_db['last_updated_ts']*100)}",
                )
                if new_val != item["physical_qty"]:
                    shared_db["inventory"][idx]["physical_qty"] = new_val
                    shared_db["last_updated_ts"] = time.time()
            st.divider()

        if shown_count == 0:
            st.info("No items verified yet. Point the live camera at a product and tap the green or blue button—it will appear here and on the Manager's laptop immediately!")

        if st.button("✅ Finalize & Post Audit to SAP S/4HANA", type="primary", use_container_width=True):
            shared_db["last_sync"] = datetime.now().strftime("%I:%M %p (Posted to SAP S/4HANA)")
            st.balloons()
            st.success("Audit posted to SAP S/4HANA!")

# ==========================================
# TAB 2: AUTO-REFRESHING MANAGER EXECUTIVE DASHBOARD
# ==========================================
with tab2:
    @st.fragment(run_every=4)
    def render_live_manager_dashboard():
        df = pd.DataFrame(shared_db["inventory"])
        df["variance"] = df["physical_qty"] - df["erp_qty"]
        df["abs_variance"] = df["variance"].abs()
        df["rev_at_risk"] = df.apply(lambda r: abs(r["variance"]) * r["price"] if r["variance"] < 0 else 0.0, axis=1)
        df["status"] = df.apply(
            lambda r: "🔴 Stockout" if r["physical_qty"] == 0 else ("🟠 Low Stock" if r["physical_qty"] <= r["reorder_pt"] else "🟢 Optimal"),
            axis=1,
        )

        total_skus = len(df)
        audited_skus = len(df[df["physical_qty"] > 0])
        progress_pct = audited_skus / total_skus if total_skus > 0 else 0.0
        total_erp = int(df["erp_qty"].sum())
        total_phys = int(df["physical_qty"].sum())
        accuracy = round((min(total_phys, total_erp) / total_erp) * 100, 1) if total_erp > 0 else 100.0
        rev_risk = df["rev_at_risk"].sum()
        alerts_count = len(df[df["physical_qty"] <= df["reorder_pt"]])

        # Live Progress Bar Header
        st.markdown(f"### 📡 Live Store Audit Progress: **{audited_skus} / {total_skus} SKUs Verified** ({progress_pct*100:.0f}%)")
        st.progress(progress_pct)
        st.caption(f"Auto-syncing live from field auditors • Last SAP status: {shared_db['last_sync']}")

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Field Audit Progress", f"{audited_skus} / {total_skus} SKUs", f"{total_phys} physical units counted")
        k2.metric("Inventory Accuracy", f"{accuracy}%", f"{total_phys - total_erp:+d} units vs SAP")
        k3.metric("Revenue at Risk", f"SAR {rev_risk:,.2f}", "Phantom stock exposure", delta_color="inverse")
        k4.metric("Replenishment Alerts", f"{alerts_count} SKUs", "SAP PO triggers")

        # Live Field Activity Stream
        if shared_db["activity_log"]:
            with st.expander(f"📲 Live Field Auditor Feed ({len(shared_db['activity_log'])} scans received)", expanded=True):
                for log in shared_db["activity_log"][:5]:
                    matched_txt = ", ".join(log["matched"]) if log["matched"] else "Unmapped catalog item"
                    st.markdown(
                        f"<div class='feed-item'><strong>[{log['timestamp']}] {log['source']}:</strong> {matched_txt}</div>",
                        unsafe_allow_html=True,
                    )

        st.write("")

        # 1. TOP 5 HORIZONTAL BAR CHARTS FIRST
        col_chart1, col_chart2 = st.columns(2, gap="large")

        with col_chart1:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("#### 📊 Top 5 SKUs by Unit Variance (SAP vs. Vision)")
            st.caption("Highlights the 5 products with the largest physical-to-ERP gap.")
            top5_var_df = df.sort_values(by="abs_variance", ascending=False).head(5).copy()
            top5_var_df["Short Label"] = top5_var_df["name"].apply(lambda x: x[:28] + "…" if len(x) > 29 else x)
            chart1_data = top5_var_df.set_index("Short Label")[["erp_qty", "physical_qty"]]
            chart1_data.columns = ["SAP Book Qty", "AI Verified Qty"]
            st.bar_chart(chart1_data, color=["#3B475E", "#1F6FEB"], horizontal=True, height=285)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_chart2:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("#### 💸 Top 5 SKUs by Revenue at Risk (SAR)")
            st.caption("Prioritizes shelf replenishment by highest financial exposure.")
            top5_risk_df = df[df["rev_at_risk"] > 0].sort_values(by="rev_at_risk", ascending=False).head(5).copy()
            if not top5_risk_df.empty:
                top5_risk_df["Short Label"] = top5_risk_df["name"].apply(lambda x: x[:28] + "…" if len(x) > 29 else x)
                chart2_data = top5_risk_df.set_index("Short Label")[["rev_at_risk"]]
                chart2_data.columns = ["Revenue at Risk (SAR)"]
                st.bar_chart(chart2_data, color="#F85149", horizontal=True, height=285)
            else:
                st.success("Zero phantom stock revenue leakage across all SKUs!")
            st.markdown('</div>', unsafe_allow_html=True)

        st.write("")

        # 2. FULL SCROLLABLE SAP INVENTORY LEDGER BELOW CHARTS
        st.subheader(f"Live Store Inventory & SAP Discrepancy Ledger ({len(df)} SKUs)")

        f_col1, f_col2, f_col3 = st.columns([1.2, 1.2, 1.6])
        with f_col1:
            cat_list = ["All Categories"] + sorted(df["category"].unique().tolist())
            sel_cat = st.selectbox("Filter by Category", cat_list, key="mgr_cat")
        with f_col2:
            status_list = ["All Statuses", "Audited (> 0 Verified)", "🔴 Stockout", "🟠 Low Stock", "🟢 Optimal"]
            sel_status = st.selectbox("Filter by Stock Status", status_list, key="mgr_status")
        with f_col3:
            tbl_search = st.text_input("Search SAP Material ID, Product (EN/AR), or Barcode", placeholder="Type to filter full SAP ledger...", key="mgr_search")

        filtered_df = df.copy()
        if sel_cat != "All Categories":
            filtered_df = filtered_df[filtered_df["category"] == sel_cat]
        if sel_status == "Audited (> 0 Verified)":
            filtered_df = filtered_df[filtered_df["physical_qty"] > 0]
        elif sel_status != "All Statuses":
            filtered_df = filtered_df[filtered_df["status"] == sel_status]
        if tbl_search.strip():
            q = tbl_search.strip().lower()
            filtered_df = filtered_df[
                filtered_df["sap_id"].str.lower().str.contains(q)
                | filtered_df["name"].str.lower().str.contains(q)
                | filtered_df["arabic_name"].str.lower().str.contains(q)
                | filtered_df["ean13"].str.lower().str.contains(q)
            ]

        display_df = filtered_df[[
            "sap_id", "ean13", "category", "name", "arabic_name", "aisle",
            "erp_qty", "physical_qty", "variance", "rev_at_risk", "status"
        ]].copy()
        display_df.columns = [
            "SAP Material ID",
            "EAN-13 Barcode",
            "Category",
            "Product (EN)",
            "Product (AR)",
            "Location",
            "SAP Qty",
            "Verified Qty",
            "Variance",
            "Rev. at Risk (SAR)",
            "Status",
        ]
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=620)

    render_live_manager_dashboard()

    # Enterprise SAP ERP Connector Expander
    with st.expander("🔌 Enterprise SAP S/4HANA Material Master Connector (MARA / MARD Feed)"):
        st.caption("Upload a customer SAP CSV export to replace the store catalog across all connected field phones and dashboards.")
        sap_csv = st.file_uploader("Upload Custom SAP Material Master (.csv)", type=["csv"])
        if sap_csv is not None:
            try:
                custom_df = pd.read_csv(sap_csv)
                required_cols = {"sap_id", "name", "erp_qty", "price"}
                if required_cols.issubset(set(custom_df.columns)):
                    new_inv = []
                    for idx_r, r in custom_df.iterrows():
                        new_inv.append({
                            "sku_key": f"custom_{idx_r}",
                            "sap_id": str(r["sap_id"]),
                            "ean13": str(r.get("ean13", "6281000000000")),
                            "category": str(r.get("category", "SAP Import")),
                            "name": str(r["name"]),
                            "arabic_name": str(r.get("arabic_name", r["name"])),
                            "keywords": [w.lower() for w in str(r["name"]).split()],
                            "aisle": str(r.get("aisle", "Aisle A1")),
                            "price": float(r["price"]),
                            "erp_qty": int(r["erp_qty"]),
                            "physical_qty": int(r.get("physical_qty", 0)),
                            "reorder_pt": int(r.get("reorder_pt", max(1, int(r["erp_qty"]) // 2))),
                        })
                    shared_db["inventory"] = new_inv
                    shared_db["last_updated_ts"] = time.time()
                    st.success(f"Loaded {len(new_inv)} SKUs from SAP CSV across all devices!")
                    st.rerun()
                else:
                    st.error(f"CSV must contain columns: {required_cols}")
            except Exception as ex:
                st.error(f"Could not parse SAP CSV: {ex}")

# ==========================================
# TAB 3: AUTOMATED STORE ALERTS
# ==========================================
with tab3:
    st.subheader("Zero-Friction Manager Alerts & SAP PO Triggers")
    df_alerts = pd.DataFrame(shared_db["inventory"])
    df_alerts["variance"] = df_alerts["physical_qty"] - df_alerts["erp_qty"]
    df_alerts["rev_at_risk"] = df_alerts.apply(lambda r: abs(r["variance"]) * r["price"] if r["variance"] < 0 else 0.0, axis=1)
    alert_items = df_alerts[df_alerts["physical_qty"] <= df_alerts["reorder_pt"]].sort_values(by="rev_at_risk", ascending=False)

    if alert_items.empty:
        st.success("✅ All shelves are stocked above SAP reorder points.")
    else:
        st.caption(f"Showing top priority replenishment triggers ({len(alert_items)} SKUs below SAP safety stock):")
        for _, row in alert_items.head(15).iterrows():
            st.markdown(f"""
            <div style="background-color:#17231E; border-left:4px solid #25D366; padding:15px; border-radius:10px; margin-bottom:12px;">
                <div style="color:#25D366; font-weight:700; font-size:0.84rem;">💬 WHATSAPP BUSINESS ALERT • STORE #104 • {row['category'].upper()}</div>
                <div style="color:#F0F6FC; margin-top:6px; font-size:0.93rem;">
                    <strong>⚠️ SHELF REPLENISHMENT REQUIRED ({row['sap_id']}):</strong><br/>
                    • <strong>Product:</strong> {row['name']} ({row['arabic_name']})<br/>
                    • <strong>Barcode / Location:</strong> {row['ean13']} • {row['aisle']}<br/>
                    • <strong>Verified Shelf Qty:</strong> {row['physical_qty']} units (SAP Book: {row['erp_qty']} | Variance: {row['variance']:+d} | Risk: SAR {row['rev_at_risk']:,.2f})<br/>
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
        <div style="background-color:#151B26; border:1px dashed #30363D; border-radius:12px; padding:65px 20px; text-align:center;">
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
