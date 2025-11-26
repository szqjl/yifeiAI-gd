# PowerShell script to run OCR conversion
# Usage: .\run_ocr_conversion.ps1

# IMPORTANT: For security, credentials are NOT stored in this file
# Please set environment variables before running:
#   $env:TENCENT_SECRET_ID = "your_secret_id"
#   $env:TENCENT_SECRET_KEY = "your_secret_key"
#
# Or set them in your system environment variables
# Get credentials from: https://console.cloud.tencent.com/cam/capi

# Optional: Set Poppler path if not in PATH
# $env:POPPLER_PATH = "C:\poppler-25.07.0\Library\bin"

# Run the conversion script
python convert_pdf_ocr_markitdown.py

