import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional

class KnowledgeLoader:
    def __init__(self, knowledge_dir: str = "docs/knowledge"):
        """
        鍒濆嬪寲鐭ヨ瘑搴撳姞杞藉櫒
        
        Args:
            knowledge_dir: 鐭ヨ瘑搴撶洰褰曡矾寰勶紝榛樿や负 "docs/knowledge"
        """
        self.knowledge_dir = Path(knowledge_dir)
        self.skills_by_type: Dict[str, List[Dict]] = {}
        self.skills_by_phase: Dict[str, List[Dict]] = {}
        self.all_knowledge: List[Dict] = []
        self._load_knowledge()
    
    def _load_knowledge(self):
        """鍔犺浇鎵鏈夌煡璇嗗簱鏂囦欢"""
        if not self.knowledge_dir.exists():
            print(f"Warning: Knowledge directory {self.knowledge_dir} does not exist.")
            return
        
        # 閬嶅巻 rules 鍜 skills 鐩褰
        for subdir in self.knowledge_dir.glob("*"):
            if subdir.is_dir():
                self._load_directory(subdir)
        
        print(f"Loaded {len(self.all_knowledge)} knowledge items.")
    
    def _load_directory(self, directory: Path):
        """鍔犺浇鐩褰曚笅鐨勬墍鏈 md 鏂囦欢"""
        for md_file in directory.rglob("*.md"):
            knowledge_item = self._parse_md_file(md_file)
            if knowledge_item:
                self.all_knowledge.append(knowledge_item)
                self._categorize_knowledge(knowledge_item)
    
    def _parse_md_file(self, file_path: Path) -> Optional[Dict]:
        """瑙ｆ瀽鍗曚釜 md 鏂囦欢"""
        try:
            # 灏濊瘯UTF-8缂栫爜
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # 濡傛灉UTF-8澶辫触锛屽皾璇旼BK
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # 濡傛灉閮藉け璐ワ紝浣跨敤errors='ignore'
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
            
            # 绠鍗 frontmatter 瑙ｆ瀽锛堝亣璁 --- ... --- 鏍煎紡锛
            frontmatter = {}
            if content.startswith('---'):
                end_idx = content.find('---', 3)
                if end_idx > 3:
                    yaml_str = content[3:end_idx].strip()
                    try:
                        frontmatter = yaml.safe_load(yaml_str) or {}
                    except Exception:
                        # YAML瑙ｆ瀽澶辫触锛岃烦杩噁rontmatter锛屼娇鐢ㄩ粯璁ゅ
                        frontmatter = {}
                    content = content[end_idx + 3:].strip()
            
            # 鎻愬彇鐗屽瀷锛堢畝鍗曞叧閿璇嶅尮閰嶏級
            card_types = self._extract_card_types(content)
            
            item = {
                'file': str(file_path.relative_to(self.knowledge_dir)),
                'title': frontmatter.get('title', file_path.stem),
                'type': frontmatter.get('type', 'rule'),
                'category': frontmatter.get('category', str(file_path.parent.name)),
                'tags': frontmatter.get('tags', []),
                'priority': frontmatter.get('priority', 1),
                'phase': frontmatter.get('game_phase', 'general'),
                'card_types': card_types,
                'content': content[:500] + '...' if len(content) > 500 else content  # 鎽樿
            }
            return item
        except Exception as e:
            # 闈欓粯澶勭悊閿欒锛屼笉鎵撳嵃锛堥伩鍏嶈緭鍑鸿繃澶氶敊璇淇℃伅锛
            # 濡傛灉闇瑕佽皟璇曪紝鍙浠ュ彇娑堜笅闈㈢殑娉ㄩ噴
            # print(f"Error parsing {file_path}: {e}")
            return None
    
    def _extract_card_types(self, content: str) -> List[str]:
        """浠庡唴瀹逛腑鎻愬彇鐗屽瀷鍏抽敭璇"""
        card_type_keywords = {
            'Single': ['鍗曞紶', '鍗曠墝'],
            'Pair': ['瀵瑰瓙'],
            'Trips': ['涓夊紶', '涓変笉甯'],
            'ThreeWithTwo': ['涓夊甫浜', '涓夊甫涓瀵'],
            'ThreePair': ['涓夎繛瀵'],
            'TwoTrips': ['閽㈡澘', '涓や笁寮'],
            'Straight': ['椤哄瓙'],
            'StraightFlush': ['鍚岃姳椤'],
            'Bomb': ['鐐稿脊', '鍥涘紶']
        }
        
        found_types = []
        content_lower = content.lower()
        for card_type, keywords in card_type_keywords.items():
            for kw in keywords:
                if kw.lower() in content_lower:
                    found_types.append(card_type)
                    break
        return found_types
    
    def _categorize_knowledge(self, item: Dict):
        """鍒嗙被鐭ヨ瘑椤"""
        # 鎸夌墝鍨嬪垎绫
        for card_type in item['card_types']:
            if card_type not in self.skills_by_type:
                self.skills_by_type[card_type] = []
            self.skills_by_type[card_type].append(item)
        
        # 鎸夐樁娈靛垎绫
        phase = item['phase']
        if phase not in self.skills_by_phase:
            self.skills_by_phase[phase] = []
        self.skills_by_phase[phase].append(item)
    
    def get_skills_by_card_type(self, card_type: str) -> List[Dict]:
        """
        鏍规嵁鐗屽瀷鑾峰彇鐩稿叧鎶鑳
        
        Args:
            card_type: 鐗屽瀷锛屽 'Pair', 'Single'
        
        Returns:
            鐩稿叧鎶鑳藉垪琛锛屾寜浼樺厛绾ф帓搴
        """
        skills = self.skills_by_type.get(card_type, [])
        # 鎸変紭鍏堢骇闄嶅簭鎺掑簭
        skills.sort(key=lambda x: x['priority'], reverse=True)
        return skills
    
    def get_skills_by_phase(self, phase: str) -> List[Dict]:
        """
        鏍规嵁娓告垙闃舵佃幏鍙栨妧鑳
        
        Args:
            phase: 闃舵碉紝濡 'midgame', 'opening'
        
        Returns:
            鐩稿叧鎶鑳藉垪琛
        """
        return self.skills_by_phase.get(phase, [])
    
    def search_knowledge(self, query: str) -> List[Dict]:
        """
        鎼滅储鐭ヨ瘑搴
        
        Args:
            query: 鎼滅储鍏抽敭璇
        
        Returns:
            鍖归厤鐨勭煡璇嗛」鍒楄〃
        """
        results = []
        query_lower = query.lower()
        for item in self.all_knowledge:
            if (query_lower in item['title'].lower() or 
                any(query_lower in tag.lower() for tag in item['tags']) or
                query_lower in item['content'].lower()):
                results.append(item)
        return results
    
    def get_knowledge_summary(self) -> Dict:
        """鑾峰彇鐭ヨ瘑搴撴憳瑕佺粺璁"""
        summary = {
            'total_items': len(self.all_knowledge),
            'by_type': {k: len(v) for k, v in self.skills_by_type.items()},
            'by_phase': {k: len(v) for k, v in self.skills_by_phase.items()}
        }
        return summary
