# PyTorch (torch) 安装指南

**Python版本**: 3.13  
**更新时间**: 2025-12-05

---

## 📥 官方下载地址

### 1. PyTorch 官网（推荐）

**官网地址**: https://pytorch.org/

**安装命令生成器**: https://pytorch.org/get-started/locally/

在官网上选择：
- **PyTorch Build**: Stable (2.6.0) 或 Latest (2.7.1)
- **Your OS**: Windows
- **Package**: Pip
- **Language**: Python
- **Compute Platform**: CPU（如果没有GPU）或 CUDA（如果有GPU）

---

## 🔗 直接下载链接

### CPU版本（推荐，如果不需要GPU）

```bash
# Python 3.13 支持的版本（2.6.0及以上）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### CUDA版本（如果有NVIDIA GPU）

```bash
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

---

## 📦 PyPI 直接安装

### 方法1：使用pip安装（最简单）

```bash
# 安装最新稳定版（Python 3.13支持）
python -m pip install torch

# 或指定版本
python -m pip install torch==2.6.0
```

### 方法2：从requirements.txt安装

```bash
python -m pip install -r requirements.txt
```

---

## 🚀 针对当前环境的安装命令

### 当前Python环境：Python 3.13

**推荐命令**（CPU版本）：
```bash
C:\Python313\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

**或使用官方源**：
```bash
C:\Python313\python.exe -m pip install torch
```

---

## 📋 完整依赖安装

### 安装所有训练相关依赖

```bash
# 1. 安装torch
C:\Python313\python.exe -m pip install torch

# 2. 安装gymnasium
C:\Python313\python.exe -m pip install gymnasium

# 3. 安装websockets
C:\Python313\python.exe -m pip install websockets

# 4. 或一次性安装所有依赖
C:\Python313\python.exe -m pip install torch gymnasium websockets pyyaml psutil
```

---

## 🔍 验证安装

安装完成后，验证是否成功：

```bash
python -c "import torch; print('PyTorch版本:', torch.__version__); print('CUDA可用:', torch.cuda.is_available())"
```

**预期输出**：
```
PyTorch版本: 2.6.0
CUDA可用: False  (如果是CPU版本)
```

---

## ⚠️ 常见问题

### 问题1：Python 3.13 兼容性

**问题**: Python 3.13 是较新版本，某些包可能不完全支持

**解决方案**:
- 使用 torch 2.6.0 及以上版本（已支持Python 3.13）
- 或降级到 Python 3.11 或 3.12

### 问题2：依赖冲突

**问题**: 安装时出现依赖冲突错误

**解决方案**:
```bash
# 先升级pip
python -m pip install --upgrade pip

# 然后安装torch
python -m pip install torch
```

### 问题3：下载速度慢

**解决方案**:
```bash
# 使用国内镜像源（清华大学）
pip install torch -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用阿里云镜像
pip install torch -i https://mirrors.aliyun.com/pypi/simple/
```

---

## 📝 快速安装脚本

创建 `install_torch.bat` 文件：

```batch
@echo off
echo 正在安装PyTorch...
C:\Python313\python.exe -m pip install --upgrade pip
C:\Python313\python.exe -m pip install torch gymnasium websockets
echo.
echo 验证安装...
C:\Python313\python.exe -c "import torch; print('PyTorch版本:', torch.__version__)"
echo.
echo 安装完成！
pause
```

---

## 🔗 相关链接

- **PyTorch官网**: https://pytorch.org/
- **PyTorch文档**: https://pytorch.org/docs/stable/index.html
- **PyPI torch页面**: https://pypi.org/project/torch/
- **GitHub**: https://github.com/pytorch/pytorch

---

## ✅ 安装检查清单

- [ ] pip已安装并可正常使用
- [ ] 已选择CPU或CUDA版本
- [ ] 已运行安装命令
- [ ] 已验证torch可以正常导入
- [ ] 已安装其他依赖（gymnasium, websockets等）

---

**创建时间**: 2025-12-05  
**最后更新**: 2025-12-05

