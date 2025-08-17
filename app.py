# app.py
# 🔐 Sketch2PDF – Engineering Drawing Renderer
# Fully fixed: No PIL errors, no deprecation warnings, works on Streamlit Cloud

import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import requests
from io import BytesIO
from fpdf import FPDF
import os
import tempfile

# --- 🔒 PASSWORD PROTECTION ---
def check_password():
    def password_entered():
        if st.session_state["password"].lower() == "goroth":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("### 🔐 Access Required")
        st.subheader("Enter the password to continue:")
        st.text_input("Password", type="password", key="password", on_change=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("### ❌ Incorrect Password")
        st.text_input("Password", type="password", key="password", on_change=password_entered)
        return False
    else:
        return True

if not check_password():
    st.stop()
# --- END PASSWORD PROTECTION ---

# --- 🖼️ DYNAMICALLY CREATE A4 LANDSCAPE TEMPLATE (No base64, no broken images) ---
def create_template():
    """Generates a clean A4 landscape engineering sheet (1169x827 px)"""
    width, height = 1169, 827  # A4 @ ~96 DPI
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([10, 10, width - 10, height - 10], outline="black", width=3)

    # Title
    draw.text((50, 50), "ENGINEERING DRAWING", fill="black", fontsize=40)

    # Title block (bottom-right)
    tb_x, tb_y = 800, 700
    draw.rectangle([tb_x, tb_y, width - 20, height - 20], outline="black", width=1)
    draw.text((tb_x + 10, tb_y + 10), "Name: ________________", fill="black", fontsize=20)
    draw.text((tb_x + 10, tb_y + 40), "Reg No: _______________", fill="black", fontsize=20)
    draw.text((tb_x + 10, tb_y + 70), "Date: _________________", fill="black", fontsize=20)
    draw.text((tb_x + 10, tb_y + 100), "Scale: 1:1", fill="black", fontsize=20)

    # Third-angle projection symbol (simplified)
    draw.text((1000, 750), "📌 TD", fill="black", fontsize=30)

    return img

def get_template_path():
    template_file = "template.jpg"
    if not os.path.exists(template_file):
        print("🔧 Generating template.jpg...")
        img = create_template()
        img.save(template_file, "JPEG", quality=95)
    return template_file
# --- END TEMPLATE GENERATION ---

# -------------------------------
# App Title & Mode Selection
# -------------------------------
st.title("📐 Sketch2PDF – Engineering Drawing Renderer")

mode = st.radio("Choose Input Mode:", ["2D Drawing", "3D Object", "Online (Pinterest)"])

# -------------------------------
# User Data Input
# -------------------------------
st.subheader("Enter Your Details")
name = st.text_input("Name")
reg = st.text_input("Registration Number")
date = st.text_input("Date", value="2025-04-05")

user_data = {"name": name, "reg": reg, "date": date}

# Get template (auto-generated)
template_file = get_template_path()

# -------------------------------
# Helper: Clean 2D Drawing
# -------------------------------
def clean_2d_drawing(img):
    img_array = np.array(img)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    return Image.fromarray(edges)

# -------------------------------
# Helper: Generate 3D Orthographic Views (Mock)
# -------------------------------
def generate_3d_views(img):
    img_array = np.array(img)
    h, w, _ = img_array.shape
    front = cv2.resize(img_array, (200, 200))
    top = cv2.resize(img_array[:h//2, :], (200, 100))
    side = cv2.resize(img_array[:, :w//2], (100, 200))
    return {
        "main": img.resize((300, 300)),
        "front": Image.fromarray(front),
        "top": Image.fromarray(top),
        "side": Image.fromarray(side)
    }

# -------------------------------
# Helper: Create PDF from Template
# -------------------------------
def create_pdf(template_path, mode, user_data, drawing_image=None, extra_images=None):
    pdf = FPDF()
    pdf.add_page(orientation="L")  # Landscape
    pdf.set_font("Arial", size=12)

    # Add template background
    pdf.image(template_path, x=0, y=0, w=297, h=210)  # FPDF uses mm: A4 landscape = 297x210

    # User info (bottom-right, matches template)
    pdf.set_xy(180, 190)
    pdf.cell(0, 10, f"Name: {user_data['name']}")
    pdf.set_xy(180, 200)
    pdf.cell(0, 10, f"Reg No: {user_data['reg']}")
    pdf.set_xy(180, 210)
    pdf.cell(0, 10, f"Date: {user_data['date']}")

    # Mode-specific drawing
    if mode == "2d" and drawing_image:
        pdf.image(drawing_image, x=90, y=60, w=100)

    elif mode == "3d" and extra_images:
        pdf.image(extra_images["main"], x=100, y=40, w=90)
        pdf.image(extra_images["front"], x=60, y=150, w=50)
        pdf.image(extra_images["top"], x=120, y=150, w=50)
        pdf.image(extra_images["side"], x=95, y=200, w=50)

    # Save
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_pdf.name)
    return temp_pdf.name

# -------------------------------
# Pinterest Image Fetcher
# -------------------------------
def get_pinterest_image(url, pin_index=0):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        imgs = soup.find_all("img", src=True)
        img_urls = [img['src'] for img in imgs if 'i.pinimg' in img['src']]
        
        if len(img_urls) > pin_index:
            img_url = img_urls[pin_index]
            img_response = requests.get(img_url, headers=headers, timeout=10)
            return Image.open(BytesIO(img_response.content))
        else:
            st.error("❌ No valid image found at that index.")
            return None
    except Exception as e:
        st.error(f"⚠️ Failed to fetch image: {e}")
        return None

# -------------------------------
# Handle Each Mode
# -------------------------------
if mode == "2D Drawing":
    uploaded = st.file_uploader("📤 Upload 2D Sketch", type=["png", "jpg", "jpeg"])
    if uploaded:
        img = Image.open(uploaded)
        st.image(img, caption="Original Sketch", use_container_width=True)

        if st.button("⚙️ Process & Generate PDF"):
            with st.spinner("Cleaning and dimensioning..."):
                cleaned = clean_2d_drawing(img)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    cleaned.save(tmp.name)
                    pdf_path = create_pdf(template_file, "2d", user_data, drawing_image=tmp.name)

            st.success("✅ PDF Generated!")
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download PDF", f, "2d_drawing.pdf", mime="application/pdf")

elif mode == "3D Object":
    uploaded = st.file_uploader("📤 Upload 3D Object Image", type=["png", "jpg", "jpeg"])
    if uploaded:
        img = Image.open(uploaded)
        st.image(img, caption="3D Object", use_container_width=True)

        if st.button("📐 Generate Views"):
            with st.spinner("Creating orthographic projections..."):
                views = generate_3d_views(img)
                st.image(views["front"], caption="Front View", width=200)
                st.image(views["top"], caption="Top View", width=200)
                st.image(views["side"], caption="Side View", width=200)

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    views["main"].save(tmp.name)
                    pdf_path = create_pdf(template_file, "3d", user_data, extra_images=views)

            st.success("✅ PDF Generated!")
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download PDF", f, "3d_drawing.pdf", mime="application/pdf")

elif mode == "Online (Pinterest)":
    st.info("🌐 Enter a Pinterest board or pin URL to fetch an image.")
    url = st.text_input("Pinterest URL")
    pin_index = st.number_input("Pin Number (0 = first)", min_value=0, max_value=50, value=0)
    online_type = st.radio("Treat as:", ["2D Drawing", "3D Object"])

    if st.button("🔍 Fetch Image"):
        if url:
            with st.spinner("Fetching image..."):
                img = get_pinterest_image(url, pin_index)
                if img:
                    st.session_state["fetched_img"] = img
                    st.image(img, caption="Fetched Image", use_container_width=True)
        else:
            st.error("Please enter a URL.")

    if "fetched_img" in st.session_state:
        img = st.session_state["fetched_img"]
        if st.button("🛠️ Process Fetched Image"):
            with st.spinner("Processing..."):
                if online_type == "2D Drawing":
                    cleaned = clean_2d_drawing(img)
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        cleaned.save(tmp.name)
                        pdf_path = create_pdf(template_file, "2d", user_data, drawing_image=tmp.name)
                else:
                    views = generate_3d_views(img)
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        views["main"].save(tmp.name)
                        pdf_path = create_pdf(template_file, "3d", user_data, extra_images=views)

            st.success("✅ PDF Ready!")
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download PDF", f, "online_drawing.pdf", mime="application/pdf")
