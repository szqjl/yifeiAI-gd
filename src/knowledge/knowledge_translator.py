# -*- coding: utf-8 -*-
"""
知识规则转化器 (Knowledge Translator)

将知识库中的文本规则转化为可执行的代码逻辑。
支持结构化规则（YAML/JSON格式）的解析和应用。
"""

from typing import Dict, List, Optional, Any, Callable
import re
from pathlib import Path

# 尝试导入yaml，如果失败则使用空实现
try:
    import yaml
except ImportError:
    yaml = None

# 优先级辅助函数（内联定义以避免循环依赖）
def get_priority_value(rule: dict) -> float:
    """安全地获取规则的优先级值"""
    priority = rule.get("priority", 0)
    if priority is None:
        return 0.0
    if isinstance(priority, (int, float)):
        return float(priority)
    if isinstance(priority, str):
        try:
            if priority.isdigit() or (priority.startswith('-') and priority[1:].isdigit()):
                return float(int(priority))
            return float(priority)
        except (ValueError, AttributeError):
            return 0.0
    return 0.0


class KnowledgeTranslator:
    """知识规则转化器 - 将文本规则转化为代码逻辑"""
    
    def __init__(self, knowledge_loader=None, rules_dir: str = "docs/knowledge"):
        """
        初始化规则转化器
        
        Args:
            knowledge_loader: KnowledgeLoader实例，用于加载知识库
            rules_dir: 规则文件目录，用于动态加载规则
        """
        self.knowledge_loader = knowledge_loader
        self.rules_dir = Path(rules_dir)
        self.rule_cache: Dict[str, List[Dict]] = {}
        self.core_rules = []
        
        # 先加载内置规则
        self._load_builtin_rules()
        
        # 尝试从Python模块加载规则（优先，无需yaml依赖）
        python_module_count = self._load_rules_from_python_module()
        
        # 如果Python模块加载失败，尝试从YAML文件加载（需要yaml模块）
        if python_module_count == 0:  # Python模块加载失败
            self._load_rules_from_files()
    
    def _load_builtin_rules(self):
        """加载内置规则（作为默认规则）"""
        # 定义核心规则（从硬编码策略迁移而来）
        builtin_rules = [
            {
                "id": "teammate_protection_1_2",
                "name": "队友保护-即将获胜",
                "description": "队友剩余1-2张牌，即将获胜",
                "condition": {
                    "type": "and",
                    "conditions": [
                        {"field": "greater_pos", "op": "==", "value": "teammate_pos"},
                        {"field": "teammate_cards", "op": "<=", "value": 2}
                    ]
                },
                "actions": [
                    {"action_type": "PASS", "score_adjust": 150},
                    {"action_type": "other", "score_adjust": -80}
                ],
                "priority": 10
            },
            {
                "id": "teammate_protection_3_5",
                "name": "队友保护-残局阶段",
                "description": "队友剩余3-5张牌，残局阶段",
                "condition": {
                    "type": "and",
                    "conditions": [
                        {"field": "greater_pos", "op": "==", "value": "teammate_pos"},
                        {"field": "teammate_cards", "op": "<=", "value": 5},
                        {"field": "teammate_cards", "op": ">=", "value": 3}
                    ]
                },
                "actions": [
                    {"action_type": "PASS", "score_adjust": 100},
                    {"action_type": "other", "score_adjust": -50}
                ],
                "priority": 8
            },
            {
                "id": "opponent_suppress_1_3",
                "name": "对手压制-即将获胜",
                "description": "对手剩余1-3张牌，必须压制",
                "condition": {
                    "type": "and",
                    "conditions": [
                        {"field": "min_opponent_cards", "op": "<=", "value": 3}
                    ]
                },
                "actions": [
                    {"action_type": "PASS", "score_adjust": -100},
                    {"action_type": "other", "score_adjust": 150}
                ],
                "priority": 10
            },
            {
                "id": "fire_not_four",
                "name": "火不打四",
                "description": "对手4张时可能是炸弹，不要轻易用炸弹",
                "condition": {
                    "type": "and",
                    "conditions": [
                        {"field": "min_opponent_cards", "op": "==", "value": 4}
                    ]
                },
                "actions": [
                    {"action_type": "Bomb", "score_adjust": -30}
                ],
                "priority": 7
            },
            {
                "id": "five_pair",
                "name": "逢五出对",
                "description": "对手5张时优先出对子",
                "condition": {
                    "type": "and",
                    "conditions": [
                        {"field": "min_opponent_cards", "op": "==", "value": 5}
                    ]
                },
                "actions": [
                    {"action_type": "Pair", "score_adjust": 100},
                    {"action_type": "other", "score_adjust": 60}
                ],
                "priority": 8
            }
        ]
        self.core_rules.extend(builtin_rules)
    
    def _load_rules_from_python_module(self):
        """从Python模块加载规则（无需yaml依赖）"""
        try:
            # 尝试导入转换后的规则模块
            from knowledge.knowledge_rules import KNOWLEDGE_RULES
            
            if KNOWLEDGE_RULES:
                loaded_count = 0
                for rule in KNOWLEDGE_RULES:
                    if self._validate_rule(rule):
                        self.core_rules.append(rule)
                        loaded_count += 1
                
                if loaded_count > 0:
                    print(f"✅ 从Python模块加载了 {loaded_count} 条规则（无需yaml依赖）")
                return loaded_count
        except ImportError:
            # 如果模块不存在，静默失败（将尝试从YAML加载）
            pass
        except Exception as e:
            # 其他错误也静默处理
            pass
        
        return 0
    
    def _load_rules_from_files(self):
        """从知识库文件动态加载规则"""
        if not self.rules_dir.exists():
            return
        
        # 检查yaml模块是否可用
        if yaml is None:
            print("⚠️  Warning: yaml module not available.")
            print("   - 无法加载YAML规则文件（29条动态规则）")
            print("   - 仅使用5条内置规则")
            print("   - 建议运行: pip install pyyaml")
            return
        
        # 查找所有YAML规则文件
        yaml_files = list(self.rules_dir.glob("**/*.yaml")) + list(self.rules_dir.glob("**/*.yml"))
        
        loaded_count = 0
        for yaml_file in yaml_files:
            try:
                    
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    
                if data and 'rules' in data:
                    rules = data['rules']
                    for rule in rules:
                        # 验证规则格式
                        if self._validate_rule(rule):
                            self.core_rules.append(rule)
                            loaded_count += 1
            except Exception as e:
                # 静默处理错误，避免影响其他规则加载
                pass
        
        if loaded_count > 0:
            print(f"✅ 已加载 {loaded_count} 条动态规则")
        
        # 按优先级排序（使用辅助函数确保priority是数字）
        self.core_rules.sort(key=get_priority_value, reverse=True)
    
    def _validate_rule(self, rule: Dict) -> bool:
        """
        验证规则格式
        
        Args:
            rule: 规则字典
            
        Returns:
            是否有效
        """
        required_fields = ['id', 'condition', 'actions']
        return all(field in rule for field in required_fields)
    
    def evaluate_condition(self, condition: Dict, context: Dict) -> bool:
        """
        评估条件表达式（支持嵌套条件和函数调用）
        
        Args:
            condition: 条件字典
            context: 上下文信息（游戏状态）
            
        Returns:
            条件是否满足
        """
        # 支持嵌套的and/or逻辑
        if condition.get("type") == "and":
            return all(self.evaluate_condition(c, context) for c in condition.get("conditions", []))
        elif condition.get("type") == "or":
            return any(self.evaluate_condition(c, context) for c in condition.get("conditions", []))
        elif condition.get("type") == "not":
            # 支持not逻辑
            sub_condition = condition.get("condition")
            if sub_condition:
                return not self.evaluate_condition(sub_condition, context)
            return False
        elif condition.get("type") == "function":
            # 支持函数调用
            return self._evaluate_function(condition, context)
        else:
            # 简单条件
            field = condition.get("field")
            op = condition.get("op")
            value = condition.get("value")
            
            # 支持函数调用获取字段值
            if isinstance(field, dict) and field.get("type") == "function":
                field_value = self._evaluate_function(field, context)
            elif field and field in context:
                field_value = context[field]
            else:
                return False
            
            # 支持函数调用获取比较值
            if isinstance(value, dict) and value.get("type") == "function":
                value = self._evaluate_function(value, context)
            elif isinstance(value, str) and value.endswith("_pos"):
                value = context.get(value, -1)
            
            # 执行操作（确保比较的值是可比较的类型）
            # 处理None值
            if field_value is None or value is None:
                # None值只支持 == 和 != 操作
                if op == "==":
                    return field_value == value
                elif op == "!=":
                    return field_value != value
                else:
                    return False
            
            # 如果field_value或value是字典/列表等不可比较类型，返回False
            if isinstance(field_value, (dict, list)) or isinstance(value, (dict, list)):
                # 对于字典和列表，只支持 == 和 != 操作
                if op == "==":
                    return field_value == value
                elif op == "!=":
                    return field_value != value
                else:
                    return False
            
            # 数值比较操作（确保都是可比较的类型）
            if op == "in":
                # 支持in操作符
                if isinstance(value, list):
                    return field_value in value
                return False
            elif op == "not_in":
                # 支持not_in操作符
                if isinstance(value, list):
                    return field_value not in value
                return False
            else:
                # 数值比较操作
                try:
                    if op == "==":
                        return field_value == value
                    elif op == "!=":
                        return field_value != value
                    elif op == "<":
                        return field_value < value
                    elif op == "<=":
                        return field_value <= value
                    elif op == ">":
                        return field_value > value
                    elif op == ">=":
                        return field_value >= value
                    else:
                        return False
                except TypeError:
                    # 如果类型不匹配导致无法比较，返回False
                    return False
    
    def _evaluate_function(self, func_condition: Dict, context: Dict) -> Any:
        """
        评估函数调用
        
        Args:
            func_condition: 函数条件字典
            context: 上下文信息
            
        Returns:
            函数返回值
        """
        func_name = func_condition.get("name")
        args = func_condition.get("args", [])
        
        # 解析参数（支持嵌套函数调用和字段引用）
        parsed_args = []
        for arg in args:
            if isinstance(arg, dict):
                if arg.get("type") == "function":
                    parsed_args.append(self._evaluate_function(arg, context))
                elif arg.get("type") == "field":
                    parsed_args.append(context.get(arg.get("field"), None))
                else:
                    parsed_args.append(arg)
            else:
                parsed_args.append(arg)
        
        # 内置函数
        if func_name == "min":
            # 过滤掉不可比较的值（字典、列表等）
            comparable_args = [arg for arg in parsed_args if isinstance(arg, (int, float))]
            return min(comparable_args) if comparable_args else None
        elif func_name == "max":
            # 过滤掉不可比较的值（字典、列表等）
            comparable_args = [arg for arg in parsed_args if isinstance(arg, (int, float))]
            return max(comparable_args) if comparable_args else None
        elif func_name == "abs":
            return abs(parsed_args[0]) if parsed_args else None
        elif func_name == "sum":
            return sum(parsed_args) if parsed_args else 0
        elif func_name == "count":
            # 统计满足条件的数量
            if len(parsed_args) >= 2:
                items = parsed_args[0]
                condition_func = parsed_args[1]
                if isinstance(items, list) and callable(condition_func):
                    return sum(1 for item in items if condition_func(item))
            return 0
        elif func_name == "has_bomb":
            # 检查是否有炸弹（简化实现）
            cards_left = context.get("cards_left", {})
            # 假设剩余4张可能是炸弹
            return any(count == 4 for count in cards_left.values())
        elif func_name == "is_endgame":
            # 判断是否残局
            min_cards = min(context.get("teammate_cards", 27), 
                          context.get("min_opponent_cards", 27))
            return min_cards <= 5
        else:
            return None
    
    def apply_rule(self, rule: Dict, action_type: str, context: Dict) -> float:
        """
        应用单个规则（根据priority动态调整加分幅度）
        
        Args:
            rule: 规则字典
            action_type: 动作类型
            context: 上下文信息
            
        Returns:
            分数调整值（已根据priority加权）
        """
        # 检查条件是否满足
        if not self.evaluate_condition(rule.get("condition", {}), context):
            return 0.0
        
        # 获取规则优先级
        priority = rule.get("priority", 1)
        
        # 应用动作调整
        base_adjust = 0.0
        for action in rule.get("actions", []):
            rule_action_type = action.get("action_type")
            if rule_action_type == action_type:
                base_adjust += action.get("score_adjust", 0)
            elif rule_action_type == "other" and action_type != "PASS":
                base_adjust += action.get("score_adjust", 0)
        
        # 根据priority动态调整加分幅度
        # priority范围通常是1-10，我们将其映射到0.5-2.0的倍数
        # priority=1: 0.5倍, priority=5: 1.0倍, priority=10: 2.0倍
        priority_multiplier = 0.5 + (priority / 10.0) * 1.5
        
        # 应用优先级加权
        adjusted_score = base_adjust * priority_multiplier
        
        return adjusted_score
    
    def translate_rules(self, game_state: Dict) -> List[Dict]:
        """
        根据游戏状态转化相关规则
        
        Args:
            game_state: 游戏状态字典
            
        Returns:
            适用的规则列表
        """
        applicable_rules = []
        
        # 构建上下文
        context = self._build_context(game_state)
        
        # 检查所有规则
        for rule in self.core_rules:
            if self.evaluate_condition(rule.get("condition", {}), context):
                applicable_rules.append(rule)
        
        # 按优先级排序（使用辅助函数确保priority是数字）
        applicable_rules.sort(key=get_priority_value, reverse=True)
        
        return applicable_rules
    
    def _build_context(self, game_state: Dict) -> Dict:
        """
        构建规则评估上下文
        
        Args:
            game_state: 游戏状态
            
        Returns:
            上下文字典
        """
        public_info = game_state.get("publicInfo", [])
        my_pos = game_state.get("myPos", 0)
        greater_pos = game_state.get("greaterPos", -1)
        cur_pos = game_state.get("curPos", -1)
        
        # 计算位置关系
        teammate_pos = (my_pos + 2) % 4
        next_pos = (my_pos + 1) % 4
        prev_pos = (my_pos - 1) % 4
        
        # 获取剩余牌数
        cards_left = {}
        for i, info in enumerate(public_info):
            if isinstance(info, dict):
                cards_left[i] = info.get('rest', 27)
            else:
                cards_left[i] = 27
        
        teammate_cards = cards_left.get(teammate_pos, 27)
        opponent_cards = [
            cards_left.get(next_pos, 27),
            cards_left.get(prev_pos, 27)
        ]
        min_opponent_cards = min(opponent_cards) if opponent_cards else 27
        max_opponent_cards = max(opponent_cards) if opponent_cards else 27
        
        context = {
            "my_pos": my_pos,
            "teammate_pos": teammate_pos,
            "next_pos": next_pos,
            "prev_pos": prev_pos,
            "greater_pos": greater_pos,
            "cur_pos": cur_pos,
            "teammate_cards": teammate_cards,
            "min_opponent_cards": min_opponent_cards,
            "max_opponent_cards": max_opponent_cards,
            "cards_left": cards_left
        }
        
        return context
    
    def enhance_score(self, action_type: str, base_score: float, 
                     game_state: Dict) -> float:
        """
        根据规则增强动作分数（根据priority动态调整）
        
        Args:
            action_type: 动作类型
            base_score: 基础分数
            game_state: 游戏状态
            
        Returns:
            增强后的分数
        """
        # 获取适用的规则（已按priority排序）
        applicable_rules = self.translate_rules(game_state)
        
        # 构建上下文
        context = self._build_context(game_state)
        
        # 应用所有适用规则（已根据priority加权）
        total_adjust = 0.0
        for rule in applicable_rules:
            adjust = self.apply_rule(rule, action_type, context)
            total_adjust += adjust
        
        return base_score + total_adjust
    
    def load_rules_from_knowledge(self, knowledge_items: List[Dict]) -> List[Dict]:
        """
        从知识库项中加载规则
        
        Args:
            knowledge_items: 知识库项列表
            
        Returns:
            规则列表
        """
        rules = []
        
        for item in knowledge_items:
            # 尝试从元数据中提取规则
            if "rules" in item:
                rules.extend(item["rules"])
        
        return rules
    
    def add_rule(self, rule: Dict):
        """
        添加新规则
        
        Args:
            rule: 规则字典
        """
        self.core_rules.append(rule)
        # 按优先级排序（使用辅助函数确保priority是数字）
        self.core_rules.sort(key=get_priority_value, reverse=True)
    
    def get_rule_summary(self) -> Dict:
        """获取规则摘要"""
        return {
            "total_rules": len(self.core_rules),
            "rules_by_priority": {
                "high": len([r for r in self.core_rules if r.get("priority", 0) >= 8]),
                "medium": len([r for r in self.core_rules if 5 <= r.get("priority", 0) < 8]),
                "low": len([r for r in self.core_rules if r.get("priority", 0) < 5])
            }
        }

