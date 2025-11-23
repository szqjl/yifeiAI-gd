# 掼蛋AI训练指南

## ? 主要训练入口

### 1. 南京邮电大学掼蛋AI算法对抗平台 ?????

**这是目前最直接、最权威的掼蛋AI训练平台**

- **平台地址**: https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **当前版本**: v1006（内测中，可参与）
- **状态**: ? 可直接参与训练

**训练特点**：
- 提供离线平台用于本地开发和测试
- 完整的WebSocket + JSON通信接口
- 支持4个AI同时对战训练
- 自动评分和排名系统
- 详细的文档和示例

**训练流程**：
```mermaid
1. 访问平台网站
   ↓
2. 下载离线平台v1006
   ↓
3. 下载使用说明书
   ↓
4. 开发AI客户端
   ↓
5. 本地测试训练
   ↓
6. 参与在线对战
   ↓
7. 获取训练反馈
```

### 2. 中国人工智能博弈算法大赛

- **类型**: 国家级比赛（已举办过掼蛋项目）
- **状态**: 需关注下一届比赛信息
- **价值**: 高水平竞技平台

### 3. Botzone平台（需确认）

- **地址**: 需查询Botzone官网
- **现状**: 主要为斗地主AI，可能有掼蛋项目
- **价值**: 在线对战平台，大量训练数据

## ? AI训练方法

### 方法一：基于规则的传统训练

**适用阶段**: 入门和基础训练

**核心思路**：
- 实现基础掼蛋规则和牌型识别
- 建立简单的决策规则库
- 通过大量对局收集经验数据
- 逐步优化规则逻辑

**训练步骤**：
```python
1. 实现基础牌型识别 (Single/Pair/Trips等)
2. 建立出牌优先级规则
3. 实现基础配合策略
4. 连续对局训练优化
5. 分析失败案例改进规则
```

**优势**: 实现简单，容易调试，规则透明
**劣势**: 策略深度有限，难以应对复杂局面

### 方法二：搜索算法训练

**适用阶段**: 中级训练

**核心思路**：
- 使用Minimax搜索算法
- Alpha-Beta剪枝优化
- 评估函数设计
- 深度搜索优化

**技术实现**:
```python
# 简化示例
class GuandanAI:
    def __init__(self):
        self.max_depth = 3  # 搜索深度
        self.evaluation_weight = {
            'card_count': 0.3,  # 手牌数量权重
            'win_probability': 0.4,  # 获胜概率权重
            'cooperation': 0.3  # 配合权重
        }
    
    def minimax_search(self, game_state, depth, maximizing_player):
        if depth == 0:
            return self.evaluate_state(game_state)
        
        possible_moves = self.get_possible_moves(game_state)
        best_value = float('-inf') if maximizing_player else float('inf')
        
        for move in possible_moves:
            next_state = self.apply_move(game_state, move)
            value = self.minimax_search(next_state, depth-1, not maximizing_player)
            best_value = max(best_value, value) if maximizing_player else min(best_value, value)
        
        return best_value
```

**优势**: 能处理复杂局面，策略深度高
**劣势**: 计算复杂度高，需要优化

### 方法三：强化学习训练

**适用阶段**: 高级训练

**核心思路**：
- 使用深度强化学习（DQN/A3C/PPO）
- 通过大量对局学习最优策略
- 自我对弈不断改进
- 多智能体协同训练

**训练架构**:
```python
import torch
import torch.nn as nn
import torch.optim as optim

class GuandanRLAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = []
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        
        # 神经网络
        self.q_network = self.build_network()
        self.target_network = self.build_network()
        
    def build_network(self):
        model = nn.Sequential(
            nn.Linear(self.state_size, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, self.action_size)
        )
        return model
    
    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state):
        if np.random.random() <= self.epsilon:
            return random.choice(range(self.action_size))
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        q_values = self.q_network(state_tensor)
        return np.argmax(q_values.cpu().data.numpy())
    
    def replay(self, batch_size):
        if len(self.memory) < batch_size:
            return
        
        batch = random.sample(self.memory, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        states = torch.FloatTensor(states)
        actions = torch.LongTensor(actions)
        rewards = torch.FloatTensor(rewards)
        next_states = torch.FloatTensor(next_states)
        dones = torch.FloatTensor(dones)
        
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        next_q_values = self.target_network(next_states).max(1)[0].detach()
        target_q_values = rewards + (0.95 * next_q_values * (1 - dones))
        
        loss = nn.MSELoss()(current_q_values.squeeze(), target_q_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
```

**优势**: 能够学习复杂策略，自我改进能力强
**劣势**: 训练时间长，需要大量计算资源

### 方法四：大模型辅助训练

**适用阶段**: 高级训练和策略优化

**核心思路**：
- 利用GPT-4等大模型进行策略分析
- 结合掼蛋专家知识
- 提示工程优化
- 多模态输入处理

**技术方案**:
```python
import openai

class LLMGuandanCoach:
    def __init__(self, api_key):
        openai.api_key = api_key
        self.system_prompt = """
        你是一个掼蛋游戏专家。请根据当前游戏状态给出最优出牌建议。
        
        游戏规则：
        - 单张、对子、三张等牌型
        - 炸弹可以压制任何单牌
        - 同花顺是特殊顺子
        - 4人游戏，1-3一队，2-4一队
        
        请分析当前局面并给出建议。
        """
    
    def analyze_position(self, game_state, hand_cards, recent_plays):
        prompt = f"""
        当前游戏状态：{game_state}
        我的手牌：{hand_cards}
        最近出牌：{recent_plays}
        
        请分析并建议：
        1. 当前最优出牌策略
        2. 队友配合建议
        3. 对手压制策略
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
```

**优势**: 能够处理复杂推理，结合专家知识
**劣势**: 成本高，实时性要求难以满足

## ? 训练数据收集

### 数据来源

1. **平台对战数据**
   - 从南邮平台获取对局记录
   - 自动保存游戏回放
   - 提取关键决策点

2. **自我对弈数据**
   - 多个AI版本对战
   - 不同策略间的对抗
   - 持续学习优化

3. **专家标注数据**
   - 邀请掼蛋高手标注
   - 关键局面决策
   - 策略技巧总结

### 数据格式

```json
{
  "game_id": "20241121_001",
  "players": [
    {"seat": 1, "ai_level": "intermediate"},
    {"seat": 2, "ai_level": "advanced"},
    {"seat": 3, "ai_level": "beginner"},
    {"seat": 4, "ai_level": "expert"}
  ],
  "game_state": {
    "current_player": 1,
    "hand_cards": ["S-A", "H-7", "D-K"],
    "played_cards": [{"player": 2, "cards": ["S-K"], "type": "Single"}],
    "current_card_type": {"type": "Single", "main_rank": "5"}
  },
  "decision": {
    "player": 1,
    "action": "play",
    "selected_cards": ["H-K"],
    "reasoning": "跟随同花色，避免过早使用大牌"
  },
  "outcome": {
    "winner": [1, 3],
    "final_score": [120, 95]
  },
  "metadata": {
    "timestamp": "2024-11-21T20:30:00",
    "game_duration": 1800,
    "version": "v1.0"
  }
}
```

## ? 具体训练实施步骤

### 第一阶段：基础训练（1-2周）

```bash
# 1. 环境搭建
git clone <repository>
cd guandan-ai-client
pip install -r requirements.txt

# 2. 下载测试平台
# 访问 https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
# 下载离线平台v1006

# 3. 基础功能实现
python -m src.communication.websocket_client
python -m src.game_logic.card_recognizer
python -m src.decision.simple_strategy

# 4. 本地测试
python main.py --mode=test
```

### 第二阶段：对弈训练（2-4周）

```python
# 训练脚本示例
import asyncio
from src.ai.client import GuandanAIClient
from src.training.self_play import SelfPlayTrainer

async def train_basic_ai():
    # 启动4个基础AI
    clients = []
    for i in range(4):
        client = GuandanAIClient(
            user_id=f"AI_TRAIN_{i}",
            strategy="basic",
            save_replays=True
        )
        clients.append(client)
    
    # 开始自我对弈训练
    trainer = SelfPlayTrainer(clients)
    await trainer.train(
        num_games=100,
        evaluation_interval=10,
        save_best=True
    )

# 运行训练
asyncio.run(train_basic_ai())
```

### 第三阶段：强化学习训练（4-8周）

```python
# 强化学习训练
import torch
from src.rl.guandan_env import GuandanEnvironment
from src.rl.dqn_agent import DQNAgent

def train_rl_agent():
    # 创建环境
    env = GuandanEnvironment()
    
    # 创建智能体
    agent = DQNAgent(
        state_size=env.observation_space,
        action_size=env.action_space,
        learning_rate=0.001,
        gamma=0.95,
        epsilon=1.0,
        epsilon_decay=0.995
    )
    
    # 训练循环
    for episode in range(1000):
        state = env.reset()
        total_reward = 0
        
        while not env.done:
            # 选择动作
            action = agent.act(state)
            
            # 执行动作
            next_state, reward, done, _ = env.step(action)
            
            # 存储经验
            agent.remember(state, action, reward, next_state, done)
            
            state = next_state
            total_reward += reward
        
        # 重放学习
        if len(agent.memory) > 1000:
            agent.replay(batch_size=32)
        
        # 保存模型
        if episode % 100 == 0:
            torch.save(agent.q_network.state_dict(), f"models/dqn_episode_{episode}.pth")
            print(f"Episode {episode}, Reward: {total_reward}")

train_rl_agent()
```

### 第四阶段：实战优化（持续）

```python
# 实战评估和优化
from src.evaluation.benchmark import BenchmarkSuite

def evaluate_and_optimize():
    benchmark = BenchmarkSuite()
    
    # 对战测试
    results = benchmark.run_benchmark(
        opponent_ai=["basic", "intermediate", "advanced"],
        num_games_per_opponent=50,
        save_detailed_analysis=True
    )
    
    # 性能分析
    print("对战结果:")
    for opponent, winrate in results.items():
        print(f"vs {opponent}: {winrate:.2%} 胜率")
    
    # 策略分析
    strategy_analysis = benchmark.analyze_strategy_patterns()
    print("策略分析:")
    print(f"平均决策时间: {strategy_analysis['avg_decision_time']:.2f}s")
    print(f"错误率: {strategy_analysis['error_rate']:.2%}")
    
    # 根据结果优化
    if results["intermediate"] < 0.6:  # 胜率低于60%
        print("需要优化策略...")

evaluate_and_optimize()
```

## ? 训练评估指标

### 技术指标
- **决策准确率**: > 95%
- **响应时间**: < 1秒
- **稳定性**: 连续100局无崩溃

### 竞技指标
- **胜率**: 
  - vs 基础AI: > 80%
  - vs 中级AI: > 60%
  - vs 高级AI: > 40%
- **配合默契度**: 与队友配合成功率 > 70%
- **策略深度**: 能够处理复杂局面

### 学习指标
- **收敛速度**: 强化学习收敛轮次 < 500
- **泛化能力**: 在新对手上表现稳定
- **适应能力**: 能够根据对手调整策略

## ? 训练工具和资源

### 开发工具
- **IDE**: VS Code + Python插件
- **版本控制**: Git + GitHub/Gitee
- **调试工具**: Python debugger, logging

### 依赖库
```python
# requirements.txt
websockets>=11.0
torch>=1.13.0
numpy>=1.21.0
pandas>=1.5.0
matplotlib>=3.5.0
beautifulsoup4>=4.11.0
requests>=2.28.0
asyncio-mqtt>=0.13.0
```

### 训练资源
- **平台**: 南邮掼蛋AI平台
- **数据**: Botzone对局数据（斗地主参考）
- **论文**: 相关AI博弈算法研究
- **社区**: 掼蛋AI技术交流群

## ?? 训练注意事项

### 技术要点
1. **数据格式严格性**: 严格按照平台JSON格式
2. **内存管理**: 及时清理训练数据，避免内存泄漏
3. **并发处理**: 合理使用异步编程提高训练效率
4. **版本兼容**: 确保训练代码兼容平台v1006版本

### 训练策略
1. **循序渐进**: 从规则引擎开始，逐步引入高级方法
2. **数据驱动**: 重视数据收集和统计分析
3. **持续优化**: 建立反馈机制，持续改进
4. **对比学习**: 与不同水平AI对比，找出问题

### 资源管理
1. **计算资源**: 合理分配CPU和GPU资源
2. **存储空间**: 及时清理旧模型和日志
3. **网络带宽**: 控制训练时的网络请求频率
4. **时间规划**: 制定合理的训练时间表

## ? 总结

掼蛋AI训练的主要入口和步骤：

1. **主要入口**: 南京邮电大学掼蛋AI算法对抗平台
2. **训练方法**: 从规则引擎到强化学习的渐进式方法
3. **数据驱动**: 重视对局数据收集和分析
4. **持续优化**: 建立评估体系，持续改进

**立即行动建议**:
1. 访问平台网站，下载离线平台
2. 实现基础通信和游戏逻辑
3. 建立简单规则引擎开始训练
4. 逐步引入高级AI技术

通过系统化的训练，能够在掼蛋AI竞赛中取得优异成绩！

---

**最后更新**: 2025-11-21
**适用平台**: 南京邮电大学掼蛋AI算法对抗平台 v1006
