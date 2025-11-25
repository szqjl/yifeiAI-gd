# PowerShell script to run OCR conversion
# Usage: .\run_ocr_conversion.ps1

# Set your Tencent Cloud API credentials here
# IMPORTANT: Replace with your actual credentials before use
# $env:TENCENT_SECRET_ID = "YOUR_SECRET_ID_HERE"
# $env:TENCENT_SECRET_KEY = "YOUR_SECRET_KEY_HERE"

# For security, credentials are not committed to repository
# Please set them manually or use environment variables

# Optional: Set Poppler path if not in PATH
# $env:POPPLER_PATH = "C:\poppler-25.07.0\Library\bin"

# Run the conversion script
python convert_pdf_ocr_markitdown.py

