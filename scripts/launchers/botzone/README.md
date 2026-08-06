# Botzone 在线 Bot 打包与上传（V8）

让 V8 决策引擎作为 **Botzone 在线 Bot**（非 Local AI HTTP 轮询）运行，脱离本机、持续在 Botzone 平台在线对战。

## 与 Local AI 的区别

| 维度 | Local AI（现有 `run_v8_vs_botzone.py`） | 在线 Bot（本目录） |
|------|----------------------------------------|--------------------|
| 运行位置 | 本机长驻进程，HTTP 轮询 | Botzone 服务器沙箱 |
| 交互协议 | HTTP GET `/api/{user}/{key}/localai` | stdin/stdout JSON（每回合一行） |
| 引擎加载 | 启动一次，常驻 | 每回合冷启动 → 用 KEEP_RUNNING 长驻 |
| 对手 | Local AI 只能 vs Botzone 现有 Bot | 可入排行榜 / 被其他 Bot 挑战 |
| 凭证 | user_id + api_key | 无需凭证（上传代码即运行） |

## 协议（Botzone JSON Interaction）

每回合 Botzone 调用一次进程：

```
stdin:  {"requests": [...], "responses": [...], "data": ..., "globaldata": ...}
stdout: {"response": "...", "debug": "...", "data": ...}
```

- `requests` 为**该局从发牌到当前回合**的全部请求（首元素是 `deal`），`responses` 为自己此前的全部响应；
- `__main__.py` 通过 `handle_online_turn()` 全量重放历史重建状态，再对当前回合决策；
- 响应后再输出一行 `>>>BOTZONE_REQUEST_KEEP_RUNNING<<<` 保持进程存活，**引擎只加载一次**（加载约 2s，冷启动会超时）。

## 打包

```bash
python scripts/launchers/botzone/package_v8_online.py            # 生成 data/eval/botzone/v8_online_bot_YYYYMMDD_vN.zip
python scripts/launchers/botzone/package_v8_online.py --rev 3    # 指定版本号
python scripts/launchers/botzone/package_v8_online.py --check    # 校验最新 zip
python scripts/launchers/botzone/package_v8_online.py --dry-run  # 只列待打包文件
```

zip 结构（Botzone 要求 zip 根含 `__main__.py`）：

```
v8_online_bot_YYYYMMDD_vN.zip
├── __main__.py      # 入口（stdin/stdout 协议 + KEEP_RUNNING）
└── src/             # V8 决策链（engine / adapter / grouping / endgame / guards ...）
```

## 上传

1. Botzone 控制台 → My Bots → 新建 Bot → 语言 Python → 上传 zip；
2. 数据文件（如有）不打包，用 Botzone「用户存储空间」上传，代码内以 `data` 路径访问（当前 V8 决策链无需数据文件）；
3. 第三方库 numpy/scipy 由 Botzone python3 沙箱预装；torch 已惰性导入（缺失时 V8 走 `model=None` 规则栈，仍可出牌）。

## 本地验证（上传前必做）

```bash
# 1. 直接跑入口（喂 deal + play 请求，应输出合法 response）
echo '{"requests":[{"stage":"deal",...}],"responses":[]}' | python scripts/launchers/botzone/__main__.py

# 2. 打包后 zip 直跑（Botzone 官方推荐自测方式）
python data/eval/botzone/v8_online_bot_20260806_v2.zip < 请求.json

# 3. 解压目录跑（模拟 Botzone 解压执行）
cd data/eval/botzone && unzip -o v8_online_bot_*.zip -d test_dir && cd test_dir && python __main__.py
```

**通过标准**：stdout 输出 `{"response":"[[...]]","data":...}` 且含 `>>>BOTZONE_REQUEST_KEEP_RUNNING<<<`。

## 工作流（本地迭代 → 验收 → 重打包）

1. 改 V8 决策代码（`src/v/nn/...`）→ `pytest` 全绿；
2. 本地 `echo | python __main__.py` 冒烟；
3. `package_v8_online.py` 重打包（版本号自动 +1，默认删旧版，`--keep` 保留）；
4. zip 直跑 + 解压目录跑双验证；
5. Botzone 上传新 zip，跑对局对比 KPI。

## 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| `ModuleNotFoundError: No module named 'src'` | `__main__.py` 的 path 推算错 | 确保打包后 `__main__.py` 与 `src/` 同级 |
| 冷启动超时（每回合 5s 级） | 引擎加载 ~2s 冷启动超限 | 必须 KEEP_RUNNING 长驻（已在入口实现） |
| torch 相关 ImportError | 沙箱 torch 版本旧/缺失 | torch 惰性导入已兜底，model 恒 None 走规则栈 |
| 对局第一回合 EOFError | 协议不匹配 | 确认 stdin 是单行 JSON，`input()` 读取 |
