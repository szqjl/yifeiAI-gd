# WF-14 · 用最新代码重启 Botzone 监听

> **目的**：本仓库代码更新（拉取新 commit / 修完 Botzone 相关 GUA）后，重启 `scripts/launchers/v8/run_v8_vs_botzone.py` 监听进程，让 Botzone 对局使用**最新决策引擎代码**。ITERATIONS 各行的「待做：重启监听加载新代码」即指向本工作流。
> **与 WF-13 分工**：WF-13 = 分析 Botzone 对局失败步的**适配层链路**；**WF-14 = 运维动作**（让新代码上线生效），是 WF-13 / GUA 修复闭环的最后一步，不产出分析结论。
> **与 WF-08 分工**：WF-14 只是**本地重启进程，不涉及 commit/push**；代码可先经 WF-08 推送再 `git pull`，也可直接以本地未推送改动重启。

---

## 1. 触发

| 触发词 | 示例 |
|--------|------|
| 重启监听 / 加载新代码 | 「重启监听加载新代码」 |
| Botzone 监听 / listener | 「监听挂了 / 用最新代码重启监听」 |
| 修完 Botzone 相关 GUA 后 | 「GUA-198 修完，重启监听验证」 |
| 拉取远端最新代码后 | 「pull 完 v8-dev，重启 Botzone 监听」 |
| 监听无新对局 / 进程不在 | 「Botzone 监听进程没在跑」 |

**输入最少信息**：无硬性要求。凭证见 §2.2。

---

## 2. Agent 必做步骤（按序）

### 2.0 Agent 自检（动手前 · 不可跳）

| # | 检查项 | 通过标准 |
|---|--------|----------|
| 1 | 当前分支 = 目标分支（v8-dev） | `git branch --show-current` = `v8-dev` |
| 2 | 本地代码 = 要生效的版本 | 已 `git pull`，或已明确要加载本地未推送改动 |
| 3 | 相关回归通过 | `tests/test_botzone_adapter.py` 绿（+ 相关 GUA 测试） |
| 4 | 凭证可用（user_id / api_key / opponent_bot_id） | §2.2 固定值已写入，无需额外获取 |
| 5 | 精确锁定待杀进程 | §2.3 用命令行匹配确认，**禁止** `Stop-Process` 全杀 python |

### 2.1 拉取最新代码（可选但推荐）

改动已推送远端时先同步（未推送的本地改动则跳过本步）：

```powershell
git fetch origin
git pull origin v8-dev
```

### 2.2 准备启动参数（凭证）

启动脚本 `scripts/launchers/v8/run_v8_vs_botzone.py` **必填** `--user-id` / `--api-key`（仓库不落盘凭证，见下）。

**固定地址**（2026-08-17 起生效）：

| 参数 | 固定值 |
|------|--------|
| `--base-url` | `https://www.botzone.org.cn/api` |
| `--user-id` | `6a6411aa27e7bf01db0291c5`（Local AI bot_id） |
| `--api-key` | `2897963415` |
| `--teammate-bot-id` | `686264afa4349e61674f526a`（Joker） |

> **URL 格式**：`{base_url}/{user_id}/{api_key}/localai` → `https://www.botzone.org.cn/api/6a6411aa27e7bf01db0291c5/2897963415/localai`

**常用参数**：

| 参数 | 说明 |
|------|------|
| `--opponent-bot-id` | 指定则自动建对局；**不指定则只监听手动创建的对局** |
| `--games N` | 自动建 N 局（仅对手模式生效） |

### 2.3 停止旧监听（精确杀）

**禁止** `Get-Process python | Stop-Process` 一把梭——会误杀同机其他 python 进程。须按命令行精确定位：

```powershell
# 按命令行匹配 Botzone 监听进程（推荐）
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*run_v8_vs_botzone*' } |
  Select-Object ProcessId, CommandLine

# 一行式：定位并强制结束（仅杀掉 run_v8_vs_botzone 监听）
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*run_v8_vs_botzone*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# 或：tasklist + wmic
tasklist | rg -i python
wmic process where "name='python.exe'" get ProcessId,CommandLine | rg -i botzone
```

确认 PID 后（taskkill 备选）：

```powershell
taskkill //PID <PID> //F
```

### 2.4 用最新代码重启监听

在**仓库根目录**运行（引擎 Import 依赖根目录路径，否则报「请确保在仓库根目录运行」）。

**Windows / PowerShell 7（推荐，仓库当前运行平台）**：

```powershell
# 后台启动（-PassThru 拿到进程对象；脚本自带时间戳日志，无需手动重定向）
$proc = Start-Process -FilePath "python" -ArgumentList @(
  "scripts/launchers/v8/run_v8_vs_botzone.py",
  "--user-id", "6a6411aa27e7bf01db0291c5",
  "--api-key", "2897963415",
  "--base-url", "https://www.botzone.org.cn/api",
  "--teammate-bot-id", "686264afa4349e61674f526a"
) -WorkingDirectory (Get-Location) -RedirectStandardOutput "logs\_listener_stdout.log" `
  -RedirectStandardError "logs\_listener_stderr.log" -PassThru -WindowStyle Hidden
$proc.Id
```

**Linux / WSL bash（若使用）**：

```bash
nohup python scripts/launchers/v8/run_v8_vs_botzone.py \
  --user-id 6a6411aa27e7bf01db0291c5 \
  --api-key 2897963415 \
  --base-url https://www.botzone.org.cn/api \
  --teammate-bot-id 686264afa4349e61674f526a \
  > logs/v8_vs_botzone_$(date +%Y%m%d_%H%M%S).log 2>&1 &
echo "PID=$!"
```

> 脚本自身也会建 `logs/v8_vs_botzone_<时间戳>.log`（logging FileHandler）；PowerShell 的 `_listener_stdout/stderr.log` 与 bash 的 nohup 重定向都只是兜底，**最终以脚本自身生成的时间戳日志为准**（脚本内部已对 stdout/stderr 强制 UTF-8）。

### 2.5 验证

```powershell
# 1) 进程存活
tasklist | rg -i python

# 2) 日志（GBK 乱码时 iconv -f GBK -t UTF-8）
tail -20 logs/v8_vs_botzone_*.log
```

**通过标准**：
- 日志出现 `V8 vs Botzone (Local AI)` 与 `user_id`；
- 日志出现 `V8 决策引擎加载完成`；
- 带 `--opponent-bot-id` 时：`对局创建成功: <match_id>`；**或**服务器侧 5xx / 403 / `{"error":"Kicked"}` —— Botzone 服务器故障，**非本地失败，监听进程存活即算成功**。

### 2.6 收尾

- 若由 ITERATIONS 某行「待做：重启监听加载新代码」触发 → 在该行标注已重启（改状态 / 追加说明），供下轮追踪。
- 重启进程是本地运维、无代码变更 → **不 commit / push**（同 WF-08 治理，L2 产物不得入库）。

---

## 3. 命令与文件速查

| 项 | 命令 / 文件 |
|----|-------------|
| 启动脚本 | `scripts/launchers/v8/run_v8_vs_botzone.py` |
| 日志 | `logs/v8_vs_botzone_YYYYMMDD_HHMMSS.log`（不进 Git） |
| 回归测试 | `python -m pytest tests/test_botzone_adapter.py -q`（+ 相关 GUA 测试） |
| 定位 PID | §2.3（CommandLine 匹配 `run_v8_vs_botzone`） |
| 停进程 | §2.3 一行式 / `taskkill //PID <PID> //F` |
| 启动 | §2.4（Windows: `Start-Process ... -PassThru`；bash: nohup） |

---

## 4. 常见问题（FAQ）

| 症状 | 原因 | 处理 |
|------|------|------|
| `ImportError: ... 请确保在仓库根目录运行` | 在非根目录执行 | `cd` 到仓库根目录重跑 |
| PowerShell 下 `nohup` / `$(date ...)` 报错 | bash 语法在 pwsh 不可用 | 用 §2.4 的 `Start-Process` 写法（脚本自带时间戳日志，无需手动重定向） |
| `对局创建失败` / HTTP 500 / 403 / `{"error":"Kicked"}` | Botzone 服务器端问题 | **不是本地失败**；监听进程存活即正常，等待或手动创建对局 |
| 日志 GBK 乱码 | Windows 控制台编码 | 脚本已强制 UTF-8；确认用脚本自身时间戳日志，而非重定向兜底日志 |
| 启动后立刻退出 | 引擎加载失败 / 端口占用 | 看日志尾部错误；确认旧监听已停（§2.3） |
| 多 python 进程难分辨 | 同机跑批 / 其他脚本 | 一律以 CommandLine 含 `run_v8_vs_botzone` 为判据 |

---

## 5. 维护

- 启动脚本参数变更（新增 flag / 改默认值）→ 同步 §2.2、§2.4。
- 换对手 / 队友 Bot → 更新 §2.2 常用参数说明。
- 服务器端错误模式变化 → 更新 §4 FAQ。
