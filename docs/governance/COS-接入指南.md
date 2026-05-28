# 腾讯云 COS — 唯一 Artifact 网盘

> 治理总纲：[M-V-Series-治理方案.md](./M-V-Series-治理方案.md)  
> **约定：大块数据只放 COS，不再使用迅雷等第二套网盘。**

COS 在控制台或 [COSBrowser](https://cloud.tencent.com/document/product/436/11366) 中可像网盘一样浏览；本仓库用脚本与本地 `data/artifacts/` 镜像对齐。

---

## 1. 什么放 COS、什么不放

| 放 COS（桶内统一目录） | 仍只留本机、不进 COS |
|------------------------|----------------------|
| 30 局 regression replay | 日常 `logs/`（太碎） |
| incident 单局、eval 摘要 | `__pycache__/` |
| 需共享的 `.pth`（放 `models/` 前缀下） | 临时中间 checkpoint（本地训完再挑版上传） |
| 归档用 `training_logs` 摘要（可选） | |

Git：**仅代码** + `data/manifests/*.json`。

本地统一镜像目录：

```text
data/artifacts/          # 与 COS 对应，已 .gitignore
  replays/
  models/
  eval/
```

---

## 2. 控制台配置（一次）

1. [创建存储桶](https://console.cloud.tencent.com/cos/bucket)：私有读写、**不启 CDN**、地域须与 `COS_REGION` 一致（本项目桶在 **`ap-shanghai`**）  
2. [API 密钥](https://console.cloud.tencent.com/cam/capi)  
3. 桶内建议前缀（可选，与 `COS_ARTIFACT_PREFIX` 一致）：

```text
replays/regression-lalala-v1/
replays/incidents/
models/
eval/summaries/
```

4. **网盘式管理（可选）**：安装 [COSBrowser](https://cosbrowser.cloud.tencent.com/)，登录后拖拽上传/下载，与脚本共用同一桶。

---

## 3. 本机配置（官方 Python SDK）

| 项 | 值 |
|----|-----|
| PyPI | [`cos-python-sdk-v5`](https://pypi.org/project/cos-python-sdk-v5/) |
| 导入 | `from qcloud_cos import CosConfig, CosS3Client` |
| 文档 | [Python SDK 快速入门](https://cloud.tencent.com/document/product/436/12269) |
| 本仓库 | `scripts/cos/cos_client.py` |

```bash
cd D:/YiFeiAI-GD
pip install -r requirements.txt

cp config/cos.env.example config/cos.env
# 填写 COS_SECRET_ID、COS_SECRET_KEY、COS_BUCKET（名称-APPID）、COS_REGION

python scripts/cos/verify_cos.py
```

`config/cos.env` 已 `.gitignore`，勿提交。

---

## 4. 多久往 COS 推一次？

**不按日历，按事件。** 本地 `data/artifacts/` 是工作台，COS 是共享备份与换机源。

| 时机 | 推什么 | 频率感 |
|------|--------|--------|
| **改 M 行为且 PR 要合并** | 更新后的 regression（最多替换 manifest 里 5 局）+ 跑过 diff 的版本 | **每个行为相关 PR 一次** |
| **修完一类 lalala 问题（RCA 结案）** | 问题局进 `replays/incidents/`，必要时替换回归集里 1～5 局 | **每类问题 1 次** |
| **换电脑 / 另一台机器要跑** | `sync_pull_all` 对方拉；或你本机先 `sync` 上传确保云端齐 | **按需** |
| **定了新「当前用」模型** | 只上传最终 1～2 个 `.pth` 到 `models/` | **里程碑**（不是每次 epoch） |
| **换电脑 / 换 Agent 接续分析** | handoff 进 **Git**；大文件进 COS | 见 [分析接续-handoff.md](./分析接续-handoff.md) |
| **日常改代码、未动策略** | 不推 | — |
| **训练中间 checkpoint** | 不推（留本机）；除非要远程续训 | — |

**实用节奏（单人 M 迭代）：**

- 平时：**0 次/天**（只 git push 代码即可）。
- 有进展时：**每周 0～2 次**（合并 PR 或更新回归集时上传）。
- **最少**：至少保证 COS 上 **30 局 regression 与 manifest 一致**；新机器能 `pull_regression` 通过。

上传后记得改 `data/manifests/regression-lalala-v1.json` 的 `sha256`（用 `upload_regression.py` 会打印），并 **git commit manifest**。

---

## 5. 日常命令（只认 COS）

| 操作 | 命令 |
|------|------|
| **验证 SDK / 密钥** | `python scripts/cos/verify_cos.py` |
| 上传一局 replay | `python scripts/cos/upload_regression.py game_records/xxx.json --id reg-001` |
| 只拉 regression 清单 | `python scripts/cos/pull_regression.py` |
| **换电脑：拉整库 artifact** | `python scripts/cos/sync_pull_all.py` |
| 控制台/COSBrowser | 与脚本同一桶；上传大文件可拖拽 |

上传模型：控制台或 COSBrowser 放到 `models/你的文件.pth`；本地镜像路径为 `data/artifacts/models/`。

---

## 6. 计费说明

开通后默认 **按量计费**；新用户获赠 **标准存储容量包**（个人 **50 GB / 6 个月**），结算顺序：免费容量包 → 自购包 → 按量。详见 [计费概述](https://cloud.tencent.com/document/product/436/16871)、[免费额度](https://cloud.tencent.com/document/product/436/62290)。

| 计费项 | 本项目 |
|--------|--------|
| 存储容量 | replay + 少量模型通常 **&lt; 数 GB**，6 个月内多在 50 GB 包内 |
| 外网下行流量 | 换机 `sync_pull_all` 时产生；小团队偶尔拉取，费用通常很低 |
| 不用后 | **须删除桶内数据**，否则持续产生存储费 |

**省流量习惯**：换机才全量 `sync_pull_all`；日常用 `pull_regression` 只拉 30 局；勿开 CDN。

---

## 7. 故障排查

| 现象 | 处理 |
|------|------|
| `NoSuchKey` | 检查 key 与桶、地域 |
| `AccessDenied` | 密钥需有该桶读写权限 |
| 列表为空 | 检查 `COS_ARTIFACT_PREFIX` 是否与桶内路径一致 |

---

## 8. 相关文件

| 文件 | 说明 |
|------|------|
| `config/cos.env.example` | 配置模板 |
| `scripts/cos/cos_client.py` | 官方 SDK 封装 |
| `scripts/cos/verify_cos.py` | 连通验证 |
| `scripts/cos/upload_regression.py` | 上传单局 |
| `scripts/cos/pull_regression.py` | 按 manifest 拉 regression |
| `scripts/cos/sync_pull_all.py` | 拉整库 artifact |
| `data/manifests/regression-lalala-v1.json` | 30 局清单 |
