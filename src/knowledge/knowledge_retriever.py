# -*- coding: utf-8 -*-
"""
增强的知识检索器 (Enhanced Knowledge Retriever)

实现更智能的知识检索功能：
1. 语义搜索（基于关键词匹配和相似度）
2. 上下文相关的知识检索（根据游戏状态）
3. 知识关联查询（相关技巧推荐）
"""

from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import re
import sys
from pathlib import Path

# 添加src到路径
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge.knowledge_loader import KnowledgeLoader


class KnowledgeRetriever:
    """增强的知识检索器"""
    
    def __init__(self, knowledge_loader: Optional[KnowledgeLoader] = None):
        """
        初始化知识检索器
        
        Args:
            knowledge_loader: KnowledgeLoader实例，如果为None则自动创建
        """
        if knowledge_loader is None:
            self.loader = KnowledgeLoader()
        else:
            self.loader = knowledge_loader
        
        # 构建知识关联图
        self.knowledge_graph = self._build_knowledge_graph()
        
        # 构建关键词索引（用于语义搜索）
        self.keyword_index = self._build_keyword_index()
    
    def _build_knowledge_graph(self) -> Dict[str, List[str]]:
        """
        构建知识关联图
        
        Returns:
            知识关联图 {knowledge_id: [related_ids]}
        """
        graph = defaultdict(list)
        
        # 基于tags建立关联
        tag_to_knowledge = defaultdict(list)
        for item in self.loader.all_knowledge:
            item_id = item.get('file', '')
            for tag in item.get('tags', []):
                tag_to_knowledge[tag].append(item_id)
        
        # 基于card_types建立关联
        type_to_knowledge = defaultdict(list)
        for item in self.loader.all_knowledge:
            item_id = item.get('file', '')
            for card_type in item.get('card_types', []):
                type_to_knowledge[card_type].append(item_id)
        
        # 构建关联关系
        for item in self.loader.all_knowledge:
            item_id = item.get('file', '')
            related = set()
            
            # 通过tags关联
            for tag in item.get('tags', []):
                related.update(tag_to_knowledge[tag])
            
            # 通过card_types关联
            for card_type in item.get('card_types', []):
                related.update(type_to_knowledge[card_type])
            
            # 移除自己
            related.discard(item_id)
            graph[item_id] = list(related)
        
        return dict(graph)
    
    def _build_keyword_index(self) -> Dict[str, List[str]]:
        """
        构建关键词索引
        
        Returns:
            关键词索引 {keyword: [knowledge_ids]}
        """
        index = defaultdict(list)
        
        # 定义关键词映射（中文到英文/概念）
        keyword_mappings = {
            # 角色相关
            '主攻': ['主攻', '进攻', '头游'],
            '助攻': ['助攻', '配合', '送牌', '传牌'],
            '队友': ['队友', '配合', '保护'],
            '对手': ['对手', '压制', '阻击'],
            
            # 牌型相关
            '单张': ['Single', '单牌', '单张'],
            '对子': ['Pair', '对子', '对牌'],
            '三带二': ['ThreeWithTwo', '三带二', '三带对'],
            '顺子': ['Straight', '顺子', '杂顺'],
            '炸弹': ['Bomb', '炸弹', '四头', '五头'],
            '同花顺': ['StraightFlush', '同花顺', '同花'],
            
            # 阶段相关
            '开局': ['opening', '开局', '开始'],
            '中局': ['midgame', '中局', '中期'],
            '残局': ['endgame', '残局', '后期'],
            
            # 策略相关
            '组牌': ['组牌', '组合', '牌型'],
            '传牌': ['传牌', '送牌', '配合'],
            '出炸': ['出炸', '炸弹', '用炸'],
            '保护': ['保护', '让牌', 'PASS'],
            '压制': ['压制', '阻击', '拦截']
        }
        
        # 为每个知识项建立索引
        for item in self.loader.all_knowledge:
            item_id = item.get('file', '')
            content = item.get('content', '').lower()
            title = item.get('title', '').lower()
            tags = [tag.lower() for tag in item.get('tags', [])]
            
            # 提取所有关键词
            all_text = ' '.join([title] + tags + [content[:200]])  # 只索引前200字符
            
            for keyword, variants in keyword_mappings.items():
                for variant in variants:
                    if variant.lower() in all_text:
                        index[keyword].append(item_id)
                        break
        
        return dict(index)
    
    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        语义搜索（基于关键词匹配和相似度）
        
        Args:
            query: 搜索查询
            top_k: 返回前k个结果
            
        Returns:
            匹配的知识项列表，按相关性排序
        """
        query_lower = query.lower()
        scores = defaultdict(float)
        
        # 1. 关键词匹配
        for keyword, knowledge_ids in self.keyword_index.items():
            if keyword in query_lower:
                for item_id in knowledge_ids:
                    scores[item_id] += 2.0  # 关键词匹配权重较高
        
        # 2. 标题匹配
        for item in self.loader.all_knowledge:
            item_id = item.get('file', '')
            title = item.get('title', '').lower()
            if query_lower in title:
                scores[item_id] += 3.0  # 标题匹配权重最高
        
        # 3. 标签匹配
        for item in self.loader.all_knowledge:
            item_id = item.get('file', '')
            tags = [tag.lower() for tag in item.get('tags', [])]
            for tag in tags:
                if query_lower in tag or tag in query_lower:
                    scores[item_id] += 1.5
        
        # 4. 内容匹配（部分匹配）
        for item in self.loader.all_knowledge:
            item_id = item.get('file', '')
            content = item.get('content', '').lower()
            # 计算匹配度（简单计数）
            matches = content.count(query_lower)
            if matches > 0:
                scores[item_id] += matches * 0.5
        
        # 5. 优先级加权
        for item in self.loader.all_knowledge:
            item_id = item.get('file', '')
            if item_id in scores:
                priority = item.get('priority', 1)
                scores[item_id] *= (1 + priority * 0.1)  # 优先级加权
        
        # 排序并返回
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for item_id, score in sorted_items[:top_k]:
            # 找到对应的知识项
            for item in self.loader.all_knowledge:
                if item.get('file') == item_id:
                    item_copy = item.copy()
                    item_copy['relevance_score'] = score
                    results.append(item_copy)
                    break
        
        return results
    
    def context_aware_retrieval(self, game_state: Dict) -> List[Dict]:
        """
        上下文相关的知识检索（根据游戏状态）
        
        Args:
            game_state: 游戏状态字典，包含：
                - phase: 游戏阶段 ('opening', 'midgame', 'endgame')
                - card_types: 当前关注的牌型列表
                - role: 当前角色 ('主攻', '助攻')
                - situation: 当前情况描述
                
        Returns:
            相关的知识项列表
        """
        results = []
        
        # 1. 根据游戏阶段检索
        phase = game_state.get('phase', 'midgame')
        phase_knowledge = self.loader.get_skills_by_phase(phase)
        results.extend(phase_knowledge)
        
        # 2. 根据牌型检索
        card_types = game_state.get('card_types', [])
        for card_type in card_types:
            type_knowledge = self.loader.get_skills_by_card_type(card_type)
            results.extend(type_knowledge)
        
        # 3. 根据角色检索
        role = game_state.get('role', '')
        if role:
            role_query = role if role in ['主攻', '助攻'] else ''
            if role_query:
                role_results = self.semantic_search(role_query, top_k=3)
                results.extend(role_results)
        
        # 4. 根据情况描述检索
        situation = game_state.get('situation', '')
        if situation:
            situation_results = self.semantic_search(situation, top_k=3)
            results.extend(situation_results)
        
        # 去重并排序
        seen = set()
        unique_results = []
        for item in results:
            item_id = item.get('file', '')
            if item_id not in seen:
                seen.add(item_id)
                unique_results.append(item)
        
        # 按优先级排序
        unique_results.sort(key=lambda x: x.get('priority', 1), reverse=True)
        
        return unique_results
    
    def get_related_knowledge(self, knowledge_id: str, top_k: int = 5) -> List[Dict]:
        """
        知识关联查询（相关技巧推荐）
        
        Args:
            knowledge_id: 知识项ID（文件路径）
            top_k: 返回前k个相关项
            
        Returns:
            相关的知识项列表
        """
        # 获取直接关联的知识
        related_ids = self.knowledge_graph.get(knowledge_id, [])
        
        # 获取关联的知识项
        related_items = []
        for item in self.loader.all_knowledge:
            if item.get('file') in related_ids:
                related_items.append(item)
        
        # 按优先级排序
        related_items.sort(key=lambda x: x.get('priority', 1), reverse=True)
        
        # 返回前k个
        return related_items[:top_k]
    
    def get_knowledge_by_context(self, context: Dict) -> List[Dict]:
        """
        综合上下文检索（结合多种条件）
        
        Args:
            context: 上下文字典，包含：
                - phase: 游戏阶段
                - card_types: 牌型列表
                - role: 角色
                - situation: 情况描述
                - query: 查询文本
                
        Returns:
            相关的知识项列表
        """
        all_results = []
        
        # 1. 上下文检索
        if any(key in context for key in ['phase', 'card_types', 'role', 'situation']):
            context_results = self.context_aware_retrieval(context)
            all_results.extend(context_results)
        
        # 2. 语义搜索
        if 'query' in context:
            search_results = self.semantic_search(context['query'], top_k=5)
            all_results.extend(search_results)
        
        # 去重并排序
        seen = set()
        unique_results = []
        for item in all_results:
            item_id = item.get('file', '')
            if item_id not in seen:
                seen.add(item_id)
                unique_results.append(item)
        
        # 按优先级和相关性排序
        unique_results.sort(
            key=lambda x: (
                x.get('relevance_score', 0),
                x.get('priority', 1)
            ),
            reverse=True
        )
        
        return unique_results
    
    def get_knowledge_summary(self) -> Dict:
        """获取检索器摘要"""
        return {
            "total_knowledge": len(self.loader.all_knowledge),
            "knowledge_graph_size": len(self.knowledge_graph),
            "keyword_index_size": len(self.keyword_index),
            "loader_summary": self.loader.get_knowledge_summary()
        }

