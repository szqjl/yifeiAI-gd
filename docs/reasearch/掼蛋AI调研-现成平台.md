---
created: 2026-06-01
updated: 2026-06-02
reviewed: 2026-06-02
status: 活跃
tags: [调研, 平台, 工具]
related_gua: []
related_iter: []
next_review: 2026-09-02
---

# 掼蛋AI平台调研（新增）

> 调研时间：2026-06-01
> 目标：找现成的掼蛋服务器+AI平台

---

## 一、南京邮电大学掼蛋离线平台（直接可用）

**性质：** 全国人工智能博弈大赛官方训练平台

**连接方式：**
```
WebSocket地址：ws://127.0.0.1:23456/game/{user_info}
```

**规则：**
- 仅支持 Windows
- 只能4个AI同时对战
- 不限制编程语言
- 通过JSON数据与平台交互

**平台API协议（已破）:**

平台→AI（JSON格式，type区分）：
- `type: 0` — 小局结束
- `type: 1` — 通知其他AI的动作（广播）
- `type: 2` — 请求当前AI动作（需要响应）

AI→平台：
```json
{"action": [[0, 'Q']], "type": "Pair", "rank": "Q"}
```

**牌型对照：**
| 牌型 | 英文 |
|------|------|
| 单张 | Single |
| 对子 | Pair |
| 三张 | Trips |
| 三带二 | ThreeWithTwo |
| 钢板 | TripsPair |
| 顺子 | Straight |
| 同花顺 | StraightFlush |
| 炸弹 | Bomb |
| 进贡/还贡 | tribute/back |
| 过 | PASS |

**下载地址：** http://gameai.njupt.edu.cn（搜索"掼蛋平台使用说明书"）

**随机AI示例代码（Python）：**
```python
from ws4py.client.threadedclient import WebSocketClient
import json, random

class ExampleClient(WebSocketClient):
    def received_message(self, message):
        content = json.loads(str(message))
        if "action_list" in content and content["action_list"]:
            card_type = random.choice(list(content["action_list"].keys()))
            rank = random.choice(list(content["action_list"][card_type].keys()))
            action = random.choice(list(content["action_list"][card_type][rank]))
            self.send(json.dumps({"action": action, "type": card_type, "rank": rank}))

ws = ExampleClient('ws://127.0.0.1:23456/game/client1')
ws.connect()
ws.run_forever()
```

---

## 二、OpenGuanDan（大规模基准平台，arXiv 2026）

**论文：** arXiv:2602.00676v1
**性质：** 学术基准平台，带标准API

**特点：**
- 每玩家独立 action-upload API
- JSON格式 observation/action 接口
- 支持人类-AI评估

**观测维度：**
- 54维手牌向量
- 28维玩家人数one-hot
- 79维动作/状态向量

**算法排名（自对弈）：**
| 算法 | 胜率 |
|------|------|
| GS2 | 62% vs DanZero |
| SDMC | 57.6% vs DanZero |
| DanZero | baseline |

---

## 三、ChinaZZH/GuanDan（GitHub服务器源码）

**性质：** 掼蛋游戏服务器代码
**地址：** https://github.com/ChinaZZH/GuanDan
**语言：** 服务器完整源码

---

## 四、AltmanD/Guandan（游戏引擎）

**性质：** 完整Python游戏引擎
**地址：** https://github.com/AltmanD/Guandan
**特点：** 完整掼蛋规则，含出牌逻辑

---

## 五、商业平台（未查到开放API）

| 平台 | 情况 |
|------|------|
| 欢乐掼蛋 | 商业黑盒，无API |
| 同城掼蛋 | 商业黑盒，无API |
| 网易数智 | 对公合作，不开放 |

---

## 六、结论与建议

**最推荐路径：**

```
南邮离线平台（Windows）
    ↓
写一个WebSocket客户端（Python）
    ↓
接入Danzero+/我们的AI模型
    ↓
在Windows上跑4AI对战评测
```

**原因：**
1. ✅ 平台现成，协议已破，有随机AI示例
2. ✅ 不需要自己写游戏引擎
3. ✅ 可以直接评测胜率
4. ⚠️ 仅支持Windows（我们可以在用户Windows机器上跑）

**替代方案（Linux服务器）：**
1. 用 AltmanD/Guandan 自己搭游戏引擎
2. 用 OpenGuanDan 平台协议自己实现

---

## 七、下一步行动

- [ ] 在用户Windows机器上安装南邮离线平台
- [ ] 基于示例代码，写Danzero+的WebSocket客户端
- [ ] 接入我们的AI模型，开始自对弈评测
