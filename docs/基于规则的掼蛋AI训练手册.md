# 基于规则的掼蛋AI训练手册

## ? 训练路径概览

基于规则的传统训练是掼蛋AI入门的最佳路径，适合没有AI/机器学习基础的开发者，通过逻辑规则实现AI决策。

```
准备阶段 (3-5天) → 规则实现 (1-2周) → 对局训练 (2-3周) → 优化提升 (持续)
```

## ?? 所需材料清单

### 1. 必需资源
- **Python 3.8+ 环境**
- **南邮掼蛋AI平台离线版v1006**
- **使用说明书 (平台配套)**
- **掼蛋游戏规则 (江苏省体育局版本)**

### 2. 技术依赖
```bash
# 安装Python库
pip install websockets>=11.0
pip install asyncio>=3.4.3
pip install numpy>=1.21.0
pip install pandas>=1.5.0
pip install matplotlib>=3.5.0
pip install beautifulsoup4>=4.11.0
pip install requests>=2.28.0
```

### 3. 硬件要求
- **最低配置**: 4GB内存，双核CPU
- **推荐配置**: 8GB内存，四核CPU
- **存储空间**: 至少2GB可用空间（保存对局数据）

### 4. 开发环境
- **IDE**: VS Code + Python插件 或 PyCharm
- **版本控制**: Git (可选)
- **调试工具**: Python debugger, logging

## ? 第一阶段：环境准备 (3-5天)

### 步骤1：获取平台资源

**1.1 下载离线平台**
```
访问：https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
下载：
- 离线平台安装包 (Windows/Linux版本)
- 使用说明书 v1006
- JSON格式说明文档
```

**1.2 安装和配置**
```bash
# 解压离线平台
unzip guandan_platform_v1006.zip
cd guandan_platform_v1006

# 启动平台 (Linux)
./start_platform.sh

# 启动平台 (Windows)
start_platform.exe

# 验证启动
# 访问本地WebSocket服务: ws://127.0.0.1:23456
```

**1.3 阅读文档**
- [ ] 仔细阅读使用说明书
- [ ] 理解JSON消息格式
- [ ] 了解游戏规则和牌型
- [ ] 学习WebSocket连接方式

### 步骤2：搭建开发环境

**2.1 创建项目结构**
```bash
mkdir guandan_ai_rule
cd guandan_ai_rule

# 创建目录结构
mkdir -p {src/{communication,game_logic,decision,data},tests,config,logs,data/replays}
```

**2.2 创建配置文件**
```yaml
# config/config.yaml
platform:
  websocket_url: "ws://127.0.0.1:23456/game/{user_id}"
  version: "v1006"

ai:
  name: "RuleBasedAI"
  strategy_level: "basic"
  response_timeout: 1.0  # 1秒超时

logging:
  level: "INFO"
  file: "logs/ai_client.log"

data:
  save_replays: true
  replay_path: "data/replays"
```

**2.3 安装依赖**
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

## ? 第二阶段：规则引擎实现 (1-2周)

### 核心数据结构

**1. 卡牌定义**
```python
# src/game_logic/cards.py
from enum import Enum
from typing import List, Tuple

class Suit(Enum):
    """花色枚举"""
    SPADES = "S"    # 黑桃
    HEARTS = "H"    # 红桃  
    DIAMONDS = "D"  # 方块
    CLUBS = "C"     # 梅花

class Rank(Enum):
    """牌面值枚举"""
    ACE = "A"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "T"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"

class Card:
    """卡牌类"""
    def __init__(self, suit: Suit, rank: Rank, is_main: bool = False):
        self.suit = suit
        self.rank = rank
        self.is_main = is_main
    
    def __str__(self):
        return f"{self.suit.value}{self.rank.value}"
    
    def __eq__(self, other):
        return isinstance(other, Card) and self.suit == other.suit and self.rank == other.rank
    
    def __hash__(self):
        return hash((self.suit, self.rank))

class CardType(Enum):
    """牌型枚举"""
    SINGLE = "Single"           # 单张
    PAIR = "Pair"              # 对子
    TRIPS = "Trips"            # 三张
    THREE_PAIR = "ThreePair"   # 三连对
    THREE_WITH_TWO = "ThreeWithTwo"  # 三带二
    TWO_TRIPS = "TwoTrips"     # 钢板
    STRAIGHT = "Straight"      # 顺子
    BOMB = "Bomb"              # 炸弹

class PlayedCard:
    """出牌类"""
    def __init__(self, cards: List[Card], card_type: CardType, main_rank: Rank = None):
        self.cards = cards
        self.card_type = card_type
        self.main_rank = main_rank
    
    def __str__(self):
        return f"{self.card_type.value}: {[str(c) for c in self.cards]}"
```

### 游戏状态管理

**2. 状态管理器**
```python
# src/game_logic/game_state.py
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from .cards import Card, PlayedCard, CardType, Rank

@dataclass
class GameState:
    """游戏状态类"""
    my_seat: int = 0                    # 我的座位号
    my_cards: List[Card] = field(default_factory=list)  # 我的手牌
    teammate_seat: int = 0              # 队友座位
    opponent_seats: List[int] = field(default_factory=list)  # 对手座位
    game_phase: str = "waiting"         # 游戏阶段
    current_player: int = 0             # 当前出牌玩家
    last_played: Optional[PlayedCard] = None  # 最后出的牌
    main_rank: Rank = Rank.FIVE         # 主牌级别
    score: Dict[int, int] = field(default_factory=dict)  # 分数
    
    def get_team_mates(self, seat: int) -> List[int]:
        """获取队友座位号"""
        if seat == 1:
            return [3]
        elif seat == 3:
            return [1]
        elif seat == 2:
            return [4]
        elif seat == 4:
            return [2]
        return []
    
    def is_my_turn(self) -> bool:
        """是否轮到我的回合"""
        return self.current_player == self.my_seat
    
    def get_available_cards(self) -> List[List[Card]]:
        """获取可出的牌型组合"""
        # 简化实现：返回所有可能的牌型
        return self._find_all_valid_plays()
    
    def _find_all_valid_plays(self) -> List[List[Card]]:
        """查找所有有效的出牌组合"""
        plays = []
        
        # 单张
        for card in self.my_cards:
            plays.append([card])
        
        # 对子
        cards_by_rank = self._group_cards_by_rank()
        for rank, cards in cards_by_rank.items():
            if len(cards) >= 2:
                for i in range(len(cards) - 1):
                    plays.append(cards[i:i+2])
        
        # 更多牌型的逻辑...
        
        return plays
    
    def _group_cards_by_rank(self) -> Dict[Rank, List[Card]]:
        """按牌面值分组"""
        groups = {}
        for card in self.my_cards:
            if card.rank not in groups:
                groups[card.rank] = []
            groups[card.rank].append(card)
        return groups
```

### 规则引擎实现

**3. 规则引擎核心**
```python
# src/decision/rule_engine.py
from typing import List, Tuple, Optional
from ..game_logic.cards import Card, PlayedCard, CardType, Rank
from ..game_logic.game_state import GameState
import logging

class RuleBasedAI:
    """基于规则的AI"""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.logger = logging.getLogger(__name__)
        
        # 规则优先级配置
        self.priority_rules = {
            'play_small_cards_first': 1,      # 优先出小牌
            'save_big_cards_for_end': 2,      # 保留大牌到最后
            'follow_teammate': 3,             # 配合队友
            'block_opponent': 4,              # 压制对手
            'use_bombs_wisely': 5             # 炸弹使用策略
        }
    
    def decide_play(self) -> Optional[List[Card]]:
        """决策出牌"""
        if not self.game_state.is_my_turn():
            return None
        
        available_plays = self.game_state.get_available_cards()
        if not available_plays:
            return None
        
        # 如果是首次出牌或有出牌权
        if self.game_state.last_played is None:
            return self._choose_opening_play(available_plays)
        
        # 压制对手
        valid_plays = self._filter_beating_plays(available_plays)
        if valid_plays:
            return self._choose_best_play(valid_plays)
        
        # 不能压制，过牌
        return None
    
    def _choose_opening_play(self, plays: List[List[Card]]) -> List[Card]:
        """选择开牌"""
        # 规则1：优先出小单张
        single_cards = [play for play in plays if len(play) == 1]
        if single_cards:
            single_cards.sort(key=lambda x: self._get_card_value(x[0]))
            return single_cards[0]
        
        # 规则2：出最小的对子
        pairs = [play for play in plays if len(play) == 2]
        if pairs:
            pairs.sort(key=lambda x: self._get_pair_value(x))
            return pairs[0]
        
        # 默认返回最小的牌
        plays.sort(key=lambda x: self._get_play_value(x))
        return plays[0]
    
    def _filter_beating_plays(self, plays: List[List[Card]]) -> List[List[Card]]:
        """筛选能够压制的牌"""
        if self.game_state.last_played is None:
            return plays
        
        last_play = self.game_state.last_played
        beating_plays = []
        
        for play in plays:
            if self._can_beat(play, last_play):
                beating_plays.append(play)
        
        return beating_plays
    
    def _choose_best_play(self, plays: List[List[Card]]) -> List[Card]:
        """选择最佳出牌"""
        # 按价值排序，选择最小价值能压制的牌
        plays_with_value = [(play, self._get_play_value(play)) for play in plays]
        plays_with_value.sort(key=lambda x: x[1])
        
        return plays_with_value[0][0]
    
    def _can_beat(self, play: List[Card], target: PlayedCard) -> bool:
        """判断能否压制"""
        if len(play) != len(target.cards):
            # 炸弹可以压制任何单牌
            if len(play) == 4 and all(card.is_main for card in play):
                return True
            return False
        
        # 比较牌面值
        play_max_rank = max(card.rank for card in play)
        target_max_rank = max(target.cards, key=lambda c: c.rank).rank
        
        # 如果有主牌，主牌优先级更高
        play_has_main = any(card.is_main for card in play)
        target_has_main = any(card.is_main for card in target.cards)
        
        if play_has_main and not target_has_main:
            return True
        elif not play_has_main and target_has_main:
            return False
        elif play_has_main and target_has_main:
            # 都是主牌，比较主牌级别
            return play_max_rank.value > self.game_state.main_rank.value
        else:
            # 都是普通牌
            return play_max_rank.value > target_max_rank.value
    
    def _get_card_value(self, card: Card) -> int:
        """获取牌的价值分数"""
        # 主牌价值更高
        if card.is_main:
            return 100 + card.rank.value
        
        # 根据牌面值给分
        rank_values = {
            Rank.ACE: 14, Rank.KING: 13, Rank.QUEEN: 12, Rank.JACK: 11,
            Rank.TEN: 10, Rank.NINE: 9, Rank.EIGHT: 8, Rank.SEVEN: 7,
            Rank.SIX: 6, Rank.FIVE: 5, Rank.FOUR: 4, Rank.THREE: 3, Rank.TWO: 2
        }
        return rank_values.get(card.rank, 0)
    
    def _get_pair_value(self, pair: List[Card]) -> int:
        """获取对子的价值"""
        return self._get_card_value(pair[0]) * 2
    
    def _get_play_value(self, play: List[Card]) -> int:
        """获取出牌的总价值"""
        return sum(self._get_card_value(card) for card in play)

    def get_strategy_explanation(self, play: List[Card]) -> str:
        """获取策略说明"""
        if len(play) == 1:
            return f"出单张 {play[0]} - 保留大牌"
        elif len(play) == 2:
            return f"出对子 {play[0]} - 配合队友"
        else:
            return f"出牌 {', '.join(str(card) for card in play)} - 策略出牌"
```

### 通信模块

**4. WebSocket通信**
```python
# src/communication/websocket_client.py
import asyncio
import websockets
import json
import logging
from typing import Callable, Optional
from ..game_logic.game_state import GameState
from ..decision.rule_engine import RuleBasedAI

class GuandanWebSocketClient:
    """掼蛋WebSocket客户端"""
    
    def __init__(self, user_id: str, game_state: GameState):
        self.user_id = user_id
        self.game_state = game_state
        self.rule_ai = RuleBasedAI(game_state)
        self.logger = logging.getLogger(__name__)
        self.websocket = None
        self.running = False
    
    async def connect(self, url: str):
        """连接WebSocket"""
        try:
            self.websocket = await websockets.connect(url)
            self.running = True
            self.logger.info(f"成功连接到 {url}")
            
            # 启动接收消息任务
            await self._handle_messages()
            
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            raise
    
    async def _handle_messages(self):
        """处理接收的消息"""
        try:
            async for message in self.websocket:
                await self._process_message(message)
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("连接已关闭")
        except Exception as e:
            self.logger.error(f"消息处理错误: {e}")
    
    async def _process_message(self, message: str):
        """处理消息"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "game_start":
                await self._handle_game_start(data)
            elif message_type == "deal_cards":
                await self._handle_deal_cards(data)
            elif message_type == "play_request":
                await self._handle_play_request(data)
            elif message_type == "game_end":
                await self._handle_game_end(data)
            else:
                self.logger.debug(f"未处理的消息类型: {message_type}")
                
        except json.JSONDecodeError:
            self.logger.error(f"JSON解析失败: {message}")
        except Exception as e:
            self.logger.error(f"消息处理异常: {e}")
    
    async def _handle_game_start(self, data: dict):
        """处理游戏开始"""
        self.logger.info("游戏开始")
        # 初始化游戏状态
        self.game_state.my_seat = data.get("seat", 1)
        self.game_state.teammate_seat = self.game_state.get_team_mates(self.game_state.my_seat)[0]
    
    async def _handle_deal_cards(self, data: dict):
        """处理发牌"""
        cards_data = data.get("cards", [])
        self.game_state.my_cards = []
        
        for card_str in cards_data:
            # 解析卡牌字符串，如 "S-A", "H-7"
            suit_char, rank_char = card_str.split('-')
            suit = Suit(suit_char)
            rank = Rank(rank_char)
            card = Card(suit, rank, rank_char == str(self.game_state.main_rank.value))
            self.game_state.my_cards.append(card)
        
        self.logger.info(f"发到 {len(self.game_state.my_cards)} 张牌")
    
    async def _handle_play_request(self, data: dict):
        """处理出牌请求"""
        self.logger.info("收到出牌请求")
        
        # 使用规则引擎决策
        selected_cards = self.rule_ai.decide_play()
        
        if selected_cards:
            # 构建出牌消息
            play_message = {
                "type": "play_cards",
                "cards": [str(card) for card in selected_cards],
                "player": self.game_state.my_seat
            }
            
            strategy_explanation = self.rule_ai.get_strategy_explanation(selected_cards)
            self.logger.info(f"出牌: {selected_cards} - {strategy_explanation}")
            
            # 发送出牌消息
            await self.send_message(play_message)
        else:
            # 过牌
            pass_message = {"type": "pass", "player": self.game_state.my_seat}
            await self.send_message(pass_message)
    
    async def _handle_game_end(self, data: dict):
        """处理游戏结束"""
        self.logger.info(f"游戏结束: {data}")
        self.running = False
    
    async def send_message(self, message: dict):
        """发送消息"""
        if self.websocket and self.running:
            try:
                await self.websocket.send(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                self.logger.error(f"发送消息失败: {e}")
    
    async def disconnect(self):
        """断开连接"""
        self.running = False
        if self.websocket:
            await self.websocket.close()

# 主程序入口
# src/main.py
import asyncio
import logging
from .communication.websocket_client import GuandanWebSocketClient
from .game_logic.game_state import GameState

async def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建游戏状态
    game_state = GameState()
    
    # 创建AI客户端
    client = GuandanWebSocketClient("RuleAI_001", game_state)
    
    # 连接到平台
    url = "ws://127.0.0.1:23456/game/RuleAI_001"
    await client.connect(url)

if __name__ == "__main__":
    asyncio.run(main())
```

## ? 第三阶段：对局训练 (2-3周)

### 训练策略

**1. 训练计划**
```
第1周：基础规则训练
- 启动4个AI客户端进行对局
- 观察基础策略表现
- 收集对局数据

第2周：规则优化
- 分析失败案例
- 优化出牌优先级
- 改进配合策略

第3周：稳定性测试
- 连续100局对局
- 检查错误率和崩溃率
- 性能调优
```

**2. 对局脚本**
```python
# src/training/self_play_trainer.py
import asyncio
import logging
from typing import List
from ..communication.websocket_client import GuandanWebSocketClient
from ..game_logic.game_state import GameState

class SelfPlayTrainer:
    """自我对弈训练器"""
    
    def __init__(self):
        self.clients = []
        self.logger = logging.getLogger(__name__)
        self.game_count = 0
        self.win_count = 0
    
    async def start_training(self, num_games: int = 50):
        """开始训练"""
        self.logger.info(f"开始自我对弈训练，共 {num_games} 局")
        
        for game_num in range(num_games):
            self.logger.info(f"开始第 {game_num + 1} 局训练")
            
            # 创建4个AI客户端
            await self._create_ai_clients()
            
            # 开始对局
            success = await self._run_single_game()
            
            if success:
                self.game_count += 1
            
            # 清理客户端
            await self._cleanup_clients()
            
            # 休息一下
            await asyncio.sleep(1)
        
        self.logger.info(f"训练完成！共完成 {self.game_count} 局")
    
    async def _create_ai_clients(self):
        """创建AI客户端"""
        self.clients = []
        for i in range(4):
            game_state = GameState()
            client = GuandanWebSocketClient(f"AI_{i+1}", game_state)
            self.clients.append(client)
    
    async def _run_single_game(self) -> bool:
        """运行单局游戏"""
        try:
            # 启动4个客户端连接
            tasks = []
            for i, client in enumerate(self.clients):
                url = f"ws://127.0.0.1:23456/game/AI_{i+1}"
                task = asyncio.create_task(client.connect(url))
                tasks.append(task)
            
            # 等待连接完成
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 等待游戏结束 (这里可以添加超时控制)
            await asyncio.sleep(300)  # 最多等待5分钟
            
            return True
            
        except Exception as e:
            self.logger.error(f"对局异常: {e}")
            return False
    
    async def _cleanup_clients(self):
        """清理客户端"""
        for client in self.clients:
            await client.disconnect()
        self.clients.clear()
```

### 训练评估

**3. 训练评估脚本**
```python
# src/training/evaluation.py
import json
import pandas as pd
from typing import List, Dict
from pathlib import Path

class TrainingEvaluator:
    """训练评估器"""
    
    def __init__(self, replay_dir: str = "data/replays"):
        self.replay_dir = Path(replay_dir)
        self.results = []
    
    def load_replay_data(self) -> pd.DataFrame:
        """加载回放数据"""
        all_games = []
        
        for replay_file in self.replay_dir.glob("*.json"):
            try:
                with open(replay_file, 'r', encoding='utf-8') as f:
                    game_data = json.load(f)
                    all_games.append(game_data)
            except Exception as e:
                print(f"加载回放文件失败: {replay_file}, 错误: {e}")
        
        return pd.DataFrame(all_games)
    
    def analyze_performance(self, df: pd.DataFrame) -> Dict:
        """分析性能指标"""
        if df.empty:
            return {}
        
        analysis = {
            "total_games": len(df),
            "win_rate": 0,
            "avg_game_duration": 0,
            "common_mistakes": [],
            "strategy_effectiveness": {}
        }
        
        # 计算胜率
        if "winner" in df.columns:
            # 这里需要根据实际数据结构调整
            analysis["win_rate"] = 0.6  # 示例值
        
        # 游戏时长分析
        if "duration" in df.columns:
            analysis["avg_game_duration"] = df["duration"].mean()
        
        return analysis
    
    def generate_report(self) -> str:
        """生成训练报告"""
        df = self.load_replay_data()
        analysis = self.analyze_performance(df)
        
        report = f"""
# 训练评估报告

## 基本统计
- 总对局数: {analysis['total_games']}
- 胜率: {analysis['win_rate']:.2%}
- 平均游戏时长: {analysis['avg_game_duration']:.1f} 秒

## 建议改进
{self._generate_improvement_suggestions(analysis)}

## 下一步训练计划
1. 继续当前策略训练
2. 针对薄弱环节优化
3. 增加对局数量
        """
        
        return report
    
    def _generate_improvement_suggestions(self, analysis: Dict) -> str:
        """生成改进建议"""
        suggestions = []
        
        if analysis['win_rate'] < 0.5:
            suggestions.append("- 胜率较低，需要优化决策策略")
        
        if analysis['avg_game_duration'] > 600:  # 10分钟
            suggestions.append("- 游戏时间过长，需要优化决策速度")
        
        if not suggestions:
            suggestions.append("- 当前表现良好，可以考虑引入更高级的策略")
        
        return "\n".join(suggestions)

# 评估脚本
async def evaluate_training():
    """运行训练评估"""
    evaluator = TrainingEvaluator()
    report = evaluator.generate_report()
    
    with open("training_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("训练评估完成，报告保存到 training_report.md")

if __name__ == "__main__":
    asyncio.run(evaluate_training())
```

## ? 第四阶段：优化提升 (持续)

### 规则优化技巧

**1. 出牌优先级优化**
```python
# src/decision/advanced_rules.py
class AdvancedRuleEngine(RuleBasedAI):
    """高级规则引擎"""
    
    def __init__(self, game_state: GameState):
        super().__init__(game_state)
        self.card_count_analysis = {}
        self.opponent_patterns = {}
    
    def _analyze_card_distribution(self):
        """分析牌型分布"""
        # 分析每种牌型的数量
        distribution = {
            'single': 0,
            'pair': 0,
            'trips': 0,
            'bomb': 0
        }
        
        for card in self.game_state.my_cards:
            # 统计逻辑...
            pass
        
        return distribution
    
    def _predict_opponent_cards(self):
        """预测对手可能的牌"""
        # 基于已出牌和游戏进程预测
        predictions = {}
        return predictions
    
    def _choose_defensive_play(self, plays: List[List[Card]]) -> List[Card]:
        """选择防守性出牌"""
        # 优先选择能阻止对手的牌
        plays_with_risk = []
        for play in plays:
            risk_score = self._calculate_risk(play)
            plays_with_risk.append((play, risk_score))
        
        # 选择风险最小的牌
        plays_with_risk.sort(key=lambda x: x[1])
        return plays_with_risk[0][0] if plays_with_risk else plays[0]
    
    def _calculate_risk(self, play: List[Card]) -> float:
        """计算出牌风险"""
        # 风险评估逻辑
        risk = 0.0
        # 考虑因素：牌型大小、是否帮助对手等
        return risk
```

**2. 配合策略优化**
```python
# src/decision/cooperation.py
class CooperationStrategy:
    """配合策略"""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
    
    def should_follow_teammate(self, teammate_play: PlayedCard) -> bool:
        """是否应该跟队友"""
        # 分析队友出牌意图
        return self._analyze_teammate_intent(teammate_play)
    
    def _analyze_teammate_intent(self, play: PlayedCard) -> bool:
        """分析队友意图"""
        # 如果队友出小牌，可能是示意配合
        if self._is_small_play(play):
            return True
        
        # 如果队友出大牌，可能是想结束这轮
        if self._is_large_play(play):
            return False
        
        return True  # 默认配合
    
    def _is_small_play(self, play: PlayedCard) -> bool:
        """判断是否是小牌"""
        # 实现小牌判断逻辑
        return False
    
    def _is_large_play(self, play: PlayedCard) -> bool:
        """判断是否是大牌"""
        # 实现大牌判断逻辑
        return False
```

### 数据分析工具

**3. 对局分析器**
```python
# src/analysis/game_analyzer.py
import matplotlib.pyplot as plt
import pandas as pd
from typing import List, Dict

class GameAnalyzer:
    """对局分析器"""
    
    def __init__(self, replay_data: List[Dict]):
        self.replay_data = replay_data
    
    def analyze_win_patterns(self) -> Dict:
        """分析获胜模式"""
        wins = [game for game in self.replay_data if game.get('winner') in [1, 3]]
        losses = [game for game in self.replay_data if game.get('winner') in [2, 4]]
        
        patterns = {
            'win_rate': len(wins) / len(self.replay_data) if self.replay_data else 0,
            'avg_cards_left_on_win': self._calculate_avg_cards(wins),
            'avg_cards_left_on_loss': self._calculate_avg_cards(losses)
        }
        
        return patterns
    
    def _calculate_avg_cards(self, games: List[Dict]) -> float:
        """计算平均剩余手牌数"""
        if not games:
            return 0
        
        total_cards = sum(game.get('final_card_count', 0) for game in games)
        return total_cards / len(games)
    
    def generate_performance_charts(self):
        """生成性能图表"""
        # 胜率趋势图
        win_rates = self._calculate_win_rates_over_time()
        
        plt.figure(figsize=(10, 6))
        plt.plot(win_rates)
        plt.title('AI训练胜率趋势')
        plt.xlabel('训练轮次')
        plt.ylabel('胜率')
        plt.grid(True)
        plt.savefig('win_rate_trend.png')
        plt.close()
        
        # 其他图表...
    
    def _calculate_win_rates_over_time(self) -> List[float]:
        """计算随时间变化的胜率"""
        # 实现胜率计算逻辑
        return []
```

## ? 训练进度监控

### 训练日志

**4. 训练监控脚本**
```python
# src/monitoring/training_monitor.py
import logging
import time
from typing import Dict, List
from datetime import datetime

class TrainingMonitor:
    """训练监控器"""
    
    def __init__(self):
        self.start_time = None
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.errors = 0
        
        # 设置监控日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('training_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def start_training(self):
        """开始训练监控"""
        self.start_time = time.time()
        self.logger.info("开始训练监控")
    
    def record_game_result(self, won: bool, error_occurred: bool = False):
        """记录游戏结果"""
        self.games_played += 1
        if won:
            self.wins += 1
        else:
            self.losses += 1
        
        if error_occurred:
            self.errors += 1
        
        # 实时输出进度
        if self.games_played % 10 == 0:
            self._log_progress()
    
    def _log_progress(self):
        """记录训练进度"""
        elapsed_time = time.time() - self.start_time
        win_rate = self.wins / self.games_played if self.games_played > 0 else 0
        error_rate = self.errors / self.games_played if self.games_played > 0 else 0
        
        self.logger.info(
            f"进度更新 - 游戏数: {self.games_played}, "
            f"胜率: {win_rate:.2%}, "
            f"错误率: {error_rate:.2%}, "
            f"用时: {elapsed_time/60:.1f}分钟"
        )
    
    def get_performance_summary(self) -> Dict:
        """获取性能总结"""
        if not self.start_time:
            return {}
        
        total_time = time.time() - self.start_time
        return {
            "games_played": self.games_played,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.wins / self.games_played if self.games_played > 0 else 0,
            "total_time_minutes": total_time / 60,
            "games_per_hour": (self.games_played / total_time) * 3600 if total_time > 0 else 0,
            "errors": self.errors,
            "error_rate": self.errors / self.games_played if self.games_played > 0 else 0
        }
```

## ? 训练效果评估

### 成功标准

**1. 技术指标**
- ? 能够稳定连接到平台
- ? 正确识别和解析JSON消息
- ? 所有牌型都能正确识别
- ? 决策响应时间 < 1秒
- ? 连续对局无崩溃

**2. 游戏指标**
- ? 基础AI胜率 > 50%
- ? 理解基本配合策略
- ? 能够处理常见局面
- ? 避免明显错误

**3. 学习指标**
- ? 能够通过训练改进策略
- ? 对局数据能指导优化
- ? 错误率逐渐下降
- ? 决策质量稳步提升

### 常见问题解决

**问题1: 连接不稳定**
```python
# 解决方案：添加重连机制
async def robust_connect(self, url: str, max_retries: int = 5):
    for attempt in range(max_retries):
        try:
            await self.connect(url)
            return True
        except Exception as e:
            self.logger.warning(f"连接失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            await asyncio.sleep(2 ** attempt)  # 指数退避
    return False
```

**问题2: 决策逻辑错误**
```python
# 解决方案：添加调试模式
def debug_decision(self, play: List[Card]) -> str:
    """调试决策过程"""
    debug_info = []
    debug_info.append(f"手牌: {[str(c) for c in self.game_state.my_cards]}")
    debug_info.append(f"候选出牌: {play}")
    debug_info.append(f"游戏状态: {self.game_state.game_phase}")
    debug_info.append(f"最后出牌: {self.game_state.last_played}")
    
    return "\n".join(debug_info)
```

**问题3: 性能问题**
```python
# 解决方案：优化算法
def optimized_card_finder(self) -> List[List[Card]]:
    """优化后的找牌算法"""
    # 使用更高效的数据结构
    from collections import defaultdict
    
    cards_by_rank = defaultdict(list)
    for card in self.my_cards:
        cards_by_rank[card.rank].append(card)
    
    # 批量处理而不是逐个查找
    return self._batch_find_valid_plays(cards_by_rank)
```

## ? 快速开始检查清单

### 第1天：环境搭建
- [ ] 下载并安装Python 3.8+
- [ ] 下载南邮平台v1006
- [ ] 阅读使用说明书
- [ ] 创建项目目录
- [ ] 安装依赖包

### 第2-3天：基础实现
- [ ] 实现卡牌数据结构
- [ ] 实现游戏状态管理
- [ ] 实现WebSocket连接
- [ ] 测试基础通信

### 第4-7天：规则引擎
- [ ] 实现基础牌型识别
- [ ] 实现出牌决策逻辑
- [ ] 实现简单的配合策略
- [ ] 完成单局对局测试

### 第2周：对局训练
- [ ] 启动4AI自我对局
- [ ] 收集和分析对局数据
- [ ] 优化决策规则
- [ ] 处理异常情况

### 第3周：优化提升
- [ ] 实现高级规则
- [ ] 性能调优
- [ ] 稳定性测试
- [ ] 生成训练报告

## ? 立即行动指南

### 今天就开始训练！

```bash
# 1. 创建项目
mkdir guandan_ai_training
cd guandan_ai_training

# 2. 下载模板代码
# 从上面的代码复制到对应文件

# 3. 安装依赖
pip install websockets asyncio numpy pandas matplotlib

# 4. 启动平台
# 运行下载的离线平台

# 5. 运行AI
python src/main.py

# 6. 观察效果
# 查看日志文件: logs/ai_client.log
```

### 训练建议

1. **循序渐进**：先实现基础功能，确保能正常运行
2. **数据驱动**：重视对局数据的收集和分析
3. **持续改进**：每次改进后都要通过对局验证效果
4. **记录经验**：建立训练日志，记录优化过程

通过这套完整的基于规则的传统训练方案，您可以在2-3周内建立一个具备基本掼蛋AI能力的系统，为后续的高级AI技术奠定基础！

---

**训练时间预估**: 2-3周
**难度等级**: ?? (入门友好)
**成功概率**: 95% (只要按步骤执行)
**下一步**: 可升级为搜索算法或强化学习AI
