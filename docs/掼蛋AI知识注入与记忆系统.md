# 掼蛋AI知识注入与记忆系统技术方案

## ? 专业术语定义

**知识注入系统** (Knowledge Injection System, KIS)
**专家知识融合引擎** (Expert Knowledge Fusion Engine, EKFE)  
**持久化记忆架构** (Persistent Memory Architecture, PMA)

## ? 三大核心技术问题解答

---

## ? 问题一：知识库投喂如何集成到掼蛋AI客户端？

### 解决方案：分层集成架构

#### 1. 知识注入系统 (KIS) 核心组件

```python
# src/core/knowledge_injection_system.py
import asyncio
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import sqlite3
import hashlib

@dataclass
class KnowledgePacket:
    """知识包结构"""
    id: str
    name: str
    version: str
    source: str
    knowledge_type: str  # rule, strategy, pattern, evaluation
    content: Dict[str, Any]
    weight: float
    confidence: float
    tags: List[str]
    created_at: datetime
    checksum: str

class KnowledgeInjectionSystem:
    """知识注入系统 - 核心控制器"""
    
    def __init__(self, knowledge_dir: str = "data/knowledge"):
        self.knowledge_dir = Path(knowledge_dir)
        self.knowledge_dir.mkdir(exist_ok=True)
        
        # 核心组件
        self.knowledge_store = KnowledgeStore()
        self.knowledge_processor = KnowledgeProcessor()
        self.knowledge_validator = KnowledgeValidator()
        self.knowledge_loader = KnowledgeLoader()
        
        # 内存缓存
        self.active_knowledge = {}
        self.knowledge_index = {}
        
        self.logger = logging.getLogger(__name__)
        
    async def inject_knowledge_package(self, package_path: str) -> Dict[str, Any]:
        """注入知识包"""
        injection_report = {
            "start_time": datetime.now().isoformat(),
            "package_path": package_path,
            "status": "processing",
            "processed_items": 0,
            "valid_items": 0,
            "errors": [],
            "integrations": []
        }
        
        try:
            # 1. 加载知识包
            knowledge_package = await self._load_knowledge_package(package_path)
            
            # 2. 处理和验证知识
            processed_knowledge = await self._process_knowledge_items(knowledge_package)
            
            # 3. 存储到持久化数据库
            storage_result = await self._store_knowledge(processed_knowledge)
            
            # 4. 构建内存索引
            index_result = await self._build_memory_index(processed_knowledge)
            
            # 5. 通知AI客户端集成
            integration_result = await self._notify_ai_integration(processed_knowledge)
            
            injection_report.update({
                "status": "completed",
                "end_time": datetime.now().isoformat(),
                "processed_items": len(processed_knowledge),
                "valid_items": len([k for k in processed_knowledge if k.is_valid]),
                "storage_result": storage_result,
                "index_result": index_result,
                "integration_result": integration_result
            })
            
            self.logger.info(f"知识注入完成: {injection_report['valid_items']} 个有效知识项")
            
        except Exception as e:
            injection_report["status"] = "failed"
            injection_report["errors"].append(str(e))
            self.logger.error(f"知识注入失败: {e}")
        
        return injection_report
    
    async def _load_knowledge_package(self, package_path: str) -> KnowledgePacket:
        """加载知识包"""
        with open(package_path, 'r', encoding='utf-8') as f:
            package_data = json.load(f)
        
        # 验证包完整性
        package = KnowledgePacket(**package_data)
        await self._verify_package_integrity(package)
        
        return package
    
    async def _process_knowledge_items(self, package: KnowledgePacket) -> List['ProcessedKnowledgeItem']:
        """处理知识项"""
        processed_items = []
        
        for item_data in package.content.get("items", []):
            # 处理每个知识项
            processed_item = await self.knowledge_processor.process(item_data, package)
            
            # 验证知识项
            if await self.knowledge_validator.validate(processed_item):
                processed_items.append(processed_item)
        
        return processed_items
    
    async def _store_knowledge(self, processed_items: List['ProcessedKnowledgeItem']) -> Dict[str, Any]:
        """存储知识到数据库"""
        # SQLite持久化存储
        db_path = self.knowledge_dir / "knowledge_base.db"
        
        with sqlite3.connect(str(db_path)) as conn:
            # 创建表（如果不存在）
            conn.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    type TEXT,
                    content TEXT,
                    weight REAL,
                    confidence REAL,
                    tags TEXT,
                    created_at TEXT,
                    last_used TEXT,
                    usage_count INTEGER DEFAULT 0,
                    effectiveness_score REAL DEFAULT 0.0
                )
            ''')
            
            # 批量插入知识项
            for item in processed_items:
                conn.execute('''
                    INSERT OR REPLACE INTO knowledge_items 
                    (id, name, type, content, weight, confidence, tags, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item.id, item.name, item.type, json.dumps(item.content),
                    item.weight, item.confidence, json.dumps(item.tags),
                    datetime.now().isoformat()
                ))
        
        return {"stored_items": len(processed_items), "database_path": str(db_path)}
    
    async def _build_memory_index(self, processed_items: List['ProcessedKnowledgeItem']) -> Dict[str, Any]:
        """构建内存索引"""
        for item in processed_items:
            # 按类型索引
            if item.type not in self.knowledge_index:
                self.knowledge_index[item.type] = {}
            
            # 按标签索引
            for tag in item.tags:
                if tag not in self.knowledge_index[item.type]:
                    self.knowledge_index[item.type][tag] = []
                self.knowledge_index[item.type][tag].append(item.id)
            
            # 加载到内存缓存
            self.active_knowledge[item.id] = item
        
        return {
            "indexed_types": list(self.knowledge_index.keys()),
            "cached_items": len(self.active_knowledge),
            "index_size": sum(len(tags) for type_dict in self.knowledge_index.values() for tags in type_dict.values())
        }
    
    async def _notify_ai_integration(self, processed_items: List['ProcessedKnowledgeItem']) -> Dict[str, Any]:
        """通知AI客户端集成新知识"""
        # 通过事件系统通知AI客户端
        integration_events = []
        
        for item in processed_items:
            event = {
                "type": "knowledge_updated",
                "knowledge_id": item.id,
                "knowledge_type": item.type,
                "timestamp": datetime.now().isoformat()
            }
            integration_events.append(event)
        
        # 这里可以集成消息队列或事件总线
        # await self.event_bus.publish_batch(integration_events)
        
        return {"notified_events": len(integration_events), "status": "sent"}

#### 2. AI客户端集成适配器

```python
# src/client/ai_integration_adapter.py
from typing import Dict, List, Any, Optional
import asyncio
from ..core.knowledge_injection_system import KnowledgeInjectionSystem

class AIIntegrationAdapter:
    """AI客户端集成适配器"""
    
    def __init__(self, ai_client, knowledge_system: KnowledgeInjectionSystem):
        self.ai_client = ai_client
        self.knowledge_system = knowledge_system
        self.knowledge_cache = {}
        self.decision_enhancer = KnowledgeEnhancedDecisionEngine()
        
    async def initialize_integration(self):
        """初始化知识集成"""
        # 1. 加载已存储的知识
        await self._load_existing_knowledge()
        
        # 2. 注册知识更新事件监听器
        await self._register_knowledge_listeners()
        
        # 3. 增强AI决策引擎
        self._enhance_ai_decision_engine()
        
        self.logger.info("AI知识集成初始化完成")
    
    def _enhance_ai_decision_engine(self):
        """增强AI决策引擎"""
        # 保存原始决策方法
        original_decide = self.ai_client.rule_ai.decide_play
        
        # 创建增强版决策方法
        async def enhanced_decide_play():
            # 1. 获取原始决策建议
            original_play = await original_decide()
            
            # 2. 应用知识增强
            enhanced_play = await self.decision_enhancer.enhance_decision(
                original_play, 
                self.ai_client.game_state,
                self.knowledge_cache
            )
            
            # 3. 记录知识使用情况
            await self._record_knowledge_usage(enhanced_play)
            
            return enhanced_play
        
        # 替换AI决策方法
        self.ai_client.rule_ai.decide_play = enhanced_decide_play
    
    async def _load_existing_knowledge(self):
        """加载现有知识到内存"""
        # 从知识系统加载所有有效知识项
        knowledge_items = await self.knowledge_system.get_all_valid_knowledge()
        
        for item in knowledge_items:
            self.knowledge_cache[item.id] = item
        
        self.logger.info(f"已加载 {len(knowledge_items)} 个知识项到内存")
```

---

## ? 问题二：如何对知识库进行整理，形成让掼蛋AI能看懂？

### 解决方案：知识表示标准化 (Knowledge Representation Standardization, KRS)

#### 1. 掼蛋AI知识表示格式

```python
# src/knowledge/guandan_knowledge_format.py
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import json

class KnowledgeLevel(Enum):
    """知识级别"""
    BASIC = "basic"           # 基础规则
    INTERMEDIATE = "intermediate"  # 中级策略
    ADVANCED = "advanced"     # 高级技巧
    EXPERT = "expert"        # 专家级知识

class DecisionContext(Enum):
    """决策上下文"""
    EARLY_GAME = "early_game"      # 开局
    MID_GAME = "mid_game"          # 中局
    LATE_GAME = "late_game"        # 尾局
    EMERGENCY = "emergency"        # 紧急情况
    COOPERATION = "cooperation"    # 配合情况

@dataclass
class GuandanKnowledgeItem:
    """掼蛋AI标准化知识项"""
    # 基本信息
    knowledge_id: str
    name: str
    description: str
    knowledge_level: KnowledgeLevel
    
    # 触发条件
    trigger_conditions: Dict[str, Any]
    decision_context: DecisionContext
    priority_score: float
    
    # 决策内容
    decision_rules: List[Dict[str, Any]]
    action_recommendations: List[str]
    avoidance_patterns: List[str]
    
    # 评估函数
    evaluation_criteria: Dict[str, float]
    success_indicators: List[str]
    
    # 元数据
    source_type: str  # manual, extracted, learned
    confidence_score: float
    usage_statistics: Dict[str, int]
    
    def to_ai_readable_format(self) -> Dict[str, Any]:
        """转换为AI可读格式"""
        return {
            "id": self.knowledge_id,
            "name": self.name,
            "level": self.knowledge_level.value,
            "conditions": self.trigger_conditions,
            "context": self.decision_context.value,
            "rules": self.decision_rules,
            "actions": self.action_recommendations,
            "evaluation": self.evaluation_criteria,
            "confidence": self.confidence_score,
            "priority": self.priority_score
        }

class GuandanKnowledgeFormatter:
    """掼蛋知识格式化器"""
    
    def __init__(self):
        self.knowledge_templates = self._load_knowledge_templates()
        self.validation_rules = self._load_validation_rules()
    
    def format_expert_text_to_ai_knowledge(self, expert_text: str, source: str) -> List[GuandanKnowledgeItem]:
        """将专家文本转换为AI可读知识"""
        knowledge_items = []
        
        # 1. 文本预处理和分块
        text_chunks = self._preprocess_and_chunk_text(expert_text)
        
        # 2. 知识抽取
        extracted_knowledge = self._extract_knowledge_from_chunks(text_chunks)
        
        # 3. 标准化格式化
        for knowledge_data in extracted_knowledge:
            formatted_item = self._format_to_standard_knowledge(knowledge_data, source)
            if self._validate_knowledge_item(formatted_item):
                knowledge_items.append(formatted_item)
        
        return knowledge_items
    
    def _preprocess_and_chunk_text(self, text: str) -> List[str]:
        """预处理和分块文本"""
        import re
        
        # 清理文本
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 按段落分块
        paragraphs = text.split('\n\n')
        
        # 按句子进一步分块
        chunks = []
        for paragraph in paragraphs:
            sentences = re.split(r'[。！？]', paragraph)
            current_chunk = ""
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) < 200:  # 块大小限制
                    current_chunk += sentence + "。"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + "。"
            
            if current_chunk:
                chunks.append(current_chunk.strip())
        
        return chunks
    
    def _extract_knowledge_from_chunks(self, chunks: List[str]) -> List[Dict[str, Any]]:
        """从文本块中抽取知识"""
        knowledge_data = []
        
        for chunk in chunks:
            # 使用规则引擎提取知识
            extracted = self._extract_using_rules(chunk)
            
            if extracted:
                knowledge_data.append(extracted)
        
        return knowledge_data
    
    def _extract_using_rules(self, text_chunk: str) -> Optional[Dict[str, Any]]:
        """使用规则引擎提取知识"""
        import re
        
        # 规则模式匹配
        patterns = {
            '出牌策略': [
                r'出牌.*?策略.*?([^。]{20,100}[。])',
                r'应该.*?出.*?([^。]{10,50}[。])',
                r'建议.*?出.*?([^。]{10,50}[。])'
            ],
            '配合技巧': [
                r'配合.*?([^。]{20,100}[。])',
                r'搭档.*?([^。]{15,80}[。])',
                r'队友.*?([^。]{15,80}[。])'
            ],
            '升级策略': [
                r'升级.*?([^。]{20,100}[。])',
                r'上游.*?([^。]{15,80}[。])'
            ],
            '防守技巧': [
                r'防守.*?([^。]{20,100}[。])',
                r'压制.*?([^。]{15,80}[。])',
                r'阻止.*?([^。]{15,80}[。])'
            ]
        }
        
        for knowledge_type, type_patterns in patterns.items():
            for pattern in type_patterns:
                matches = re.findall(pattern, text_chunk)
                if matches:
                    return {
                        'type': knowledge_type,
                        'content': matches[0].strip(),
                        'source_text': text_chunk,
                        'extraction_confidence': 0.8
                    }
        
        return None
    
    def _format_to_standard_knowledge(self, knowledge_data: Dict[str, Any], source: str) -> GuandanKnowledgeItem:
        """格式化到标准知识格式"""
        # 生成知识ID
        knowledge_id = self._generate_knowledge_id(knowledge_data)
        
        # 确定知识级别
        level = self._determine_knowledge_level(knowledge_data)
        
        # 确定决策上下文
        context = self._determine_decision_context(knowledge_data)
        
        # 构建触发条件
        trigger_conditions = self._build_trigger_conditions(knowledge_data)
        
        # 构建决策规则
        decision_rules = self._build_decision_rules(knowledge_data)
        
        # 构建行动建议
        action_recommendations = self._build_action_recommendations(knowledge_data)
        
        return GuandanKnowledgeItem(
            knowledge_id=knowledge_id,
            name=f"{knowledge_data['type']}_{knowledge_id}",
            description=knowledge_data['content'],
            knowledge_level=level,
            trigger_conditions=trigger_conditions,
            decision_context=context,
            priority_score=self._calculate_priority_score(knowledge_data),
            decision_rules=decision_rules,
            action_recommendations=action_recommendations,
            avoidance_patterns=[],
            evaluation_criteria=self._build_evaluation_criteria(knowledge_data),
            success_indicators=self._build_success_indicators(knowledge_data),
            source_type="extracted",
            confidence_score=knowledge_data['extraction_confidence'],
            usage_statistics={}
        )
    
    def _generate_knowledge_id(self, knowledge_data: Dict[str, Any]) -> str:
        """生成知识ID"""
        import hashlib
        content = f"{knowledge_data['type']}_{knowledge_data['content']}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def _determine_knowledge_level(self, knowledge_data: Dict[str, Any]) -> KnowledgeLevel:
        """确定知识级别"""
        content = knowledge_data['content'].lower()
        
        # 基于关键词判断级别
        if any(keyword in content for keyword in ['基础', '新手', '简单']):
            return KnowledgeLevel.BASIC
        elif any(keyword in content for keyword in ['高级', '复杂', '深度']):
            return KnowledgeLevel.ADVANCED
        elif any(keyword in content for keyword in ['专家', '专业']):
            return KnowledgeLevel.EXPERT
        else:
            return KnowledgeLevel.INTERMEDIATE
    
    def _determine_decision_context(self, knowledge_data: Dict[str, Any]) -> DecisionContext:
        """确定决策上下文"""
        content = knowledge_data['content']
        
        if any(keyword in content for keyword in ['开局', '开始', '首先']):
            return DecisionContext.EARLY_GAME
        elif any(keyword in content for keyword in ['配合', '搭档', '队友']):
            return DecisionContext.COOPERATION
        elif any(keyword in content for keyword in ['最后', '尾局', '收官']):
            return DecisionContext.LATE_GAME
        else:
            return DecisionContext.MID_GAME
    
    def _build_trigger_conditions(self, knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建触发条件"""
        conditions = {
            "knowledge_type": knowledge_data['type'],
            "content_keywords": self._extract_keywords(knowledge_data['content']),
            "context_requirements": self._determine_context_requirements(knowledge_data)
        }
        
        return conditions
    
    def _build_decision_rules(self, knowledge_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """构建决策规则"""
        rules = [
            {
                "rule_id": f"rule_{knowledge_data['type']}_1",
                "condition": f"当遇到 {knowledge_data['type']} 相关局面时",
                "action": knowledge_data['content'],
                "priority": 1,
                "weight": 1.0
            }
        ]
        
        return rules
    
    def _build_action_recommendations(self, knowledge_data: Dict[str, Any]) -> List[str]:
        """构建行动建议"""
        content = knowledge_data['content']
        
        # 提取行动动词和短语
        import re
        action_patterns = [
            r'应该([^，。]{5,20})',
            r'建议([^，。]{5,20})',
            r'可以([^，。]{5,20})',
            r'需要([^，。]{5,20})'
        ]
        
        actions = []
        for pattern in action_patterns:
            matches = re.findall(pattern, content)
            actions.extend(matches)
        
        if not actions:
            actions = [content]  # 默认使用原内容
        
        return actions[:3]  # 最多3个建议
    
    def _build_evaluation_criteria(self, knowledge_data: Dict[str, Any]) -> Dict[str, float]:
        """构建评估标准"""
        return {
            "relevance": 0.8,
            "actionability": 0.7,
            "clarity": 0.8,
            "completeness": 0.6
        }
    
    def _build_success_indicators(self, knowledge_data: Dict[str, Any]) -> List[str]:
        """构建成功指标"""
        return [
            "决策执行成功",
            "符合规则要求",
            "达到预期效果"
        ]
    
    def _calculate_priority_score(self, knowledge_data: Dict[str, Any]) -> float:
        """计算优先级分数"""
        base_score = 0.5
        
        # 基于知识类型调整分数
        type_multipliers = {
            '出牌策略': 1.0,
            '配合技巧': 0.9,
            '升级策略': 0.8,
            '防守技巧': 0.7
        }
        
        multiplier = type_multipliers.get(knowledge_data['type'], 0.5)
        return base_score * multiplier
```

#### 2. 知识可视化验证器

```python
# src/validation/knowledge_validator.py
from typing import List, Dict, Any
import json

class KnowledgeValidator:
    """知识验证器"""
    
    def __init__(self):
        self.validation_rules = self._load_validation_rules()
        self.syntax_checker = KnowledgeSyntaxChecker()
        self.semantic_checker = KnowledgeSemanticChecker()
    
    async def validate(self, knowledge_item: GuandanKnowledgeItem) -> bool:
        """验证知识项"""
        validation_result = {
            "syntax_valid": self.syntax_checker.validate(knowledge_item),
            "semantic_valid": self.semantic_checker.validate(knowledge_item),
            "completeness_check": self._check_completeness(knowledge_item),
            "consistency_check": self._check_consistency(knowledge_item)
        }
        
        # 只有全部通过才认为有效
        return all(validation_result.values())
    
    def _check_completeness(self, item: GuandanKnowledgeItem) -> bool:
        """检查完整性"""
        required_fields = [
            'knowledge_id', 'name', 'description', 'knowledge_level',
            'trigger_conditions', 'decision_rules', 'action_recommendations'
        ]
        
        return all(hasattr(item, field) for field in required_fields)
    
    def _check_consistency(self, item: GuandanKnowledgeItem) -> bool:
        """检查一致性"""
        # 检查优先级分数范围
        if not (0.0 <= item.priority_score <= 1.0):
            return False
        
        # 检查置信度分数范围
        if not (0.0 <= item.confidence_score <= 1.0):
            return False
        
        return True

class KnowledgeSyntaxChecker:
    """知识语法检查器"""
    
    def validate(self, knowledge_item: GuandanKnowledgeItem) -> bool:
        """语法验证"""
        # ID格式检查
        if not knowledge_item.knowledge_id.replace('_', '').isalnum():
            return False
        
        # 字符串长度检查
        if len(knowledge_item.name) < 3 or len(knowledge_item.name) > 50:
            return False
        
        return True

class KnowledgeSemanticChecker:
    """知识语义检查器"""
    
    def validate(self, knowledge_item: GuandanKnowledgeItem) -> bool:
        """语义验证"""
        # 检查决策规则的有效性
        for rule in knowledge_item.decision_rules:
            if not self._validate_decision_rule(rule):
                return False
        
        return True
    
    def _validate_decision_rule(self, rule: Dict[str, Any]) -> bool:
        """验证决策规则"""
        required_fields = ['condition', 'action', 'priority']
        return all(field in rule for field in required_fields)
```

---

## ? 问题三：系统中是否有掼蛋AI记忆功能模块，投喂一次，终生受用？

### 解决方案：持久化记忆架构 (Persistent Memory Architecture, PMA)

#### 1. 终身记忆系统

```python
# src/memory/lifetime_memory_system.py
import asyncio
import sqlite3
import pickle
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json

@dataclass
class MemoryEntry:
    """记忆条目"""
    entry_id: str
    memory_type: str  # knowledge, experience, pattern, lesson
    content: Dict[str, Any]
    importance_score: float
    access_count: int
    last_accessed: datetime
    created_at: datetime
    tags: List[str]
    decay_factor: float = 0.95

class LifetimeMemorySystem:
    """终身记忆系统"""
    
    def __init__(self, memory_dir: str = "data/memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        # 记忆数据库
        self.db_path = self.memory_dir / "lifetime_memory.db"
        self._initialize_memory_database()
        
        # 记忆缓存
        self.memory_cache = {}
        self.frequent_memories = {}
        
        # 记忆管理
        self.memory_manager = MemoryManager()
        self.memory_retriever = MemoryRetriever()
        self.memory_consolidator = MemoryConsolidator()
        
    def _initialize_memory_database(self):
        """初始化记忆数据库"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS memory_entries (
                    entry_id TEXT PRIMARY KEY,
                    memory_type TEXT,
                    content TEXT,
                    importance_score REAL,
                    access_count INTEGER,
                    last_accessed TEXT,
                    created_at TEXT,
                    tags TEXT,
                    decay_factor REAL,
                    effectiveness_score REAL DEFAULT 0.0
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS memory_associations (
                    entry_id_1 TEXT,
                    entry_id_2 TEXT,
                    association_strength REAL,
                    association_type TEXT,
                    created_at TEXT,
                    FOREIGN KEY (entry_id_1) REFERENCES memory_entries (entry_id),
                    FOREIGN KEY (entry_id_2) REFERENCES memory_entries (entry_id)
                )
            ''')
    
    async def store_knowledge_memory(self, knowledge_item: GuandanKnowledgeItem, 
                                   context: Dict[str, Any] = None) -> str:
        """存储知识记忆"""
        memory_entry = MemoryEntry(
            entry_id=f"knowledge_{knowledge_item.knowledge_id}",
            memory_type="knowledge",
            content={
                "knowledge_item": asdict(knowledge_item),
                "context": context or {},
                "storage_metadata": {
                    "stored_by": "knowledge_injection_system",
                    "original_source": "expert_knowledge"
                }
            },
            importance_score=self._calculate_knowledge_importance(knowledge_item),
            access_count=0,
            last_accessed=datetime.now(),
            created_at=datetime.now(),
            tags=knowledge_item.tags + ["knowledge", "expert"],
            decay_factor=0.98  # 知识记忆衰减很慢
        )
        
        # 存储到数据库
        await self._store_memory_entry(memory_entry)
        
        # 构建记忆关联
        await self._build_memory_associations(memory_entry)
        
        # 更新缓存
        self.memory_cache[memory_entry.entry_id] = memory_entry
        
        return memory_entry.entry_id
    
    async def store_experience_memory(self, experience_data: Dict[str, Any]) -> str:
        """存储经验记忆"""
        memory_entry = MemoryEntry(
            entry_id=f"experience_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            memory_type="experience",
            content=experience_data,
            importance_score=self._calculate_experience_importance(experience_data),
            access_count=0,
            last_accessed=datetime.now(),
            created_at=datetime.now(),
            tags=experience_data.get("tags", ["experience"]),
            decay_factor=0.90  # 经验记忆中等衰减
        )
        
        await self._store_memory_entry(memory_entry)
        await self._build_memory_associations(memory_entry)
        
        self.memory_cache[memory_entry.entry_id] = memory_entry
        
        return memory_entry.entry_id
    
    async def retrieve_relevant_memories(self, query_context: Dict[str, Any], 
                                       max_results: int = 10) -> List[MemoryEntry]:
        """检索相关记忆"""
        # 使用记忆检索器
        relevant_memories = await self.memory_retriever.retrieve(
            query_context, max_results, self.memory_cache
        )
        
        # 更新访问统计
        for memory in relevant_memories:
            await self._update_memory_access(memory.entry_id)
        
        return relevant_memories
    
    async def consolidate_memories(self):
        """记忆整合"""
        self.logger.info("开始记忆整合...")
        
        # 获取需要整合的记忆
        candidates = await self._get_consolidation_candidates()
        
        # 执行整合
        for candidate_group in candidates:
            consolidated_memory = await self.memory_consolidator.consolidate(candidate_group)
            await self._store_memory_entry(consolidated_memory)
        
        # 清理过期记忆
        await self._cleanup_expired_memories()
        
        self.logger.info("记忆整合完成")
    
    async def _store_memory_entry(self, memory_entry: MemoryEntry):
        """存储记忆条目到数据库"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO memory_entries 
                (entry_id, memory_type, content, importance_score, access_count, 
                 last_accessed, created_at, tags, decay_factor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                memory_entry.entry_id,
                memory_entry.memory_type,
                json.dumps(memory_entry.content, ensure_ascii=False),
                memory_entry.importance_score,
                memory_entry.access_count,
                memory_entry.last_accessed.isoformat(),
                memory_entry.created_at.isoformat(),
                json.dumps(memory_entry.tags),
                memory_entry.decay_factor
            ))
    
    async def _build_memory_associations(self, new_memory: MemoryEntry):
        """构建记忆关联"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # 查找相关记忆
            related_memories = await self._find_related_memories(new_memory)
            
            # 建立关联
            for related_memory in related_memories:
                association_strength = self._calculate_association_strength(new_memory, related_memory)
                
                conn.execute('''
                    INSERT OR REPLACE INTO memory_associations 
                    (entry_id_1, entry_id_2, association_strength, association_type, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    new_memory.entry_id,
                    related_memory.entry_id,
                    association_strength,
                    self._determine_association_type(new_memory, related_memory),
                    datetime.now().isoformat()
                ))
    
    def _calculate_knowledge_importance(self, knowledge_item: GuandanKnowledgeItem) -> float:
        """计算知识重要性"""
        base_importance = 0.5
        
        # 基于知识级别调整
        level_multipliers = {
            KnowledgeLevel.BASIC: 0.8,
            KnowledgeLevel.INTERMEDIATE: 1.0,
            KnowledgeLevel.ADVANCED: 1.2,
            KnowledgeLevel.EXPERT: 1.5
        }
        
        level_multiplier = level_multipliers.get(knowledge_item.knowledge_level, 1.0)
        
        # 基于置信度调整
        confidence_factor = knowledge_item.confidence_score
        
        return min(base_importance * level_multiplier * confidence_factor, 1.0)
    
    def _calculate_experience_importance(self, experience_data: Dict[str, Any]) -> float:
        """计算经验重要性"""
        base_importance = 0.6
        
        # 基于经验类型调整
        type_multipliers = {
            "successful_pattern": 1.3,
            "failure_lesson": 1.1,
            "cooperation_success": 1.2,
            "opponent_analysis": 1.0
        }
        
        type_multiplier = type_multipliers.get(experience_data.get("type"), 1.0)
        
        # 基于结果调整
        result_factor = 1.0
        if experience_data.get("outcome") == "win":
            result_factor = 1.2
        elif experience_data.get("outcome") == "loss":
            result_factor = 1.1
        
        return min(base_importance * type_multiplier * result_factor, 1.0)

#### 2. 记忆管理器

```python
# src/memory/memory_manager.py
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import heapq

class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, max_memory_entries: int = 10000):
        self.max_memory_entries = max_memory_entries
        self.memory_priority_queue = []  # (importance_score, entry_id)
        self.memory_access_tracker = {}
        
    async def manage_memory_lifecycle(self, memory_system):
        """管理记忆生命周期"""
        while True:
            try:
                # 清理低价值记忆
                await self._cleanup_low_value_memories(memory_system)
                
                # 更新记忆强度
                await self._update_memory_strengths(memory_system)
                
                # 检查记忆整合需求
                await self._check_consolidation_needs(memory_system)
                
                # 等待下次管理周期
                await asyncio.sleep(3600)  # 每小时执行一次
                
            except Exception as e:
                memory_system.logger.error(f"记忆管理错误: {e}")
                await asyncio.sleep(300)  # 错误时等待5分钟
    
    async def _cleanup_low_value_memories(self, memory_system):
        """清理低价值记忆"""
        # 获取所有记忆条目
        all_memories = await memory_system._get_all_memory_entries()
        
        # 按价值排序
        memories_with_value = []
        for memory in all_memories:
            current_value = self._calculate_current_value(memory)
            memories_with_value.append((current_value, memory))
        
        # 排序并保留高价值记忆
        memories_with_value.sort(reverse=True)
        
        if len(memories_with_value) > self.max_memory_entries:
            # 删除低价值记忆
            memories_to_delete = memories_with_value[self.max_memory_entries:]
            
            for _, memory in memories_to_delete:
                await memory_system._delete_memory_entry(memory.entry_id)
    
    def _calculate_current_value(self, memory_entry) -> float:
        """计算记忆当前价值"""
        # 基础重要性
        base_value = memory_entry.importance_score
        
        # 访问频率因子
        access_factor = min(1.0, memory_entry.access_count / 10.0)
        
        # 时间衰减因子
        days_since_creation = (datetime.now() - memory_entry.created_at).days
        time_factor = memory_entry.decay_factor ** days_since_creation
        
        # 最近使用因子
        if memory_entry.last_accessed:
            days_since_access = (datetime.now() - memory_entry.last_accessed).days
            recency_factor = max(0.1, 1.0 - (days_since_access / 30.0))
        else:
            recency_factor = 0.5
        
        return base_value * (0.4 + 0.3 * access_factor + 0.3 * time_factor) * recency_factor

#### 3. 知识-记忆融合引擎

```python
# src/fusion/knowledge_memory_fusion.py
class KnowledgeMemoryFusion:
    """知识记忆融合引擎"""
    
    def __init__(self, knowledge_system, memory_system):
        self.knowledge_system = knowledge_system
        self.memory_system = memory_system
        
    async def fuse_knowledge_with_memory(self, knowledge_item: GuandanKnowledgeItem) -> Dict[str, Any]:
        """融合知识与记忆"""
        # 1. 查找相关记忆
        relevant_memories = await self.memory_system.retrieve_relevant_memories(
            {"knowledge_type": knowledge_item.knowledge_level.value}
        )
        
        # 2. 融合新知识与已有记忆
        fused_knowledge = self._merge_knowledge_with_memories(knowledge_item, relevant_memories)
        
        # 3. 更新记忆系统
        await self.memory_system.store_knowledge_memory(fused_knowledge)
        
        # 4. 返回融合结果
        return {
            "original_knowledge": knowledge_item,
            "fused_knowledge": fused_knowledge,
            "merged_memories": len(relevant_memories),
            "fusion_metadata": {
                "fusion_timestamp": datetime.now().isoformat(),
                "memory_integration": True,
                "knowledge_enhancement": True
            }
        }
    
    def _merge_knowledge_with_memories(self, knowledge_item: GuandanKnowledgeItem, 
                                     memories: List[MemoryEntry]) -> GuandanKnowledgeItem:
        """合并知识与记忆"""
        # 增强知识内容
        enhanced_content = knowledge_item.description
        enhanced_actions = knowledge_item.action_recommendations.copy()
        
        # 从记忆中提取增强信息
        for memory in memories:
            if memory.memory_type == "experience":
                # 提取经验教训
                lessons = memory.content.get("lessons", [])
                for lesson in lessons:
                    if lesson not in enhanced_actions:
                        enhanced_actions.append(f"经验: {lesson}")
                
                # 更新置信度
                memory_confidence = memory.content.get("effectiveness_score", 0.5)
                knowledge_item.confidence_score = (knowledge_item.confidence_score + memory_confidence) / 2
        
        # 创建增强版知识项
        enhanced_knowledge = GuandanKnowledgeItem(
            knowledge_id=f"{knowledge_item.knowledge_id}_enhanced",
            name=f"{knowledge_item.name}_enhanced",
            description=enhanced_content,
            knowledge_level=knowledge_item.knowledge_level,
            trigger_conditions=knowledge_item.trigger_conditions,
            decision_context=knowledge_item.decision_context,
            priority_score=min(knowledge_item.priority_score * 1.1, 1.0),  # 适度提升优先级
            decision_rules=knowledge_item.decision_rules,
            action_recommendations=enhanced_actions,
            avoidance_patterns=knowledge_item.avoidance_patterns,
            evaluation_criteria=knowledge_item.evaluation_criteria,
            success_indicators=knowledge_item.success_indicators,
            source_type="enhanced",
            confidence_score=knowledge_item.confidence_score,
            usage_statistics=knowledge_item.usage_statistics
        )
        
        return enhanced_knowledge
```

---

## ? 完整集成方案总结

### 知识注入工作流程

```python
# 完整的知识注入和记忆系统集成
class GuandanAIFusionSystem:
    """掼蛋AI融合系统"""
    
    def __init__(self):
        # 核心系统
        self.knowledge_injection = KnowledgeInjectionSystem()
        self.memory_system = LifetimeMemorySystem()
        self.fusion_engine = KnowledgeMemoryFusion(self.knowledge_injection, self.memory_system)
        
    async def inject_and_integrate_knowledge(self, knowledge_source: str) -> Dict[str, Any]:
        """注入并整合知识"""
        integration_report = {
            "start_time": datetime.now().isoformat(),
            "knowledge_source": knowledge_source,
            "steps": []
        }
        
        try:
            # 步骤1: 知识注入
            injection_result = await self.knowledge_injection.inject_knowledge_package(knowledge_source)
            integration_report["steps"].append(("injection", injection_result))
            
            # 步骤2: 记忆存储
            memory_entries = []
            for knowledge_item in injection_result.get("processed_items", []):
                memory_id = await self.memory_system.store_knowledge_memory(knowledge_item)
                memory_entries.append(memory_id)
            
            integration_report["steps"].append(("memory_storage", {"stored_memories": len(memory_entries)}))
            
            # 步骤3: 知识融合
            fusion_results = []
            for knowledge_item in injection_result.get("processed_items", []):
                fusion_result = await self.fusion_engine.fuse_knowledge_with_memory(knowledge_item)
                fusion_results.append(fusion_result)
            
            integration_report["steps"].append(("knowledge_fusion", {"fused_items": len(fusion_results)}))
            
            integration_report["status"] = "completed"
            integration_report["total_integrated_items"] = len(fusion_results)
            
        except Exception as e:
            integration_report["status"] = "failed"
            integration_report["error"] = str(e)
        
        return integration_report

# 使用示例
async def main():
    """主函数示例"""
    fusion_system = GuandanAIFusionSystem()
    
    # 注入专家知识
    report = await fusion_system.inject_and_integrate_knowledge("experts/guandan_secrets.json")
    
    print("知识注入和整合完成！")
    print(f"状态: {report['status']}")
    print(f"整合项目数: {report.get('total_integrated_items', 0)}")
    
    # 初始化AI客户端集成
    await fusion_system.knowledge_injection.initialize_integration()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## ? 三大核心问题解决方案总结

### 1. 专业名称
- **知识注入系统** (Knowledge Injection System, KIS)
- **专家知识融合引擎** (Expert Knowledge Fusion Engine, EKFE)
- **持久化记忆架构** (Persistent Memory Architecture, PMA)

### 2. AI可读知识格式
- 标准化知识表示格式 (GuandanKnowledgeItem)
- 结构化触发条件和决策规则
- 优先级和置信度评估系统
- 完整的验证和格式化流程

### 3. 终身记忆系统
- SQLite持久化存储
- 记忆重要性评分和衰减机制
- 记忆关联和检索系统
- 自动记忆整合和清理
- **投喂一次，终生受用** ?

这套完整的系统确保您的掼蛋AI能够：
- ? **专业集成** - 无缝融入现有AI客户端
- ? **标准化学习** - 将任何专家知识转化为AI可读格式
- ? **终身记忆** - 投喂一次，终生受益，持续改进

