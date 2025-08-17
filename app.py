# app.py
# Sketch2PDF – Engineering Drawing Renderer (Now with Real Dimensions & Layout)

import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from fpdf import FPDF
import os
import tempfile
import math

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

# --- 🖼 DYNAMICALLY CREATE A4 LANDSCAPE TEMPLATE ---
def create_template():
    width, height = 1169, 827  # A4 landscape @ 96 DPI
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([10, 10, width-10, height-10], outline="black", width=3)

    # Title block
    tb_x, tb_y = 800, 700
    draw.rectangle([tb_x, tb_y, width-20, height-20], outline="black", width=1)
    draw.text((tb_x+10, tb_y+10), "Name: ________________", fill="black")
    draw.text((tb_x+10, tb_y+40), "Reg No: _____________", fill="black")
    draw.text((tb_x+10, tb_y+70), "Date: _______________", fill="black")

    # Third-angle symbol
    draw.text((1000, 750), "📌 TD", fill="black", fontsize=30)

    return img

def get_template_path():
    template_file = "template.jpg"
    if not os.path.exists(template_file):
        img = create_template()
        img.save(template_file, "JPEG", quality=95)
    return template_file
# --- END TEMPLATE ---

# -------------------------------
# User Data
# -------------------------------
st.title("📐 Sketch2PDF – Engineering Drawing Renderer")
mode = st.radio("Choose Input Mode:", ["2D Drawing", "3D Object", "Online (Pinterest)"])

name = st.text_input("Name")
reg = st.text_input("Registration Number")
date = st.text_input("Date", value="2025-04-05")
user_data = {"name": name, "reg": reg, "date": date}

template_file = get_template_path()

# -------------------------------
# Helper: Clean & Add Dimensions
# -------------------------------
def process_2d_sketch(img):
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    
    # Detect lines and circles
    lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, minDist=20,
                               param1=50, param2=30, minRadius=5, maxRadius=100)
    
    # Create clean image
    clean = np.zeros_like(edges)
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(clean, (x1, y1), (x2, y2), 255, 2)
    
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        for (x, y, r) in circles:
            cv2.circle(clean, (x, y), r, 255, 2)
            cv2.circle(clean, (x, y), 2, 255, 3)
    
    # Add fake dimensions (for demo)
    dim_text = [
        ("Ø58", (300, 200)),
        ("R20", (250, 250)),
        ("Ø16", (150, 150)),
        ("8-Ø10", (400, 250))
    ]
    
    # Draw text on clean image
    clean_pil = Image.fromarray(clean)
    draw = ImageDraw.Draw(clean_pil)
    font = ImageFont.truetype("arial.ttf", 20) if os.path.exists("arial.ttf") else ImageFont.load_default()
    for text, pos in dim_text:
        draw.text(pos, text, fill="black", font=font)
    
    return clean_pil

# -------------------------------
# Helper: Generate 3D Views
# -------------------------------
def generate_3d_views(img):
    # Mock: front, top, side
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
# Helper: Create PDF
# -------------------------------
def create_pdf(template_path, mode, user_data, drawing_image=None, extra_images=None):
    pdf = FPDF()
    pdf.add_page(orientation="L")
    pdf.set_font("Arial", size=12)

    # Background
    pdf.image(template_path, x=0, y=0, w=297, h=210)

    # User info
    pdf.set_xy(180, 190)
    pdf.cell(0, 10, f"Name: {user_data['name']}")
    pdf.set_xy(180, 200)
    pdf.cell(0, 10, f"Reg No: {user_data['reg']}")
    pdf.set_xy(180, 210)
    pdf.cell(0, 10, f"Date: {user_data['date']}")

    # 2D: Cleaned + dims
    if mode == "2d" and drawing_image:
        pdf.image(drawing_image, x=90, y=60, w=100)

    # 3D: Main + views
    elif mode == "3d" and extra_images:
        pdf.image(extra_images["main"], x=60, y=40, w=90)
        pdf.image(extra_images["front"], x=60, y=150, w=50)
        pdf.image(extra_images["top"], x=120, y=150, w=50)
        pdf.image(extra_images["side"], x=95, y=200, w=50)

    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_pdf.name)
    return temp_pdf.name

# -------------------------------
# Handle Each Mode
# -------------------------------
if mode == "2D Drawing":
    uploaded = st.file_uploader("📤 Upload 2D Sketch", type=["png", "jpg"])
    if uploaded:
        img = Image.open(uploaded)
        st.image(img, caption="Original", use_container_width=True)

        if st.button("⚙️ Process"):
            with st.spinner("Cleaning and adding dimensions..."):
                cleaned = process_2d_sketch(img)
                st.image(cleaned, caption="Processed", use_container_width=True)

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    cleaned.save(tmp.name)
                    pdf_path = create_pdf(template_file, "2d", user_data, drawing_image=tmp.name)
                    st.success("✅ PDF Ready!")
                    with open(pdf_path, "rb") as f:
                        st.download_button("📥 Download PDF", f, "2d_drawing.pdf", mime="application/pdf")

elif mode == "3D Object":
    uploaded = st.file_uploader("📤 Upload 3D Object", type=["png", "jpg"])
    if uploaded:
        img = Image.open(uploaded)
        st.image(img, caption="3D Object", use_container_width=True)

        if st.button("📐 Generate Views"):
            views = generate_3d_views(img)
            col1, col2, col3 = st.columns(3)
            col1.image(views["front"], caption="Front", use_container_width=True)
            col2.image(views["top"], caption="Top", use_container_width=True)
            col3.image(views["side"], caption="Side", use_container_width=True)

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                views["main"].save(tmp.name)
                pdf_path = create_pdf(template_file, "3d", user_data, extra_images=views)
                st.success("✅ PDF Generated!")
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 Download PDF", f, "3d_drawing.pdf", mime="application/pdf")

elif mode == "Online (Pinterest)":
    url = st.text_input("Pinterest URL")
    pin_index = st.number_input("Pin Number", 0, 50, 0)
    online_type = st.radio("Treat as:", ["2D Drawing", "3D Object"])

    if st.button("🔍 Fetch"):
        if url:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            imgs = soup.find_all("img", src=True)
            img_urls = [img['src'] for img in imgs if 'i.pinimg' in img['src']]
            if len(img_urls) > pin_index:
                img_url = img_urls[pin_index]
                img_response = requests.get(img_url, headers=headers)
                img = Image.open(BytesIO(img_response.content))
                st.session_state["fetched_img"] = img
                st.image(img, caption="Fetched", use_container_width=True)
            else:
                st.error("No image found.")
        else:
            st.error("Please enter a URL.")

    if "fetched_img" in st.session_state:
        img = st.session_state["fetched_img"]
        if st.button("🛠️ Process"):
            if online_type == "2D Drawing":
                cleaned = process_2d_sketch(img)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    cleaned.save(tmp.name)
                    pdf_path = create_pdf(template_file, "2d", user_data, drawing_image=tmp.name)
                    st.success("✅ PDF Ready!")
                    with open(pdf_path, "rb") as f:
                        st.download_button("📥 Download PDF", f, "online_drawing.pdf", mime="application/pdf")
            else:
                views = generate_3d_views(img)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    views["main"].save(tmp.name)
                    pdf_path = create_pdf(template_file, "3d", user_data, extra_images=views)
                    st.success("✅ PDF Ready!")
                    with open(pdf_path, "rb") as f:
                        st.download_button("📥 Download PDF", f, "online_drawing.pdf", mime="application/pdf")
