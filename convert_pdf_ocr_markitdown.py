# -*- coding: utf-8 -*-
"""Use OCR to recognize PDF, then convert with markitdown"""

import os
import sys
from pathlib import Path

# Check dependencies
try:
    from pdf2image import convert_from_path
except ImportError:
    print("Need to install pdf2image: pip install pdf2image pillow")
    sys.exit(1)

try:
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.ocr.v20181119 import ocr_client, models
except ImportError:
    print("Need to install Tencent Cloud SDK: pip install tencentcloud-sdk-python")
    sys.exit(1)

try:
    from markitdown import MarkItDown
except ImportError:
    print("Need to install markitdown: pip install markitdown")
    sys.exit(1)

import base64
import io

# Configuration
SECRET_ID = os.getenv("TENCENT_SECRET_ID", "")
SECRET_KEY = os.getenv("TENCENT_SECRET_KEY", "")
REGION = "ap-beijing"
POPPLER_PATH = os.getenv("POPPLER_PATH", r"C:\poppler-25.07.0\Library\bin")

if not SECRET_ID or not SECRET_KEY:
    print("Please set environment variables TENCENT_SECRET_ID and TENCENT_SECRET_KEY")
    print("Or set them directly in the code")
    print("Get them from: https://console.cloud.tencent.com/cam/capi")
    sys.exit(1)

# PDF file path - find file dynamically to avoid encoding issues
pdf_dir = Path("docs/gdrules")
# Find all PDF files and use the one with "1006" in name
pdf_files = [f for f in pdf_dir.glob("*.pdf") if "1006" in f.name]
if not pdf_files:
    print(f"PDF file not found in {pdf_dir}")
    sys.exit(1)
pdf_path = pdf_files[0]
print(f"Found PDF file: {pdf_path.name}")

print(f"Processing: {pdf_path}")

# Initialize OCR client
print("Initializing OCR client...")
cred = credential.Credential(SECRET_ID, SECRET_KEY)
http_profile = HttpProfile()
http_profile.endpoint = "ocr.tencentcloudapi.com"
client_profile = ClientProfile()
client_profile.httpProfile = http_profile
client = ocr_client.OcrClient(cred, REGION, client_profile)

# Initialize markitdown
print("Initializing markitdown...")
md = MarkItDown()

# Convert PDF to images
print("Converting PDF to images...")
try:
    if os.path.exists(POPPLER_PATH):
        images = convert_from_path(str(pdf_path), poppler_path=POPPLER_PATH)
    else:
        images = convert_from_path(str(pdf_path))
    print(f"Total {len(images)} pages")
except Exception as e:
    print(f"Failed to convert PDF to images: {e}")
    print("Please ensure Poppler is installed and POPPLER_PATH is set")
    sys.exit(1)

# OCR each page
print("Starting OCR recognition...")
all_pages_text = []
for i, image in enumerate(images, 1):
    print(f"   Recognizing page {i}/{len(images)}...")
    
    try:
        # Convert image to base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # OCR recognition
        req = models.GeneralBasicOCRRequest()
        req.ImageBase64 = image_data
        resp = client.GeneralBasicOCR(req)
        
        # Extract text
        text = "\n".join([item.DetectedText for item in resp.TextDetections])
        all_pages_text.append(f"## Page {i}\n\n{text}")
        
    except Exception as e:
        print(f"   Warning: Page {i} recognition failed: {e}")
        all_pages_text.append(f"## Page {i}\n\n[OCR recognition failed]")

# Merge all text
print("Merging OCR results...")
ocr_text = "\n\n".join(all_pages_text)

# Save OCR intermediate result
ocr_temp_file = pdf_path.with_suffix('.ocr_temp.md')
with open(ocr_temp_file, 'w', encoding='utf-8') as f:
    f.write(ocr_text)
print(f"OCR result saved: {ocr_temp_file}")

# Use markitdown to process OCR result
print("Processing OCR result with markitdown...")
try:
    # markitdown is mainly for structured documents, but we can try
    result = md.convert(str(ocr_temp_file))
    
    # Save final result
    output_file = pdf_path.with_suffix('.md')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result.markdown)
    
    print(f"Conversion completed: {output_file}")
    
    # Delete temporary file
    if ocr_temp_file.exists():
        ocr_temp_file.unlink()
        print(f"Deleted temporary file: {ocr_temp_file}")
        
except Exception as e:
    print(f"Warning: markitdown processing failed: {e}")
    print("Using OCR result as final output...")
    # If markitdown fails, use OCR result directly
    output_file = pdf_path.with_suffix('.md')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(ocr_text)
    print(f"Saved OCR result: {output_file}")

print("\nAll done!")

