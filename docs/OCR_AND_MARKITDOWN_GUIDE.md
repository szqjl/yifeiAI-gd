# OCR 识别和 Markitdown 转换指南

## 📋 概述

本指南介绍如何使用腾讯云 OCR API 识别图片/PDF，以及使用 markitdown 转换文档为 Markdown 格式。

---

## 🔧 环境准备

### 1. 安装 Python 依赖

```bash
# 安装腾讯云 SDK
py -3.12 -m pip install tencentcloud-sdk-python

# 安装 markitdown
py -3.12 -m pip install markitdown

# 安装 PDF 处理工具（如需要）
py -3.12 -m pip install pdf2image pillow
```

### 2. 安装 Poppler（PDF 转图片需要）

```bash
# 使用 winget 安装
winget install Poppler
```

安装后，将 Poppler 的 `Library\bin` 目录添加到系统 PATH，或设置环境变量：
```bash
set POPPLER_PATH=C:\poppler-25.07.0\Library\bin
```

---

## 🔑 腾讯云 OCR 配置

### 1. 获取 API 密钥

1. 登录腾讯云控制台：https://console.cloud.tencent.com/cam/capi
2. 创建 API 密钥，获取 `SecretId` 和 `SecretKey`
3. 开通 OCR 服务：https://console.cloud.tencent.com/ocr

### 2. 设置环境变量（可选）

```bash
# Windows CMD
set TENCENT_SECRET_ID=你的SecretId
set TENCENT_SECRET_KEY=你的SecretKey

# Windows PowerShell
$env:TENCENT_SECRET_ID="你的SecretId"
$env:TENCENT_SECRET_KEY="你的SecretKey"
```

---

## 📸 OCR 识别图片

### 基本用法

```python
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.ocr.v20181119 import ocr_client, models
import base64

# 配置 API 密钥
SECRET_ID = "你的SecretId"
SECRET_KEY = "你的SecretKey"
REGION = "ap-beijing"

# 读取图片并转换为 base64
with open("image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# 创建 OCR 客户端
cred = credential.Credential(SECRET_ID, SECRET_KEY)
http_profile = HttpProfile()
http_profile.endpoint = "ocr.tencentcloudapi.com"
client_profile = ClientProfile()
client_profile.httpProfile = http_profile
client = ocr_client.OcrClient(cred, REGION, client_profile)

# 创建请求
req = models.GeneralBasicOCRRequest()
req.ImageBase64 = image_data

# 调用 API
resp = client.GeneralBasicOCR(req)

# 提取文本
text = "\n".join([item.DetectedText for item in resp.TextDetections])
print(text)
```

---

## 📄 OCR 识别 PDF

### 方法：逐页转换为图片后识别

```python
from pdf2image import convert_from_path
import os

# 设置 Poppler 路径（如果未添加到 PATH）
poppler_path = r"C:\poppler-25.07.0\Library\bin"
os.environ["POPPLER_PATH"] = poppler_path

# 将 PDF 转换为图片
images = convert_from_path("document.pdf", poppler_path=poppler_path)

# 逐页识别
all_text = []
for i, image in enumerate(images):
    # 将图片转换为 base64
    import io
    import base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # OCR 识别（使用上面的代码）
    # ... OCR 调用代码 ...
    
    all_text.append(f"## 第 {i+1} 页\n\n{text}")

# 合并所有文本
final_text = "\n\n".join(all_text)
```

---

## 📝 Markitdown 转换

### 基本用法

```python
from markitdown import MarkItDown
from pathlib import Path

# 创建转换器
md = MarkItDown()

# 转换 DOCX 文件
docx_file = Path("document.docx")
result = md.convert(str(docx_file))

# 保存为 Markdown
output_file = docx_file.with_suffix('.md')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(result.markdown)

print(f"✅ 转换完成: {output_file}")
```

### 支持的格式

- DOCX（Word 文档）
- PDF（部分支持，扫描版 PDF 可能识别不佳）
- 图片（需要 OCR，markitdown 本身对图片文本识别有限）

---

## 🔄 完整工作流示例

### 场景：将扫描版 PDF 转换为 Markdown

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""将扫描版 PDF 转换为 Markdown"""

from pdf2image import convert_from_path
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.ocr.v20181119 import ocr_client, models
import base64
import io
import os

# 配置
SECRET_ID = "你的SecretId"
SECRET_KEY = "你的SecretKey"
REGION = "ap-beijing"
POPPLER_PATH = r"C:\poppler-25.07.0\Library\bin"

# 初始化 OCR 客户端
cred = credential.Credential(SECRET_ID, SECRET_KEY)
http_profile = HttpProfile()
http_profile.endpoint = "ocr.tencentcloudapi.com"
client_profile = ClientProfile()
client_profile.httpProfile = http_profile
client = ocr_client.OcrClient(cred, REGION, client_profile)

# PDF 转图片
pdf_path = "document.pdf"
images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)

# 逐页识别
all_pages = []
for i, image in enumerate(images, 1):
    print(f"正在识别第 {i}/{len(images)} 页...")
    
    # 图片转 base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # OCR 识别
    req = models.GeneralBasicOCRRequest()
    req.ImageBase64 = image_data
    resp = client.GeneralBasicOCR(req)
    
    # 提取文本
    text = "\n".join([item.DetectedText for item in resp.TextDetections])
    all_pages.append(f"## 第 {i} 页\n\n{text}")

# 保存为 Markdown
output_file = "document_ocr.md"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("\n\n".join(all_pages))

print(f"✅ 转换完成: {output_file}")
```

---

## ⚠️ 注意事项

### OCR 识别

1. **免费额度**：新用户每月有 1000 次免费调用，需要开启按量付费才能使用
2. **文件大小限制**：单次请求不超过 10MB
3. **PDF 处理**：大 PDF 需要逐页转换为图片后识别
4. **识别质量**：扫描版文档识别质量取决于图片清晰度

### Markitdown 转换

1. **DOCX 文件**：转换效果较好
2. **PDF 文件**：仅支持文本型 PDF，扫描版 PDF 需要先 OCR
3. **图片文件**：markitdown 对图片文本识别有限，建议使用 OCR

---

## 📚 相关资源

- [腾讯云 OCR 文档](https://cloud.tencent.com/document/product/866)
- [Markitdown 文档](https://github.com/microsoft/markitdown)
- [Poppler 下载](https://github.com/oschwartz10612/poppler-windows/releases)

---

**最后更新**: 使用系统时间API获取（`datetime.now()`）

