# �走AIר��֪ʶͶιָ��

## ? ���ĸ���

**ר��֪ʶͶι** = ��������走���ɡ����ԡ�����ת��ΪAI��ѧϰ�Ľṹ��֪ʶ����AI��ֻͨ���Ծ�ѧϰ������ֱ�Ӵ�ר��֪ʶ�л��档

## ? ��Ŀ�е�ר��֪ʶ��Դ

### 1. �ѷ��ֵ�����
- **�走����ָ��** (`docs/skill/�走����ָ��.txt`)
- **�走�����ؼ�(����).pdf** (`docs/skill/�走�����ؼ�(����).pdf`)
- **�走����ͼƬ** (`docs/gdrules/` Ŀ¼��26��ͼƬ)
- **��Դ�嵥** (`docs/skill/��Դ.txt`)

### 2. ֪ʶ���ͷ���
```
ר��֪ʶ �� �ṹ��֪ʶ �� AI��ѧϰ��ʽ
     ��           ��              ��
������    ��  ���Կ�      ��  ���߹���
ʵս����    ��  ģʽ��      ��  ����ģʽ
���Ʒ���    ��  ��������    ��  ��ֵ����
���ս��    ��  ��ϲ���    ��  �Ŷ�AI
```

## ? ֪ʶ��ȡ��ṹ��

### ��һ����֪ʶ��ȡ��

**1. �ĵ�������**
```python
# src/knowledge/extractor.py
import re
from typing import List, Dict, Tuple
from pathlib import Path
import json

class ExpertKnowledgeExtractor:
    """ר��֪ʶ��ȡ��"""
    
    def __init__(self):
        self.knowledge_base = {
            "basic_rules": {},
            "strategies": [],
            "card_values": {},
            "cooperation_tactics": [],
            "situational_play": []
        }
    
    def extract_from_text(self, text: str, source: str) -> Dict:
        """���ı�����ȡ֪ʶ"""
        extracted = {
            "source": source,
            "extraction_time": datetime.now().isoformat(),
            "rules": [],
            "strategies": [],
            "tips": [],
            "tactics": []
        }
        
        # ��ȡ��������
        extracted["rules"] = self._extract_rules(text)
        
        # ��ȡ���Լ���
        extracted["strategies"] = self._extract_strategies(text)
        
        # ��ȡʵս����
        extracted["tips"] = self._extract_tips(text)
        
        # ��ȡս�����
        extracted["tactics"] = self._extract_tactics(text)
        
        return extracted
    
    def _extract_rules(self, text: str) -> List[Dict]:
        """��ȡ��������"""
        rules = []
        
        # ƥ�����ģʽ
        rule_patterns = [
            r"(����|����|����|ը��|˳��|ͬ��˳).*?����",
            r"ʹ��.*?����.*?(\d+).*?��",
            r"����.*?����.*?([^��]+)",
            r"����.*?����.*?([^��]+)"
        ]
        
        for pattern in rule_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                rules.append({
                    "type": "basic_rule",
                    "content": match.strip(),
                    "priority": "high"
                })
        
        return rules
    
    def _extract_strategies(self, text: str) -> List[Dict]:
        """��ȡ���Լ���"""
        strategies = []
        
        # ���Թؼ���
        strategy_keywords = [
            "���Ʋ���", "����", "���", "ѹ��", "����",
            "������", "������", "�ƶ���", "ʱ������"
        ]
        
        for keyword in strategy_keywords:
            pattern = f"{keyword}.*?([^��]{{20,100}}[��])"
            matches = re.findall(pattern, text, re.DOTALL)
            
            for match in matches:
                strategies.append({
                    "type": "strategy",
                    "keyword": keyword,
                    "content": match.strip(),
                    "situation": "general",
                    "effectiveness": 0.7  # Ĭ������
                })
        
        return strategies
    
    def _extract_tips(self, text: str) -> List[Dict]:
        """��ȡʵս����"""
        tips = []
        
        # ����ģʽ
        tip_patterns = [
            r"����.*?([^��]{{10,50}}[��])",
            r"����.*?([^��]{{10,50}}[��])",
            r"����.*?([^��]{{10,50}}[��])",
            r"��ϰ.*?([^��]{{10,50}}[��])"
        ]
        
        for pattern in tip_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                tips.append({
                    "type": "tip",
                    "content": match.strip(),
                    "level": "beginner",
                    "category": "general"
                })
        
        return tips
    
    def _extract_tactics(self, text: str) -> List[Dict]:
        """��ȡս�����"""
        tactics = []
        
        # ���ģʽ
        cooperation_patterns = [
            r"�.*?([^��]{{15,80}}[��])",
            r"����.*?([^��]{{15,80}}[��])",
            r"���.*?([^��]{{15,80}}[��])",
            r"�Ŷ�.*?([^��]{{15,80}}[��])"
        ]
        
        for pattern in cooperation_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                tactics.append({
                    "type": "tactic",
                    "content": match.strip(),
                    "scope": "team",
                    "complexity": "medium"
                })
        
        return tactics

    def load_all_knowledge(self) -> Dict:
        """��������֪ʶ��Դ"""
        knowledge_sources = [
            "docs/skill/�走����ָ��.txt",
            # ����PDF�ļ���Ҫ���⴦��
        ]
        
        all_knowledge = {}
        
        for source in knowledge_sources:
            try:
                with open(source, 'r', encoding='utf-8') as f:
                    content = f.read()
                    extracted = self.extract_from_text(content, source)
                    all_knowledge[Path(source).stem] = extracted
            except Exception as e:
                print(f"����֪ʶԴʧ��: {source}, ����: {e}")
        
        return all_knowledge
```

### �ڶ�����֪ʶ�ṹ��

**2. ֪ʶ�⹹����**
```python
# src/knowledge/knowledge_base.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json

class KnowledgeType(Enum):
    """֪ʶ����ö��"""
    BASIC_RULE = "basic_rule"
    STRATEGY = "strategy"
    TACTIC = "tactic"
    TIP = "tip"
    PATTERN = "pattern"
    EVALUATION = "evaluation"

@dataclass
class KnowledgeItem:
    """֪ʶ��"""
    id: str
    type: KnowledgeType
    content: str
    source: str
    confidence: float
    situation: str
    priority: int
    tags: List[str]
    metadata: Dict[str, Any]

class GuandanKnowledgeBase:
    """�走֪ʶ��"""
    
    def __init__(self):
        self.knowledge_items = []
        self.strategy_rules = []
        self.evaluation_functions = []
        self.situation_patterns = []
        
    def add_knowledge_item(self, item: KnowledgeItem):
        """����֪ʶ��"""
        self.knowledge_items.append(item)
    
    def build_strategy_rules(self) -> List[Dict]:
        """�������Թ���"""
        strategy_rules = []
        
        for item in self.knowledge_items:
            if item.type == KnowledgeType.STRATEGY:
                # ������ת��Ϊ��ִ�еĹ���
                rule = {
                    "id": f"strategy_{item.id}",
                    "condition": self._extract_conditions(item.content),
                    "action": self._extract_actions(item.content),
                    "priority": item.priority,
                    "confidence": item.confidence,
                    "source": item.source
                }
                strategy_rules.append(rule)
        
        return strategy_rules
    
    def _extract_conditions(self, content: str) -> List[str]:
        """��ȡ��������"""
        conditions = []
        
        # �����������ؼ���
        condition_keywords = [
            "���", "��", "����", "������", "����", "����",
            "����", "����", "����", "ը��", "����"
        ]
        
        for keyword in condition_keywords:
            if keyword in content:
                conditions.append(keyword)
        
        return conditions
    
    def _extract_actions(self, content: str) -> List[str]:
        """��ȡ�ж�����"""
        actions = []
        
        # �������ж��ؼ���
        action_keywords = [
            "��", "��", "��", "ѹ", "��", "���", "����", "��",
            "��", "��", "ʹ��", "����", "ע��"
        ]
        
        for keyword in action_keywords:
            if keyword in content:
                actions.append(keyword)
        
        return actions
    
    def build_evaluation_functions(self) -> Dict:
        """������������"""
        evaluations = {
            "card_value": self._build_card_value_function(),
            "hand_strength": self._build_hand_strength_function(),
            "situation_advantage": self._build_situation_advantage_function(),
            "cooperation_score": self._build_cooperation_function()
        }
        
        return evaluations
    
    def _build_card_value_function(self) -> Dict:
        """������ֵ��������"""
        return {
            "type": "card_value",
            "description": "����ר��֪ʶ����ֵ����",
            "factors": {
                "basic_rank": {
                    "A": 14, "K": 13, "Q": 12, "J": 11,
                    "10": 10, "9": 9, "8": 8, "7": 7,
                    "6": 6, "5": 5, "4": 4, "3": 3, "2": 2
                },
                "suit_priority": {
                    "����": 20,  # �������ȼ����
                    "����": 15,  # �����Ǽ���ʱ���⴦��
                    "����": 10
                },
                "position_bonus": {
                    "�׷�": 5,
                    "���": 3,
                    "ѹ��": 7,
                    "����": 2
                }
            },
            "formula": "������ + ��ɫ�� + λ�÷�"
        }
    
    def _build_hand_strength_function(self) -> Dict:
        """��������ǿ����������"""
        return {
            "type": "hand_strength",
            "description": "������ǰ���Ƶ�����ǿ��",
            "factors": {
                "card_count": {"weight": 0.3},
                "bomb_count": {"weight": 0.4},
                "high_card_ratio": {"weight": 0.2},
                "flexible_combo": {"weight": 0.1}
            },
            "formula": "��Ȩ���"
        }
    
    def build_situation_patterns(self) -> List[Dict]:
        """��������ģʽ"""
        patterns = []
        
        # ����ר��֪ʶ�������;���ģʽ
        patterns.append({
            "id": "early_game_opening",
            "description": "���ֽ׶�",
            "characteristics": [
                "���ƽ϶�",
                "����δȷ��",
                "��Ϣ�����"
            ],
            "recommended_strategies": [
                "���س���",
                "�۲����",
                "����ʵ��"
            ]
        })
        
        patterns.append({
            "id": "mid_game_battle",
            "description": "�оֶ�ս",
            "characteristics": [
                "����ȷ��",
                "����ʵ������",
                "�����Ҫ"
            ],
            "recommended_strategies": [
                "����ѹ��",
                "�Ŷ����",
                "ʱ������"
            ]
        })
        
        patterns.append({
            "id": "late_game_finish",
            "description": "β���չ�",
            "characteristics": [
                "���Ƽ���",
                "��������",
                "�ؼ�ʱ��"
            ],
            "recommended_strategies": [
                "���ϳ���",
                "����������",
                "��������"
            ]
        })
        
        return patterns
    
    def export_knowledge(self, output_path: str):
        """����֪ʶ��"""
        export_data = {
            "knowledge_items": [asdict(item) for item in self.knowledge_items],
            "strategy_rules": self.build_strategy_rules(),
            "evaluation_functions": self.build_evaluation_functions(),
            "situation_patterns": self.build_situation_patterns(),
            "metadata": {
                "version": "1.0",
                "build_time": datetime.now().isoformat(),
                "total_items": len(self.knowledge_items)
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

    def load_from_file(self, file_path: str):
        """���ļ�����֪ʶ��"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # �ؽ�֪ʶ��
        self.knowledge_items = []
        for item_data in data["knowledge_items"]:
            item = KnowledgeItem(
                id=item_data["id"],
                type=KnowledgeType(item_data["type"]),
                content=item_data["content"],
                source=item_data["source"],
                confidence=item_data["confidence"],
                situation=item_data["situation"],
                priority=item_data["priority"],
                tags=item_data["tags"],
                metadata=item_data["metadata"]
            )
            self.knowledge_items.append(item)
```

## ? AI֪ʶ����ϵͳ

### ��������֪ʶ����AI

**3. ֪ʶ��֪��������**
```python
# src/ai/knowledge_driven_ai.py
from typing import List, Dict, Optional, Tuple
import json
from ..knowledge.knowledge_base import GuandanKnowledgeBase, KnowledgeType
from ..game_logic.cards import Card, PlayedCard
from ..game_logic.game_state import GameState

class KnowledgeDrivenAI:
    """֪ʶ������AI"""
    
    def __init__(self, game_state: GameState, knowledge_base: GuandanKnowledgeBase):
        self.game_state = game_state
        self.kb = knowledge_base
        self.applied_strategies = []
        self.learned_patterns = []
        
    def make_decision(self) -> Optional[List[Card]]:
        """�������ߣ��ں�֪ʶ�;��飩"""
        # 1. ��ȡ���ó���
        available_plays = self.game_state.get_available_cards()
        if not available_plays:
            return None
        
        # 2. ������ǰ����
        situation_analysis = self._analyze_situation()
        
        # 3. Ӧ��ר��֪ʶ
        knowledge_based_plays = self._apply_expert_knowledge(available_plays, situation_analysis)
        
        # 4. ��Ͼ���ѧϰ
        experience_based_plays = self._apply_experience_learning(available_plays)
        
        # 5. �ۺ�����ѡ��
        final_play = self._comprehensive_evaluation(
            available_plays, 
            knowledge_based_plays, 
            experience_based_plays,
            situation_analysis
        )
        
        return final_play
    
    def _analyze_situation(self) -> Dict:
        """������ǰ����"""
        analysis = {
            "game_phase": self._determine_game_phase(),
            "position": self._analyze_position(),
            "hand_strength": self._evaluate_hand_strength(),
            "team_situation": self._analyze_team_situation(),
            "opponent_threat": self._assess_opponent_threat()
        }
        
        return analysis
    
    def _apply_expert_knowledge(self, plays: List[List[Card]], situation: Dict) -> List[Tuple[List[Card], float]]:
        """Ӧ��ר��֪ʶ"""
        scored_plays = []
        
        # ƥ����Թ���
        matching_rules = self._find_matching_rules(situation)
        
        for play in plays:
            score = 0.0
            for rule in matching_rules:
                rule_score = self._evaluate_play_against_rule(play, rule)
                score += rule_score * rule["confidence"]
            
            scored_plays.append((play, score))
        
        # ��֪ʶ��������
        scored_plays.sort(key=lambda x: x[1], reverse=True)
        return scored_plays
    
    def _find_matching_rules(self, situation: Dict) -> List[Dict]:
        """����ƥ��Ĳ��Թ���"""
        matching_rules = []
        
        for rule in self.kb.strategy_rules:
            if self._rule_matches_situation(rule, situation):
                matching_rules.append(rule)
        
        return matching_rules
    
    def _rule_matches_situation(self, rule: Dict, situation: Dict) -> bool:
        """�жϹ����Ƿ�ƥ�䵱ǰ����"""
        conditions = rule["conditions"]
        
        # �����Ϸ�׶�ƥ��
        if "����" in conditions and situation["game_phase"] == "early":
            return True
        if "�о�" in conditions and situation["game_phase"] == "mid":
            return True
        if "β��" in conditions and situation["game_phase"] == "late":
            return True
        
        # ���λ��ƥ��
        if "�׷�" in conditions and situation["position"] == "first":
            return True
        if "���" in conditions and situation["team_situation"]["need_cooperation"]:
            return True
        
        # �������ǿ��ƥ��
        if "ǿ��" in conditions and situation["hand_strength"] == "strong":
            return True
        if "����" in conditions and situation["hand_strength"] == "weak":
            return True
        
        return False
    
    def _evaluate_play_against_rule(self, play: List[Card], rule: Dict) -> float:
        """���������Ƿ���Ϲ���"""
        score = 0.0
        actions = rule["actions"]
        
        # ������������
        play_features = self._analyze_play_features(play)
        
        # ����Ƿ����������ж�
        for action in actions:
            if action in play_features["suggested_actions"]:
                score += 0.3
        
        # ����Ƿ����ר�ҽ����ʱ��
        if self._is_good_timing(play, rule):
            score += 0.4
        
        # ����Ƿ���ϲ�����ͼ
        if self._matches_strategy_intent(play, rule):
            score += 0.3
        
        return min(score, 1.0)  # ��߷ֲ�����1.0
    
    def _analyze_play_features(self, play: List[Card]) -> Dict:
        """������������"""
        features = {
            "card_count": len(play),
            "card_types": self._identify_card_types(play),
            "risk_level": self._assess_risk_level(play),
            "suggested_actions": []
        }
        
        # �����Ƶ������ƶϿ��ܵ��ж�
        if len(play) == 1:
            features["suggested_actions"].extend(["��", "��"])
        elif self._is_bomb(play):
            features["suggested_actions"].extend(["ʹ��", "ѹ��"])
        elif self._is_low_value(play):
            features["suggested_actions"].extend(["��", "��"])
        
        return features
    
    def _apply_experience_learning(self, plays: List[List[Card]]) -> List[Tuple[List[Card], float]]:
        """Ӧ�þ���ѧϰ"""
        # ������Լ���֮ǰ�ĶԾ־����ģʽʶ��
        scored_plays = []
        
        for play in plays:
            # �������֣�������ʷ���֣�
            experience_score = self._get_experience_score(play)
            scored_plays.append((play, experience_score))
        
        scored_plays.sort(key=lambda x: x[1], reverse=True)
        return scored_plays
    
    def _comprehensive_evaluation(self, all_plays: List[List[Card]], 
                                knowledge_plays: List[Tuple[List[Card], float]],
                                experience_plays: List[Tuple[List[Card], float]],
                                situation: Dict) -> List[Card]:
        """�ۺ�����ѡ����ѳ���"""
        if not knowledge_plays:
            # û��ƥ���ר��֪ʶ��ʹ�þ���
            return experience_plays[0][0] if experience_plays else all_plays[0]
        
        best_play = None
        best_score = -1.0
        
        # Ϊÿ�����Ƽ����ۺϵ÷�
        for play in all_plays:
            knowledge_score = self._get_score_for_play(play, knowledge_plays)
            experience_score = self._get_score_for_play(play, experience_plays)
            
            # Ȩ�����ã�֪ʶ70%������30%
            total_score = knowledge_score * 0.7 + experience_score * 0.3
            
            # ���ݾ������Ȩ��
            if situation["game_phase"] == "early":
                total_score = knowledge_score * 0.8 + experience_score * 0.2  # ���ڸ�����֪ʶ
            elif situation["game_phase"] == "late":
                total_score = knowledge_score * 0.6 + experience_score * 0.4  # ���ڸ���������
            
            if total_score > best_score:
                best_score = total_score
                best_play = play
        
        return best_play if best_play else all_plays[0]
    
    def _get_score_for_play(self, play: List[List[Card]], scored_plays: List[Tuple[List[Card], float]]) -> float:
        """��ȡ�����������б��еĵ÷�"""
        for scored_play, score in scored_plays:
            if self._plays_equal(scored_play, play):
                return score
        return 0.0
    
    def _plays_equal(self, play1: List[Card], play2: List[Card]) -> bool:
        """�ж����������Ƿ���ͬ"""
        if len(play1) != len(play2):
            return False
        
        # ת��Ϊ�ַ����Ƚ�
        return sorted([str(card) for card in play1]) == sorted([str(card) for card in play2])
```

## ? ֪ʶѧϰ�ܵ�

### ���Ĳ�������ѧϰϵͳ

**4. ר��֪ʶѧϰ�ܵ�**
```python
# src/learning/knowledge_learning_pipeline.py
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from ..knowledge.extractor import ExpertKnowledgeExtractor
from ..knowledge.knowledge_base import GuandanKnowledgeBase, KnowledgeItem, KnowledgeType

class KnowledgeLearningPipeline:
    """ר��֪ʶѧϰ�ܵ�"""
    
    def __init__(self, output_dir: str = "data/knowledge"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.extractor = ExpertKnowledgeExtractor()
        self.kb = GuandanKnowledgeBase()
        
    async def learn_from_documents(self) -> Dict[str, Any]:
        """���ĵ�ѧϰ"""
        learning_report = {
            "start_time": datetime.now().isoformat(),
            "sources_processed": [],
            "knowledge_extracted": 0,
            "rules_generated": 0,
            "patterns_identified": 0,
            "errors": []
        }
        
        try:
            # 1. ��������֪ʶԴ
            all_knowledge = self.extractor.load_all_knowledge()
            
            # 2. ����ÿ��֪ʶԴ
            for source_name, knowledge_data in all_knowledge.items():
                learning_report["sources_processed"].append(source_name)
                
                # ��ȡ���ṹ��֪ʶ
                self._process_knowledge_source(source_name, knowledge_data)
                
                learning_report["knowledge_extracted"] += len(knowledge_data.get("rules", []))
                learning_report["knowledge_extracted"] += len(knowledge_data.get("strategies", []))
            
            # 3. ����֪ʶ��
            await self._build_knowledge_base()
            
            # 4. ��֤֪ʶһ����
            validation_result = self._validate_knowledge_base()
            
            # 5. ����ѧϰ����
            learning_report.update({
                "end_time": datetime.now().isoformat(),
                "rules_generated": len(self.kb.build_strategy_rules()),
                "evaluation_functions": len(self.kb.build_evaluation_functions()),
                "patterns_identified": len(self.kb.build_situation_patterns()),
                "validation_result": validation_result
            })
            
            # 6. ����֪ʶ��
            await self._save_knowledge_base()
            
        except Exception as e:
            learning_report["errors"].append(str(e))
        
        return learning_report
    
    def _process_knowledge_source(self, source_name: str, knowledge_data: Dict):
        """��������֪ʶԴ"""
        # ��������
        for rule in knowledge_data.get("rules", []):
            item = KnowledgeItem(
                id=f"{source_name}_rule_{len(self.kb.knowledge_items)}",
                type=KnowledgeType.BASIC_RULE,
                content=rule["content"],
                source=source_name,
                confidence=0.9,  # ������֪ʶ���Ŷȸ�
                situation="general",
                priority=1,
                tags=["rule", "basic"],
                metadata=rule
            )
            self.kb.add_knowledge_item(item)
        
        # ��������
        for strategy in knowledge_data.get("strategies", []):
            item = KnowledgeItem(
                id=f"{source_name}_strategy_{len(self.kb.knowledge_items)}",
                type=KnowledgeType.STRATEGY,
                content=strategy["content"],
                source=source_name,
                confidence=strategy.get("effectiveness", 0.7),
                situation=strategy.get("situation", "general"),
                priority=2,
                tags=["strategy", strategy.get("keyword", "general")],
                metadata=strategy
            )
            self.kb.add_knowledge_item(item)
        
        # ��������
        for tip in knowledge_data.get("tips", []):
            item = KnowledgeItem(
                id=f"{source_name}_tip_{len(self.kb.knowledge_items)}",
                type=KnowledgeType.TIP,
                content=tip["content"],
                source=source_name,
                confidence=0.8,
                situation=tip.get("level", "beginner"),
                priority=3,
                tags=["tip", tip.get("category", "general")],
                metadata=tip
            )
            self.kb.add_knowledge_item(item)
    
    async def _build_knowledge_base(self):
        """����֪ʶ��"""
        # ������������첽�����߼�
        pass
    
    def _validate_knowledge_base(self) -> Dict[str, Any]:
        """��֤֪ʶ��"""
        validation_result = {
            "total_items": len(self.kb.knowledge_items),
            "rule_consistency": True,
            "strategy_coverage": 0.0,
            "quality_score": 0.0,
            "issues": []
        }
        
        # ������һ����
        rules = [item for item in self.kb.knowledge_items if item.type == KnowledgeType.BASIC_RULE]
        strategies = [item for item in self.kb.knowledge_items if item.type == KnowledgeType.STRATEGY]
        
        # ������Ը�����
        strategy_keywords = {"����", "���", "����", "ѹ��", "����"}
        covered_keywords = set()
        
        for strategy in strategies:
            for keyword in strategy_keywords:
                if keyword in strategy.content:
                    covered_keywords.add(keyword)
        
        validation_result["strategy_coverage"] = len(covered_keywords) / len(strategy_keywords)
        
        # ������������
        validation_result["quality_score"] = self._calculate_quality_score()
        
        return validation_result
    
    def _calculate_quality_score(self) -> float:
        """����֪ʶ��������"""
        if not self.kb.knowledge_items:
            return 0.0
        
        # ���ڶ��ά�ȼ�������
        quality_factors = {
            "completeness": self._evaluate_completeness(),
            "consistency": self._evaluate_consistency(),
            "actionability": self._evaluate_actionability(),
            "confidence": self._evaluate_confidence()
        }
        
        # ��Ȩƽ��
        weights = {"completeness": 0.3, "consistency": 0.3, "actionability": 0.2, "confidence": 0.2}
        
        quality_score = sum(quality_factors[key] * weights[key] for key in weights)
        return min(quality_score, 1.0)
    
    def _evaluate_completeness(self) -> float:
        """����������"""
        # ����Ƿ񸲸������л���Ҫ��
        required_elements = [
            "���ƹ���", "��ϲ���", "��������", "��������",
            "ʱ������", "���տ���", "�ŶӺ���"
        ]
        
        covered_elements = 0
        for element in required_elements:
            for item in self.kb.knowledge_items:
                if element in item.content:
                    covered_elements += 1
                    break
        
        return covered_elements / len(required_elements)
    
    def _evaluate_consistency(self) -> float:
        """����һ����"""
        # �򻯵�һ���Լ��
        return 0.8  # �����������ݹ���
    
    def _evaluate_actionability(self) -> float:
        """�����ɲ�����"""
        actionable_items = 0
        for item in self.kb.knowledge_items:
            if any(keyword in item.content for keyword in ["Ӧ��", "����", "��Ҫ", "����"]):
                actionable_items += 1
        
        return actionable_items / len(self.kb.knowledge_items) if self.kb.knowledge_items else 0
    
    def _evaluate_confidence(self) -> float:
        """�������Ŷ�"""
        if not self.kb.knowledge_items:
            return 0.0
        
        return sum(item.confidence for item in self.kb.knowledge_items) / len(self.kb.knowledge_items)
    
    async def _save_knowledge_base(self):
        """����֪ʶ��"""
        output_path = self.output_dir / "guandan_knowledge_base.json"
        self.kb.export_knowledge(str(output_path))
        
        # ����ѧϰ����
        report_path = self.output_dir / "learning_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.learning_report, f, ensure_ascii=False, indent=2)

# ʹ��ʾ��
async def main():
    """������ʾ��"""
    pipeline = KnowledgeLearningPipeline()
    
    # ��ר���ĵ�ѧϰ
    report = await pipeline.learn_from_documents()
    
    print("֪ʶѧϰ��ɣ�")
    print(f"������֪ʶԴ: {len(report['sources_processed'])}")
    print(f"��ȡ��֪ʶ��: {report['knowledge_extracted']}")
    print(f"���ɵ�֪ʶ����: {report['rules_generated']}")
    print(f"��������: {report['validation_result']['quality_score']:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
```

## ? ʵս����ʾ��

### ���岽����������

**5. ֪ʶ��ǿ��AI�ͻ���**
```python
# src/main_enhanced.py
import asyncio
import logging
from pathlib import Path
from .communication.websocket_client import GuandanWebSocketClient
from .game_logic.game_state import GameState
from .ai.knowledge_driven_ai import KnowledgeDrivenAI
from .learning.knowledge_learning_pipeline import KnowledgeLearningPipeline

class EnhancedGuandanAI:
    """��ǿ���走AI������ר��֪ʶ��"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.game_state = GameState()
        self.knowledge_base = None
        self.knowledge_ai = None
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """��ʼ��AI������ר��֪ʶ��"""
        self.logger.info("��ʼ����ǿ���走AI...")
        
        # 1. ����ר��֪ʶ
        await self._load_expert_knowledge()
        
        # 2. ����֪ʶ������AI
        self.knowledge_ai = KnowledgeDrivenAI(self.game_state, self.knowledge_base)
        
        self.logger.info("��ǿ��AI��ʼ�����")
    
    async def _load_expert_knowledge(self):
        """����ר��֪ʶ"""
        knowledge_file = Path("data/knowledge/guandan_knowledge_base.json")
        
        if knowledge_file.exists():
            # ������ѱ����֪ʶ�⣬ֱ�Ӽ���
            self.knowledge_base = GuandanKnowledgeBase()
            self.knowledge_base.load_from_file(str(knowledge_file))
            self.logger.info("�Ѽ�������֪ʶ��")
        else:
            # ���û�У����ĵ�ѧϰ֪ʶ
            self.logger.info("��ʼ��ר���ĵ�ѧϰ֪ʶ...")
            pipeline = KnowledgeLearningPipeline()
            report = await pipeline.learn_from_documents()
            
            # �����µ�֪ʶ��
            self.knowledge_base = pipeline.kb
            self.logger.info(f"֪ʶѧϰ��ɣ�ѧϰ�� {len(self.knowledge_base.knowledge_items)} ��֪ʶ��")
    
    async def connect_and_play(self, url: str):
        """���ӵ�ƽ̨����ʼ��Ϸ"""
        client = GuandanWebSocketClient(self.user_id, self.game_state)
        
        # �滻ԭ���ľ����߼�Ϊ֪ʶ�����ľ���
        original_decide = client.rule_ai.decide_play
        client.rule_ai.decide_play = self.knowledge_ai.make_decision
        
        await client.connect(url)

# ʹ��ʾ��
async def run_enhanced_ai():
    """������ǿ��AI"""
    # ������־
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # ������ǿ��AI
    ai = EnhancedGuandanAI("EnhancedAI_001")
    await ai.initialize()
    
    # ���ӵ�ƽ̨��ʼ��Ϸ
    url = "ws://127.0.0.1:23456/game/EnhancedAI_001"
    await ai.connect_and_play(url)

if __name__ == "__main__":
    asyncio.run(run_enhanced_ai())
```

## ? ֪ʶͶιЧ������

### ��������Ч�����

**6. ֪ʶЧ��������**
```python
# src/evaluation/knowledge_effectiveness.py
from typing import Dict, List, Any
import json
from datetime import datetime, timedelta

class KnowledgeEffectivenessEvaluator:
    """֪ʶЧ��������"""
    
    def __init__(self):
        self.performance_history = []
        self.knowledge_usage_stats = {}
        
    def evaluate_knowledge_impact(self, before_stats: Dict, after_stats: Dict) -> Dict:
        """����֪ʶͶιǰ���Ч������"""
        impact_analysis = {
            "win_rate_improvement": after_stats["win_rate"] - before_stats["win_rate"],
            "decision_quality_improvement": after_stats["avg_decision_score"] - before_stats["avg_decision_score"],
            "strategic_thinking_improvement": after_stats["strategic_depth"] - before_stats["strategic_depth"],
            "knowledge_utilization_rate": self._calculate_knowledge_utilization(),
            "mistake_reduction": before_stats["mistake_rate"] - after_stats["mistake_rate"]
        }
        
        return impact_analysis
    
    def _calculate_knowledge_utilization(self) -> float:
        """����֪ʶ������"""
        # ����AI�������ж���ʹ����ר��֪ʶ
        total_decisions = sum(self.knowledge_usage_stats.get("total_decisions", 0))
        knowledge_based_decisions = sum(self.knowledge_usage_stats.get("knowledge_decisions", 0))
        
        return knowledge_based_decisions / total_decisions if total_decisions > 0 else 0.0
    
    def generate_effectiveness_report(self) -> str:
        """����Ч������"""
        report = f"""
# ר��֪ʶͶιЧ������

## ����Ч��
- ֪ʶ������: {len(self.knowledge_base.knowledge_items) if self.knowledge_base else 0}
- ֪ʶ������: {self._calculate_knowledge_utilization():.2%}
- ����ƥ����: {len(self.knowledge_base.strategy_rules) if self.knowledge_base else 0}

## ����Ľ�
- ʤ������: {self._get_recent_win_rate_change():.2%}
- ������������: {self._get_decision_quality_change():.2%}
- �������½�: {self._get_mistake_reduction():.2%}

## ֪ʶӦ�÷���
{self._analyze_knowledge_application()}

## �����Ż�����
{self._generate_optimization_suggestions()}
        """
        
        return report
    
    def _analyze_knowledge_application(self) -> str:
        """����֪ʶӦ�����"""
        analysis = []
        
        if self.knowledge_base:
            for rule in self.knowledge_base.strategy_rules:
                usage_count = self.knowledge_usage_stats.get(rule["id"], 0)
                analysis.append(f"- ���� '{rule['id']}' ʹ���� {usage_count} ��")
        
        return "\n".join(analysis) if analysis else "����֪ʶӦ������"
    
    def _generate_optimization_suggestions(self) -> List[str]:
        """�����Ż�����"""
        suggestions = []
        
        utilization_rate = self._calculate_knowledge_utilization()
        
        if utilization_rate < 0.3:
            suggestions.append("- ֪ʶ�����ʽϵͣ������Ż�֪ʶƥ���߼�")
        
        if utilization_rate > 0.8:
            suggestions.append("- ��������֪ʶ������ƽ��֪ʶ�;���")
        
        # ���ھ����������ɸ��ཨ��
        suggestions.extend([
            "- ���ڸ��º���չר��֪ʶ��",
            "- ����֪ʶ��֤�ͷ�������",
            "- �Ż�֪ʶȨ�غ����ȼ�����"
        ])
        
        return suggestions
```

## ? ������ʼ֪ʶͶι

### ���������ű�

```bash
# 1. ������ǿ����Ŀ
mkdir guandan_ai_knowledge
cd guandan_ai_knowledge

# 2. ��װ��������
pip install nltk spacy textstat  # ��Ȼ���Դ�����

# 3. ��ʼ��֪ʶѧϰ
python -c "
import asyncio
from src.learning.knowledge_learning_pipeline import KnowledgeLearningPipeline

async def init_knowledge():
    pipeline = KnowledgeLearningPipeline()
    report = await pipeline.learn_from_documents()
    print('֪ʶѧϰ���:', report)

asyncio.run(init_knowledge())
"

# 4. ������ǿ��AI
python src/main_enhanced.py

# 5. Ч������
python -c "
from src.evaluation.knowledge_effectiveness import KnowledgeEffectivenessEvaluator
evaluator = KnowledgeEffectivenessEvaluator()
report = evaluator.generate_effectiveness_report()
print(report)
"
```

## ? ��������

1. **֪ʶ����**��������ר�Ҿ���ת��ΪAI��ѧϰ����ʽ
2. **������**������Ҫ�����Ծ־��ܻ��ר�Ҽ�����
3. **����ѧϰ**�����Բ��������µ�ר��֪ʶ
4. **�ɽ�����**��AI���߿���׷�ݵ������ר��֪ʶ
5. **֪ʶ��֤**��������֤֪ʶ����Ч�Ժ�һ����

## ? �ܽ�

ͨ��ר��֪ʶͶι�������走AI���ܹ���
- **���ٻ��ר�Ҽ�����**��������Ҫ��ʱ��Ծ�ѵ��
- **��������ǻۺͻ���ѧϰ**��ʵ�ָ����ܵľ���
- **����ѧϰ�͸Ľ�**�����������µ�֪ʶ�;���
- **�ṩ�ɽ��͵ľ��߹���**����AI˼�����͸��

���ֻ��ѵ����ʽ��������AI��ѧϰ���̣������ڸ��̵�ʱ���ڴﵽ���ߵ�ˮƽ��

---

**����Ҫ��**��
1. ? **����Ͷιר��֪ʶ** - ��ֻ�ǶԾ�ѵ��
2. ? **������ʵ�ַ���** - ����ȡ������ȫ����
3. ? **����ѧϰЧ��** - ר��֪ʶ����AI�ɳ�
4. ? **�����Ż�����** - ֪ʶ��ɲ�������

������ʼ֪ʶͶι���������走AIվ�ھ��˵ļ���ϣ�

### 丁华秘籍（OCR）整合摘要

来源: `docs/skill/掼蛋技巧秘籍_OCR.txt`（OCR 提取）。已将该 OCR 文本的关键信息整理为结构化要点，集中摘要见 `docs/丁华掼蛋秘籍_整合.md`。

要点摘录：
- 规则类：明确出牌优先级、主牌与副牌的使用时机、炸弹与拆牌原则（何时保留炸弹，何时拆牌以保节奏）。
- 配合策略：强调队友间的让牌、配合节奏与信息利用（例如利用队友的出牌推断并配合“升级/封堵”）。
- 观察判断：通过记牌与出牌顺序估算对手手牌结构，并据此选择拆牌或保牌策略。
- 升级/防守：在关键回合保留阻止对方升级的关键牌或炸弹，并在适当时机触发升级或阻断策略。
- 时机把握：首轮进攻与留牌权衡、何时用炸弹、何时保存主牌做终结。

工程化建议：
- 把 OCR 文本作为 `KnowledgeLearningPipeline` 的输入，进行轻量清洗（常见 OCR 纠错、合并断行）。
- 用 `RealExpertKnowledgeExtractor` 抽取知识项，`ExpertKnowledgeFormatter` 格式化为 `GuandanKnowledgeItem` 后入库。高置信度（>=0.8）项可直接注入，低置信度项留待人工校验。


**已合并丁华秘籍（OCR）摘要**

- 来源: `docs/skill/掼蛋技巧秘籍_OCR.txt`（已载入）。
- 说明: 已将 OCR 文本中的高价值规则/策略/实战技巧提取为结构化知识建议，详见 `docs/丁华掼蛋秘籍_整合.md`。
- 建议: 对 `RealExpertKnowledgeExtractor` 运行该 OCR 文本，优先注入 `confidence >= 0.8` 的知识项，低置信度项标注为人工校验。

如需我现在批量抽取并生成 JSON 结果（并将结果写入 `data/knowledge/`），请回复“开始抽取”。
