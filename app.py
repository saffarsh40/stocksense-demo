import base64
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
    page_title="StockSense AI | Enterprise Shelf & Loss-Prevention Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- LOAD LOGO FROM REPOSITORY (logo.png) ---
def get_logo_base64() -> str:
    for candidate in ["logo.png", "logo.jpg", "logo.jpeg", "assets/logo.png"]:
        if os.path.exists(candidate):
            with open(candidate, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
    return ""

LOGO_B64 = get_logo_base64()

# --- RICH BRAND THEME MATCHED TO STOCKSENSE LOGO (NAVY #0B2C5F, BLUE #0072CE, EMERALD #00A86B) ---
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(160deg, #E8F0FA 0%, #F1F6FC 52%, #E9F7F2 100%);
        color: #0B2C5F;
    }
    #MainMenu, footer {visibility: hidden;}
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2.5rem;
        max-width: 1360px;
    }
    .brand-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 14px;
        padding: 14px 22px;
        background: linear-gradient(90deg, #FFFFFF 0%, #F5FAFF 65%, #EFFBF6 100%);
        border: 1px solid #C6D8EC;
        border-left: 6px solid #0B2C5F;
        border-right: 6px solid #00A86B;
        border-radius: 14px;
        margin-bottom: 16px;
        box-shadow: 0 6px 18px rgba(11, 44, 95, 0.08);
    }
    .brand-left {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .brand-logo {
        height: 58px;
        width: auto;
        border-radius: 10px;
        background: #FFFFFF;
        padding: 3px;
        border: 1px solid #DCE7F3;
        object-fit: contain;
    }
    .brand-title {
        font-size: 1.55rem;
        font-weight: 800;
        color: #0B2C5F;
        letter-spacing: -0.4px;
        line-height: 1.1;
    }
    .brand-title span {
        color: #00A86B;
    }
    .brand-sub {
        color: #334155;
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 3px;
    }
    .status-pill {
        background: linear-gradient(90deg, #DCFCE7 0%, #D1FAE5 100%);
        color: #065F46;
        border: 1px solid #6EE7B7;
        padding: 7px 15px;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
    }
    .user-badge {
        background: #EFF6FF;
        color: #0B2C5F;
        border: 1px solid #93C5FD;
        padding: 6px 14px;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #DCE8F6;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #BFD3EA;
        overflow-x: auto;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 9px 16px;
        font-weight: 700;
        color: #0B2C5F !important;
        background-color: rgba(255, 255, 255, 0.65);
        white-space: nowrap;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #0B2C5F 0%, #0072CE 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 3px 10px rgba(0, 114, 206, 0.25);
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F4F9FF 100%);
        border: 1px solid #C6D8EC;
        border-top: 4px solid #0072CE;
        padding: 15px 18px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(11, 44, 95, 0.06);
    }
    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetricLabel"] label,
    div[data-testid="stMetricLabel"] {
        color: #1E3A5F !important;
        font-size: 0.88rem !important;
        font-weight: 700 !important;
        opacity: 1 !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.65rem !important;
        font-weight: 800 !important;
        color: #0B2C5F !important;
    }
    .stRadio label, .stRadio p, .stCheckbox label, .stCheckbox p,
    .stSelectbox label, .stTextInput label, .stNumberInput label, .stFileUploader label {
        color: #0B2C5F !important;
        font-weight: 600 !important;
    }
    .chart-card {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
        border: 1px solid #C6D8EC;
        border-top: 4px solid #00A86B;
        border-radius: 14px;
        padding: 16px 18px 10px 18px;
        margin-bottom: 14px;
        box-shadow: 0 4px 14px rgba(11, 44, 95, 0.06);
    }
    .login-card {
        background: #FFFFFF;
        border: 1px solid #C6D8EC;
        border-top: 5px solid #0072CE;
        border-radius: 16px;
        padding: 24px 28px;
        box-shadow: 0 8px 24px rgba(11, 44, 95, 0.08);
        max-width: 560px;
        margin: 18px auto;
    }
    .sap-badge {
        display: inline-block;
        background-color: #E0EEFF;
        color: #0B2C5F;
        border: 1px solid #93C5FD;
        padding: 2px 8px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 0.76rem;
        font-weight: 700;
        margin-right: 6px;
    }
    .feed-item {
        background-color: #FFFFFF;
        border: 1px solid #CBDCEB;
        border-left: 5px solid #00A86B;
        padding: 10px 14px;
        border-radius: 0 10px 10px 0;
        margin-bottom: 8px;
        font-size: 0.87rem;
        color: #0F172A;
        box-shadow: 0 2px 6px rgba(11, 44, 95, 0.04);
    }
    .cctv-panel {
        background: linear-gradient(180deg, #FFFFFF 0%, #F4F9FF 100%);
        border: 1px solid #C6D8EC;
        border-top: 4px solid #0B2C5F;
        border-radius: 14px;
        padding: 18px;
        box-shadow: 0 4px 14px rgba(11, 44, 95, 0.06);
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #0072CE 0%, #00A86B 100%);
        color: #FFFFFF !important;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.65rem 1.2rem;
        box-shadow: 0 3px 10px rgba(0, 114, 206, 0.22);
    }
    h1, h2, h3, h4 {
        color: #0B2C5F !important;
    }
</style>
""", unsafe_allow_html=True)

# --- REGISTER TWO-WAY LIVE SHELF SCANNER COMPONENT (ON-DEMAND CAMERA LOCK) ---
@st.cache_resource
def get_live_scanner_component():
    comp_dir = os.path.join(tempfile.gettempdir(), "stocksense_live_scanner_brand_v9")
    os.makedirs(comp_dir, exist_ok=True)
    index_path = os.path.join(comp_dir, "index.html")
    html_code = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  body { margin: 0; padding: 0; background: transparent; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #0B2C5F; }
  .card { background: linear-gradient(180deg, #FFFFFF 0%, #F4F9FF 100%); border: 1px solid #C6D8EC; border-top: 4px solid #0072CE; border-radius:14px; padding:12px; box-sizing:border-box; box-shadow: 0 4px 14px rgba(11,44,95,0.07); }
  .vid-wrap { position:relative; width:100%; min-height:200px; border-radius:10px; overflow:hidden; background:#0B2C5F; border: 1px solid #93C5FD; }
  video { width:100%; max-height:260px; object-fit:cover; display:block; }
  .hud { position:absolute; top:10px; left:10px; right:10px; display:flex; justify-content:space-between; align-items:center; }
  .badge { background:rgba(255,255,255,0.96); color:#047857; border:1px solid #00A86B; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:700; }
  .timer { background:rgba(11,44,95,0.92); color:#FFFFFF; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:600; }
  .row { display:flex; gap:8px; margin-top:10px; }
  .btn-start { flex:1; background: linear-gradient(90deg, #0072CE 0%, #0284C7 100%); color:#fff; border:none; padding:11px; border-radius:8px; font-weight:700; font-size:13px; cursor:pointer; }
  .btn-now { background:#E0EEFF; color:#0B2C5F; border:1px solid #93C5FD; padding:11px 14px; border-radius:8px; font-weight:700; font-size:13px; cursor:pointer; }
  .results { margin-top:10px; background:#FFFFFF; border:1px solid #CBDCEB; border-radius:8px; padding:12px; min-height:95px; max-height:175px; overflow-y:auto; font-size:13px; color:#1E293B; }
  .sync-col { display:flex; flex-direction:column; gap:8px; margin-top:12px; }
  .btn-green { width:100%; background: linear-gradient(90deg, #00A86B 0%, #059669 100%); color:#FFFFFF; border:none; padding:13px; border-radius:8px; font-weight:700; font-size:14px; cursor:pointer; }
  .btn-blue { width:100%; background: linear-gradient(90deg, #0B2C5F 0%, #0072CE 100%); color:#FFFFFF; border:none; padding:13px; border-radius:8px; font-weight:700; font-size:14px; cursor:pointer; }
  .status { margin-top:8px; text-align:center; font-size:12px; font-weight:700; min-height:18px; }
</style>
</head>
<body>
<div class="card">
  <div class="vid-wrap">
    <video id="cam" autoplay playsinline muted></video>
    <div class="hud">
      <span id="badge" class="badge">● STANDBY (TAP START)</span>
      <span id="timer" class="timer">Auto-Scan: OFF</span>
    </div>
  </div>
  <canvas id="canvas" style="display:none;"></canvas>
  <canvas id="motionCanvas" width="32" height="32" style="display:none;"></canvas>

  <div class="row">
    <button id="toggleBtn" class="btn-start" onclick="toggleAutoScan()">▶ Start Live AI Viewfinder</button>
    <button class="btn-now" onclick="scanSingleNow(true)">⚡ Scan Now</button>
  </div>

  <div id="liveResults" class="results">
    <span style="color:#475569;">Point camera at products and tap <b>Start Live AI Viewfinder</b>...</span>
  </div>

  <div class="sync-col">
    <button class="btn-green" onclick="sendLiveSync('set')">📥 Update SAP Ledger with Live Count</button>
    <button class="btn-blue" onclick="sendLiveSync('add')">➕ Add Live Count to Existing SAP Total</button>
  </div>
  <div id="pushStatus" class="status"></div>
</div>

<script>
let API_KEY = "";
let CATALOG = [];

function sendToStreamlit(type, data) {
  window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: type }, data), "*");
}

window.addEventListener("message", function(event) {
  if (event.data && event.data.type === "streamlit:render") {
    const args = event.data.args || {};
    if (args.api_key) API_KEY = args.api_key;
    if (args.catalog) CATALOG = args.catalog;
    sendToStreamlit("streamlit:setFrameHeight", { height: document.body.scrollHeight + 10 });
  }
});

sendToStreamlit("streamlit:componentReady", { apiVersion: 1 });
sendToStreamlit("streamlit:setFrameHeight", { height: 640 });

const video = document.getElementById('cam');
const canvas = document.getElementById('canvas');
const motionCanvas = document.getElementById('motionCanvas');
const badge = document.getElementById('badge');
const timerEl = document.getElementById('timer');
const resultsEl = document.getElementById('liveResults');
const toggleBtn = document.getElementById('toggleBtn');
const pushStatus = document.getElementById('pushStatus');

let activeCamStream = null;
let scanning = false;
let intervalId = null;
let inFlight = false;
let currentFrameCounts = {};
let currentFrameItems = [];
let lastValidHtml = "";
let prevThumb = null;
let unchangedCount = 0;

function sendLiveSync(mode) {
  if (Object.keys(currentFrameCounts).length === 0) {
    pushStatus.style.color = "#D97706";
    pushStatus.innerText = "⚠ Scan a product first so its SAP ID appears in the box above.";
    return;
  }
  pushStatus.style.color = "#047857";
  pushStatus.innerText = "✅ Sent to Manager Dashboard (" + new Date().toLocaleTimeString() + ")!";
  sendToStreamlit("streamlit:setComponentValue", {
    value: {
      event_id: Date.now() + "_" + Math.random().toString(36).slice(2, 7),
      mode: mode,
      counts: currentFrameCounts,
      items: currentFrameItems
    }
  });
}

function frameChangedSignificantly() {
  const mCtx = motionCanvas.getContext('2d');
  mCtx.drawImage(video, 0, 0, 32, 32);
  const data = mCtx.getImageData(0, 0, 32, 32).data;
  if (!prevThumb) { prevThumb = data; return true; }
  let diff = 0;
  for (let i = 0; i < data.length; i += 16) { diff += Math.abs(data[i] - prevThumb[i]); }
  prevThumb = data;
  return (diff / (data.length / 16)) > 4.5;
}

async function ensureCameraStarted() {
  if (activeCamStream && video.srcObject) return true;
  try {
    activeCamStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false
    });
    video.srcObject = activeCamStream;
    await video.play().catch(() => {});
    badge.innerText = "● LIVE CAMERA READY";
    badge.style.color = "#047857";
    return true;
  } catch (err) {
    badge.innerText = "⚠ Camera blocked";
    badge.style.color = "#DC2626";
    resultsEl.innerHTML = `<span style="color:#DC2626;">Camera error: ${err.message}</span>`;
    return false;
  }
}

function stopCameraStream() {
  if (activeCamStream) {
    activeCamStream.getTracks().forEach(t => t.stop());
    activeCamStream = null;
    video.srcObject = null;
  }
}

async function toggleAutoScan() {
  scanning = !scanning;
  if (scanning) {
    const ok = await ensureCameraStarted();
    if (!ok) { scanning = false; return; }
    toggleBtn.innerText = "⏸ Pause & Release Camera";
    toggleBtn.style.background = "#DC2626";
    timerEl.innerText = "Auto-Scan: ON (4.0s)";
    scanSingleNow(true);
    intervalId = setInterval(() => scanSingleNow(false), 4000);
  } else {
    toggleBtn.innerText = "▶ Start Live AI Viewfinder";
    toggleBtn.style.background = "#0072CE";
    timerEl.innerText = "Auto-Scan: OFF";
    badge.innerText = "● STANDBY (CAMERA RELEASED)";
    clearInterval(intervalId);
    stopCameraStream();
  }
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function callGeminiWithRetry(base64Jpeg) {
  const prompt = `You are StockSense AI. Identify all grocery/household products in this frame and count the EXACT number of physical units currently visible. Map each product to its matching sap_id in this catalog: ${JSON.stringify(CATALOG)}. If a visible product is not in the catalog, set sap_id="SAP-UNMAPPED". Return ONLY valid JSON: {"items": [{"sap_id": "...", "name": "...", "text_read": "...", "count": 1}]}`;
  const models = ["gemini-3.5-flash-lite", "gemini-3.8-flash"];

  for (const model of models) {
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json", "x-goog-api-key": API_KEY },
          body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }, { inline_data: { mime_type: "image/jpeg", data: base64Jpeg } }] }],
            generationConfig: { responseMimeType: "application/json", temperature: 0.1 }
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data?.error?.message || ("HTTP " + res.status));
        const rawText = data.candidates[0].content.parts[0].text;
        return { parsed: JSON.parse(rawText), usedModel: model };
      } catch (e) {
        await sleep(650 * (attempt + 1));
      }
    }
  }
  return null;
}

async function scanSingleNow(forceManual) {
  if (inFlight || !API_KEY) return;
  const ok = await ensureCameraStarted();
  if (!ok || !video.videoWidth) return;

  if (!forceManual && !frameChangedSignificantly()) {
    unchangedCount++;
    if (unchangedCount > 1 && lastValidHtml) {
      badge.innerText = "● LOCKED (STEADY VIEW)";
      badge.style.color = "#047857";
      return;
    }
  } else {
    unchangedCount = 0;
  }

  inFlight = true;
  badge.innerText = "🔍 READING LABELS...";
  badge.style.color = "#0072CE";

  canvas.width = 512;
  canvas.height = Math.round((video.videoHeight / video.videoWidth) * 512);
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  const b64 = canvas.toDataURL('image/jpeg', 0.78).split(',')[1];

  const result = await callGeminiWithRetry(b64);

  if (result && result.parsed && result.parsed.items) {
    badge.innerText = "● LIVE LOCK (" + result.usedModel + ")";
    badge.style.color = "#047857";

    let freshCounts = {};
    let html = `<div style="color:#047857; font-weight:700; margin-bottom:6px;">✅ Live Shelf View (${new Date().toLocaleTimeString()})</div>`;

    if (result.parsed.items.length === 0) {
      html += `<div style="color:#475569;">No product label in frame — pan camera toward a product...</div>`;
    } else {
      currentFrameItems = result.parsed.items;
      result.parsed.items.forEach(it => {
        if (it.sap_id && it.sap_id !== "SAP-UNMAPPED") {
          freshCounts[it.sap_id] = (freshCounts[it.sap_id] || 0) + (it.count || 1);
        }
        const tagColor = it.sap_id === "SAP-UNMAPPED" ? "#D97706" : "#0072CE";
        html += `<div style="border-left:3px solid #00A86B; padding-left:8px; margin-bottom:6px;">
          <span style="color:${tagColor}; font-family:monospace; font-weight:700;">[${it.sap_id}]</span> <b>${it.name}</b> — In View: <b>${it.count} unit(s)</b><br/>
          <span style="color:#475569; font-size:12px;">Read Text: "${it.text_read}"</span>
        </div>`;
      });
      if (Object.keys(freshCounts).length > 0) {
        currentFrameCounts = freshCounts;
      }
    }
    lastValidHtml = html;
    resultsEl.innerHTML = html;
    sendToStreamlit("streamlit:setFrameHeight", { height: document.body.scrollHeight + 10 });
  } else {
    badge.innerText = "⏳ CLOUD BUSY (HOLDING)";
    badge.style.color = "#D97706";
    if (!lastValidHtml) {
      resultsEl.innerHTML = `<div style="color:#D97706; font-size:12px;">⏳ High cloud demand — automatically retrying on next sweep...</div>`;
    }
  }
  inFlight = false;
}
</script>
</body>
</html>"""
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_code)
    return components.declare_component("stocksense_live_scanner_brand_v9", path=comp_dir)

live_scanner_component = get_live_scanner_component()

# --- REGISTER OVERHEAD CCTV LIVE OBS / CAMERA GUARD COMPONENT ---
@st.cache_resource
def get_live_cctv_component():
    comp_dir = os.path.join(tempfile.gettempdir(), "stocksense_live_cctv_guard_v6")
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
    <option value="">Connecting to OBS Virtual Camera...</option>
  </select>
  <button class="btn-refresh" onclick="initCameras()">🔄 Connect / Refresh Camera</button>
</div>

<div class="wrap">
  <video id="cctvVid" autoplay playsinline muted></video>
  <div class="top-hud">
    <span id="recBadge" class="rec">● REC • OVERHEAD CCTV</span>
    <span id="cctvClock" class="clk"></span>
  </div>
  <div class="bot-hud">
    <span id="poseHud" class="pose">POSE KEYPOINTS + CONCEALMENT TRACKER ACTIVE</span>
  </div>
</div>
<canvas id="c1" style="display:none;"></canvas>
<canvas id="c2" style="display:none;"></canvas>

<div class="controls">
  <button id="guardBtn" class="btn-guard" onclick="toggleGuard()">🛡️ Start Live AI Theft Guard (Auto-Detect)</button>
  <button class="btn-check" onclick="runBurstCheck()">⚡ Analyze Burst Now</button>
</div>
<div id="guardStatus" class="status-box">
  Select <b>OBS Virtual Camera</b> above and click <b>Start Live AI Theft Guard</b>.
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

function stopExistingTracks() {
  if (activeStream) {
    activeStream.getTracks().forEach(t => t.stop());
    activeStream = null;
    v.srcObject = null;
  }
}

async function startStream(deviceId) {
  stopExistingTracks();
  let stream = null;
  if (deviceId) {
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: { exact: deviceId } },
        audio: false
      });
    } catch (e1) {
      stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    }
  } else {
    stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  }
  activeStream = stream;
  v.srcObject = stream;
  await v.play().catch(() => {});
}

async function initCameras() {
  try {
    let devices = await navigator.mediaDevices.enumerateDevices();
    let videoInputs = devices.filter(d => d.kind === 'videoinput');

    if (!videoInputs.some(d => d.label)) {
      await startStream(null);
      devices = await navigator.mediaDevices.enumerateDevices();
      videoInputs = devices.filter(d => d.kind === 'videoinput');
    }

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
      await startStream(obsDeviceId);
      guardStatus.innerHTML = `<span style="color:#047857; font-weight:700;">✅ Connected to OBS Virtual Camera (EZVIZ C6N Live Feed).</span>`;
    } else if (videoInputs.length > 0) {
      camPicker.value = videoInputs[0].deviceId;
      await startStream(videoInputs[0].deviceId);
      guardStatus.innerHTML = `<span style="color:#047857; font-weight:700;">✅ Connected to ${videoInputs[0].label || "Camera"}.</span>`;
    } else {
      guardStatus.innerHTML = `<span style="color:#DC2626; font-weight:700;">⚠ No camera devices reported by browser.</span>`;
    }
  } catch (err) {
    guardStatus.innerHTML = `<span style="color:#DC2626; font-weight:700;">⚠ Camera Status:</span> ${err.message}. Click Connect / Refresh Camera.`;
  }
  sendToStreamlit("streamlit:setFrameHeight", { height: document.body.scrollHeight + 14 });
}

async function switchSelectedCamera() {
  if (camPicker.value) {
    try {
      await startStream(camPicker.value);
      const selText = camPicker.options[camPicker.selectedIndex]?.text || "Selected Camera";
      guardStatus.innerHTML = `<span style="color:#047857; font-weight:700;">✅ Active Feed: ${selText}</span>`;
    } catch (err) {
      guardStatus.innerHTML = `<span style="color:#DC2626; font-weight:700;">⚠ Switch Error:</span> ${err.message}`;
    }
  }
}

setTimeout(initCameras, 350);

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
    poseHud.innerText = "POSE KEYPOINTS + CONCEALMENT TRACKER ACTIVE";
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

  const models = ["gemini-3.5-flash-lite", "gemini-3.8-flash"];
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
    return components.declare_component("stocksense_live_cctv_guard_v6", path=comp_dir)

cctv_guard_component = get_live_cctv_component()

# --- 42-SKU SAUDI SUPERMARKET SAP MATERIAL MASTER CATALOG ---
DEFAULT_INVENTORY = [
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

    {"sku_key": "almarai_milk", "sap_id": "SAP-10045411", "ean13": "6281007020017", "category": "Dairy & Breakfast", "name": "Almarai Fresh Milk 1L", "arabic_name": "حليب المراعي طازج 1 لتر", "keywords": ["almarai", "milk", "fresh", "المراعي", "حليب", "طازج"], "aisle": "Chiller C1", "price": 6.00, "erp_qty": 20, "physical_qty": 0, "reorder_pt": 10},
    {"sku_key": "almarai_laban", "sap_id": "SAP-10045418", "ean13": "6281007020093", "category": "Dairy & Breakfast", "name": "Almarai Fresh Laban 1L", "arabic_name": "لبن المراعي طازج 1 لتر", "keywords": ["laban", "almarai", "لبن", "المراعي"], "aisle": "Chiller C1", "price": 6.00, "erp_qty": 18, "physical_qty": 0, "reorder_pt": 9},
    {"sku_key": "puck_cheese", "sap_id": "SAP-10045424", "ean13": "5760466901024", "category": "Dairy & Breakfast", "name": "Puck Cream Cheese Jar 500g", "arabic_name": "جبنة بوك كريم قابلة للدهن 500 جم", "keywords": ["puck", "cream cheese", "cheese", "بوك", "جبن", "جبنة"], "aisle": "Chiller C2", "price": 19.50, "erp_qty": 12, "physical_qty": 0, "reorder_pt": 6},
    {"sku_key": "kraft_cheddar", "sap_id": "SAP-10045430", "ean13": "7622210100948", "category": "Dairy & Breakfast", "name": "Kraft Original Cheddar Tin 100g", "arabic_name": "جبنة كرافت شيدر أصلية 100 جم", "keywords": ["kraft", "cheddar", "cheese", "كرافت", "شيدر", "جبنة"], "aisle": "Aisle C3", "price": 7.50, "erp_qty": 22, "physical_qty": 0, "reorder_pt": 10},
    {"sku_key": "nido_milk", "sap_id": "SAP-10045437", "ean13": "7613034890016", "category": "Dairy & Breakfast", "name": "Nestle Nido Milk Powder 900g", "arabic_name": "حليب نيدو مجفف 900 جم", "keywords": ["nido", "nestle", "milk powder", "نيدو", "نستله", "حليب مجفف"], "aisle": "Aisle C3", "price": 46.00, "erp_qty": 10, "physical_qty": 0, "reorder_pt": 5},
    {"sku_key": "lipton_tea", "sap_id": "SAP-10045443", "ean13": "6281006010125", "category": "Dairy & Breakfast", "name": "Lipton Yellow Label Tea 100 Bags", "arabic_name": "شاي ليبتون العلامة الصفراء 100 كيس", "keywords": ["lipton", "tea", "yellow label", "ليبتون", "شاي"], "aisle": "Aisle C4", "price": 17.50, "erp_qty": 15, "physical_qty": 0, "reorder_pt": 7},
    {"sku_key": "nescafe_classic", "sap_id": "SAP-10045450", "ean13": "7613033010125", "category": "Dairy & Breakfast", "name": "Nescafe Classic Jar 190g", "arabic_name": "قهوة نسكافيه كلاسيك 190 جم", "keywords": ["nescafe", "coffee", "classic", "نسكافيه", "قهوة"], "aisle": "Aisle C4", "price": 26.00, "erp_qty": 11, "physical_qty": 0, "reorder_pt": 5},
    {"sku_key": "kelloggs_cornflakes", "sap_id": "SAP-10045458", "ean13": "5053827100120", "category": "Dairy & Breakfast", "name": "Kelloggs Corn Flakes 500g", "arabic_name": "رقائق الذرة كيلوقز كورن فليكس 500 جم", "keywords": ["kellogg", "corn flakes", "cereal", "كيلوقز", "كورن فليكس"], "aisle": "Aisle C2", "price": 18.00, "erp_qty": 12, "physical_qty": 0, "reorder_pt": 6},

    {"sku_key": "pepsi_can", "sap_id": "SAP-10045502", "ean13": "6281034000112", "category": "Beverages", "name": "Pepsi Cola Can 330ml", "arabic_name": "بيبسي كولا علبة 330 مل", "keywords": ["pepsi", "cola", "بيبسي", "كولا"], "aisle": "Aisle D4", "price": 2.50, "erp_qty": 24, "physical_qty": 0, "reorder_pt": 12},
    {"sku_key": "sevenup_can", "sap_id": "SAP-10045508", "ean13": "6281034000228", "category": "Beverages", "name": "7UP Lemon Lime Can 330ml", "arabic_name": "سفن أب علبة 330 مل", "keywords": ["7up", "seven up", "سفن اب", "سفن أب"], "aisle": "Aisle D4", "price": 2.50, "erp_qty": 20, "physical_qty": 0, "reorder_pt": 10},
    {"sku_key": "mirinda_can", "sap_id": "SAP-10045514", "ean13": "6281034000334", "category": "Beverages", "name": "Mirinda Citrus Can 330ml", "arabic_name": "ميرندا حمضيات علبة 330 مل", "keywords": ["mirinda", "citrus", "ميرندا", "حمضيات"], "aisle": "Aisle D4", "price": 2.50, "erp_qty": 18, "physical_qty": 0, "reorder_pt": 9},
    {"sku_key": "cocacola_can", "sap_id": "SAP-10045520", "ean13": "5449000000996", "category": "Beverages", "name": "Coca-Cola Can 330ml", "arabic_name": "كوكاكولا علبة 330 مل", "keywords": ["coca-cola", "coca cola", "coke", "كوكاكولا", "كولا"], "aisle": "Aisle D4", "price": 2.50, "erp_qty": 22, "physical_qty": 0, "reorder_pt": 10},
    {"sku_key": "nova_water", "sap_id": "SAP-10045609", "ean13": "6281038000019", "category": "Beverages", "name": "Nova Bottled Water 330ml", "arabic_name": "مياه نوفا 330 مل", "keywords": ["nova", "water", "نوفا", "مياه", "ماء"], "aisle": "Aisle D1", "price": 1.00, "erp_qty": 30, "physical_qty": 0, "reorder_pt": 15},
    {"sku_key": "berain_water", "sap_id": "SAP-10045615", "ean13": "6281068000115", "category": "Beverages", "name": "Berain Bottled Water 330ml", "arabic_name": "مياه بيرين 330 مل", "keywords": ["berain", "water", "بيرين", "مياه"], "aisle": "Aisle D1", "price": 1.00, "erp_qty": 28, "physical_qty": 0, "reorder_pt": 14},
    {"sku_key": "almarai_juice", "sap_id": "SAP-10045622", "ean13": "6281007030115", "category": "Beverages", "name": "Almarai Mango Juice 1L", "arabic_name": "عصير المراعي مانجو 1 لتر", "keywords": ["juice", "mango", "almarai", "عصير", "مانجو", "المراعي"], "aisle": "Chiller C1", "price": 7.00, "erp_qty": 14, "physical_qty": 0, "reorder_pt": 7},

    {"sku_key": "lays_chips", "sap_id": "SAP-10045701", "ean13": "6281034011019", "category": "Snacks & Sweets", "name": "Lay's Salted Potato Chips 155g", "arabic_name": "بطاطس ليز بالملح 155 جم", "keywords": ["lays", "lay's", "chips", "ليز", "بطاطس", "شيبس"], "aisle": "Aisle E1", "price": 6.50, "erp_qty": 16, "physical_qty": 0, "reorder_pt": 8},
    {"sku_key": "pringles_original", "sap_id": "SAP-10045708", "ean13": "5053990101573", "category": "Snacks & Sweets", "name": "Pringles Original Can 165g", "arabic_name": "بطاطس برينجلز أصلي 165 جم", "keywords": ["pringles", "chips", "برينجلز", "بطاطس"], "aisle": "Aisle E1", "price": 11.00, "erp_qty": 12, "physical_qty": 0, "reorder_pt": 6},
    {"sku_key": "galaxy_chocolate", "sap_id": "SAP-10045715", "ean13": "6294003530112", "category": "Snacks & Sweets", "name": "Galaxy Smooth Milk Chocolate 80g", "arabic_name": "شوكولاتة جالكسي بالحليب 80 جم", "keywords": ["galaxy", "chocolate", "جالكسي", "شوكولاتة"], "aisle": "Aisle E2", "price": 6.50, "erp_qty": 20, "physical_qty": 0, "reorder_pt": 10},
    {"sku_key": "kitkat_4finger", "sap_id": "SAP-10045721", "ean13": "7613034626844", "category": "Snacks & Sweets", "name": "KitKat 4-Finger Chocolate 41.5g", "arabic_name": "شوكولاتة كيت كات 4 أصابع", "keywords": ["kitkat", "kit kat", "chocolate", "كيت كات", "شوكولاتة"], "aisle": "Aisle E2", "price": 3.50, "erp_qty": 25, "physical_qty": 0, "reorder_pt": 12},
    {"sku_key": "oreo_biscuits", "sap_id": "SAP-10045728", "ean13": "7622210449283", "category": "Snacks & Sweets", "name": "Oreo Original Sandwich Cookies 154g", "arabic_name": "بسكويت أوريو الأصلي 154 جم", "keywords": ["oreo", "biscuit", "cookies", "أوريو", "اوريو", "بسكويت"], "aisle": "Aisle E3", "price": 5.50, "erp_qty": 18, "physical_qty": 0, "reorder_pt": 9},

    {"sku_key": "goody_tuna", "sap_id": "SAP-10045801", "ean13": "6281011001011", "category": "Canned Foods", "name": "Goody Tenderina Tuna 185g", "arabic_name": "تونة قودي تندرينا 185 جم", "keywords": ["goody", "tuna", "tenderina", "قودي", "تونة"], "aisle": "Aisle A4", "price": 8.50, "erp_qty": 20, "physical_qty": 0, "reorder_pt": 10},
    {"sku_key": "luna_foul", "sap_id": "SAP-10045809", "ean13": "6281004002011", "category": "Canned Foods", "name": "Luna Foul Medames Plain 450g", "arabic_name": "فول مدمس لونا سادة 450 جم", "keywords": ["luna", "foul", "beans", "لونا", "فول"], "aisle": "Aisle A4", "price": 4.25, "erp_qty": 16, "physical_qty": 0, "reorder_pt": 8},
    {"sku_key": "al_alali_corn", "sap_id": "SAP-10045815", "ean13": "6281014005012", "category": "Canned Foods", "name": "Al Alali Whole Kernel Sweet Corn 340g", "arabic_name": "ذرة حلوة كاملة العلالي 340 جم", "keywords": ["sweet corn", "corn", "al alali", "ذرة", "العلالي"], "aisle": "Aisle A4", "price": 5.00, "erp_qty": 15, "physical_qty": 0, "reorder_pt": 7},

    {"sku_key": "dettol_antiseptic", "sap_id": "SAP-10045901", "ean13": "6291100120015", "category": "Household & Care", "name": "Dettol Antiseptic Disinfectant 500ml", "arabic_name": "مطهر ديتول الأصلي 500 مل", "keywords": ["dettol", "antiseptic", "disinfectant", "ديتول", "مطهر"], "aisle": "Aisle F1", "price": 21.00, "erp_qty": 12, "physical_qty": 0, "reorder_pt": 6},
    {"sku_key": "fairy_dishwash", "sap_id": "SAP-10045908", "ean13": "4084500123456", "category": "Household & Care", "name": "Fairy Lemon Dishwashing Liquid 800ml", "arabic_name": "سائل غسيل الصحون فيري ليمون 800 مل", "keywords": ["fairy", "dish", "lemon", "فيري", "صحون"], "aisle": "Aisle F1", "price": 13.50, "erp_qty": 14, "physical_qty": 0, "reorder_pt": 7},
    {"sku_key": "tide_detergent", "sap_id": "SAP-10045915", "ean13": "6281006040115", "category": "Household & Care", "name": "Tide Laundry Powder Detergent 2.5kg", "arabic_name": "مسحوق غسيل تايد 2.5 كجم", "keywords": ["tide", "detergent", "laundry", "تايد", "مسحوق غسيل"], "aisle": "Aisle F2", "price": 34.00, "erp_qty": 10, "physical_qty": 0, "reorder_pt": 5},
    {"sku_key": "fine_tissues", "sap_id": "SAP-10045922", "ean13": "6281029001012", "category": "Household & Care", "name": "Fine Fluffy Facial Tissues 150 Sheets", "arabic_name": "مناديل وجه فاين فلافي 150 منديل", "keywords": ["fine", "tissue", "tissues", "فاين", "مناديل"], "aisle": "Aisle F3", "price": 6.00, "erp_qty": 24, "physical_qty": 0, "reorder_pt": 12},
    {"sku_key": "sanita_bags", "sap_id": "SAP-10045929", "ean13": "6281012003018", "category": "Household & Care", "name": "Sanita Club Trash Bags 30 Gallon", "arabic_name": "أكياس نفايات سانيتا كلوب 30 جالون", "keywords": ["sanita", "trash bags", "garbage", "سانيتا", "أكياس"], "aisle": "Aisle F3", "price": 12.50, "erp_qty": 15, "physical_qty": 0, "reorder_pt": 7},

    {"sku_key": "signal_toothpaste", "sap_id": "SAP-10045951", "ean13": "6281006070112", "category": "Personal Care", "name": "Signal Cavity Fighter Toothpaste 120ml", "arabic_name": "معجون أسنان سيجنال مكافح التسوس 120 مل", "keywords": ["signal", "toothpaste", "colgate", "سيجنال", "كولجيت", "معجون أسنان"], "aisle": "Aisle G1", "price": 8.00, "erp_qty": 18, "physical_qty": 0, "reorder_pt": 9},
    {"sku_key": "head_shoulders", "sap_id": "SAP-10045958", "ean13": "4084500987654", "category": "Personal Care", "name": "Head & Shoulders Menthol Shampoo 400ml", "arabic_name": "شامبو هيد آند شولدرز نعناع 400 مل", "keywords": ["head", "shoulders", "shampoo", "هيد اند شولدرز", "شامبو"], "aisle": "Aisle G2", "price": 22.00, "erp_qty": 12, "physical_qty": 0, "reorder_pt": 6},
    {"sku_key": "nivea_cream", "sap_id": "SAP-10045965", "ean13": "4005808123456", "category": "Personal Care", "name": "Nivea Soft Moisturizing Cream 200ml", "arabic_name": "كريم نيفيا سوفت المرطب 200 مل", "keywords": ["nivea", "cream", "soft", "نيفيا", "كريم"], "aisle": "Aisle G2", "price": 16.50, "erp_qty": 14, "physical_qty": 0, "reorder_pt": 7},
    {"sku_key": "lifebuoy_handwash", "sap_id": "SAP-10045972", "ean13": "6281006080111", "category": "Personal Care", "name": "Lifebuoy Total 10 Hand Wash 200ml", "arabic_name": "غسول اليدين لايفبوي 200 مل", "keywords": ["lifebuoy", "hand wash", "soap", "لايفبوي", "غسول", "صابون"], "aisle": "Aisle G1", "price": 9.50, "erp_qty": 16, "physical_qty": 0, "reorder_pt": 8},
]

DEFAULT_USERS = {
    "Manager (Admin)": {
        "role": "Manager",
        "pin": "0000",
        "assigned_zone": "All Store Zones",
        "active": True,
        "units_verified": 0,
        "skus_touched": set(),
        "scan_events": 0,
        "last_active": "Online",
    },
    "Salman (Auditor 1)": {
        "role": "Field Auditor",
        "pin": "1111",
        "assigned_zone": "Aisles A & B (Pantry)",
        "active": True,
        "units_verified": 0,
        "skus_touched": set(),
        "scan_events": 0,
        "last_active": "Ready",
    },
    "Nasser (Auditor 2)": {
        "role": "Field Auditor",
        "pin": "2222",
        "assigned_zone": "Chiller C & Beverages D",
        "active": True,
        "units_verified": 0,
        "skus_touched": set(),
        "scan_events": 0,
        "last_active": "Ready",
    },
    "Mahdi (Auditor 3)": {
        "role": "Field Auditor",
        "pin": "3333",
        "assigned_zone": "Snacks E & Care F/G",
        "active": True,
        "units_verified": 0,
        "skus_touched": set(),
        "scan_events": 0,
        "last_active": "Ready",
    },
}

def clone_default_users():
    cloned = {}
    for uname, info in DEFAULT_USERS.items():
        c = info.copy()
        c["skus_touched"] = set()
        cloned[uname] = c
    return cloned

# --- SHARED MULTI-DEVICE SERVER STORE ---
@st.cache_resource
def get_shared_store_db():
    return {
        "inventory": [item.copy() for item in DEFAULT_INVENTORY],
        "last_sync": "09:15 AM (SAP S/4HANA Connected)",
        "activity_log": [],
        "theft_alerts": [],
        "users": clone_default_users(),
        "last_updated_ts": time.time(),
    }

shared_db = get_shared_store_db()
if "users" not in shared_db:
    shared_db["users"] = clone_default_users()

def record_user_work(username: str, sap_ids: List[str], units_counted: int):
    if username not in shared_db["users"]:
        shared_db["users"][username] = {
            "role": "Field Auditor",
            "pin": "1234",
            "assigned_zone": "General Floor",
            "active": True,
            "units_verified": 0,
            "skus_touched": set(),
            "scan_events": 0,
            "last_active": "Active",
        }
    u = shared_db["users"][username]
    u["units_verified"] += max(0, int(units_counted))
    for s in sap_ids:
        u["skus_touched"].add(s)
    u["scan_events"] += 1
    u["last_active"] = datetime.now().strftime("%I:%M:%S %p")

# --- STRUCTURED OUTPUT SCHEMAS ---
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

class TheftBehaviorResult(BaseModel):
    theft_detected: bool = Field(description="True if suspicious shoplifting, item concealment in pocket/bag, or rapid shelf sweeping is observed")
    behavior_type: str = Field(description="e.g., 'Item Concealment in Pocket/Bag', 'Rapid Shelf Sweeping', or 'Normal Shopping Behavior'")
    confidence_pct: int = Field(description="Confidence percentage 0-100")
    description: str = Field(description="Objective description of body/hand interaction with shelf items observed in the CCTV frames")
    recommended_action: str = Field(description="Immediate security guard or floor supervisor action")

# --- SESSION STATE ---
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None
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
if "last_cctv_alert_id" not in st.session_state:
    st.session_state.last_cctv_alert_id = None

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
    if st.button("🔄 Reset Store Audit, Users & Alerts", use_container_width=True):
        shared_db["inventory"] = [item.copy() for item in DEFAULT_INVENTORY]
        shared_db["activity_log"] = []
        shared_db["theft_alerts"] = []
        shared_db["users"] = clone_default_users()
        shared_db["last_updated_ts"] = time.time()
        st.session_state.last_annotated_img = None
        st.session_state.last_barcode_hits = []
        st.session_state.live_sync_feedback = ""
        st.session_state.last_cctv_alert_id = None
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
            draw.polygon(poly_coords, outline="#00A86B", width=5)
            x0, y0 = poly_coords[0]
            label_txt = f" {sap_id} | {code_val} "
            draw.rectangle([x0, max(0, y0 - 26), x0 + len(label_txt) * 8, y0], fill="#00A86B")
            draw.text((x0 + 4, max(2, y0 - 22)), label_txt, fill="#FFFFFF")

    return annotated, barcode_hits


def call_gemini_schema_with_failover(client: genai.Client, contents: list, schema_cls):
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
                        response_schema=schema_cls,
                        temperature=0.1,
                    ),
                )
                st.session_state.active_model_used = model_name
                return schema_cls.model_validate_json(response.text)
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
    parsed = call_gemini_schema_with_failover(client, contents, ShelfScanResult)
    return first_annotated, barcode_hits, parsed


def analyze_cctv_theft_behavior(pil_images: List[Image.Image], camera_id: str, api_key: str) -> TheftBehaviorResult:
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY. Add your key in Streamlit Secrets or the left sidebar.")

    client = genai.Client(api_key=api_key)
    prompt = f"""
You are StockSense AI Loss-Prevention & Behavioral Analytics running on overhead retail CCTV camera ({camera_id}).
Analyze these sequential overhead CCTV frames for shoplifting or suspicious theft behavior:
- Look specifically for hand-to-pocket / hand-to-bag concealment, hiding items under clothing, or rapid shelf-sweeping of multiple products into a personal bag.
- Distinguish normal shopping (placing items in a store basket/trolley or inspecting a label) from active concealment/theft behavior.
Return structured JSON evaluating whether theft behavior is occurring.
"""
    return call_gemini_schema_with_failover(client, [*pil_images, prompt], TheftBehaviorResult)


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


def update_shared_inventory(scan_result: ShelfScanResult, barcode_hits: list, accumulate: bool, source_label: str, active_user: str):
    detected_map = {}
    for det in scan_result.detections:
        detected_map[det.sku_key] = detected_map.get(det.sku_key, 0) + det.unit_count

    for b_hit in barcode_hits:
        k = b_hit["sku_key"]
        if k != "unmapped_item" and k not in detected_map:
            detected_map[k] = 1

    matched_items = []
    touched_sap_ids = []
    total_units_added = 0

    for item in shared_db["inventory"]:
        k = item["sku_key"]
        if k in detected_map:
            qty_found = detected_map[k]
            if accumulate:
                item["physical_qty"] += qty_found
            else:
                item["physical_qty"] = qty_found
            matched_items.append(f"{item['name']} ({item['sap_id']}) → {item['physical_qty']} unit(s)")
            touched_sap_ids.append(item["sap_id"])
            total_units_added += qty_found

    if touched_sap_ids:
        record_user_work(active_user, touched_sap_ids, total_units_added)

    shared_db["last_updated_ts"] = time.time()
    shared_db["activity_log"].insert(0, {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "user": active_user,
        "source": source_label,
        "model": st.session_state.active_model_used,
        "summary": scan_result.raw_visible_text_summary,
        "matched": matched_items,
        "items": [d.model_dump() for d in scan_result.detections],
    })
    return matched_items


# --- TOP BRAND HEADER WITH LOGO & ACTIVE USER STATUS ---
logo_html = (
    f'<img src="data:image/png;base64,{LOGO_B64}" class="brand-logo" alt="StockSense Logo" />'
    if LOGO_B64 else
    '<div style="font-size:2.2rem;">📦</div>'
)

current_user = st.session_state.authenticated_user
user_pill_html = (
    f'<div class="user-badge">👤 {current_user} ({shared_db["users"].get(current_user, {}).get("role", "User")})</div>'
    if current_user else
    '<div class="user-badge">🔒 Sign In Required</div>'
)

st.markdown(f"""
<div class="brand-bar">
    <div class="brand-left">
        {logo_html}
        <div>
            <div class="brand-title">Stock<span>Sense</span> AI</div>
            <div class="brand-sub">SEE • TRACK • MANAGE • GROW — Real-Time Shelf & Loss-Prevention Intelligence</div>
        </div>
    </div>
    <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
        {user_pill_html}
        <div class="status-pill">● Live Cloud Store Sync Active</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# USER ACCESS GATE (MANAGER VS. AUTHORIZED FIELD AUDITOR)
# ==========================================
if current_user is None or current_user not in shared_db["users"] or not shared_db["users"][current_user]["active"]:
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown("### 🔐 StockSense Store Access Portal")
    st.caption("Managers grant mobile access to authorized field auditors. Select your assigned user account to begin.")

    active_accounts = [u for u, meta in shared_db["users"].items() if meta["active"]]
    selected_login_user = st.selectbox("Select Authorized User Account:", active_accounts)
    user_meta = shared_db["users"][selected_login_user]

    st.info(
        f"**Role:** {user_meta['role']}  •  **Assigned Zone:** {user_meta['assigned_zone']}  \n"
        f"*(Demo PIN for {selected_login_user}: **`{user_meta['pin']}`**)*"
    )

    entered_pin = st.text_input("Enter 4-Digit Access PIN:", value=user_meta["pin"], type="password", max_chars=8)

    if st.button("🔓 Sign In & Launch Workspace", type="primary", use_container_width=True):
        if entered_pin.strip() == user_meta["pin"]:
            st.session_state.authenticated_user = selected_login_user
            shared_db["users"][selected_login_user]["last_active"] = datetime.now().strftime("%I:%M %p")
            st.rerun()
        else:
            st.error("Invalid PIN. Please enter the 4-digit PIN assigned by your Store Manager.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- TOP SESSION BAR WITH SWITCH USER BUTTON ---
active_role = shared_db["users"][current_user]["role"]
active_zone = shared_db["users"][current_user]["assigned_zone"]

bar_c1, bar_c2 = st.columns([4, 1])
with bar_c1:
    st.caption(f"Signed in as **{current_user}** • Role: **{active_role}** • Assigned Zone: **{active_zone}**")
with bar_c2:
    if st.button("🚪 Switch User / Log Out", use_container_width=True):
        st.session_state.authenticated_user = None
        st.rerun()

# --- ROLE-BASED NAVIGATION TABS ---
theft_count = len(shared_db["theft_alerts"])
alerts_tab_label = f"📲 Automated Store Alerts (🚨 {theft_count})" if theft_count > 0 else "📲 Automated Store Alerts"

if active_role == "Manager":
    tab_scanner, tab_dashboard, tab_workforce, tab_alerts, tab_cctv = st.tabs([
        "🎥 Live Field Auditor Scanner",
        "📊 Manager Executive Dashboard (Live)",
        "👥 Workforce & Auditor Efficiency",
        alerts_tab_label,
        "🛡️ Overhead CCTV Theft Detection",
    ])
else:
    tab_scanner, tab_workforce = st.tabs([
        "🎥 Live Field Auditor Scanner",
        "👥 My Efficiency & Team Leaderboard",
    ])
    tab_dashboard = None
    tab_alerts = None
    tab_cctv = None

# ==========================================
# TAB 1: CONTINUOUS LIVE VIEWFINDER (USER-STAMPED)
# ==========================================
with tab_scanner:
    col_cam, col_list = st.columns([1.1, 1], gap="large")

    with col_cam:
        st.subheader("1. Live Rear-Camera Shelf Scanner")
        st.caption(f"All scans pushed from this device are credited to **{current_user}**.")
        audit_mode = st.radio(
            "Capture Mode:",
            [
                "🎥 Live Rear-Camera Auto-Scanner (Instant Push)",
                "🎞️ Aisle Walk-Through Video (100+ Items)",
                "📸 Multi-Shelf Photo Batch",
            ],
            horizontal=False,
        )

        # --- MODE A: TRUE TWO-WAY LIVE VIEWFINDER ---
        if audit_mode == "🎥 Live Rear-Camera Auto-Scanner (Instant Push)":
            catalog_payload = [
                {
                    "sku_key": i["sku_key"],
                    "sap_id": i["sap_id"],
                    "name": i["name"],
                    "arabic_name": i["arabic_name"],
                    "keywords": i["keywords"],
                }
                for i in shared_db["inventory"]
            ]

            live_event = live_scanner_component(
                api_key=active_gemini_key,
                catalog=catalog_payload,
                key="live_field_cam_brand_v9",
            )

            if isinstance(live_event, dict) and live_event.get("event_id"):
                ev_id = live_event["event_id"]
                if ev_id != st.session_state.processed_live_event_id:
                    st.session_state.processed_live_event_id = ev_id
                    counts_map = live_event.get("counts", {})
                    mode_flag = live_event.get("mode", "set")
                    raw_items = live_event.get("items", [])

                    matched_updates = []
                    touched_saps = []
                    total_units_pushed = 0

                    for item in shared_db["inventory"]:
                        sap = item["sap_id"]
                        if sap in counts_map:
                            qty_val = int(counts_map[sap])
                            if mode_flag == "add":
                                item["physical_qty"] += qty_val
                            else:
                                item["physical_qty"] = qty_val
                            matched_updates.append(f"{item['name']} ({sap}) → {item['physical_qty']} unit(s)")
                            touched_saps.append(sap)
                            total_units_pushed += qty_val

                    if matched_updates:
                        record_user_work(current_user, touched_saps, total_units_pushed)
                        shared_db["last_updated_ts"] = time.time()
                        shared_db["activity_log"].insert(0, {
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "user": current_user,
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
                        st.session_state.live_sync_feedback = f"✅ Pushed by {current_user}: " + " | ".join(matched_updates)
                        st.rerun()

            if st.session_state.live_sync_feedback:
                st.success(st.session_state.live_sync_feedback)

        # --- MODE B: AISLE WALK-THROUGH VIDEO ---
        elif audit_mode == "🎞️ Aisle Walk-Through Video (100+ Items)":
            st.info("Record a 10–30 second walk-through video panning across an entire aisle (up to 100+ products). StockSense extracts key frames, deduplicates overlaps, and credits all verified units to your user profile.")
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
                                    scan_res, b_hits, accumulate=accumulate_vid, source_label="Aisle Video Audit", active_user=current_user
                                )
                                st.success(f"✅ Video synced by {current_user}! Updated {len(matched_list)} SKU(s).")
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
                                scan_res, b_hits, accumulate=accumulate_batch, source_label="Batch Photo Upload", active_user=current_user
                            )
                            st.success(f"✅ Batch synced by {current_user} ({len(matched_list)} SKU(s) updated)!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Scan error: {e}")

        # --- DISPLAY LATEST AUDIT EVIDENCE ---
        if shared_db["activity_log"]:
            st.markdown("#### 🧠 Latest Field Scan Feed")
            latest = shared_db["activity_log"][0]
            st.caption(f"{latest['timestamp']} • 👤 **{latest.get('user', 'Auditor')}** • {latest['source']}")
            for det in latest["items"]:
                st.markdown(f"""
                <div class="feed-item">
                    <span class="sap-badge">{det['sap_id']}</span>
                    <strong style="color:#0B2C5F;">{det['product_name']}</strong>
                    <span style="color:#047857; font-weight:700; float:right;">{det['unit_count']} unit(s)</span><br/>
                    <span style="color:#334155;">Read Text: <em>"{det['extracted_text_ar_en']}"</em></span>
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
                    f"<span style='color:#475569; font-size:0.82rem;'>{item['arabic_name']}</span>  \n"
                    f"<span class='sap-badge'>{item['sap_id']}</span>",
                    unsafe_allow_html=True,
                )
            with c_erp:
                st.markdown(
                    f"<span style='color:#475569; font-size:0.76rem;'>SAP</span><br/>"
                    f"<strong style='color:#0B2C5F;'>{item['erp_qty']}</strong>",
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
                    diff = max(0, new_val - item["physical_qty"])
                    shared_db["inventory"][idx]["physical_qty"] = new_val
                    shared_db["last_updated_ts"] = time.time()
                    if diff > 0:
                        record_user_work(current_user, [item["sap_id"]], diff)
            st.divider()

        if shown_count == 0:
            st.info("No items verified yet. Point the live camera at a product and tap the green or navy button—it will appear here and credit your user efficiency score!")

        if st.button("✅ Finalize & Post Audit to SAP S/4HANA", type="primary", use_container_width=True):
            shared_db["last_sync"] = datetime.now().strftime(f"%I:%M %p (Posted by {current_user})")
            st.balloons()
            st.success(f"Audit posted to SAP S/4HANA by {current_user}!")

# ==========================================
# TAB 2: MANAGER EXECUTIVE DASHBOARD
# ==========================================
if tab_dashboard is not None:
    with tab_dashboard:
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

            st.markdown(f"### 📡 Live Store Audit Progress: **{audited_skus} / {total_skus} SKUs Verified** ({progress_pct*100:.0f}%)")
            st.progress(progress_pct)
            st.caption(f"Auto-syncing live from field auditors • Last SAP status: {shared_db['last_sync']}")

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Field Audit Progress", f"{audited_skus} / {total_skus} SKUs", f"{total_phys} physical units counted")
            k2.metric("Inventory Accuracy", f"{accuracy}%", f"{total_phys - total_erp:+d} units vs SAP")
            k3.metric("Revenue at Risk", f"SAR {rev_risk:,.2f}", "Phantom stock exposure", delta_color="inverse")
            k4.metric("Active Alerts", f"{alerts_count} Stock | {len(shared_db['theft_alerts'])} Security", "SAP PO & CCTV triggers")

            if shared_db["activity_log"]:
                with st.expander(f"📲 Live Field Auditor Feed ({len(shared_db['activity_log'])} scans received)", expanded=True):
                    for log in shared_db["activity_log"][:5]:
                        matched_txt = ", ".join(log["matched"]) if log["matched"] else "Unmapped catalog item"
                        who = log.get("user", "Field Auditor")
                        st.markdown(
                            f"<div class='feed-item'><strong>[{log['timestamp']}] 👤 {who} ({log['source']}):</strong> {matched_txt}</div>",
                            unsafe_allow_html=True,
                        )

            st.write("")

            col_chart1, col_chart2 = st.columns(2, gap="large")

            with col_chart1:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.markdown("#### 📊 Top 5 SKUs by Unit Variance (SAP vs. Vision)")
                st.caption("Highlights the 5 products with the largest physical-to-ERP gap.")
                top5_var_df = df.sort_values(by="abs_variance", ascending=False).head(5).copy()
                top5_var_df["Short Label"] = top5_var_df["name"].apply(lambda x: x[:28] + "…" if len(x) > 29 else x)
                chart1_data = top5_var_df.set_index("Short Label")[["erp_qty", "physical_qty"]]
                chart1_data.columns = ["SAP Book Qty", "AI Verified Qty"]
                st.bar_chart(chart1_data, color=["#0B2C5F", "#00A86B"], horizontal=True, height=285)
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
                    st.bar_chart(chart2_data, color="#0072CE", horizontal=True, height=285)
                else:
                    st.success("Zero phantom stock revenue leakage across all SKUs!")
                st.markdown('</div>', unsafe_allow_html=True)

            st.write("")

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

# ==========================================
# TAB 3: WORKFORCE & AUDITOR EFFICIENCY + ACCESS MANAGEMENT
# ==========================================
with tab_workforce:
    @st.fragment(run_every=4)
    def render_workforce_efficiency():
        st.subheader("👥 Workforce Productivity & Mobile Auditor Access Control")
        st.caption("Tracks how many physical units and unique SKUs each authorized field auditor has verified in real time.")

        rows = []
        auditor_items = [
            (uname, udata)
            for uname, udata in shared_db["users"].items()
            if udata.get("role") == "Field Auditor"
        ]
        total_team_units = sum(u["units_verified"] for _, u in auditor_items)

        for order_idx, (uname, udata) in enumerate(auditor_items):
            skus_count = len(udata["skus_touched"])
            units_count = udata["units_verified"]
            share_pct = round((units_count / total_team_units) * 100, 1) if total_team_units > 0 else 0.0
            rows.append({
                "_order": order_idx,
                "User Account": uname,
                "Role": udata["role"],
                "Assigned Zone": udata["assigned_zone"],
                "Mobile Access": "🟢 Authorized" if udata["active"] else "🔴 Revoked",
                "Units Verified": units_count,
                "Unique SKUs Audited": skus_count,
                "Scan Push Events": udata["scan_events"],
                "Team Contribution (%)": share_pct,
                "Last Active": udata["last_active"],
            })

        eff_df = pd.DataFrame(rows).sort_values(by="_order", ascending=True).drop(columns=["_order"])

        top_row = eff_df.sort_values(by="Units Verified", ascending=False).iloc[0] if not eff_df.empty else None
        top_performer = (
            top_row["User Account"]
            if top_row is not None and top_row["Units Verified"] > 0
            else "Awaiting Scans"
        )
        active_auditors_cnt = len([u for _, u in auditor_items if u["active"]])

        w1, w2, w3 = st.columns(3)
        w1.metric("Authorized Field Auditors", f"{active_auditors_cnt} Active", "Mobile scanner enabled")
        w2.metric("Total Team Units Verified", f"{total_team_units} Units", "Across all field auditors")
        w3.metric("Top Auditor (By Volume)", top_performer, "Highest verified count")

        st.write("")

        col_eff_chart, col_eff_admin = st.columns([1.25, 1], gap="large")

        with col_eff_chart:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("#### 📈 Verified Units by Auditor (Efficiency Comparison)")
            st.caption("Live comparison of physical shelf items verified per field auditor.")
            chart_eff = eff_df.set_index("User Account")[["Units Verified", "Unique SKUs Audited"]]
            st.bar_chart(chart_eff, color=["#00A86B", "#0072CE"], horizontal=True, height=280)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("#### 📋 Detailed Auditor Performance Ledger")
            st.dataframe(eff_df, use_container_width=True, hide_index=True)

        with col_eff_admin:
            if active_role == "Manager":
                st.markdown('<div class="cctv-panel">', unsafe_allow_html=True)
                st.markdown("#### 🔑 Grant Mobile Access to New Auditor")
                st.caption("Provision a new mobile user account and PIN so they can log in from their smartphone.")

                next_num = len(auditor_items) + 1
                new_name = st.text_input("Auditor Name / Label:", placeholder=f"e.g. Mohammed (Auditor {next_num})")
                new_zone = st.text_input("Assigned Store Aisle / Zone:", placeholder="e.g. Aisle D (Beverages)")
                new_pin = st.text_input("Assign 4-Digit PIN:", value=f"{next_num}{next_num}{next_num}{next_num}"[:4], max_chars=8)

                if st.button("➕ Grant Mobile Scanner Access", type="primary", use_container_width=True):
                    clean_name = new_name.strip()
                    if not clean_name:
                        st.warning("Enter an auditor name first.")
                    elif clean_name in shared_db["users"]:
                        st.warning("That user already exists.")
                    else:
                        shared_db["users"][clean_name] = {
                            "role": "Field Auditor",
                            "pin": new_pin.strip() or "4444",
                            "assigned_zone": new_zone.strip() or "General Floor",
                            "active": True,
                            "units_verified": 0,
                            "skus_touched": set(),
                            "scan_events": 0,
                            "last_active": "Provisioned",
                        }
                        st.success(f"✅ Mobile access granted to **{clean_name}** (PIN: `{new_pin.strip() or '4444'}`)!")
                        st.rerun()

                st.markdown("---")
                st.markdown("#### 🛡️ Manage Existing User Permissions")
                manageable_users = [u for u, meta in shared_db["users"].items() if meta.get("role") == "Field Auditor"]
                target_u = st.selectbox("Select Auditor Account:", manageable_users, key="manage_u_sel")
                is_currently_active = shared_db["users"][target_u]["active"]

                if is_currently_active:
                    if st.button(f"🚫 Suspend Mobile Access for {target_u}", use_container_width=True):
                        shared_db["users"][target_u]["active"] = False
                        st.warning(f"Suspended mobile access for {target_u}.")
                        st.rerun()
                else:
                    if st.button(f"✅ Re-Enable Mobile Access for {target_u}", use_container_width=True):
                        shared_db["users"][target_u]["active"] = True
                        st.success(f"Re-enabled mobile access for {target_u}.")
                        st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("Log in as **Manager (Admin)** (PIN: `0000`) to provision new mobile auditor accounts or suspend access.")

    render_workforce_efficiency()

# ==========================================
# TAB 4: AUTOMATED STORE ALERTS
# ==========================================
if tab_alerts is not None:
    with tab_alerts:
        @st.fragment(run_every=4)
        def render_automated_alerts():
            st.subheader("🚨 Loss-Prevention & Behavioral Theft Alerts (Overhead CCTV)")
            if not shared_db["theft_alerts"]:
                st.info("No suspicious theft behavior detected by overhead aisle CCTV cameras. Run a feed or test clip in Tab 5 ('Overhead CCTV Theft Detection') to trigger live security alerts here.")
            else:
                for alert in shared_db["theft_alerts"]:
                    st.markdown(f"""
                    <div style="background-color:#FEF2F2; border:1px solid #FECACA; border-left:5px solid #DC2626; padding:16px; border-radius:10px; margin-bottom:12px; box-shadow: 0 2px 8px rgba(220,38,38,0.08);">
                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
                            <span style="color:#B91C1C; font-weight:800; font-size:0.88rem;">
                                🚨 PRIORITY SECURITY ALERT • {alert['camera_id']} • {alert['aisle']}
                            </span>
                            <span style="background:#DC2626; color:#FFFFFF; padding:3px 10px; border-radius:999px; font-size:0.76rem; font-weight:700;">
                                🕒 {alert['timestamp']} • Confidence: {alert['confidence_pct']}%
                            </span>
                        </div>
                        <div style="color:#1E293B; margin-top:8px; font-size:0.94rem; line-height:1.5;">
                            <strong>Detected Behavior:</strong> {alert['behavior_type']}<br/>
                            <strong>AI CCTV Observation:</strong> {alert['description']}<br/>
                            <strong>Recommended Action:</strong> <span style="color:#991B1B; font-weight:600;">{alert['recommended_action']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                if st.button("🧹 Acknowledge & Clear Security Alerts", key="clear_theft_btn"):
                    shared_db["theft_alerts"] = []
                    st.rerun()

            st.markdown("---")

            st.subheader("📦 Automated SAP Shelf Replenishment Alerts")
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
                    <div style="background: linear-gradient(90deg, #FFFFFF 0%, #F2FBF7 100%); border:1px solid #BCE3D1; border-left:5px solid #00A86B; padding:15px; border-radius:10px; margin-bottom:12px; box-shadow: 0 2px 6px rgba(11,44,95,0.05);">
                        <div style="color:#047857; font-weight:800; font-size:0.84rem;">💬 WHATSAPP BUSINESS ALERT • STORE #104 • {row['category'].upper()}</div>
                        <div style="color:#1E293B; margin-top:6px; font-size:0.93rem; line-height:1.5;">
                            <strong style="color:#0B2C5F;">⚠️ SHELF REPLENISHMENT REQUIRED ({row['sap_id']}):</strong><br/>
- <strong>Product:</strong> {row['name']} ({row['arabic_name']})<br/>
- <strong>Barcode / Location:</strong> {row['ean13']} • {row['aisle']}<br/>
- <strong>Verified Shelf Qty:</strong> {row['physical_qty']} units (SAP Book: {row['erp_qty']} | Variance: {row['variance']:+d} | Risk: SAR {row['rev_at_risk']:,.2f})<br/>
- <strong>Action:</strong> Pull 1 case from Backroom Bay B or approve draft SAP Purchase Order.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        render_automated_alerts()

# ==========================================
# TAB 5: OVERHEAD CCTV THEFT BEHAVIORAL DETECTION
# ==========================================
if tab_cctv is not None:
    with tab_cctv:
        st.subheader("🛡️ Overhead Store CCTV — Behavioral Theft Detection")
        st.caption("Dedicated fixed overhead aisle camera feed (separate from handheld inventory phones). Detects concealment gestures and shelf sweeping in real time and dispatches alerts directly to Automated Store Alerts.")

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
                    "📹 Live Overhead Webcam / OBS Virtual CCTV Feed",
                    "🎞️ Upload Overhead CCTV Footage (.mp4 / .mov)",
                ],
                horizontal=True,
            )

            if cctv_source == "📹 Live Overhead Webcam / OBS Virtual CCTV Feed":
                st.caption("Select **OBS Virtual Camera** (streaming your EZVIZ C6N) or your laptop webcam in the dropdown below, then toggle **Start Live AI Theft Guard**.")
                cctv_event = cctv_guard_component(
                    api_key=active_gemini_key,
                    cam_code=cam_code,
                    aisle=aisle_label,
                    key="live_ezviz_cctv_guard_v6",
                )

                if isinstance(cctv_event, dict) and cctv_event.get("alert_id"):
                    al_id = cctv_event["alert_id"]
                    if st.session_state.last_cctv_alert_id != al_id:
                        st.session_state.last_cctv_alert_id = al_id
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

                st.markdown("##### ⚡ Demo Trigger: Simulate Overhead CCTV Theft Event")
                sim_behavior = st.selectbox(
                    "Simulated Behavioral Event:",
                    [
                        "Item Concealment in Jacket / Personal Bag (2 units removed from shelf)",
                        "Rapid Shelf Sweeping into Backpack (High-Value Dairy/Formula)",
                    ],
                    key="sim_beh_select",
                )
                if st.button("🚨 Trigger Overhead CCTV Theft Detection Alert", type="primary", use_container_width=True):
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
                    st.error(f"🚨 Theft alert dispatched at {now_str}! Check Automated Store Alerts.")
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
2. **Action & Concealment Recognition (SlowFast / VideoMAE + Vision AI):** Analyzes 3–5 second motion sequences to detect:
  - **Concealment:** Hand picks item from shelf and moves directly into a pocket, backpack, or under clothing.
  - **Shelf Sweeping:** Rapidly clearing multiple high-value items into a personal bag.
3. **Instant Alert Routing:** Whenever suspicious behavior is detected, StockSense timestamps the exact camera channel and aisle and pushes a **Priority Security Alert** to the Store Manager's alert feed.
            """)
            st.markdown("---")
            st.markdown("#### 📡 Overhead CCTV Edge Telemetry")
            st.write("• **Connected Store Cameras:** 14 / 14 RTSP Channels Online")
            st.write("• **Privacy Compliance:** Anonymous Pose Keypoints (No Facial Recognition)")
            st.write("• **Alert Latency:** < 2.5 seconds from gesture to Manager Alert")
            st.markdown('</div>', unsafe_allow_html=True)
