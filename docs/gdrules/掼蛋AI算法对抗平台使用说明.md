# 掼蛋AI算法对抗平台使用说明

> **状态**：目前正在内测中

---

## 📋 游戏规则

游戏规则参考**江苏省体育局的掼蛋竞赛简易规则**中的游戏规则。

**每局游戏参与的AI数量**：4个

---

## 🖥️ 平台基本信息

| 项 | 内容 |
|----|------|
| 平台名称 | 南京邮电大学掼蛋AI算法对抗平台 |
| 平台地址 | https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html |
| 当前版本 | v1006（内测中） |
| 编程语言 | 不限，需 WebSocket + JSON |
| AI 数量 | 4 个（两两组队） |
| 研究合作 | chenxg@njupt.edu.cn |
| 问题反馈 | wuguduofeng@gmail.com / QQ: 519301156 |

### 历史版本

| 版本 | 变更 |
|------|------|
| **v1006** | 调整抗贡规则与比赛版一致；修正手牌表示方法；接口与 v1003 一致 |
| **v1003** | 剔除图形可视化界面；纯命令行窗口；支持 Linux |

---

## 📦 离线环境平台

**下载地址**：`D:\掼蛋算法大赛选手人工智能代码\离线环境平台\guandan_offline_v1006`

### 离线平台使用说明

- **支持运行环境**：Windows/Linux
- **离线平台使用说明书包含**：
  - 使用说明
  - JSON说明
  - JSON例子说明

**离线平台使用说明书**：[掼蛋平台使用说明书1006.md](./掼蛋平台使用说明书1006.md)（对应版本v1006）

### 平台运行要求

1. 离线版本目前支持Windows平台和Linux平台（注：可能会被一些防护软件看做为病毒，添加信任即可或者无视即可）
2. 确认本地端口号23456空闲
3. 解压文件夹之后会得到3个目录及1个文件
   - `clients` -- 包含解析的随机程序
   - `Ubuntu` -- 在Linux系统下可使用的离线平台
   - `windows` -- 在windows系统下可使用的离线平台
   - `使用说明.pdf`

### Ubuntu使用方法

- ubuntu文件夹存放着文件`guandan_offline_v1006`
- 找到`guandan_offline_v1006`所在目录
- 在终端输入如下命令，看见`Ready for connect.`字样即运行成功（请勿占用23456端口）

```bash
./guandan_offline_v1006 10
```

- 其中10为游戏次数（即一方从2打到A，并且双下且当前等级为我方等级）。例如，100次游戏的命令如下

```bash
./guandan_offline_v1006 100
```

### Windows使用方法

- windows文件夹存放着文件`guandan_offline_v1006.exe`
- 找到`guandan_offline_v1006.exe`所在目录
- 在命令行输入如下命令，看见`Ready for connect.`字样即运行成功（请勿占用23456端口）

```cmd
guandan_offline_v1006.exe 10
```

- 其中10为游戏次数。例如，100次游戏的命令如下

```cmd
guandan_offline_v1006.exe 100
```

4. clients文件夹下包含4个示例代码，分别为`client1.py`、`client2.py`、`client3.py`、`client4.py`，及动作类和状态类
   - 示例代码使用方法：
     - 根据对应系统，按上面的使用方法成功运行后，依次运行`client1.py`、`client2.py`、`client3.py`、`client4.py`
     - 注意：由于本版本为命令行版本，所以连满4人之后游戏将自动开始，即在连入`client4.py`之后将自动开始

---

## 🔌 连接与座位

- **编程语言要求**：无限制，通过 **WebSocket** 连接平台，使用 **JSON 数据格式** 通信
- **WebSocket连接地址**：
  - **本地环境**：`ws://127.0.0.1:23456/game/{user_info}`
  - **局域网连接**：将`127.0.0.1`换为局域网本机IP即可
- `user_info`字段表示用户信息，用于标识该算法程序
- 由于是本地的离线平台，不做掉线重连处理，且不会对所发出的错误的动作做任何处理，做出错误动作时服务器会输出错误动作，直至正确的算法程序发送了正确的动作
- **启动**：`guandan_offline_v1006.exe N` 或 `./guandan_offline_v1006 N`；见 `Ready for connect` 后再连 4 客户端
- **支持环境**：Windows / Linux（注意可能被杀毒软件误报，添加信任即可）
- **座位**：**连入顺序** → 0、1、2、3 号；**0+2 一队，1+3 一队**（不可选座）
- **队友**：`teammate_pos = (myPos + 2) % 4`
- **参数 N**：说明书「**游戏次数**」= **平台局数**（`settingTimes` / `completed_games`）。见下文 §局与副。

### 组队规则

默认地，**第一位连接的和第三位连接的自动为一队**，反之亦然。

> **详细的使用方法请参见上述使用说明书**

---

## 🎮 局与副（协议视角）

**局 ⊃ 多副**。平台 `exe N` / 批跑 `--target-games N` 的 **N = 局数**，不是副数（实测 `N=1` → 59 副，2026-05-31）。

### 副 — 最小单位

| 项 | 内容 |
|----|------|
| 流程 | 发牌 →（进贡还贡）→ 出牌 → 四人完牌 → 升级 |
| 协议 | **`episodeOver`**（state.py：「小局结束」） |
| 落盘 | 每座 1 条 JSON；数副用 `total_rounds` / match_key |

### 局 — 更大单位

| 项 | 内容 |
|----|------|
| 含义 | 从 2 打到 A，某队 **A 级本副双上** 过关（PDF `gameOver` 段「一次游戏」） |
| 协议 | 打满 N 局 → **`gameOver`**（`curTimes` = `settingTimes` = N） |
| 批跑 | **`completed_games`** 累计局数；**≠** `episodeOver` 次数 |
| 客户端 | `game_scores_m2.json` → `games[]`（跨副追踪规则一局） |

### 关联定音

```text
1 局  =  多副升级 → 直至 A 级双上结束
1 副  =  1 次 episodeOver
N     =  连续 N 局（非 N 副）
```

| 概念 | 平台 `stage` | 数什么 |
|------|--------------|--------|
| 副 | `episodeOver` | 副数、`game_records` |
| 局 | `gameOver` | `completed_games`、`settingTimes` |

**`victoryNum`**（`gameResult`，**平台下发、按规则正确**）：每 **一整局**（一方 A 级双上过关）结束，赢方 **+1 局**；批跑 N 局后 **`[0]` vs `[1]`** = 各队本批 **赢几局**（同队 0=2、1=3 数值相同；**禁止四席相加**）。**不是副数**。

例（M3 在 0+2、lalala 在 1+3）：`[0,3,0,3]` → lalala 赢 **3 局**、M3 赢 **0 局**；`[3,0,3,0]` → M3 赢 **3 局**、lalala 赢 **0 局**。

**`game_records`**：每条 JSON = **一副**（小局），与 `victoryNum` 无关。

---

## 📡 消息类型

| `type` | 含义 |
|--------|------|
| `notify` | 广播通知，无需回复 |
| `act` | 请求动作，须回复 `{"actIndex": N}`（N = `actionList` 下标） |

## 阶段 `stage`

| stage | type | 说明 |
|-------|------|------|
| `beginning` | notify | 发牌；含 `handCards`、`myPos`（官方示例**无**三等级字段） |
| `tribute` | notify / act | 进贡；notify 的 `result` = `[[进贡位, 收贡位, 牌], ...]` |
| `anti-tribute` | notify | 抗贡；`antiNums`、`antiPos` |
| `back` | notify / act | 还贡；`result` 格式同 tribute |
| `play` | notify / act | 出牌；act 含 `actionList`、`publicInfo`、`selfRank`/`oppoRank`/`curRank` |
| `episodeOver` | notify | **一副结束**（小局）；`order`、`curRank`、`restCards` |
| `gameOver` | notify | 跑满 N **局**（平台「游戏次数」）；`curTimes`、`settingTimes` |
| `gameResult` | notify | 本批结束；**`victoryNum`** = 各队本批 **赢局数**（整局结束计胜）；`draws` |

**解析约束**：仅在对应 `(stage, type)` 下读取该消息字段；其他属性可能是上一轮残留（见 state.py 注释）。

---

## 🃏 JSON数据说明

### 1. 卡牌

使用长度为2的字符串表示，`'S2'`表示黑桃2，下面进行详细说明

- **花色**：黑桃、红桃、梅花、方片分别对应字符`S`、`H`、`C`、`D`。特别地，小王的花色为`S`，大王的花色为`H`
- **点数**：A、2、3、4、5、6、7、8、9、10、J、Q、K分别对应`A`、`2`、`3`、`4`、`5`、`6`、`7`、`8`、`9`、`T`、`J`、`Q`、`K`。即点数10用字符`T`表示。特别地，小王的点数为字符`B`，大王的点数为字符`R`
- 如`'S2'`表示黑桃2，`'HQ'`表示红桃Q；`'SB'`表示小王，`'HR'`表示大王，`'PASS'`表示PASS

### 2. 牌型：[牌型，点数，卡牌]

- 一个牌型表示为一个长度为3的列表（数组），包含三个固定部分：牌型，点数，卡牌
- 牌型的类型为字符串，取值范围为`['Single','Pair','Trips','ThreePair','ThreeWithTwo','TripsPair','Straight','StraightFlush','Bomb','PASS','tribute','back']`
  - 牌型的中英文对照见附件
- 点数的类型为字符串，取值范围为`['A','2','3','4','5','6','7','8','9','T','J','Q','K','B','R','PASS']`
- 卡牌用于表示该牌型所包含的全部卡牌，类型为列表数据结构，例子如下
  - 单张方片5表示为：`['Single','5',['D5']]`
  - 对4表示为：`['Pair','4',['H4','C4']]`
  - PASS：`['PASS','PASS','PASS']`
  - `["tribute","tribute",['D5']]`表示为进贡方片5，`["back","back",['D5']]`表示为还贡方片5

### 3. 游戏过程中的JSON消息

整个游戏过程中，AI会收到平台发来的11种JSON数据格式，可通过JSON中字`(stage,type)`的值来判定是何种类型

- `stage`表示游戏阶段，`type`表示消息类型，下面进行详细说明

#### (1) 游戏开始阶段

`"type":"notify","stage":"beginning"`表示游戏开始阶段，告知每位玩家的手牌情况，例子如下：

```json
{
  "type": "notify",
  "stage": "beginning",
  "handCards": ["S2", "H2", "H2", "C2", "D2", "S3", "H3", "D3", "S4", "S3", "D5", "C6", "H7", "C7", "C8", "D8", "DT", "HJ", "DJ", "HQ", "HQ", "CQ", "SK", "H9", "H9", "C9", "D9", "HR"],
  "myPos": 1
}
```

- 该例子所对应的语义为：游戏开始，我是1号位，我的手牌为handCards

#### (2) 出牌阶段通知

`"type":"notify","stage":"play"`表示出牌阶段，用于通知其他玩家做出的动作，例子如下：

```json
{
  "type": "notify",
  "stage": "play",
  "curPos": 1,
  "curAction": ["Single", "2", ["S2"]],
  "greaterPos": 1,
  "greaterAction": ["Single", "2", ["S2"]]
}
```

- 该例子所对应的语义为：在游戏的出牌阶段，1号位打出单张-黑桃2，当前的最大动作为1号位打出的黑桃2

#### (3) 进贡阶段通知

`"type":"notify","stage":"tribute"`表示进贡阶段，用于通知所有玩家进贡（们）都进贡了什么牌，例子如下：

```json
{
  "type": "notify",
  "stage": "tribute",
  "result": [[0, 3, "S2"]]
}
```

- 该例子所对应的语义为：在游戏的进贡阶段，0号位玩家向3号位玩家进贡了黑桃2
- 若result的值为`[[0,3,'S2'],[2,1,'S2']]`，则对应语义为：在游戏的进贡阶段，0号位玩家向3号位玩家进贡了黑桃2，2号玩家向1号玩家进贡了黑桃2

#### (4) 抗贡阶段通知

`"type":"notify","stage":"anti-tribute"`表示抗贡阶段，用于通知所有玩家，有人抗贡。其中antiNums的取值与antiPos数组的长度所对应，例子如下：

```json
{
  "type": "notify",
  "stage": "anti-tribute",
  "antiNums": 2,
  "antiPos": [0, 2]
}
```

- 该例子所对应的语义为：在游戏的进贡阶段发生了抗贡，抗贡玩家有2名，抗贡的玩家的座位号分别为0号位玩家和2号位玩家

#### (5) 还贡阶段通知

`"type":"notify","stage":"back"`表示还贡阶段，用于通知所有玩家还贡（们）都还贡了什么牌，例子如下：

```json
{
  "type": "notify",
  "stage": "back",
  "result": [[3, 0, "S2"]]
}
```

- 该例子所对应的语义为：在游戏的还贡阶段，3号位玩家向0号位玩家还贡了黑桃2
- 若result的值为`[[3,0,'S2'],[1,2,'S2']]`，则对应语义为：在游戏的还贡阶段，3号位玩家向0号位玩家还贡了黑桃2，1号玩家向2号玩家还贡了黑桃2

#### (6) 小局结束阶段

`"type":"notify","stage":"episodeOver"`表示小局结束阶段，用于通知所有玩家小局结束，例子如下：

```json
{
  "type": "notify",
  "stage": "episodeOver",
  "order": [0, 1, 2, 3],
  "curRank": "A",
  "restCards": [[3, ["C2"]]]
}
```

- 该例子所对应的语义为：在游戏的出牌阶段，该小局结束，结束时所打的等级为A，各个玩家完牌的次序分别为0号位、1号位、2号位、3号位，其中在3号位所剩余的手牌为方片2
- 若完牌次序为`[0,2,1,3]`，即第一完牌的玩家和第二完牌的玩家同属同一队伍时，该小局结束，restCards会收录1号位玩家的手牌和3号位玩家的手牌，例如`restCards:[[3,['C2']],[1,['C2']]]`

#### (7) 游戏结束（到达指定次数）

`"type":"notify","stage":"gameOver"`表示到达指定游戏次数游戏结束，用于通知所有玩家游戏结束，例子如下：

```json
{
  "type": "notify",
  "stage": "gameOver",
  "curTimes": 1,
  "settingTimes": 1
}
```

- 该例子的语义为：当前训练次数为2，设定的游戏次数为3，本次游戏结束
- 注：一次游戏是指：0、1、2、3四位玩家中有任意一方处于A等级时（且当前所打的等级为我方的A等级）同时以第一名、第二名的完牌次序进行完牌，则该次游戏结束

#### (8) 游戏结果

`"type":"notify","stage":"gameResult"`表示到达指定游戏次数游戏结束，用于通知所有玩家游戏结果，例子如下：

```json
{
  "type": "notify",
  "stage": "gameResult",
  "victoryNum": [2, 0, 2, 0],
  "draws": [0, 0, 0, 0]
}
```

- 该例子的语义为：达到设定的场次，其中0号位胜利2次，1号位胜利0次，2号位胜利2次，3号位胜利0次，在所进行的场次游戏中发生的平局次数为：0号位平局0次，1号位平局0次，2号位平局0次，3号位平局0次
- 注：根据规则，当有一方处于A等级，经过2小局游戏后仍未获得游戏胜利，则自动降为2等级，继续从2等级打至A等级。理论上可能会发生死循环的情况（即从A-2，再从2-A），在离线平台中做如下处理
  - 离线平台：任意一方从A降级为2，记为一次，当这个次数达到50次时，该次游戏记为平局
  - 当这一次数达到50次时，在线平台与离线平台的处理略有不同，以大赛官网所公布的规则为准

#### (9) 出牌阶段动作请求

`"type":"act","stage":"play"`表示出牌阶段，用于通知该玩家做出动作，例子如下：

```json
{
  "type": "act",
  "handCards": ["S2", "H2", "H2", "C2", "D2", "S3", "H3", "D3", "S4", "D5", "C6", "H7", "C7", "C8", "D8", "DT", "HJ", "DJ", "HQ", "HQ", "CQ", "SK", "H9", "H9", "C9", "D9", "HR"],
  "publicInfo": [
    {"rest": 22, "playArea": ["ThreeWithTwo", "A", ["SA", "SA", "DA", "H8", "D8"]]},
    {"rest": 23, "playArea": ["Bomb", "4", ["H4", "H4", "C4", "D4"]]},
    {"rest": 23, "playArea": ["Bomb", "A", ["HA", "HA", "CA", "DA"]]},
    {"rest": 27, "playArea": null}
  ],
  "selfRank": "K",
  "oppoRank": "9",
  "curRank": "9",
  "stage": "play",
  "curPos": 2,
  "curAction": ["Bomb", "A", ["HA", "HA", "CA", "DA"]],
  "greaterPos": 2,
  "greaterAction": ["Bomb", "A", ["HA", "HA", "CA", "DA"]],
  "actionList": [
    ["PASS", "PASS", "PASS"],
    ["Bomb", "9", ["H9", "H9", "C9", "D9"]],
    ["Bomb", "2", ["S2", "H2", "H2", "C2", "H9"]]
  ],
  "indexRange": 21
}
```

- 该例子的语义为：
  - 0号位打出`['ThreeWithTwo', 'A', ['SA', 'SA', 'DA', 'H8', 'D8']]`
  - 1号位打出`['Bomb', '4', ['H4', 'H4', 'C4', 'D4']]`
  - 2号位打出`['Bomb', 'A', ['HA', 'HA', 'CA', 'DA']]`，最大动作为2号位打出的`['Bomb', 'A', ['HA', 'HA', 'CA', 'DA']]`
  - 我方等级：K，对方等级：9，当前等级9
  - 当前动作为2号-动作`['Bomb', 'A', ['HA', 'HA', 'CA', 'DA']]`，最大动作为2号-动作`['Bomb', 'A', ['HA', 'HA', 'CA', 'DA']]`，目前可选动作见actionList所示
  - 可选动作范围为：0至21（包含0和21）
- 注：若某一位玩家打出某牌型，其余玩家均PASS，又转到该玩家重新出牌时，如下的部分字段表示当前的无任何人做出动作，也无任何最大动作。即率先出牌时、接风时、进贡时、还贡时，该部分字段为-1和None

```json
"curPos": -1,
"curAction": null,
"greaterAction": null,
"greaterPos": -1
```

#### (10) 进贡阶段动作请求

`"type":"act","stage":"tribute"`表示进贡阶段，用于该玩家进贡，例子如下：

```json
{
  "type": "act",
  "handCards": ["H3", "D3", "D4", "H5", "C5", "S6", "C6", "D6", "S7", "S7", "H7", "D7", "H8", "C8", "C8", "H9", "C9", "HT", "DT", "HJ", "DQ", "HK", "DK", "SA", "H2", "H2", "D2"],
  "publicInfo": [
    {"rest": 27, "playArea": null},
    {"rest": 27, "playArea": null},
    {"rest": 27, "playArea": null},
    {"rest": 27, "playArea": null}
  ],
  "selfRank": "2",
  "oppoRank": "9",
  "curRank": "2",
  "stage": "tribute",
  "curPos": -1,
  "curAction": null,
  "greaterAction": -1,
  "greaterPos": null,
  "actionList": [["tribute", "tribute", ["D2"]]],
  "indexRange": 0
}
```

- 该例子的语义为：游戏进贡阶段开始，我方手牌为handCards，轮到自己进贡，可进贡的牌为方片2（红桃配系统会自动跳过），可选动作索引范围为0（包含0）

#### (11) 还贡阶段动作请求

`"type":"act","stage":"back"`表示还贡阶段，用于该玩家还贡，如下所示：

```json
{
  "type": "act",
  "handCards": ["H2", "S3", "H3", "C3", "D3", "S4", "C4", "S6", "C6", "C7", "C7", "C8", "H9", "CJ", "HQ", "SK", "SK", "CK", "SA", "SA", "DA", "H5", "C5", "SB", "HR", "HR"],
  "publicInfo": [
    {"rest": 27, "playArea": null},
    {"rest": 27, "playArea": null},
    {"rest": 27, "playArea": null},
    {"rest": 27, "playArea": null}
  ],
  "selfRank": "5",
  "oppoRank": "9",
  "curRank": "5",
  "stage": "back",
  "curPos": -1,
  "curAction": null,
  "greaterAction": -1,
  "greaterPos": null,
  "actionList": [
    ["back", "back", ["H2"]],
    ["back", "back", ["S3"]],
    ["back", "back", ["H3"]],
    ["back", "back", ["C3"]],
    ["back", "back", ["D3"]],
    ["back", "back", ["S4"]],
    ["back", "back", ["C4"]],
    ["back", "back", ["S6"]],
    ["back", "back", ["C6"]],
    ["back", "back", ["C7"]],
    ["back", "back", ["C8"]],
    ["back", "back", ["H9"]]
  ]
}
```

- 该例子的语义为：游戏还贡阶段开始，我方手牌为handCards，轮到自己还贡，可还贡的牌为actionList（系统会自动跳过等级5的牌），可选动作索引范围为0至11（包含0和11）

### 4. 发送动作

- 相比之前的版本，动作的发送方式有所变化
- 选手需要在所给定的动作列表中进行选择并给出指定动作的下标，如动作列表为：`[['PASS','PASS','PASS'],['Single','5',['C5']]]`，则选手的可选动作范围为0-1
- 选手只需返回形如JSON：`{"actIndex": 0}`的形式即可
- 在所给的示例代码中包含动作解析类，解析完成后会返回随机索引，并由程序发送至平台
- 其他详细内容，详见所提供的示例代码
- 在需要做出动作时，算法程序所发送的动作必须符合平台所给的动作范围

---

## 📊 等级字段（易混，决策以 `act`·`play` 为准）

| 字段 | 含义 |
|------|------|
| `selfRank` | 我方队伍等级（跨副累积） |
| `oppoRank` | 对方队伍等级（跨副累积） |
| `curRank` | **当前等级**（本副级牌点数；`play` 阶段即本副打几） |

- 等级字符：`2,3,4,5,6,7,8,9,T,J,Q,K,A`
- `notify`·`play` **不带**三字段；`game_info` 快照可能滞后于进贡后本副 `act`·`play`
- 分析级牌 / AI 决策：**优先**同副 `act`·`stage=play` 的 `curRank`

### `curRank` 真值优先级（读 `game_records` / 回放 / 决策）

**禁止**只读文件名 `[level]` 或 `game_info.curRank` 就定「本副打几」。

| 优先级 | 来源 | 说明 |
|--------|------|------|
| **1** | 同副 `my_decisions` / `act` · `stage=play` 的 `curRank` | AI 决策与级牌规则**唯一可靠真值** |
| **2** | 同副 `act` · `back` / `tribute` 的 `curRank` | 贡还阶段已有级牌；还贡后常与 play 一致 |
| **3** | `episodeOver` 的 `curRank` | 本副结束快照 |
| **4** | `game_info.curRank` | 落盘快照，**常滞后**（仍停在进贡前） |
| **5（仅索引）** | 文件名 `…-[round]-[level].json` 的 `[level]` | **归档标签**，= 本副**开局/进贡前**落盘级；**≠** 还贡后出牌级 |

**一副内可变化**（2026-06-01 实测 round 40）：进贡 `act` 时 `curRank=9`（`selfRank=J`，`oppoRank=9`）；还贡后 `act`·`play` 起 **`curRank=K`**（约 70/73 步）。文件名仍为 `[9]`，`game_info.curRank` 仍为 `9` — **三者不一致属正常**，分析/回放排序/级牌保护须用 **还贡后 `act`·`play` 的 K**。

**`actions[].context`**：来自 `notify`·`play` 录制，**无**三等级字段；客户端写入的 context 可能混有邻副/滞后值，**低于** `my_decisions` 与原始 `act` 消息。

**下发时机（摘要）**：`beginning` notify 无三字段 →（第二副起）`act`·tribute/back → 每条 **`act`·play** 均带三字段 → `episodeOver` 仅 `curRank`。详见 PDF / `state.py`。

---

## 🔍 常用字段速查

| 字段 | 含义 |
|------|------|
| `episodeOver.order` | `[头游, 二游, 三游, 末游]` 座位号 0–3 |
| `episodeOver.restCards` | `[[座位, 剩余手牌], ...]`（双上提前结束时） |
| `publicInfo[i].rest` | 各玩家剩余张数 |
| `curPos` / `greaterPos` | 当前出牌位 / 当前圈最大牌位；接风时常为 -1 |
| `actionList` | 合法动作列表；选下标回 `actIndex` |

---

## 📚 牌型中英对照表

| 中文 | 英文 | 说明 |
|------|------|------|
| 单张 | `Single` | - |
| 对子 | `Pair` | - |
| 三张 | `Trips` | - |
| 三连对 | `ThreePair` | - |
| 三带二 | `ThreeWithTwo` | - |
| 钢板 | `TwoTrips` | 两个三张（二连三） |
| 顺子 | `Straight` | 固定 5 张 |
| 同花顺 | `StraightFlush` | 固定 5 张 |
| 炸弹 | `Bomb` | 四星～八星 |
| 王炸 | 特殊炸弹 | 2 大王 + 2 小王 |
| 进贡 | `tribute` | 末游→头游 |
| 还贡 | `back` | 头游→末游 |
| 抗贡 | - | 双大王免进贡 |
| 过 | `PASS` | - |

> 注意：部分旧文档将同花顺记为 `Straight`，但 v1006 平台协议中同花顺为 `StraightFlush`。

---

## 📎 副/局与仓库实现（索引）

与上文 §局与副 一致；改客户端 / 批跑时对照：

- **一副生命周期**：`beginning` →（第二副起 `tribute`/`back`）→ `play` → **`episodeOver`**
- **规则一局检测**：`_detect_game_end` → `game_scores_m2.json` §三
- **批跑台账**：`batch_executor` 的 `completed_games` = 局数；日志「match_key」= 副数诊断
- 等级字段、`curRank` 易混 → 上文 §等级字段

---

## 💡 改代码前

- 字段/JSON 歧义 → 查 **PDF**，勿凭 OCR 版 `docs/gdrules/掼蛋平台使用说明书1006.md`
- 改 AI **行为/规则** → 另读 `docs/guandan-brain/`
- 平台信息/历史版本 → 本文档

---

## 📧 联系我们

### 研究合作

如果你对我们的研究有兴趣，欢迎联系我们：

- **邮箱**：chenxg@njupt.edu.cn

### 问题反馈

若您在使用中发现问题或其他建议，欢迎随时骚扰：

- **邮箱**：wuguduofeng@gmail.com
- **QQ**：519301156

我们将不胜感激！

---

**文档来源**：合并自 `guandan-platform-v1006.mdc` + `掼蛋平台使用说明书1006.md` + `掼蛋AI算法对抗平台使用说明.md`  
**最后更新**：2026-06-05
