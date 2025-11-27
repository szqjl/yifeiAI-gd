# OCR 璇嗗埆鍜 Markitdown 杞鎹㈡寚鍗

## 馃搵 姒傝堪

鏈鎸囧崡浠嬬粛濡備綍浣跨敤鑵捐浜 OCR API 璇嗗埆鍥剧墖/PDF锛屼互鍙婁娇鐢 markitdown 杞鎹㈡枃妗ｄ负 Markdown 鏍煎紡銆

---

## 馃敡 鐜澧冨噯澶

### 1. 瀹夎 Python 渚濊禆

```bash
# 瀹夎呰吘璁浜 SDK
py -3.12 -m pip install tencentcloud-sdk-python

# 瀹夎 markitdown
py -3.12 -m pip install markitdown

# 瀹夎 PDF 澶勭悊宸ュ叿锛堝傞渶瑕侊級
py -3.12 -m pip install pdf2image pillow
```

### 2. 瀹夎 Poppler锛圥DF 杞鍥剧墖闇瑕侊級

```bash
# 浣跨敤 winget 瀹夎
winget install Poppler
```

瀹夎呭悗锛屽皢 Poppler 鐨 `Library\bin` 鐩褰曟坊鍔犲埌绯荤粺 PATH锛屾垨璁剧疆鐜澧冨彉閲忥細
```bash
set POPPLER_PATH=C:\poppler-25.07.0\Library\bin
```

---

## 馃攽 鑵捐浜 OCR 閰嶇疆

### 1. 鑾峰彇 API 瀵嗛挜

1. 鐧诲綍鑵捐浜戞帶鍒跺彴锛歨ttps://console.cloud.tencent.com/cam/capi
2. 鍒涘缓 API 瀵嗛挜锛岃幏鍙 `SecretId` 鍜 `SecretKey`
3. 寮閫 OCR 鏈嶅姟锛歨ttps://console.cloud.tencent.com/ocr

### 2. 璁剧疆鐜澧冨彉閲忥紙鍙閫夛級

```bash
# Windows CMD
set TENCENT_SECRET_ID=浣犵殑SecretId
set TENCENT_SECRET_KEY=浣犵殑SecretKey

# Windows PowerShell
$env:TENCENT_SECRET_ID="浣犵殑SecretId"
$env:TENCENT_SECRET_KEY="浣犵殑SecretKey"
```

---

## 馃摳 OCR 璇嗗埆鍥剧墖

### 鍩烘湰鐢ㄦ硶

```python
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.ocr.v20181119 import ocr_client, models
import base64

# 閰嶇疆 API 瀵嗛挜
SECRET_ID = "浣犵殑SecretId"
SECRET_KEY = "浣犵殑SecretKey"
REGION = "ap-beijing"

# 璇诲彇鍥剧墖骞惰浆鎹涓 base64
with open("image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# 鍒涘缓 OCR 瀹㈡埛绔
cred = credential.Credential(SECRET_ID, SECRET_KEY)
http_profile = HttpProfile()
http_profile.endpoint = "ocr.tencentcloudapi.com"
client_profile = ClientProfile()
client_profile.httpProfile = http_profile
client = ocr_client.OcrClient(cred, REGION, client_profile)

# 鍒涘缓璇锋眰
req = models.GeneralBasicOCRRequest()
req.ImageBase64 = image_data

# 璋冪敤 API
resp = client.GeneralBasicOCR(req)

# 鎻愬彇鏂囨湰
text = "\n".join([item.DetectedText for item in resp.TextDetections])
print(text)
```

---

## 馃搫 OCR 璇嗗埆 PDF

### 鏂规硶锛氶愰〉杞鎹涓哄浘鐗囧悗璇嗗埆

```python
from pdf2image import convert_from_path
import os

# 璁剧疆 Poppler 璺寰勶紙濡傛灉鏈娣诲姞鍒 PATH锛
poppler_path = r"C:\poppler-25.07.0\Library\bin"
os.environ["POPPLER_PATH"] = poppler_path

# 灏 PDF 杞鎹涓哄浘鐗
images = convert_from_path("document.pdf", poppler_path=poppler_path)

# 閫愰〉璇嗗埆
all_text = []
for i, image in enumerate(images):
    # 灏嗗浘鐗囪浆鎹涓 base64
    import io
    import base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # OCR 璇嗗埆锛堜娇鐢ㄤ笂闈㈢殑浠ｇ爜锛
    # ... OCR 璋冪敤浠ｇ爜 ...
    
    all_text.append(f"## 绗 {i+1} 椤礬n\n{text}")

# 鍚堝苟鎵鏈夋枃鏈
final_text = "\n\n".join(all_text)
```

---

## 馃摑 Markitdown 杞鎹

### 鍩烘湰鐢ㄦ硶

```python
from markitdown import MarkItDown
from pathlib import Path

# 鍒涘缓杞鎹㈠櫒
md = MarkItDown()

# 杞鎹 DOCX 鏂囦欢
docx_file = Path("document.docx")
result = md.convert(str(docx_file))

# 淇濆瓨涓 Markdown
output_file = docx_file.with_suffix('.md')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(result.markdown)

print(f"鉁 杞鎹㈠畬鎴: {output_file}")
```

### 鏀鎸佺殑鏍煎紡

- DOCX锛圵ord 鏂囨。锛
- PDF锛堥儴鍒嗘敮鎸侊紝鎵鎻忕増 PDF 鍙鑳借瘑鍒涓嶄匠锛
- 鍥剧墖锛堥渶瑕 OCR锛宮arkitdown 鏈韬瀵瑰浘鐗囨枃鏈璇嗗埆鏈夐檺锛

---

## 馃攧 瀹屾暣宸ヤ綔娴佺ず渚

### 鍦烘櫙锛氬皢鎵鎻忕増 PDF 杞鎹涓 Markdown

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""灏嗘壂鎻忕増 PDF 杞鎹涓 Markdown"""

from pdf2image import convert_from_path
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.ocr.v20181119 import ocr_client, models
import base64
import io
import os

# 閰嶇疆
SECRET_ID = "浣犵殑SecretId"
SECRET_KEY = "浣犵殑SecretKey"
REGION = "ap-beijing"
POPPLER_PATH = r"C:\poppler-25.07.0\Library\bin"

# 鍒濆嬪寲 OCR 瀹㈡埛绔
cred = credential.Credential(SECRET_ID, SECRET_KEY)
http_profile = HttpProfile()
http_profile.endpoint = "ocr.tencentcloudapi.com"
client_profile = ClientProfile()
client_profile.httpProfile = http_profile
client = ocr_client.OcrClient(cred, REGION, client_profile)

# PDF 杞鍥剧墖
pdf_path = "document.pdf"
images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)

# 閫愰〉璇嗗埆
all_pages = []
for i, image in enumerate(images, 1):
    print(f"姝ｅ湪璇嗗埆绗 {i}/{len(images)} 椤...")
    
    # 鍥剧墖杞 base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # OCR 璇嗗埆
    req = models.GeneralBasicOCRRequest()
    req.ImageBase64 = image_data
    resp = client.GeneralBasicOCR(req)
    
    # 鎻愬彇鏂囨湰
    text = "\n".join([item.DetectedText for item in resp.TextDetections])
    all_pages.append(f"## 绗 {i} 椤礬n\n{text}")

# 淇濆瓨涓 Markdown
output_file = "document_ocr.md"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("\n\n".join(all_pages))

print(f"鉁 杞鎹㈠畬鎴: {output_file}")
```

---

## 鈿狅笍 娉ㄦ剰浜嬮」

### OCR 璇嗗埆

1. **鍏嶈垂棰濆害**锛氭柊鐢ㄦ埛姣忔湀鏈 1000 娆″厤璐硅皟鐢锛岄渶瑕佸紑鍚鎸夐噺浠樿垂鎵嶈兘浣跨敤
2. **鏂囦欢澶у皬闄愬埗**锛氬崟娆¤锋眰涓嶈秴杩 10MB
3. **PDF 澶勭悊**锛氬ぇ PDF 闇瑕侀愰〉杞鎹涓哄浘鐗囧悗璇嗗埆
4. **璇嗗埆璐ㄩ噺**锛氭壂鎻忕増鏂囨。璇嗗埆璐ㄩ噺鍙栧喅浜庡浘鐗囨竻鏅板害

### Markitdown 杞鎹

1. **DOCX 鏂囦欢**锛氳浆鎹㈡晥鏋滆緝濂
2. **PDF 鏂囦欢**锛氫粎鏀鎸佹枃鏈鍨 PDF锛屾壂鎻忕増 PDF 闇瑕佸厛 OCR
3. **鍥剧墖鏂囦欢**锛歮arkitdown 瀵瑰浘鐗囨枃鏈璇嗗埆鏈夐檺锛屽缓璁浣跨敤 OCR

---

## 馃摎 鐩稿叧璧勬簮

- [鑵捐浜 OCR 鏂囨。](https://cloud.tencent.com/document/product/866)
- [Markitdown 鏂囨。](https://github.com/microsoft/markitdown)
- [Poppler 涓嬭浇](https://github.com/oschwartz10612/poppler-windows/releases)

---

**鏈鍚庢洿鏂**: 浣跨敤绯荤粺鏃堕棿API鑾峰彇锛坄datetime.now()`锛

