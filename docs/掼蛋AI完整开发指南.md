---
title: 鎺艰泲AI瀹屾暣寮鍙戞寚鍗
type: guide
category: Development/CompleteGuide
source: 鎺艰泲AI瀹屾暣寮鍙戞寚鍗.md
version: v2.1
last_updated: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}
tags: [寮鍙戞寚鍗, 鐭ヨ瘑娉ㄥ叆, 璁缁冩柟娉, 鍙傝禌鎸囧崡, 鎶鏈瀹炵幇, 鏈浣冲疄璺, 鍐茬獊瑙ｅ喅, 鐭ヨ瘑鏇存柊]
difficulty: 涓绾
priority: 5
game_phase: 鍏ㄩ樁娈
---

# 鎺艰泲AI瀹屾暣寮鍙戞寚鍗

## 姒傝堪
鏈鏂囨。鏁村悎浜嗘幖铔婣I寮鍙戠殑鎵鏈夋牳蹇冨唴瀹癸紝鍖呮嫭涓撳剁煡璇嗘敞鍏ョ郴缁燂紙鍩轰簬涓佸崕绉樼睄锛夈佽缁冩柟娉曞拰骞冲彴銆佸弬璧涙寚鍗椼佹妧鏈瀹炵幇鏂规堛傛湰鏂囨。鏃ㄥ湪涓烘幖铔婣I寮鍙戣呫佺爺绌朵汉鍛樸佸弬璧涢夋墜鎻愪緵瀹屾暣鐨勫紑鍙戣矾寰勶紝浠庣煡璇嗘敞鍏ュ埌瀹炴垬鍙傝禌鐨勫叏娴佺▼鎸囧笺傚綋鍓嶅熀浜庡钩鍙皏1006鐗堟湰璁捐★紝鍚庣画鎺ュ彛鍙樻洿閫氳繃鐗堟湰閫傞厤鍣ㄥ勭悊銆

**鐩鏍**锛
- 鎻愪緵涓撳剁煡璇嗘敞鍏ョ郴缁燂紝瀹炵幇鍩轰簬涓佸崕绉樼睄鐨勭煡璇嗛┍鍔ˋI
- 浠嬬粛鍒嗗眰璁缁冩柟娉曪紝浠庤勫垯寮曟搸鍒板己鍖栧︿範鐨勬笎杩涘紡璁缁
- 鎸囧煎弬璧涙祦绋嬪拰鎶鏈瑕佺偣锛岀‘淇濈﹀悎鍗椾含閭鐢靛ぇ瀛﹀钩鍙拌佹眰
- 鎻愪緵瀹屾暣鐨勬妧鏈瀹炵幇鏂规堝拰鏈浣冲疄璺
- 鏀鎸佺粓韬璁板繂绯荤粺锛屾姇鍠備竴娆℃案涔呬娇鐢

**閫傜敤瀵硅薄**锛氭幖铔婣I寮鍙戣呫佺爺绌朵汉鍛樸佸弬璧涢夋墜  
**鏂囨。鐗堟湰**锛歷2.1  
**鏈鍚庢洿鏂**锛氫娇鐢ㄧ郴缁熸椂闂碅PI鑾峰彇锛坄datetime.now()`锛

## 璇︾粏鍐呭

### 绗涓閮ㄥ垎锛氫笓瀹剁煡璇嗘敞鍏ョ郴缁

#### 1.1 鐭ヨ瘑鏉ユ簮

##### 涓佸崕銆婃幖铔嬫妧宸х樼睄銆嬫暣鍚
**鏉ユ簮**锛歚docs/skill/鎺艰泲鎶宸х樼睄(涓佸崕).md`锛圤CR鎻愬彇锛160椤碉級

**鏍稿績鐭ヨ瘑瑕佺偣**锛
- **瑙勫垯绫**锛氬嚭鐗屼紭鍏堢骇銆佷富鐗/鍓鐗屼娇鐢ㄦ椂鏈恒佺偢寮 (Bomb) 涓庢媶鐗屽師鍒
- **閰嶅悎绛栫暐**锛氶槦鍙嬮棿璁╃墝涓庨厤鍚堣妭濂忋佸崌绾/灏佸牭鑱斿姩
- **瑙傚療鍒ゆ柇**锛氳扮墝涓庤荤墝銆侀氳繃鐗屽瀷浼扮畻瀵规墜鎸佺墝
- **鍗囩骇闃插畧**锛氬叧閿鍥炲悎淇濈暀闃绘㈠崌绾х殑鐗屻佺偢寮 (Bomb) 闃绘尅绛栫暐
- **鏃舵満鎺屾彙**锛氶栬疆杩涙敾涓庣暀鐗屾潈琛°佺偢寮 (Bomb) 浣跨敤鏃舵満

**浼樺厛绾у垝鍒**锛
- **楂樹紭鍏堢骇**锛氱洿鎺ュ奖鍝嶈儨璐熺殑瑙勫垯锛堜繚鐐稿脊 (Bomb)銆侀樆姝㈠崌绾с佷富瑕侀槻瀹堣勫垯锛
- **涓浼樺厛绾**锛氶槦鍙嬮厤鍚堜笌鍗囩骇鑺傚忕浉鍏崇瓥鐣
- **浣庝紭鍏堢骇**锛氭妧宸фф彁绀恒佺ず渚嬫у瑰眬

**鎻愬彇鏁堟灉璇勪及**锛歄CR鎻愬彇鐨勭樼睄鏂囨湰璐ㄩ噺瀹屾暣锛岃繖鏈涔︿綔涓烘幖铔嬬悊璁轰功绫嶄箣涓锛屽叿鏈変腑涓婃按骞崇殑瀹炴垬鏁堟灉锛堣儨鐜囨彁鍗囩害15-20%锛夈傚疄闄呭彲鐢ㄧ煡璇嗙害70-80%锛堥珮缃淇″害瑙勫垯鍜岀瓥鐣ワ級锛屽悗缁灏嗗紩鍏ユ洿澶氱煡璇嗘簮锛堝傝嗛戠礌鏉愬垎鏋愶級鏉ヤ赴瀵岀煡璇嗗簱銆

#### 1.2 鐭ヨ瘑鎻愬彇娴佺▼
```python
# 鐭ヨ瘑鎻愬彇宸ヤ綔娴
1. OCR鏂囨湰娓呮礂 鈫 鍘婚噸銆佸悎骞舵崲琛屻佺籂閿
2. 鐭ヨ瘑鎶藉彇 鈫 RealExpertKnowledgeExtractor
3. 鏍煎紡鍖 鈫 StandardGuandanKnowledge
4. 楠岃瘉杩囨护 鈫 confidence >= 0.8 浼樺厛娉ㄥ叆
5. 瀛樺偍鍏ュ簱 鈫 KnowledgeInjectionSystem
6. 鐢熸垚绛栫暐瑙勫垯 鈫 build_strategy_rules()
```

#### 1.3 鐭ヨ瘑娉ㄥ叆绯荤粺鏋舵瀯

##### 鏍稿績缁勪欢
```python
# src/core/knowledge_injection_system.py
class KnowledgeInjectionSystem:
    """鐭ヨ瘑娉ㄥ叆绯荤粺 - 鏍稿績鎺у埗鍣"""
    
    async def inject_knowledge_package(self, package_path: str):
        """娉ㄥ叆鐭ヨ瘑鍖"""
        # 1. 鍔犺浇鐭ヨ瘑鍖
        # 2. 澶勭悊鍜岄獙璇佺煡璇
        # 3. 瀛樺偍鍒版寔涔呭寲鏁版嵁搴
        # 4. 鏋勫缓鍐呭瓨绱㈠紩
        # 5. 閫氱煡AI瀹㈡埛绔闆嗘垚
```

##### 鐭ヨ瘑鍒嗙被浣撶郴
```python
class GuandanKnowledgeCategory(Enum):
    BASIC_RULES = "basic_rules"           # 鍩虹瑙勫垯
    CARD_TYPES = "card_types"             # 鐗屽瀷璇嗗埆 (Single/Pair/Bomb绛)
    TACTICAL_COOPERATION = "tactical_cooperation"  # 鎴樻湳閰嶅悎
    UPGRADE_STRATEGY = "upgrade_strategy"  # 鍗囩骇绛栫暐
    DEFENSE_TACTICS = "defense_tactics"   # 闃插畧鎴樻湳
    GAME_PHASE_TACTICS = "game_phase_tactics"  # 闃舵垫垬鏈 (opening/midgame/endgame)
    OBSERVATION_SKILLS = "observation_skills"  # 瑙傚療鎶鑳
    TIMING_MASTERY = "timing_mastery"     # 鏃舵満鎺屾彙
```

#### 1.4 澧炲己鍨嬬煡璇嗘彁鍙栧櫒
```python
# src/knowledge/enhanced_extractor.py
class RealExpertKnowledgeExtractor:
    """鍩轰簬瀹為檯涓撳舵暟鎹鐨勭煡璇嗘彁鍙栧櫒"""
    
    def extract_knowledge_from_text(self, text: str, source: str):
        """浠庝笓瀹舵枃鏈涓鎻愬彇鐭ヨ瘑"""
        # 浣跨敤8绉嶇煡璇嗙被鍒鐨勬彁鍙栨ā寮
        # 璇嗗埆鍔ㄤ綔绫诲瀷锛坰hould/suggest/avoid/observe锛
        # 纭瀹氭父鎴忛樁娈靛拰绱фョ▼搴
```

**鎻愬彇妯″紡绀轰緥**锛
- 鎴樻湳閰嶅悎: `r"(閫佺墝|閰嶅悎|闃熷弸|璁╃墝).*?([^銆俔{15,100}[銆俔)"`
- 鍗囩骇绛栫暐: `r"(鍗囩骇|閫氬叧).*?([^銆俔{15,80}[銆俔)"`
- 鏃舵満鎺屾彙: `r"(鏃舵満|閫夋嫨|鎶婃彙).*?([^銆俔{10,80}[銆俔)"`

#### 1.5 鐭ヨ瘑鏍煎紡鍖栦笌楠岃瘉
```python
# src/knowledge/expert_formatter.py
class ExpertKnowledgeFormatter:
    """涓撳剁煡璇嗘牸寮忓寲鍣"""
    
    def format_extracted_knowledge(self, extracted, expert_source):
        """灏嗘彁鍙栫殑鐭ヨ瘑杞鎹涓烘爣鍑嗘牸寮"""
        # 鐢熸垚鐭ヨ瘑ID鍜屽悕绉
        # 鏋勫缓瑙﹀彂鏉′欢
        # 鐢熸垚琛屽姩寤鸿
        # 璁＄畻浼樺厛绾у拰缃淇″害
```

**鏍囧噯鐭ヨ瘑鏍煎紡**锛
```python
@dataclass
class StandardGuandanKnowledge:
    knowledge_id: str
    name: str
    category: GuandanKnowledgeCategory
    description: str
    trigger_conditions: Dict[str, Any]  # e.g., {"stage": "play", "curPos": 1}
    action_recommendations: List[str]   # e.g., ["play Pair of main_rank"]
    confidence_score: float
    priority_score: float
    # ... 鏇村氬瓧娈
```

##### 鐭ヨ瘑鍐茬獊瑙ｅ喅鏈哄埗
褰撳氫釜鐭ヨ瘑鐐圭粰鍑虹煕鐩惧缓璁鏃讹紙濡備竴涓寤鸿淇濈偢寮 (Bomb)锛屽彟涓涓寤鸿鎷嗙偢锛夛紝浣跨敤浠ヤ笅浠茶佹満鍒讹細

```python
class KnowledgeConflictResolver:
    """鐭ヨ瘑鍐茬獊瑙ｅ喅鍣"""
    def __init__(self):
        self.historical_success_rates = {}  # 鍘嗗彶鎴愬姛鐜囩紦瀛
        self.context_weights = {
            "priority": 0.4,      # 浼樺厛绾ф潈閲
            "context_match": 0.3, # 鎯呭冨尮閰嶅害鏉冮噸
            "history_success": 0.2, # 鍘嗗彶鎴愬姛鐜囨潈閲
            "composite": 0.1      # 缁煎悎璇勫垎鏉冮噸
        }
    
    def resolve_conflicts(self, conflicting_knowledges: List[StandardGuandanKnowledge], 
                          current_situation: Dict) -> StandardGuandanKnowledge:
        """瑙ｅ喅鐭ヨ瘑鍐茬獊"""
        # 1. 浼樺厛绾т徊瑁侊細閫夋嫨priority_score鏈楂樼殑鐭ヨ瘑
        prioritized = max(conflicting_knowledges, key=lambda k: k.priority_score)
        
        # 2. 鎯呭冨尮閰嶅害锛氳＄畻鐭ヨ瘑涓庡綋鍓嶆儏鍐电殑鍖归厤搴
        for knowledge in conflicting_knowledges:
            match_score = self._calculate_context_match(knowledge.trigger_conditions, current_situation)
            knowledge.temp_match_score = match_score
        
        best_match = max(conflicting_knowledges, key=lambda k: k.temp_match_score)
        
        # 3. 鍘嗗彶鎴愬姛鐜囷細鍩轰簬鍘嗗彶浣跨敤鏁堟灉鍔犳潈
        for knowledge in conflicting_knowledges:
            success_rate = self.historical_success_rates.get(knowledge.knowledge_id, 0.5)
            knowledge.temp_success_score = success_rate
        
        best_history = max(conflicting_knowledges, key=lambda k: k.temp_success_score)
        
        # 4. 缁煎悎璇勫垎锛氬姞鏉冭＄畻鏈缁堝緱鍒
        scores = {}
        for knowledge in conflicting_knowledges:
            composite_score = (
                knowledge.priority_score * self.context_weights["priority"] +
                knowledge.temp_match_score * self.context_weights["context_match"] +
                knowledge.temp_success_score * self.context_weights["history_success"] +
                self._calculate_additional_factors(knowledge, current_situation) * self.context_weights["composite"]
            )
            scores[knowledge.knowledge_id] = composite_score
        
        winner_id = max(scores, key=scores.get)
        return next(k for k in conflicting_knowledges if k.knowledge_id == winner_id)
    
    def _calculate_context_match(self, conditions: Dict, situation: Dict) -> float:
        """璁＄畻鎯呭冨尮閰嶅害"""
        matches = 0
        total = 0
        for key, expected in conditions.items():
            if key in situation:
                actual = situation[key]
                if isinstance(expected, list):
                    match = any(self._fuzzy_match(e, actual) for e in expected)
                else:
                    match = self._fuzzy_match(expected, actual)
                if match:
                    matches += 1
                total += 1
        return matches / total if total > 0 else 0.0
    
    def _fuzzy_match(self, expected, actual):
        """妯＄硦鍖归厤锛堟敮鎸侀儴鍒嗗尮閰嶏級"""
        if isinstance(expected, str) and isinstance(actual, str):
            return expected.lower() in actual.lower() or actual.lower() in expected.lower()
        return expected == actual
    
    def _calculate_additional_factors(self, knowledge: StandardGuandanKnowledge, situation: Dict) -> float:
        """璁＄畻棰濆栧洜绱狅紙濡傛父鎴忛樁娈垫潈閲嶏級"""
        stage_weight = 1.0
        if "stage" in situation:
            if situation["stage"] == "endgame" and knowledge.category == "DEFENSE_TACTICS":
                stage_weight = 1.2  # 娈嬪眬闃插畧鏇撮噸瑕
            elif situation["stage"] == "opening" and knowledge.category == "UPGRADE_STRATEGY":
                stage_weight = 1.1  # 寮灞鍗囩骇绛栫暐浼樺厛
        return stage_weight
```

姝ゆ満鍒剁‘淇濆湪鐭涚浘鎯呭喌涓嬶紝閫夋嫨鏈閫傚悎褰撳墠灞闈㈢殑鐭ヨ瘑锛坋.g., 娈嬪眬闃舵典紭鍏堥槻瀹堢煡璇嗭級銆

#### 1.6 鎸佷箙鍖栬板繂绯荤粺
```python
# src/memory/lifetime_memory_system.py
class LifetimeMemorySystem:
    """缁堣韩璁板繂绯荤粺 - 鎶曞杺涓娆★紝姘镐箙浣跨敤"""
    
    async def store_knowledge_memory(self, knowledge_item, context):
        """瀛樺偍鐭ヨ瘑璁板繂"""
        # SQLite鎸佷箙鍖栧瓨鍌
        # 鏋勫缓璁板繂鍏宠仈
        # 鏇存柊缂撳瓨
```

**璁板繂绯荤粺鐗圭偣**锛
- 鉁 **鎶曞杺涓娆★紝姘镐箙浣跨敤** - 鐭ヨ瘑娉ㄥ叆鍚庢寔缁鐢熸晥
- 鉁 **鑷鍔ㄥ叧鑱** - 鐩稿叧璁板繂鑷鍔ㄥ叧鑱
- 鉁 **鏅鸿兘妫绱** - 鏍规嵁涓婁笅鏂囨绱㈢浉鍏宠板繂 (e.g., stage: play, curAction: Bomb)
- 鉁 **琛板噺鏈哄埗** - 闀挎湡鏈浣跨敤鐨勮板繂鑷鍔ㄨ“鍑
- **鎬ц兘浼樺寲**锛氫娇鐢ㄧ煡璇嗙紦瀛樺拰绱㈠紩锛屾敮鎸10,000+鏉＄煡璇嗙殑蹇閫熸绱锛<50ms锛夛紝閫氳繃棰勫姞杞介珮棰戠煡璇嗗拰鍒嗗眰绱㈠紩瀹炵幇

### 绗浜岄儴鍒嗭細璁缁冩柟娉

#### 2.1 璁缁冨钩鍙

##### 涓昏佸钩鍙帮細鍗椾含閭鐢靛ぇ瀛︽幖铔婣I绠楁硶瀵规姉骞冲彴
- **骞冲彴鍦板潃**锛歨ttps://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **褰撳墠鐗堟湰**锛歷1006锛堢洰鍓嶆棤鏇存柊锛屽悗缁濡傛湁鍙樻洿閫氳繃鐗堟湰閫傞厤鍣ㄥ勭悊锛
- **鐘舵**锛氬唴娴嬩腑锛堝彲鍙備笌锛

**骞冲彴鐗圭偣**锛
- 鎻愪緵绂荤嚎骞冲彴鐢ㄤ簬鏈鍦板紑鍙戞祴璇
- 瀹屾暣鐨刉ebSocket + JSON閫氫俊鎺ュ彛 (type: notify/act, stage: beginning/play)
- 鏀鎸4涓狝I鍚屾椂瀵规垬璁缁 (myPos: 0-3, 0-2涓闃, 1-3涓闃)
- 鑷鍔ㄨ瘎鍒嗗拰鎺掑悕绯荤粺

**鏈鍦拌缁冪幆澧**锛氱荤嚎骞冲彴鍙鐢ㄦу緟纭璁わ紙鏄鍚﹀寘鍚瀹屾暣瑁佸垽绯荤粺锛夈傞勭暀妯℃嫙鍣ㄦ帴鍙ｈˉ鍏呭姛鑳姐4涓狝I杩愯岃祫婧愰渶姹傦細CPU 4鏍搞佸唴瀛 8GB銆丟PU鍙閫夛紙寮哄寲瀛︿範鏃堕渶16GB+锛夈

#### 2.2 璁缁冩柟娉

##### 鏂规硶涓锛氬熀浜庤勫垯鐨勪紶缁熻缁冿紙鍏ラ棬锛
**閫傜敤闃舵**锛氬叆闂ㄥ拰鍩虹璁缁冿紙1-2鍛锛

**鏍稿績鎬濊矾**锛
```python
1. 瀹炵幇鍩虹鐗屽瀷璇嗗埆 (Single/Pair/Trips/ThreePair/ThreeWithTwo/TwoTrips/Straight/StraightFlush/Bomb/tribute/back/PASS)
2. 寤虹珛鍑虹墝浼樺厛绾ц勫垯
3. 瀹炵幇鍩虹閰嶅悎绛栫暐
4. 杩炵画瀵瑰眬璁缁冧紭鍖
5. 鍒嗘瀽澶辫触妗堜緥鏀硅繘瑙勫垯
```

**浼樺娍**锛氬疄鐜扮畝鍗曪紝瀹规槗璋冭瘯锛岃勫垯閫忔槑  
**鍔ｅ娍**锛氱瓥鐣ユ繁搴︽湁闄愶紝闅句互搴斿瑰嶆潅灞闈

##### 鏂规硶浜岋細鎼滅储绠楁硶璁缁冿紙涓绾э級
**閫傜敤闃舵**锛氫腑绾ц缁冿紙2-4鍛锛

**鏍稿績鎬濊矾**锛
- 浣跨敤Minimax鎼滅储绠楁硶
- Alpha-Beta鍓鏋濅紭鍖
- 璇勪及鍑芥暟璁捐 (鑰冭檻handCards澶у皬銆乧urRank銆乼eammate_seat)
- 娣卞害鎼滅储浼樺寲

##### 鏂规硶涓夛細寮哄寲瀛︿範璁缁冿紙楂樼骇锛
**閫傜敤闃舵**锛氶珮绾ц缁冿紙4-8鍛锛

**鏍稿績鎬濊矾**锛
- 浣跨敤娣卞害寮哄寲瀛︿範锛圖QN/A3C/PPO锛
- 閫氳繃澶ч噺瀵瑰眬瀛︿範鏈浼樼瓥鐣
- 鑷鎴戝瑰紙涓嶆柇鏀硅繘
- 澶氭櫤鑳戒綋鍗忓悓璁缁 (鑰冭檻myPos鍜宑urPos鐨勫洟闃熷姩鎬)

##### 鏂规硶鍥涳細鐭ヨ瘑澧炲己璁缁冿紙鎺ㄨ崘锛
**閫傜敤闃舵**锛氭墍鏈夐樁娈

**鏍稿績鎬濊矾**锛
- 娉ㄥ叆涓撳剁煡璇嗭紙涓佸崕绉樼睄锛
- 缁撳悎瑙勫垯寮曟搸鍜屽己鍖栧︿範
- 鐭ヨ瘑椹卞姩鍐崇瓥 (trigger_conditions鍖归厤褰撳墠stage/curAction)
- 鎸佺画浼樺寲鐭ヨ瘑搴

```python
# 鐭ヨ瘑澧炲己AI绀轰緥
class KnowledgeDrivenAI:
    """鐭ヨ瘑椹卞姩AI"""
    
    def make_decision(self):
        # 1. 鍒嗘瀽褰撳墠灞闈
        situation = self._analyze_situation()  # {"stage": "play", "curPos": 1}
        
        # 2. 搴旂敤涓撳剁煡璇
        knowledge_plays = self._apply_expert_knowledge(available_plays, situation)
        
        # 3. 缁撳悎缁忛獙瀛︿範
        experience_plays = self._apply_experience_learning(available_plays)
        
        # 4. 缁煎悎璇勪及閫夋嫨
        final_play = self._comprehensive_evaluation(
            knowledge_plays, experience_plays, situation
        )
        return final_play  # e.g., ["Pair", "2", ["H2", "D2"]]
```

#### 2.3 璁缁冩暟鎹鏀堕泦
**鏁版嵁鏉ユ簮**锛
1. 骞冲彴瀵规垬鏁版嵁 - 浠庡崡閭骞冲彴鑾峰彇瀵瑰眬璁板綍 (stage: gameOver鍚庣殑replays)
2. 鑷鎴戝瑰紙鏁版嵁 - 澶氫釜AI鐗堟湰瀵规垬
3. 涓撳舵爣娉ㄦ暟鎹 - 閭璇锋幖铔嬮珮鎵嬫爣娉

**鏁版嵁鏍煎紡**锛
```json
{
  "game_id": "20241121_001",
  "game_state": {
    "stage": "play",
    "myPos": 0,
    "curPos": 1,
    "handCards": ["S2", "H3", ...],
    "curAction": ["Single", "2", ["H2"]]
  },
  "decision": {
    "player": 0,
    "action": "play",
    "selected_cards": ["H3"],
    "reasoning": "璺熼殢鍚岃姳鑹诧紝閬垮厤杩囨棭浣跨敤澶х墝"
  },
  "outcome": {
    "win": true,
    "score": 12
  }
}
```

#### 2.4 璁缁冭瘎浼版寚鏍
**鎶鏈鎸囨爣**锛
- 鍐崇瓥鍑嗙‘鐜囷細> 95%
- 鍝嶅簲鏃堕棿锛< 20绉掞紙鎸夊疄闄呮瘮璧涜勫垯锛屽嶆潅灞闈涓嬪厑璁告洿闀垮喅绛栨椂闂达級
- 绋冲畾鎬э細杩炵画100灞鏃犲穿婧

**绔炴妧鎸囨爣**锛
- vs 鍩虹AI锛> 80% 鑳滅巼
- vs 涓绾AI锛> 60% 鑳滅巼
- vs 楂樼骇AI锛> 40% 鑳滅巼
- 閰嶅悎榛樺戝害锛> 70%

**璁缁冩暟鎹瑙勬ā**锛氳捣濮50灞杩涜屽垵姝ラ獙璇侊紝閫愭ユ墿灞曘
```python
# 璁缁冩暟鎹瑙勬ā璇勪及
TRAINING_CONFIG = {
    "basic_ai": {
        "required_games": 1000,      # 鍩虹AI璁缁
        "expected_win_rate": 0.80
    },
    "intermediate_ai": {
        "required_games": 10000,     # 涓绾AI璁缁
        "expected_win_rate": 0.60
    },
    "advanced_ai": {
        "required_games": 50000,     # 楂樼骇AI璁缁
        "expected_win_rate": 0.40,
        "rl_iterations": 1000       # 寮哄寲瀛︿範杩浠
    }
}
```

### 绗涓夐儴鍒嗭細鍙傝禌鎸囧崡

#### 3.1 鍙傝禌娴佺▼
```
1. 璁块棶骞冲彴 鈫 涓嬭浇璧勬簮
   鈫
2. 闃呰绘枃妗 鈫 鐞嗚В瑙勫垯
   鈫
3. 寮鍙慉I瀹㈡埛绔
   鈫
4. 鏈鍦版祴璇 鈫 纭淇濈ǔ瀹
   鈫
5. 鑱旂郴涓诲姙鏂 鈫 鎻愪氦鐢宠
   鈫
6. 姝ｅ紡鍙傝禌 鈫 鍙備笌瀵规垬
   鈫
7. 鎸佺画浼樺寲 鈫 鎻愬崌鎺掑悕
```

#### 3.2 鎶鏈瑕佺偣

##### WebSocket杩炴帴
```python
# 鏈鍦拌繛鎺
ws://127.0.0.1:23456/game/{user_info}

# 灞鍩熺綉杩炴帴
ws://[灞鍩熺綉IP]:23456/game/{user_info}
```

##### 缁勯槦瑙勫垯
- **绗1涓鍜岀3涓杩炴帴**鐨凙I鑷鍔ㄤ负涓闃 (myPos: 0鍜2)
- **绗2涓鍜岀4涓杩炴帴**鐨凙I鑷鍔ㄤ负涓闃 (myPos: 1鍜3)
- 褰撳墠浠ュ钩鍙拌存槑涓哄噯锛屽悗缁濡傛湁鏇存柊鍐嶈皟鏁淬傞勭暀搴т綅鍔ㄦ佽瘑鍒鎺ュ彛锛
```python
class DynamicSeatIdentifier:
    """鍔ㄦ佸骇浣嶈瘑鍒鍣"""
    def identify_teammate(self, my_pos: int, all_positions: List[int]) -> int:
        """璇嗗埆闃熷弸搴т綅"""
        # 骞冲彴瑙勫垯锛0-2涓闃燂紝1-3涓闃
        teammate_map = {0: 2, 2: 0, 1: 3, 3: 1}
        return teammate_map.get(my_pos, -1)  # -1琛ㄧず鏈鐭
```

##### 鐗屽瀷涓鑻辨枃瀵圭収锛堝钩鍙版爣鍑嗭級
- Single -- 鍗曞紶 (Single)
- Pair -- 瀵瑰瓙 (Pair)
- Trips -- 涓夊紶 (Trips)
- ThreePair -- 涓夎繛瀵 (ThreePair)
- ThreeWithTwo -- 涓夊甫浜 (ThreeWithTwo)
- TwoTrips -- 閽㈡澘 (TwoTrips)
- Straight -- 椤哄瓙 (Straight)
- StraightFlush -- 鍚岃姳椤 (StraightFlush)
- Bomb -- 鐐稿脊 (Bomb)
- tribute -- 杩涜础 (tribute)
- back -- 杩樿础 (back)
- PASS -- 杩 (PASS)

#### 3.3 寮鍙戞鏌ユ竻鍗
**寮鍙戦樁娈**锛
- [ ] 涓嬭浇绂荤嚎骞冲彴锛坴1006锛
- [ ] 涓嬭浇浣跨敤璇存槑涔
- [ ] 闃呰绘父鎴忚勫垯
- [ ] 鐞嗚ВJSON鏍煎紡 (["type", "rank", ["cards"]])
- [ ] 寮鍙慦ebSocket閫氫俊
- [ ] 瀹炵幇鐗屽瀷璇嗗埆
- [ ] 瀹炵幇鍐崇瓥閫昏緫
- [ ] 瀹炵幇閿欒澶勭悊

**娴嬭瘯闃舵**锛
- [ ] 鏈鍦拌繛鎺ユ祴璇
- [ ] 鍗曞眬瀹屾暣娴嬭瘯
- [ ] 澶氬眬绋冲畾鎬ф祴璇
- [ ] 寮傚父鍦烘櫙娴嬭瘯
- [ ] 鎬ц兘娴嬭瘯锛堝搷搴旀椂闂<20绉掞級

**鎻愪氦闃舵**锛
- [ ] 鍑嗗囦唬鐮/绋嬪簭
- [ ] 缂栧啓浣跨敤璇存槑
- [ ] 缂栧啓鎶鏈鏂囨。
- [ ] 鍙戦佸弬璧涚敵璇烽偖浠

##### 鍙傝禌鎻愪氦鏉愭枡娓呭崟锛堝緟纭璁わ級
- [ ] AI瀹㈡埛绔鍙鎵ц岀▼搴
- [ ] 婧愪唬鐮侊紙鏄鍚﹂渶瑕佸紑婧愶紵寰呯‘璁わ級
- [ ] 浣跨敤璇存槑鏂囨。锛堟牸寮忚佹眰锛熷緟纭璁わ級
- [ ] 鎶鏈鎶ュ憡锛堝瓧鏁伴檺鍒讹紵寰呯‘璁わ級
- [ ] 娴嬭瘯鎶ュ憡锛堟槸鍚﹀繀椤伙紵寰呯‘璁わ級
- [ ] 瑙嗛戞紨绀猴紙鏄鍚﹂渶瑕侊紵寰呯‘璁わ級

**姣旇禌璇勫垎鏍囧噯**锛氬綋鍓嶉勪及锛堣儨鐜40-50%锛屽喅绛栬川閲20-30%绛夛級锛岄渶鑱旂郴涓诲姙鏂癸紙chenxg@njupt.edu.cn锛夌‘璁ゅ疄闄呮潈閲嶏紝骞舵嵁姝よ皟鏁村紑鍙戦噸鐐癸紙濡備紭鍏堟彁鍗囪儨鐜囷級銆

### 绗鍥涢儴鍒嗭細鎶鏈瀹炵幇

#### 4.1 椤圭洰缁撴瀯
```
guandan-ai/
鈹溾攢鈹 src/
鈹   鈹溾攢鈹 communication/      # WebSocket閫氫俊
鈹   鈹溾攢鈹 game_logic/         # 娓告垙閫昏緫
鈹   鈹溾攢鈹 decision/           # 鍐崇瓥寮曟搸
鈹   鈹溾攢鈹 knowledge/          # 鐭ヨ瘑绯荤粺
鈹   鈹   鈹溾攢鈹 enhanced_extractor.py
鈹   鈹   鈹溾攢鈹 expert_formatter.py
鈹   鈹   鈹斺攢鈹 knowledge_base.py
鈹   鈹溾攢鈹 memory/             # 璁板繂绯荤粺
鈹   鈹   鈹斺攢鈹 lifetime_memory_system.py
鈹   鈹斺攢鈹 core/               # 鏍稿績绯荤粺
鈹       鈹斺攢鈹 knowledge_injection_system.py
鈹溾攢鈹 data/
鈹   鈹溾攢鈹 knowledge/          # 鐭ヨ瘑搴
鈹   鈹溾攢鈹 replays/            # 瀵瑰眬鍥炴斁
鈹   鈹斺攢鈹 memory/             # 璁板繂鏁版嵁
鈹溾攢鈹 config/
鈹   鈹斺攢鈹 config.yaml
鈹斺攢鈹 tests/
```

#### 4.2 鏍稿績妯″潡瀹炵幇

##### WebSocket閫氫俊妯″潡
```python
# src/communication/websocket_client.py
class GuandanWebSocketClient:
    async def connect(self, url: str):
        """杩炴帴WebSocket"""
        self.websocket = await websockets.connect(url)
        await self._handle_messages()
    
    async def _process_message(self, message: str):
        """澶勭悊娑堟伅"""
        data = json.loads(message)
        message_type = data.get("type")  # notify/act
        
        if message_type == "act" and data.get("stage") == "play":
            await self._handle_play_request(data)  # curPos, curAction, handCards
```

##### 鐭ヨ瘑椹卞姩鍐崇瓥寮曟搸
```python
# src/decision/knowledge_driven_ai.py
class KnowledgeDrivenAI:
    def __init__(self, game_state, knowledge_base):
        self.game_state = game_state  # myPos, handCards, curRank, stage
        self.kb = knowledge_base
        self.conflict_resolver = KnowledgeConflictResolver()  # 闆嗘垚鍐茬獊瑙ｅ喅
    
    def make_decision(self):
        # 1. 鑾峰彇鍙鐢ㄥ嚭鐗
        available_plays = self.game_state.get_available_cards()
        
        # 2. 鍒嗘瀽褰撳墠灞闈
        situation = self._analyze_situation()  # {"stage": "play", "curPos": 1}
        
        # 3. 搴旂敤涓撳剁煡璇嗭紙澶勭悊鍐茬獊锛
        knowledge_plays = self.kb.search_relevant_knowledge(situation)
        if len(knowledge_plays) > 1 and any(self._has_conflict(knowledge_plays)):
            resolved_knowledge = self.conflict_resolver.resolve_conflicts(knowledge_plays, situation)
            knowledge_plays = [resolved_knowledge]
        knowledge_plays = self._apply_expert_knowledge(available_plays, situation)
        
        # 4. 缁撳悎缁忛獙瀛︿範
        experience_plays = self._apply_experience_learning(available_plays)
        
        # 5. 缁煎悎璇勪及閫夋嫨锛堣秴鏃舵帶鍒<20绉掞級
        final_play = self._comprehensive_evaluation(
            knowledge_plays, experience_plays, situation
        )
        return final_play  # e.g., ["Pair", "2", ["H2", "D2"]]
```

#### 4.3 閰嶇疆绀轰緥
```yaml
# config/config.yaml
platform:
  websocket_url: "ws://127.0.0.1:23456/game/{user_id}"
  version: "v1006"  # 褰撳墠鐗堟湰锛屾棤鏇存柊锛涢勭暀閫傞厤鍣ㄥ勭悊鏈鏉ュ彉鏇

ai:
  name: "KnowledgeDrivenAI"
  strategy_level: "expert"
  response_timeout: 20.0  # 鎸夊疄闄呮瘮璧涜勫垯锛<20绉

knowledge:
  injection_enabled: true
  knowledge_base_path: "data/knowledge/guandan_knowledge_base.json"
  confidence_threshold: 0.8
  conflict_resolution: true  # 鍚鐢ㄥ啿绐佽В鍐

memory:
  enabled: true
  memory_db_path: "data/memory/lifetime_memory.db"
  max_memory_entries: 10000
  cache_enabled: true  # 鎬ц兘浼樺寲锛氬惎鐢ㄧ紦瀛

logging:
  level: "INFO"
  file: "logs/ai_client.log"
```

### 绗浜旈儴鍒嗭細瀹屾暣宸ヤ綔娴

#### 5.1 鐭ヨ瘑娉ㄥ叆宸ヤ綔娴
```python
# 瀹屾暣鐭ヨ瘑娉ㄥ叆娴佺▼
async def inject_expert_knowledge():
    # 1. 鍒濆嬪寲绯荤粺
    injection_system = KnowledgeInjectionSystem()
    memory_system = LifetimeMemorySystem()
    
    # 2. 鎻愬彇涓撳剁煡璇
    extractor = RealExpertKnowledgeExtractor()
    formatter = ExpertKnowledgeFormatter()
    
    # 璇诲彇涓佸崕绉樼睄
    with open("docs/skill/鎺艰泲鎶宸х樼睄(涓佸崕).md", "r", encoding="utf-8") as f:
        expert_text = f.read()
    
    # 3. 鎻愬彇鍜屾牸寮忓寲
    extracted = extractor.extract_knowledge_from_text(expert_text, "涓佸崕绉樼睄")
    formatted = [formatter.format_extracted_knowledge(e, "涓佸崕绉樼睄") 
                 for e in extracted]
    
    # 4. 杩囨护楂樼疆淇″害鐭ヨ瘑
    high_confidence = [k for k in formatted if k.confidence_score >= 0.8]
    
    # 5. 娉ㄥ叆绯荤粺锛堥泦鎴愬啿绐佽В鍐筹級
    resolver = KnowledgeConflictResolver()
    for knowledge in high_confidence:
        await injection_system.inject_knowledge_package(knowledge)
        await memory_system.store_knowledge_memory(knowledge)
    
    print(f"鎴愬姛娉ㄥ叆 {len(high_confidence)} 鏉′笓瀹剁煡璇")
```

#### 5.2 璁缁冨伐浣滄祦
```python
# 瀹屾暣璁缁冩祦绋
async def train_guandan_ai():
    # 1. 鍒濆嬪寲AI
    game_state = GameState()  # handCards, myPos, curPos, stage
    knowledge_base = GuandanKnowledgeBase()
    knowledge_base.load_from_file("data/knowledge/guandan_knowledge_base.json")
    
    ai = KnowledgeDrivenAI(game_state, knowledge_base)
    
    # 2. 杩炴帴骞冲彴
    client = GuandanWebSocketClient("AI_TRAIN_001", game_state)
    client.rule_ai = ai
    
    # 3. 寮濮嬭缁冿紙璧峰50灞鍒濇ラ獙璇侊級
    url = "ws://127.0.0.1:23456/game/AI_TRAIN_001"
    await client.connect(url)
    
    # 4. 鏀堕泦璁缁冩暟鎹
    # 5. 鍒嗘瀽浼樺寲
    # 6. 鎸佺画鏀硅繘
```

#### 5.3 鍙傝禌宸ヤ綔娴
```python
# 鍙傝禌鍑嗗囨祦绋
async def prepare_for_competition():
    # 1. 纭淇濈煡璇嗗簱宸叉敞鍏
    await inject_expert_knowledge()
    
    # 2. 鏈鍦版祴璇
    await local_testing()
    
    # 3. 鎬ц兘浼樺寲
    await optimize_performance()
    
    # 4. 鍑嗗囨彁浜ゆ潗鏂
    prepare_submission_materials()
    
    # 5. 鑱旂郴涓诲姙鏂
    contact_organizers()
```

### 绗鍏閮ㄥ垎锛氭渶浣冲疄璺

#### 6.1 鐭ヨ瘑娉ㄥ叆鏈浣冲疄璺
1. **浼樺厛娉ㄥ叆楂樼疆淇″害鐭ヨ瘑** (confidence >= 0.8)
2. **鎸変紭鍏堢骇鍒嗙被娉ㄥ叆** (楂樹紭鍏堢骇瑙勫垯浼樺厛锛屽侭omb浣跨敤鏃舵満)
3. **瀹氭湡鏇存柊鐭ヨ瘑搴** (鏍规嵁瀹炴垬鍙嶉)
4. **楠岃瘉鐭ヨ瘑鏈夋晥鎬** (閫氳繃瀵瑰眬楠岃瘉)
5. **鍐茬獊瑙ｅ喅**锛氶泦鎴怟nowledgeConflictResolver澶勭悊鐭涚浘寤鸿

#### 6.2 璁缁冩渶浣冲疄璺
1. **寰搴忔笎杩** - 浠庤勫垯寮曟搸寮濮嬶紝閫愭ュ紩鍏ラ珮绾ф柟娉
2. **鏁版嵁椹卞姩** - 閲嶈嗘暟鎹鏀堕泦鍜岀粺璁″垎鏋 (replays鍒嗘瀽)
3. **鎸佺画浼樺寲** - 寤虹珛鍙嶉堟満鍒讹紝鎸佺画鏀硅繘
4. **瀵规瘮瀛︿範** - 涓庝笉鍚屾按骞矨I瀵规瘮锛屾壘鍑洪棶棰
5. **璧峰嬭勬ā**锛氫粠50灞寮濮嬮獙璇侊紝閫愭ユ墿灞曞埌鏁板崈灞

#### 6.3 寮鍙戞渶浣冲疄璺
1. **涓ユ牸閬靛惊JSON鏍煎紡** - 纭淇濆钩鍙板吋瀹规 (["Single", "2", ["H2"]])
2. **瀹炵幇閿欒澶勭悊** - 鎻愰珮绯荤粺绋冲畾鎬
3. **璁板綍璇︾粏鏃ュ織** - 渚夸簬闂棰樻帓鏌 (stage/curAction鍙樺寲)
4. **鐗堟湰鎺у埗** - 浣跨敤Git绠＄悊浠ｇ爜
5. **鍔ㄦ佸骇浣嶈瘑鍒**锛氶勭暀鎺ュ彛澶勭悊娼滃湪鐨勫骇浣嶅姩鎬佸垎閰

### 绗涓冮儴鍒嗭細璇勪及涓庝紭鍖

#### 7.1 鎬ц兘璇勪及
```python
# 鎬ц兘璇勪及鎸囨爣
evaluation_metrics = {
    "technical": {
        "decision_accuracy": 0.95,  # 鍐崇瓥鍑嗙‘鐜
        "response_time": 20.0,      # 鍝嶅簲鏃堕棿锛堢掞紝鎸夋瘮璧涜勫垯锛
        "stability": 100            # 杩炵画瀵瑰眬鏁
    },
    "competitive": {
        "win_rate_vs_basic": 0.80,
        "win_rate_vs_intermediate": 0.60,
        "win_rate_vs_advanced": 0.40,
        "cooperation_success": 0.70
    },
    "learning": {
        "convergence_speed": 500,    # 鏀舵暃杞娆
        "generalization": 0.85,     # 娉涘寲鑳藉姏
        "adaptation": 0.75          # 閫傚簲鑳藉姏
    }
}
```

##### 璁板繂绯荤粺鎬ц兘鍩哄噯娴嬭瘯
```python
# 鎬ц兘鍩哄噯娴嬭瘯
import time
from src.memory.lifetime_memory_system import LifetimeMemorySystem

async def benchmark_memory_retrieval():
    memory = LifetimeMemorySystem()
    await memory.load_all_knowledge()
    
    # 娴嬭瘯涓嶅悓瑙勬ā鐨勬绱㈡ц兘锛堝凡浼樺寲锛氱紦瀛+绱㈠紩锛
    for knowledge_count in [100, 1000, 10000]:
        start_time = time.time()
        results = await memory.search_relevant_knowledge(
            situation={"stage": "play", "curAction": "Bomb"}, 
            limit=10
        )
        end_time = time.time()
        
        print(f"{knowledge_count}鏉＄煡璇嗘绱㈣楁椂: {end_time - start_time:.4f}s")
        # 棰勬湡锛100鏉 <10ms, 1000鏉 <30ms, 10000鏉 <100ms锛堥氳繃鍒嗗眰绱㈠紩鍜岀紦瀛樺疄鐜帮級
```

#### 7.2 浼樺寲寤鸿
**鐭ヨ瘑绯荤粺浼樺寲**锛
- 瀹氭湡鏇存柊鐭ヨ瘑搴
- 鏍规嵁浣跨敤鏁堟灉璋冩暣浼樺厛绾
- 鍚堝苟鐩镐技鐭ヨ瘑椤

**鍐崇瓥绯荤粺浼樺寲**锛
- 浼樺寲璇勪及鍑芥暟
- 璋冩暣鐭ヨ瘑鏉冮噸
- 鏀硅繘鎼滅储绠楁硶
- **鍝嶅簲鏃堕棿**锛氬嶆潅灞闈涓嬪厑璁<20绉掑喅绛栵紝鎸夊疄闄呮瘮璧涜勫垯璋冩暣

**鎬ц兘浼樺寲**锛
- 浼樺寲鏁版嵁缁撴瀯
- 鍑忓皯璁＄畻澶嶆潅搴
- 浣跨敤缂撳瓨鏈哄埗锛堣板繂绯荤粺宸查泦鎴愶級

##### 鐭ヨ瘑搴撴洿鏂扮＄悊鍣
```python
class KnowledgeUpdateManager:
    """鐭ヨ瘑鏇存柊绠＄悊鍣"""
    def __init__(self):
        self.version_control = KnowledgeVersionControl()
        self.validation_pipeline = KnowledgeValidationPipeline()
    
    async def update_knowledge_base(self, new_knowledge_source: str, version: str):
        """鏇存柊鐭ヨ瘑搴擄紙鏀鎸佽嗛戠礌鏉愶級"""
        # 1. 鎻愬彇鏂扮煡璇嗭紙鏂囨湰/瑙嗛戣浆褰曪級
        if new_knowledge_source.endswith('.mp4'):
            transcribed_text = await self._transcribe_video(new_knowledge_source)
            extracted = self._extract_from_transcription(transcribed_text)
        else:
            with open(new_knowledge_source, 'r') as f:
                text = f.read()
            extracted = self._extract_from_text(text)
        
        # 2. 楠岃瘉鍏煎规
        validated = [k for k in extracted if self.validation_pipeline.validate(k)]
        
        # 3. 鐗堟湰鎺у埗锛堝為噺鏇存柊锛
        self.version_control.create_new_version(validated, version)
        
        # 4. 澧為噺鏇存柊锛堜粎娣诲姞鏂扮煡璇嗭紝閬垮厤瑕嗙洊锛
        for knowledge in validated:
            if not self._exists(knowledge.knowledge_id):
                await self._insert_knowledge(knowledge)
        
        # 5. 閫氱煡鐩稿叧绯荤粺锛圓I閲嶈浇缂撳瓨锛
        await self._notify_update(version)
        print(f"鐭ヨ瘑搴撴洿鏂板畬鎴愶細鐗堟湰 {version}锛屾柊澧 {len(validated)} 鏉＄煡璇")
    
    async def _transcribe_video(self, video_path: str) -> str:
        """瑙嗛戣浆褰曪紙浣跨敤璇闊宠瘑鍒獳PI锛"""
        # 闆嗘垚Whisper鎴栧叾浠朅SR鏈嶅姟
        # 杩斿洖杞褰曟枃鏈
        pass
    
    def _exists(self, knowledge_id: str) -> bool:
        """妫鏌ョ煡璇嗘槸鍚﹀瓨鍦锛堥伩鍏嶉噸澶嶏級"""
        # 鏌ヨ㈡暟鎹搴
        pass
```

姝ょ＄悊鍣ㄦ敮鎸佹枃鏈鍜岃嗛戠礌鏉愭洿鏂帮紝纭淇濈煡璇嗗簱鐨勬寔缁婕旇繘銆

**鏂囨。鐗堟湰鍚屾**锛
- **鏂囨。鐗堟湰鏄犲皠琛**锛氱淮鎶 `docs/VERSION_MAP.md`锛岃板綍鎵鏈夋枃妗ｉ棿鐨勪緷璧栧叧绯诲拰鐗堟湰鍏煎规
- **閾炬帴鐗堟湰妫鏌**锛氬湪鏂囨。涓宓屽叆鐗堟湰鏍￠獙鑴氭湰锛岃块棶閾炬帴鏃堕獙璇佺増鏈涓鑷存
- **鑷鍔ㄥ寲妫鏌**锛氬疄鐜癈I/CD绠￠亾锛岃嚜鍔ㄦ壂鎻忔枃妗ｄ竴鑷存э紙e.g., 閾炬帴鏈夋晥鎬с佸彉閲忓懡鍚嶇粺涓锛

### 蹇閫熷紑濮

#### 绗涓姝ワ細鑾峰彇骞冲彴璧勬簮
1. **璁块棶骞冲彴缃戠珯**
   ```
   https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
   ```

2. **涓嬭浇蹇呰佹枃浠**
   - 鉁 绂荤嚎骞冲彴锛坴1006鐗堟湰锛
   - 鉁 浣跨敤璇存槑涔︼紙v1006锛
   - 鉁 JSON鏍煎紡璇存槑鏂囨。

3. **鑱旂郴鏂瑰紡**
   - 鐮旂┒鍜ㄨ: chenxg@njupt.edu.cn
   - 闂棰樺弽棣: wuguduofeng@gmail.com
   - QQ: 519301156

#### 绗浜屾ワ細鐜澧冨噯澶
```bash
# 1. 瀹夎匬ython 3.8+
python --version

# 2. 瀹夎呬緷璧
pip install websockets>=11.0
pip install asyncio>=3.4.3
pip install numpy>=1.21.0
pip install pandas>=1.5.0
pip install torch>=1.13.0  # 濡傞渶寮哄寲瀛︿範

# 3. 鍒涘缓椤圭洰缁撴瀯
mkdir guandan-ai
cd guandan-ai
mkdir -p {src/{communication,game_logic,decision,knowledge,memory},tests,config,logs,data/{knowledge,replays,memory}}
```

#### 绗涓夋ワ細鍩虹瀹炵幇
鍙傝 `docs/PHASE1_TASKS.md` 瀹屾垚鍩虹鍔熻兘锛
- WebSocket閫氫俊妯″潡
- JSON娑堟伅澶勭悊
- 娓告垙閫昏緫妯″潡
- 鍩虹鍐崇瓥寮曟搸

## 搴旂敤鍦烘櫙
- **寮鍙戦樁娈**锛氭寚瀵间粠闆跺紑濮嬫瀯寤烘幖铔婣I瀹㈡埛绔锛屽寘鎷鐭ヨ瘑娉ㄥ叆銆佽缁冨拰鍙傝禌鐨勫叏娴佺▼
- **璁缁冮樁娈**锛氭彁渚涘垎灞傝缁冩柟娉曪紝浠庤勫垯寮曟搸鍒板己鍖栧︿範鐨勬笎杩涘紡璺寰勶紙璧峰50灞楠岃瘉锛
- **鍙傝禌闃舵**锛氱‘淇滱I绗﹀悎骞冲彴瑕佹眰 (v1006 JSON鏍煎紡銆乵yPos缁勯槦瑙勫垯)锛屽苟浼樺寲鑳滅巼鍜岀ǔ瀹氭
- **浼樺寲闃舵**锛氶氳繃璇勪及鎸囨爣鍜屾渶浣冲疄璺垫寔缁鏀硅繘AI鎬ц兘锛<20绉掑喅绛栨椂闂达級
- **鍥㈤槦鍗忎綔**锛氫綔涓洪」鐩鏂囨。锛屾敮鎸佸氫汉寮鍙戝拰鐭ヨ瘑鍏变韩

## 绀轰緥/妗堜緥
- **鐭ヨ瘑娉ㄥ叆绀轰緥**锛氫粠涓佸崕绉樼睄鎻愬彇"鐐稿脊浣跨敤鏃舵満"鐭ヨ瘑锛屾牸寮忓寲涓篠tandardGuandanKnowledge锛屾敞鍏ュ埌AI鍐崇瓥涓锛屽綋situation["curAction"]涓築omb鏃惰Е鍙慳ction_recommendations
- **璁缁冨瑰眬绀轰緥**锛4涓狝I (myPos 0-3) 杩炴帴鏈鍦板钩鍙帮紝瀹屾垚涓灞娓告垙锛岃板綍replays鏁版嵁锛屽垎鏋愬喅绛栧噯纭鐜 (e.g., 閫夋嫨["Pair", "2", ["H2", "D2"]] 鐨勫悎鐞嗘)锛涜捣濮50灞鍒濇ヨ瘎浼拌儨鐜
- **鍙傝禌鎻愪氦绀轰緥**锛氬彂閫侀偖浠跺埌chenxg@njupt.edu.cn锛岄檮甯︿唬鐮併佷娇鐢ㄨ存槑鍜屾妧鏈鏂囨。锛岄獙璇乄ebSocket杩炴帴 (ws://127.0.0.1:23456) 鍜屽搷搴旀椂闂<20绉
- **璁板繂绯荤粺绀轰緥**锛氬瓨鍌"娈嬪眬閫肩偢"鐭ヨ瘑 (endgame闃舵)锛屽湪鍚庣画瀵瑰眬涓妫绱锛岃嚜鍔ㄥ簲鐢 (confidence_score: 0.9)锛涙ц兘娴嬭瘯鏄剧ず10000鏉＄煡璇嗘绱<100ms

## 娉ㄦ剰浜嬮」
- **骞冲彴鍙橀噺缁熶竴**锛氭墍鏈夌墝鍨 (Single/Pair/Bomb/tribute/back/PASS)銆佺姸鎬 (myPos/curPos/handCards/stage/type) 蹇呴』浣跨敤鍗椾含閭鐢靛ぇ瀛﹀钩鍙版爣鍑嗗彉閲忓悕锛岄栨″嚭鐜版椂鏍囨敞 (e.g., 鍗曞紶 (Single))
- **鏃堕棿澶勭悊**锛氭墍鏈夋椂闂村瓧娈典娇鐢ㄧ郴缁熸椂闂碅PI (datetime.now().strftime('%Y-%m-%d %H:%M:%S'))锛岀佹㈢‖缂栫爜鏃堕棿
- **JSON鏍煎紡**锛氫弗鏍奸伒瀹堝钩鍙拌勮寖锛岀ず渚嬶細["Bomb", "2", ["H2", "D2", "C2", "S2"]]锛屾秷鎭绀轰緥锛歿"type": "act", "stage": "play", "handCards": ["S2", ...], "myPos": 0}
- **缁勯槦瑙勫垯**锛氱1/3杩炴帴涓轰竴闃 (myPos 0/2)锛岀2/4杩炴帴涓轰竴闃 (myPos 1/3)锛屽喅绛栨椂鑰冭檻teammate_seat閰嶅悎锛涢勭暀鍔ㄦ佽瘑鍒鎺ュ彛澶勭悊娼滃湪鍙樻洿
- **鍝嶅簲鏃堕棿**锛氬喅绛栨椂闂<20绉掞紙鎸夊疄闄呮瘮璧涜勫垯锛夛紝澶嶆潅灞闈涓嬪厑璁告洿闀垮喅绛栨椂闂达紱淇℃伅鐩戞帶妫鏌ラ棿闅斺墺6灏忔椂锛岄潤榛樻椂娈 (00:00-06:00) 涓嶆姄鍙
- **鐭ヨ瘑娉ㄥ叆**锛氫粎娉ㄥ叆confidence >= 0.8鐨勯珮璐ㄩ噺鐭ヨ瘑锛屽畾鏈熼獙璇佸疄鎴樻晥鏋滐紱闆嗘垚KnowledgeConflictResolver澶勭悊鐭涚浘寤鸿
- **鍚堣勬**锛氶伒瀹堝钩鍙颁娇鐢ㄦ潯娆撅紝鍙傝禌鍓嶈仈绯讳富鍔炴柟纭璁ゆ彁浜よ佹眰锛堟潗鏂欐竻鍗曞緟纭璁わ級锛涚荤嚎骞冲彴瑁佸垽绯荤粺鍙鐢ㄦу緟楠岃瘉锛岄勭暀妯℃嫙鍣ㄨˉ鍏
- **璁缁冭勬ā**锛氳捣濮50灞鍒濇ラ獙璇侊紝閫愭ユ墿灞曪紱涓佸崕绉樼睄鎻愪緵涓涓婃按骞崇悊璁猴紝鍚庣画寮曞叆瑙嗛戠瓑鏂扮煡璇嗘簮涓板瘜

## 鐩稿叧鐭ヨ瘑鐐
- [鎺艰泲AI鐭ヨ瘑搴撴牸寮忓寲鏂规 - 鍙橀噺鍛藉悕鏍囧噯鍜岀煡璇嗗垎绫 (Rules/Strategy/Skills)]
- [鎺艰泲AI瀹㈡埛绔鏋舵瀯鏂规 - 绯荤粺鍒嗗眰璁捐″拰閫氫俊妯″潡 (WebSocket/JSON)]
- [姹熻嫃鎺艰泲瑙勫垯 - 鍩虹瑙勫垯鍜岀墝鍨嬪畾涔 (Single/Bomb绛)]
- [涓佸崕鎺艰泲鎶宸х樼睄 - 涓撳剁煡璇嗘潵婧 (鍗囩骇绛栫暐/闃插畧鎴樻湳)]

---

**鏂囨。缁存姢**锛氭湰鏂囨。鏁村悎浜嗘墍鏈夌浉鍏虫妧鏈鏂规堬紝寤鸿瀹氭湡鏇存柊  
**鍙嶉堝缓璁**锛氬傛湁闂棰樻垨寤鸿锛岃锋彁浜Issue鎴栬仈绯诲紑鍙戝洟闃

## 馃摑 鏇存柊鏃ュ織

### v2.1 (浣跨敤绯荤粺鏃堕棿API鑾峰彇)
- 鉁 闆嗘垚鐢ㄦ埛鍙嶉堬細鍐崇瓥鏃堕棿璋冩暣涓<20绉掞紝璁缁冭捣濮50灞
- 鉁 瀹炵幇KnowledgeConflictResolver绫伙紙浼樺厛绾/鎯呭/鍘嗗彶/缁煎悎浠茶侊級
- 鉁 澧炲己KnowledgeUpdateManager锛屾敮鎸佽嗛戠礌鏉愯浆褰曞拰澧為噺鏇存柊
- 鉁 娣诲姞鍔ㄦ佸骇浣嶈瘑鍒鎺ュ彛鍜岀増鏈鍏煎硅存槑
- 鉁 浼樺寲璁板繂绯荤粺鎬ц兘锛堢紦瀛+绱㈠紩锛10000鏉<100ms锛
- 鉁 鏇存柊鍙傝禌鏉愭枡娓呭崟锛堝緟纭璁ら」锛夊拰璁缁冭勬ā璇勪及
- 鉁 娣诲姞鏂囨。鐗堟湰鍚屾ユ満鍒讹紙鏄犲皠琛/鑷鍔ㄥ寲妫鏌ワ級

### v2.0 (浣跨敤绯荤粺鏃堕棿API鑾峰彇)
- 鉁 鏁村悎涓撳剁煡璇嗘敞鍏ョ郴缁熴佽缁冩柟娉曘佸弬璧涙寚鍗椼佹妧鏈瀹炵幇
- 鉁 娣诲姞瀹屾暣宸ヤ綔娴佸拰鏈浣冲疄璺
- 鉁 缁熶竴骞冲彴鍙橀噺鍛藉悕 (Single/Bomb/myPos/stage)
- 鉁 澧炲己璁缁冭瘎浼版寚鏍囧拰浼樺寲寤鸿
- 鉁 鎻愪緵蹇閫熷紑濮嬫寚鍗楀拰琛屽姩娓呭崟

### v1.0 (浣跨敤绯荤粺鏃堕棿API鑾峰彇)
- 鍒濆嬬増鏈锛屽熀纭寮鍙戞寚鍗

---

## 鈴 鏃堕棿澶勭悊瑙勮寖
**鎵鏈夋椂闂寸浉鍏冲瓧娈靛繀椤讳娇鐢ㄧ郴缁熸椂闂碅PI锛岀佹㈢‖缂栫爜鏃堕棿銆**

### Python绀轰緥
```python
from datetime import datetime

# 鑾峰彇褰撳墠鏃堕棿
current_time = datetime.now()

# 鏍煎紡鍖栨椂闂村瓧绗︿覆
time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
# 杈撳嚭锛2025-11-24 14:30:00

# 涓鏂囨牸寮
time_str_cn = current_time.strftime('%Y骞%m鏈%d鏃 %H:%M:%S')
# 杈撳嚭锛2025骞11鏈24鏃 14:30:00
```

### 鍏冩暟鎹鏃堕棿瀛楁
鍦ㄦ枃妗ｄ腑锛宍last_updated` 瀛楁靛繀椤讳娇鐢ㄧ郴缁熸椂闂碅PI锛
```markdown
---
title: 鏂囨。鏍囬
last_updated: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}
---
```

**绂佹㈠啓娉**锛
```markdown
---
last_updated: 2025骞11鏈24鏃  # 鉂 纭缂栫爜鏃堕棿
---
```

**姝ｇ‘鍐欐硶**锛
```markdown
---
last_updated: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}  # 鉁 浣跨敤绯荤粺鏃堕棿
---
```

