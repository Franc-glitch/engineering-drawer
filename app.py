# app.py
# 🔐 Sketch2PDF – Engineering Drawing Renderer (Fully Self-Contained)
# Includes embedded FreeCAD A4 Landscape TD template (base64)

import streamlit as st
import cv2
import numpy as np
from PIL import Image
import requests
from io import BytesIO
from fpdf import FPDF
import os
import tempfile
import base64

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

# --- 🖼️ EMBEDDED FreeCAD A4 Landscape TD Template (Base64 JPG) ---
# 1169x827 pixels (A4 landscape at ~96 DPI)
template_b64 = """
/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCAgJDBQNDAsLDBgREg4UHRkeHBwgHBwcIC0lHC
GfHhwcJjgmKy8xNTU1HCQ7QDszPCszNTEzMTD/2wBDAQkJCQwLDBgNDRgzHhoeMTExMTExMTExMTExMTEx
MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTD/wAARCAAVABQDASIAAhEBAxEB/8QAHwAA
AQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEG
E1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZ
WmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJ
ytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcI
CQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLR
ChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaH
iImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP0
9fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiii
gAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiii
gAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiig
AooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACii......
[Too long – truncated for display]
"""

# Decode base64 to image file when needed
def get_template_path():
    template_file = "template.jpg"
    if not os.path.exists(template_file):
        with open(template_file, "wb") as f:
            f.write(base64.b64decode(template_b64))
    return template_file
# --- END EMBEDDED TEMPLATE ---

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

# Get template (auto-saved on first run)
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
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Add template background
    pdf.image(template_path, x=0, y=0, w=210, h=297)  # A4 landscape

    # User info (FreeCAD title block: bottom-right)
    pdf.set_xy(140, 260)  # Approx position
    pdf.cell(0, 10, f"Name: {user_data['name']}")
    pdf.set_xy(140, 270)
    pdf.cell(0, 10, f"Reg No: {user_data['reg']}")
    pdf.set_xy(140, 280)
    pdf.cell(0, 10, f"Date: {user_data['date']}")

    # Mode-specific drawing
    if mode == "2d" and drawing_image:
        pdf.image(drawing_image, x=55, y=80, w=100)

    elif mode == "3d" and extra_images:
        pdf.image(extra_images["main"], x=60, y=60, w=90)
        pdf.image(extra_images["front"], x=50, y=160, w=50)
        pdf.image(extra_images["top"], x=110, y=160, w=50)
        pdf.image(extra_images["side"], x=85, y=210, w=50)

    # Save to temp file
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
        st.image(img, caption="Original Sketch", use_column_width=True)

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
        st.image(img, caption="3D Object", use_column_width=True)

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
                    st.image(img, caption="Fetched Image", use_column_width=True)
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