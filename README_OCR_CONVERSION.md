# PDF OCR + Markitdown 转换说明

## ? 使用步骤

### 1. 获取腾讯云 OCR API 密钥

1. 访问：https://console.cloud.tencent.com/cam/capi
2. 创建 API 密钥，获取 `SecretId` 和 `SecretKey`
3. 开通 OCR 服务：https://console.cloud.tencent.com/ocr

### 2. 设置环境变量

**Windows PowerShell:**
```powershell
$env:TENCENT_SECRET_ID = "你的SecretId"
$env:TENCENT_SECRET_KEY = "你的SecretKey"
```

**Windows CMD:**
```cmd
set TENCENT_SECRET_ID=你的SecretId
set TENCENT_SECRET_KEY=你的SecretKey
```

**或者编辑 `run_ocr_conversion.ps1` 文件，填入你的密钥后运行：**
```powershell
.\run_ocr_conversion.ps1
```

### 3. 安装依赖（如果未安装）

```bash
pip install pdf2image pillow
pip install tencentcloud-sdk-python
pip install markitdown
```

### 4. 安装 Poppler（PDF转图片需要）

```bash
winget install Poppler
```

安装后，将 Poppler 的 `Library\bin` 目录添加到系统 PATH，或设置环境变量：
```powershell
$env:POPPLER_PATH = "C:\poppler-25.07.0\Library\bin"
```

### 5. 运行转换脚本

```bash
python convert_pdf_ocr_markitdown.py
```

## ? 转换流程

1. **PDF转图片**：使用 pdf2image 将PDF逐页转换为图片
2. **OCR识别**：使用腾讯云OCR API识别每页图片中的文字
3. **合并文本**：将所有页面的识别结果合并
4. **Markitdown处理**：使用markitdown进一步处理和格式化
5. **保存结果**：保存为 `掼蛋平台使用说明书1006.md`

## ?? 注意事项

1. **免费额度**：新用户每月有 1000 次免费调用
2. **文件大小**：单次请求不超过 10MB
3. **识别质量**：取决于PDF图片清晰度
4. **处理时间**：根据PDF页数，可能需要几分钟到十几分钟

## ? 输出文件

- `docs/gdrules/掼蛋平台使用说明书1006.md` - 最终转换结果
- `docs/gdrules/掼蛋平台使用说明书1006.ocr_temp.md` - OCR中间结果（处理完成后会自动删除）

