---
title: 鎺艰泲AI瀹㈡埛绔鍩虹鏋舵瀯鏂规
type: architecture
category: System/Architecture
source: 鎺艰泲AI瀹㈡埛绔鏋舵瀯鏂规.md
version: v2.5
last_updated: 2025-01-27
tags: [鏋舵瀯, 瀹㈡埛绔, WebSocket, 鍐崇瓥寮曟搸, 淇℃伅鐩戞帶, 鐭ヨ瘑搴, 鍔ㄤ綔绌洪棿浼樺寲, 鐗瑰緛缂栫爜, 鐭ヨ瘑搴旂敤妗嗘灦]
difficulty: 楂樼骇
priority: 5
game_phase: 鍏ㄩ樁娈
---

# 鎺艰泲AI瀹㈡埛绔鍩虹鏋舵瀯鏂规

## 姒傝堪
鏈鏂囨。鎻愬嚭鎺艰泲AI瀹㈡埛绔鐨勫熀纭鏋舵瀯鏂规堬紝鏃ㄥ湪寮鍙戠﹀悎鍗椾含閭鐢靛ぇ瀛︽幖铔婣I骞冲彴鐨勫㈡埛绔锛屽疄鐜癆I鑷鍔ㄥ嚭鐗屽喅绛栵紝鏀鎸佽嚜鎴戝瑰紙鍜屾暟鎹鏀堕泦锛屾彁渚涘彲鎵╁睍鐨勬灦鏋勮捐°

**鐩鏍**锛
- 寮鍙戠﹀悎鍗椾含閭鐢靛ぇ瀛︽幖铔婣I骞冲彴鐨勫㈡埛绔
- 瀹炵幇AI鑷鍔ㄥ嚭鐗屽喅绛
- 鏀鎸佽嚜鎴戝瑰紙鍜屾暟鎹鏀堕泦
- 鍙鎵╁睍鐨勬灦鏋勮捐

## 璇︾粏鍐呭

### 涓銆侀」鐩姒傝堪

#### 1.1 椤圭洰鐩鏍
- 寮鍙戠﹀悎鍗椾含閭鐢靛ぇ瀛︽幖铔婣I骞冲彴鐨勫㈡埛绔
- 瀹炵幇AI鑷鍔ㄥ嚭鐗屽喅绛
- 鏀鎸佽嚜鎴戝瑰紙鍜屾暟鎹鏀堕泦
- 鍙鎵╁睍鐨勬灦鏋勮捐

#### 1.2 鎶鏈閫夊瀷
- **缂栫▼璇瑷**: Python锛堟帹鑽愶紝渚夸簬蹇閫熷紑鍙戝拰璋冭瘯锛
- **WebSocket搴**: websockets / websocket-client
- **JSON澶勭悊**: json锛堟爣鍑嗗簱锛
- **鏃ュ織绯荤粺**: logging锛堟爣鍑嗗簱锛
- **閰嶇疆绠＄悊**: configparser / yaml
- **缃戦〉鎶撳彇**: requests / httpx锛圚TTP璇锋眰锛
- **HTML瑙ｆ瀽**: beautifulsoup4 / lxml锛堢綉椤靛唴瀹硅В鏋愶級
- **瀹氭椂浠诲姟**: schedule / APScheduler锛堝畾鏃舵姄鍙栵級
- **閫氱煡绯荤粺**: 鍙閫夛紙閭浠/妗岄潰閫氱煡绛夛級

#### 1.3 骞冲彴瑕佹眰
- **骞冲彴鍚嶇О**: 鍗椾含閭鐢靛ぇ瀛︽幖铔婣I绠楁硶瀵规姉骞冲彴
- **骞冲彴鍦板潃**: https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **褰撳墠鐗堟湰**: v1006锛堝唴娴嬩腑锛屽彲鍙備笌锛
- **WebSocket杩炴帴**锛
  - 鏈鍦拌繛鎺ワ細`ws://127.0.0.1:23456/game/{user_info}`
  - 灞鍩熺綉杩炴帴锛歚ws://[灞鍩熺綉IP]:23456/game/{user_info}`
- **JSON鏁版嵁鏍煎紡閫氫俊**锛氫弗鏍兼寜鐓у钩鍙版牸寮忚佹眰
- **4涓狝I鍚屾椂鍙備笌**锛氱1銆3涓杩炴帴涓轰竴闃燂紝绗2銆4涓杩炴帴涓轰竴闃
- **鏀鎸乄indows/Linux鐜澧**

### 浜屻佺郴缁熸灦鏋勮捐

#### 2.1 鏁翠綋鏋舵瀯锛堝垎灞傝捐★級

```
鈹屸攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
鈹        搴旂敤灞 (Application)         鈹
鈹  - 涓荤▼搴忓叆鍙                       鈹
鈹  - 閰嶇疆绠＄悊                         鈹
鈹  - 鏃ュ織绠＄悊                         鈹
鈹斺攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
          鈫
鈹屸攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
鈹    淇℃伅鐩戞帶灞 (Info Monitor)        鈹
鈹  - 骞冲彴鍔ㄦ佹姄鍙                     鈹
鈹  - 姣旇禌娑堟伅鐩戞帶                     鈹
鈹  - 淇℃伅閫氱煡                         鈹
鈹斺攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
          鈫
鈹屸攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
鈹      鍐崇瓥灞 (Decision Engine)        鈹
鈹  - 绛栫暐璇勪及                         鈹
鈹  - 鍑虹墝鍐崇瓥                         鈹
鈹  - 閰嶅悎绛栫暐                         鈹
鈹  - 鐭ヨ瘑搴撴煡璇                       鈹
鈹斺攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
          鈫
鈹屸攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
鈹      鐭ヨ瘑搴撳眰 (Knowledge Base)       鈹
鈹  - 瑙勫垯搴擄紙纭缂栫爜锛                 鈹
鈹  - 绛栫暐搴擄紙鍐呭瓨鍔犺浇锛               鈹
鈹  - 鎶宸у簱锛堟寜闇鏌ヨ锛               鈹
鈹  - 鐭ヨ瘑妫绱涓庣紦瀛                   鈹
鈹斺攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
          鈫
鈹屸攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
鈹      閫昏緫灞 (Game Logic)             鈹
鈹  - 娓告垙瑙勫垯                         鈹
鈹  - 鐗屽瀷璇嗗埆                         鈹
鈹  - 鐗屽瀷姣旇緝                         鈹
鈹  - 鐘舵佺＄悊                         鈹
鈹斺攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
          鈫
鈹屸攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
鈹      閫氫俊灞 (Communication)         鈹
鈹  - WebSocket杩炴帴                    鈹
鈹  - JSON瑙ｆ瀽/鏋勫缓                    鈹
鈹  - 娑堟伅璺鐢                         鈹
鈹斺攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
          鈫
鈹屸攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
鈹      鏁版嵁灞 (Data Layer)             鈹
鈹  - 瀵瑰眬璁板綍                         鈹
鈹  - 鏁版嵁瀛樺偍                         鈹
鈹  - 缁熻″垎鏋                         鈹
鈹  - 骞冲彴淇℃伅瀛樺偍                     鈹
鈹斺攢鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹鈹
```

### 涓夈佹牳蹇冩ā鍧楄捐

#### 3.1 閫氫俊妯″潡 (Communication Module)

##### 3.1.1 WebSocket瀹㈡埛绔
- **鍔熻兘**:
  - 寤虹珛鍜岀淮鎶WebSocket杩炴帴
  - 鏀鎸佹湰鍦板拰灞鍩熺綉杩炴帴
  - 澶勭悊杩炴帴閲嶈繛鏈哄埗
  - 蹇冭烦淇濇椿
  - 寮傚父澶勭悊鍜屾仮澶

- **杩炴帴鍦板潃**:
  - 鏈鍦版祴璇曪細`ws://127.0.0.1:23456/game/{user_info}`
  - 灞鍩熺綉瀵规垬锛歚ws://[灞鍩熺綉IP]:23456/game/{user_info}`
  - `{user_info}` 涓虹敤鎴蜂俊鎭鏍囪瘑

- **鎺ュ彛璁捐**:
  ```python
  class WebSocketClient:
      - connect(url: str) -> bool
      - send(message: dict) -> bool
      - receive() -> dict
      - disconnect()
      - is_connected() -> bool
      - reconnect() -> bool  # 閲嶈繛鍔熻兘
  ```

##### 3.1.2 JSON娑堟伅澶勭悊
- **鍔熻兘**:
  - 瑙ｆ瀽骞冲彴鍙戦佺殑JSON娑堟伅
  - 鏋勫缓鍙戦佺粰骞冲彴鐨凧SON娑堟伅
  - 娑堟伅鏍煎紡楠岃瘉
  - 娑堟伅绫诲瀷璺鐢

- **娑堟伅绫诲瀷**:
  - 娓告垙寮濮嬫秷鎭
  - 鍙戠墝娑堟伅
  - 鍑虹墝璇锋眰娑堟伅
  - 娓告垙鐘舵佹洿鏂版秷鎭
  - 娓告垙缁撴潫娑堟伅

#### 3.2 娓告垙閫昏緫妯″潡 (Game Logic Module)

##### 3.2.1 鐗屽瀷璇嗗埆鍣 (CardTypeRecognizer)
- **鍔熻兘**:
  - 璇嗗埆鎵鏈夋幖铔嬬墝鍨
  - 涓ユ牸鎸夌収骞冲彴JSON鏍煎紡瑕佹眰
  - 鏀鎸佷富鐗岃瘑鍒

- **鐗屽瀷涓鑻辨枃瀵圭収**锛堝钩鍙版爣鍑嗭級:
  - **Single** -- 鍗曞紶 (Single)
  - **Pair** -- 瀵瑰瓙 (Pair)
  - **Trips** -- 涓夊紶 (Trips)
  - **ThreePair** -- 涓夎繛瀵 (ThreePair)
  - **ThreeWithTwo** -- 涓夊甫浜 (ThreeWithTwo)
  - **TwoTrips** -- 閽㈡澘锛堜袱涓涓夊紶锛 (TwoTrips)
  - **Straight** -- 椤哄瓙 (Straight)
  - **StraightFlush** -- 鍚岃姳椤猴紙鐗规畩椤哄瓙锛 (StraightFlush)
  - **Bomb** -- 鐐稿脊 (Bomb)

- **鐗规畩瑙勫垯**:
  - v1006鐗堟湰璋冩暣浜嗘姉璐¤勫垯锛屼笌姣旇禌鐗堣勫垯涓鑷
  - 娉ㄦ剰鎵嬬墝鐨勮〃绀烘柟娉
  - 鎺ュ彛涓巚1003鐗堟湰淇濇寔涓鑷

##### 3.2.2 鐗屽瀷姣旇緝鍣 (CardTypeComparator)
- **鍔熻兘**:
  - 姣旇緝鐗屽瀷澶у皬
  - 鍒ゆ柇鏄鍚﹀彲浠ュ帇鍒
  - 鍒ゆ柇鐗屽瀷鍚堟硶鎬

##### 3.2.3 澧炲己娓告垙鐘舵佺＄悊鍣 (EnhancedGameStateManager)
- **鍔熻兘**:
  - 缁存姢瀹屾暣鐨勬父鎴忕姸鎬佷俊鎭
  - 闆嗘垚璁扮墝妯″潡
  - 鎻愪緵鐘舵佹煡璇㈡帴鍙
  - 鏀鎸佺姸鎬佸揩鐓у拰鎭㈠
  - **璇嗗埆闃熷弸鍏崇郴**锛堥噸瑕侊級

- **缁勯槦瑙勫垯**锛堝钩鍙拌勫垯锛:
  - **绗1涓鍜岀3涓杩炴帴**鐨凙I鑷鍔ㄤ负涓闃 (myPos: 0鍜2)
  - **绗2涓鍜岀4涓杩炴帴**鐨凙I鑷鍔ㄤ负涓闃 (myPos: 1鍜3)
  - 闃熷弸璇嗗埆鍏寮: `teammate_pos = (myPos + 2) % 4`锛堝弬鑰冭幏濂栦唬鐮侊級

- **鍑虹墝椤哄簭**锛堝钩鍙板疄闄呭疄鐜帮級:
  - 鏍规嵁骞冲彴浣跨敤璇存槑锛歚order` 瀛楁佃〃绀哄畬鐗屾″簭锛堝 `[0, 1, 2, 3]`锛夛紝浠ｈ〃鍑虹墝椤哄簭
  - 鏍规嵁涓绛夊栦唬鐮佸疄鐜帮細`numofnext = (myPos+1)%4`锛堜笅瀹讹級锛宍numofpre = (myPos-1)%4`锛堜笂瀹讹級
  - **骞冲彴瀹為檯鍑虹墝椤哄簭**锛**0 鈫 1 鈫 2 鈫 3 鈫 0...**锛堥『鏃堕拡锛
  - **浣嶇疆鍏崇郴璁＄畻鍏寮**锛
    - 涓嬪朵綅缃锛歚(myPos + 1) % 4`
    - 涓婂朵綅缃锛歚(myPos - 1) % 4`
    - 瀵瑰朵綅缃锛歚(myPos + 2) % 4`锛堥槦鍙嬶級
  - **閲嶈佽存槑**锛氳櫧鐒舵睙鑻忔幖铔嬭勫垯绗240鏉¤"鍑虹墝浠ラ嗘椂閽堜负搴"锛屼絾骞冲彴瀹為檯瀹炵幇涓洪『鏃堕拡椤哄簭銆傚簲浠ュ钩鍙板疄鐜颁负鍑嗐

- **鐘舵佷俊鎭**:
  - 褰撳墠鎵嬬墝鍒楄〃 (handCards)
  - 宸插嚭鐗屽巻鍙
  - 褰撳墠鍑虹墝鐜╁ (curPos)
  - 褰撳墠鐗屽瀷 (curAction)
  - 娓告垙闃舵 (stage)
  - 闃熷弸搴т綅鍙
  - 瀵规墜搴т綅鍙
  - 涓荤墝绾у埆 (curRank)
  
- **澧炲己鍔熻兘**:
  - 鐜╁跺巻鍙茶板綍锛坔istory锛: 姣忎釜鐜╁舵墦鍑虹殑鐗屽拰鍓╀綑鐗屾暟
  - 鐗屽簱鐘舵侊紙remain_cards锛: 鎸夎姳鑹插拰鐐规暟鍒嗙被鐨勫墿浣欑墝
  - 娓告垙杩涘害鐘舵: 杩炵画PASS娆℃暟锛坧ass_num, my_pass_num锛
  - 閰嶅悎鐘舵: 闃熷弸浣嶇疆璇嗗埆銆侀槦鍙嬪嚭鐗屾剰鍥惧垎鏋
  
- **鐘舵佹煡璇㈡帴鍙**:
  - `is_passive_play()`: 鍒ゆ柇鏄鍚﹁鍔ㄥ嚭鐗
  - `is_active_play()`: 鍒ゆ柇鏄鍚︿富鍔ㄥ嚭鐗
  - `is_teammate_action()`: 鍒ゆ柇鏄鍚︽槸闃熷弸鍑虹殑鐗
  - `get_player_remain_cards()`: 鑾峰彇鐜╁跺墿浣欑墝鏁
  - `get_teammate_remain_cards()`: 鑾峰彇闃熷弸鍓╀綑鐗屾暟
  - `get_opponent_remain_cards()`: 鑾峰彇瀵规墜鍓╀綑鐗屾暟
  - `get_pass_count()`: 鑾峰彇PASS娆℃暟
  - `get_state_summary()`: 鑾峰彇鐘舵佹憳瑕

#### 3.3 鍐崇瓥寮曟搸妯″潡 (Decision Engine Module)

##### 3.3.1 澶氬洜绱犺瘎浼扮郴缁 (MultiFactorEvaluator)
- **鍔熻兘**:
  - 缁煎悎璇勪及澶氫釜鍥犵礌
  - 璁＄畻鍔ㄤ綔鐨勭患鍚堣瘎鍒
  - 鏀鎸佹潈閲嶈皟鏁
  
- **璇勪及鍥犵礌**锛6涓鍥犵礌锛屾潈閲嶅彲璋冿級:
  1. **鍓╀綑鐗屾暟鍥犵礌** (25%): 鑰冭檻鑷宸便侀槦鍙嬨佸规墜鐨勫墿浣欑墝鏁
  2. **鐗屽瀷澶у皬鍥犵礌** (20%): 璇勪及鐗屽瀷澶у皬鍜屽帇鍒惰兘鍔
  3. **閰嶅悎鍥犵礌** (20%): 璇勪及閰嶅悎鏈轰細鍜岄厤鍚堟晥鏋
  4. **椋庨櫓鍥犵礌** (15%): 璇勪及鍑虹墝椋庨櫓
  5. **鏃舵満鍥犵礌** (10%): 璇勪及娓告垙闃舵靛拰鏃舵満
  6. **鎵嬬墝缁撴瀯鍥犵礌** (10%): 璇勪及瀵规墜鐗岀粨鏋勭殑褰卞搷

- **鎺ュ彛璁捐**:
  ```python
  class MultiFactorEvaluator:
      def evaluate_action(self, action, action_index, cur_action, action_list) -> float
      def evaluate_all_actions(self, action_list, cur_action) -> List[Tuple[int, float]]
      def get_best_action(self, action_list, cur_action) -> int
      def update_weights(self, weights: Dict[str, float])
  ```

##### 3.3.2 绛栫暐璇勪及鍣 (StrategyEvaluator)
- **鍔熻兘**:
  - 璇勪及褰撳墠灞闈
  - 璇勪及鎵嬬墝浠峰
  - 璇勪及鍑虹墝椋庨櫓
  - 璇勪及閰嶅悎鏈轰細

##### 3.3.3 鍑虹墝鍐崇瓥鍣 (PlayDecisionMaker)
- **鍔熻兘**:
  - 鐢熸垚鍊欓夊嚭鐗屾柟妗
  - 璇勪及姣忎釜鏂规堢殑浠峰
  - 閫夋嫨鏈浼樺嚭鐗
  - 鍐冲畾鏄鍚﹁繃鐗 (PASS)
  - **涓诲姩/琚鍔ㄥ喅绛栧垎绂**:
    - `active_decision()`: 涓诲姩鍑虹墝鍐崇瓥锛堢巼鍏堝嚭鐗屾垨鎺ラ庯級
    - `passive_decision()`: 琚鍔ㄥ嚭鐗屽喅绛栵紙闇瑕佸帇鍒讹級

##### 3.3.4 閰嶅悎绛栫暐鍣 (CooperationStrategy)
- **鍔熻兘**:
  - 璇嗗埆闃熷弸鎰忓浘
  - 鍒ゆ柇鏄鍚﹂渶瑕侀厤鍚
  - 鍒跺畾閰嶅悎绛栫暐
  - 璇勪及閰嶅悎鏁堟灉
  
- **璇︾粏瀹炵幇**:
  - `should_support_teammate()`: 鍒ゆ柇鏄鍚﹀簲璇ラ厤鍚堥槦鍙嬶紙PASS璁╅槦鍙嬬户缁锛
  - `should_take_over()`: 鍒ゆ柇鏄鍚﹀簲璇ユ帴鏇块槦鍙
  - `evaluate_cooperation_opportunity()`: 璇勪及閰嶅悎鏈轰細
  - `get_cooperation_strategy()`: 鑾峰彇閰嶅悎绛栫暐寤鸿
  
- **閰嶅悎绛栫暐鍙傛暟**锛堝彲閰嶇疆锛:
  - `support_threshold`: 闃熷弸鐗屽瀷鍊奸槇鍊硷紙榛樿15锛
  - `danger_threshold`: 瀵规墜鍓╀綑鐗屾暟鍗遍櫓闃堝硷紙榛樿4锛
  - `max_val_threshold`: 鏈澶х墝鍊奸槇鍊硷紙榛樿14锛

##### 3.3.5 鍐崇瓥鏃堕棿鎺у埗鍣 (DecisionTimer) / 鑷閫傚簲鍐崇瓥鏃堕棿鎺у埗鍣 (AdaptiveDecisionTimer)
- **鍔熻兘**:
  - 璁剧疆鏈澶у喅绛栨椂闂达紙榛樿0.8绉掞級
  - 瓒呮椂妫娴嬪拰淇濇姢鏈哄埗
  - 娓愯繘寮忓喅绛栨敮鎸
  - 瑁呴グ鍣ㄦ敮鎸侊紙`@with_timeout`锛
  - **鑷閫傚簲鏃堕棿鍒嗛厤**锛堟柊澧烇級:
    - 鏍规嵁鍔ㄤ綔绌洪棿澶у皬鍔ㄦ佽皟鏁磋瘎浼版繁搴
    - 澶у姩浣滅┖闂达細鏇村氭椂闂寸敤浜庡揩閫熺瓫閫
    - 灏忓姩浣滅┖闂达細鏇村氭椂闂寸敤浜庣簿缁嗚瘎浼

- **鎺ュ彛璁捐**:
  ```python
  class AdaptiveDecisionTimer:
      def get_time_budget(self, action_count: int) -> Dict[str, float]
      def start(self)
      def check_timeout(self) -> bool
      def get_remaining_time(self) -> float
  ```

##### 3.3.6 鍔ㄤ綔绌洪棿浼樺寲鍣 (ActionSpaceOptimizer)
- **鍔熻兘**:
  - 鏍规嵁鍔ㄤ綔绌洪棿澶у皬鍔ㄦ佺瓫閫夊欓夊姩浣
  - 澶у姩浣滅┖闂达紙>100锛夛細蹇閫熺瓫閫塗op-K鍊欓
  - 灏忓姩浣滅┖闂达紙鈮100锛夛細绮剧粏璇勪及鎵鏈夊姩浣
  - 鎻愬崌鍐崇瓥鏁堢巼锛岄伩鍏嶅湪澶у姩浣滅┖闂翠笅璇勪及鎵鏈夊欓

- **璁捐℃濊矾**锛堝熼壌DanZero+璁烘枃锛:
  - 鎺艰泲娓告垙鍒濆嬬姸鎬佸彲鑳>5000鍚堟硶鍔ㄤ綔锛屽悗鏈熷彲鑳<50
  - 澶у姩浣滅┖闂撮渶瑕佸揩閫熺瓫閫夛紝灏忓姩浣滅┖闂村彲浠ョ簿缁嗚瘎浼
  - 浣跨敤鍚鍙戝紡瑙勫垯蹇閫熻瘎浼帮紝淇濈暀Top-K鍊欓

- **鎺ュ彛璁捐**:
  ```python
  class ActionSpaceOptimizer:
      def filter_actions(self, action_list: List, game_state: GameState) -> List
      def _fast_filter(self, action_list: List, game_state: GameState) -> List
      def _quick_evaluate(self, action: List, game_state: GameState) -> float
  ```

- **閰嶇疆鍙傛暟**:
  - `large_space_threshold`: 澶у姩浣滅┖闂撮槇鍊硷紙榛樿100锛
  - `candidate_ratio`: 鍊欓夊姩浣滄瘮渚嬶紙榛樿0.1锛屽嵆10%锛
  - `min_candidates`: 鏈灏忓欓夋暟閲忥紙榛樿10锛

##### 3.3.7 鍔ㄤ綔鐗瑰緛缂栫爜鍣 (ActionFeatureEncoder)
- **鍔熻兘**:
  - 灏嗗姩浣滅紪鐮佷负鐗瑰緛鍚戦噺
  - 鎻愬彇鍔ㄤ綔鐨勫叧閿鐗瑰緛锛堢墝鍨嬨佸ぇ灏忋佷富鐗屻佺櫨鎼鐗岀瓑锛
  - 鏀鎸佸揩閫熻瘎浼板拰鐩镐技搴﹁＄畻
  - 涓烘湭鏉ュ己鍖栧︿範闆嗘垚鍋氬噯澶

- **璁捐℃濊矾**锛堝熼壌DanZero+璁烘枃鐨凞MC鏂规硶锛:
  - DMC鏂规硶鍒╃敤鍔ㄤ綔鐗瑰緛杩涜屾棤鍋忎及璁
  - 缁撴瀯鍖栫壒寰佽〃绀烘彁鍗囪瘎浼版晥鐜
  - 鑰冭檻鎺艰泲鐗硅壊锛堣姳鑹查噸瑕佹с佺櫨鎼鐗屻佺骇鐗岋級

- **鐗瑰緛缁村害**:
  1. **鐗屽瀷绫诲瀷鐗瑰緛**锛圤ne-hot缂栫爜锛: Single/Pair/Trips/ThreePair/ThreeWithTwo/TwoTrips/Straight/StraightFlush/Bomb
  2. **鐗屽瀷澶у皬鐗瑰緛**: 褰掍竴鍖栫殑鐗屽瀷澶у皬鍊
  3. **涓荤墝鏁伴噺鐗瑰緛**: 浣跨敤鐨勪富鐗岋紙绾х墝锛夋暟閲
  4. **鐧炬惌鐗屾暟閲忕壒寰**: 浣跨敤鐨勭櫨鎼鐗岋紙绾㈠績绾х墝锛夋暟閲
  5. **鎵嬬墝缁撴瀯褰卞搷鐗瑰緛**: 鍑虹墝鍚庢墜鐗岀粨鏋勫彉鍖
  6. **鍘嬪埗鑳藉姏鐗瑰緛**: 瀵瑰綋鍓嶇墝鍨嬬殑鍘嬪埗鑳藉姏

- **鎺ュ彛璁捐**:
  ```python
  class ActionFeatureEncoder:
      def encode_action(self, action: List, game_state: GameState) -> np.ndarray
      def _encode_card_type(self, card_type: str) -> List[float]
      def _encode_rank(self, rank: str, cur_rank: str) -> float
      def _encode_special_cards(self, cards: List[str], game_state: GameState) -> List[float]
      def _encode_hand_structure_impact(self, action: List, game_state: GameState) -> List[float]
  ```

##### 3.3.8 鐘舵佺壒寰佺紪鐮佸櫒 (StateFeatureEncoder)
- **鍔熻兘**:
  - 灏嗘父鎴忕姸鎬佺紪鐮佷负鐗瑰緛鍚戦噺
  - 鎻愬彇鐘舵佺殑鍏抽敭淇℃伅锛堟墜鐗屻佸巻鍙层佺帺瀹剁姸鎬佺瓑锛
  - 鏀鎸佺姸鎬佺浉浼煎害璁＄畻鍜屾ā寮忚瘑鍒
  - 涓烘湭鏉ュ己鍖栧︿範闆嗘垚鍋氬噯澶

- **璁捐℃濊矾**锛堝熼壌DanZero+璁烘枃鐨勭壒寰佺紪鐮佹妧鏈锛:
  - 浣跨敤鐗瑰緛缂栫爜鎶鏈澶勭悊鐘舵佸拰鍔ㄤ綔
  - 鑰冭檻鑺辫壊閲嶈佹э紙鎺艰泲鐗硅壊锛
  - 澶勭悊鐧炬惌鐗屽拰绾х墝鐨勭壒娈婃
  - 缁撴瀯鍖栫姸鎬佽〃绀

- **鐗瑰緛缁村害**:
  1. **鎵嬬墝鐗瑰緛**锛27缁达級: 姣忓紶鐗岀殑瀛樺湪鎬э紙鑰冭檻鑺辫壊鍜岀偣鏁帮級
  2. **宸插嚭鐗屽巻鍙茬壒寰**: 鍚勭帺瀹跺嚭鐗屽巻鍙茬粺璁
  3. **鐜╁跺墿浣欑墝鏁扮壒寰**锛4缁达級: 姣忎釜鐜╁剁殑鍓╀綑鐗屾暟
  4. **褰撳墠鐗屽瀷鐗瑰緛**: 褰撳墠闇瑕佸帇鍒剁殑鐗屽瀷淇℃伅
  5. **娓告垙闃舵电壒寰**: 娓告垙闃舵碉紙beginning/play/tribute/back绛夛級
  6. **绾х墝鍜岀櫨鎼鐗岀壒寰**: 褰撳墠绾х墝鍜岀櫨鎼鐗屼俊鎭
  7. **閰嶅悎鐘舵佺壒寰**: 闃熷弸鐘舵併侀厤鍚堟満浼氱瓑

- **鎺ュ彛璁捐**:
  ```python
  class StateFeatureEncoder:
      def encode_state(self, game_state: GameState) -> np.ndarray
      def _encode_hand_cards(self, hand_cards: List[str], cur_rank: str) -> List[float]
      def _encode_play_history(self, history: Dict) -> List[float]
      def _encode_player_states(self, game_state: GameState) -> List[float]
      def _encode_current_action(self, cur_action: List) -> List[float]
      def _encode_game_phase(self, stage: str) -> List[float]
      def _encode_special_cards(self, game_state: GameState) -> List[float]
  ```

##### 3.3.9 鐗屽瀷涓撻棬澶勭悊鍣 (CardTypeHandlers)
- **鍔熻兘**:
  - 涓烘瘡绉嶇墝鍨嬪垱寤轰笓闂ㄧ殑澶勭悊绫
  - 瀹炵幇閽堝规х殑鍐崇瓥閫昏緫
  - 鏀鎸佷富鍔ㄥ拰琚鍔ㄤ袱绉嶅嚭鐗屾ā寮
  
- **宸插疄鐜扮殑澶勭悊鍣**:
  - `SingleHandler`: 鍗曞紶涓撻棬澶勭悊
  - `PairHandler`: 瀵瑰瓙涓撻棬澶勭悊
  - `TripsHandler`: 涓夊紶涓撻棬澶勭悊
  - `BombHandler`: 鐐稿脊涓撻棬澶勭悊
  - `StraightHandler`: 椤哄瓙涓撻棬澶勭悊
  
- **璁捐℃ā寮**:
  - 浣跨敤鎶借薄鍩虹被 `BaseCardTypeHandler` 瀹氫箟缁熶竴鎺ュ彛
  - 閫氳繃宸ュ巶妯″紡 `CardTypeHandlerFactory` 鑾峰彇澶勭悊鍣

#### 3.4 鐭ヨ瘑搴撴ā鍧 (Knowledge Base Module)

**涓庣煡璇嗗簱鏍煎紡鍖栨柟妗堝归綈**锛
- 鉁 鏈妯″潡璁捐′笌銆婄煡璇嗗簱鏍煎紡鍖栨柟妗.md銆嬪畬鍏ㄥ归綈
- 鉁 鐭ヨ瘑鍒嗙被浣撶郴瀵瑰簲鏍煎紡鍖栨柟妗堢殑涓绾у垎绫伙紙瑙勫垯/鍩虹/绛栫暐/鎶宸/蹇冪悊锛
- 鉁 鐩褰曠粨鏋勫瑰簲鏍煎紡鍖栨柟妗堢殑`docs/knowledge/`鐩褰曡捐
- 鉁 鍙橀噺鍛藉悕缁熶竴浣跨敤骞冲彴鏍囧噯鍙橀噺鍚嶏紙Single/Pair/Bomb绛夛級
- 鉁 鐭ヨ瘑妫绱㈡柟寮忓瑰簲鏍煎紡鍖栨柟妗堢殑鏌ヨ㈡帴鍙ｈ捐

##### 3.4.1 鐭ヨ瘑搴撴灦鏋勮捐

**鍒嗗眰璁板繂绛栫暐**锛堝熀浜庢ц兘鍜屼娇鐢ㄩ戠巼锛屽瑰簲鐭ヨ瘑搴撴牸寮忓寲鏂规堬級锛

1. **纭缂栫爜灞傦紙Hardcoded Rules锛**
   - **鍐呭**锛氬熀纭瑙勫垯锛堢墝鍨嬪畾涔夈佸帇鐗岃勫垯銆佸ぇ灏忓叧绯荤瓑锛
   - **瀹炵幇鏂瑰紡**锛氱洿鎺ュ啓鍦ㄤ唬鐮佷腑锛屼綔涓哄嚱鏁/绫绘柟娉
   - **璁块棶鏂瑰紡**锛歄(1)鐩存帴璋冪敤
   - **鏇存柊鏂瑰紡**锛氫唬鐮佷慨鏀
   - **绀轰緥**锛
     ```python
     class GameRules:
         CARD_TYPES = ['Single', 'Pair', 'Trips', ...]
         def can_beat(self, card1, card2): ...
         def is_valid_type(self, cards): ...
     ```

2. **鍐呭瓨鍔犺浇灞傦紙In-Memory Knowledge锛**
   - **鍐呭**锛氬父鐢ㄧ瓥鐣ュ拰鎶宸э紙缁勭墝鎶宸с侀厤鐏鍘熷垯銆佸父瑙佺瓥鐣ユā寮忥級
   - **瀹炵幇鏂瑰紡**锛氱▼搴忓惎鍔ㄦ椂鍔犺浇鍒板唴瀛橈紙瀛楀吀/瀵硅薄锛
   - **璁块棶鏂瑰紡**锛歄(1)鍐呭瓨璁块棶
   - **鏇存柊鏂瑰紡**锛氶噸鍚绋嬪簭鎴栫儹鏇存柊
   - **绀轰緥**锛
     ```python
     class KnowledgeBase:
         def __init__(self):
             self.grouping_priorities = self.load_grouping_rules()
             self.strategy_patterns = self.load_strategies()
     ```

3. **鎸夐渶鏌ヨ㈠眰锛圤n-Demand Query锛**
   - **鍐呭**锛氶珮绾ф妧宸у拰鐗规畩鎯呭喌锛堝嶆潅绛栫暐銆佽竟缂樻堜緥锛
   - **瀹炵幇鏂瑰紡**锛氶渶瑕佹椂鏌ヨ㈢煡璇嗗簱鏂囦欢锛岀粨鏋滅紦瀛
   - **璁块棶鏂瑰紡**锛氶栨O(n)鏌ヨ锛屽悗缁璒(1)缂撳瓨璁块棶
   - **鏇存柊鏂瑰紡**锛氱煡璇嗗簱鏂囦欢鏇存柊锛岀紦瀛樺け鏁
   - **绀轰緥**锛
     ```python
     class KnowledgeQuery:
         def __init__(self):
             self.cache = {}
         def query_advanced_skill(self, situation): ...
     ```

**鐭ヨ瘑搴撶洰褰曠粨鏋**锛堝归綈鐭ヨ瘑搴撴牸寮忓寲鏂规堬級锛
```
docs/knowledge/
鈹溾攢鈹 rules/              # 瑙勫垯鐭ヨ瘑锛堢‖缂栫爜灞傦級- 瀵瑰簲瑙勫垯搴擄紙鏈楂樺噯鍒欙級
鈹   鈹溾攢鈹 01_basic_rules/      # 鍩虹瑙勫垯锛堟暣鍚堜簡鍘焍asics鐩褰曠殑鍐呭癸級
鈹   鈹   鈹溾攢鈹 01_card_types.md          # 鐗屽瀷瀹氫箟
鈹   鈹   鈹溾攢鈹 01_card_types_guide.md    # 鐗屽瀷鎸囧崡
鈹   鈹   鈹溾攢鈹 02_card_distribution.md    # 鐗屽紶鍒嗛厤
鈹   鈹   鈹溾攢鈹 03_game_flow.md            # 娓告垙娴佺▼
鈹   鈹   鈹溾攢鈹 04_upgrade_rules.md        # 鍗囩骇瑙勫垯
鈹   鈹   鈹溾攢鈹 05_game_introduction.md    # 娓告垙浠嬬粛
鈹   鈹   鈹溾攢鈹 06_basic_concepts.md       # 鍩烘湰姒傚康
鈹   鈹   鈹溾攢鈹 07_quick_start.md          # 蹇閫熷叆闂
鈹   鈹   鈹溾攢鈹 08_basic_strategy.md       # 鍩虹绛栫暐
鈹   鈹   鈹斺攢鈹 09_practice_tips.md        # 缁冧範寤鸿
鈹   鈹溾攢鈹 02_competition_rules/ # 姣旇禌瑙勫垯
鈹   鈹斺攢鈹 03_advanced_rules/    # 杩涜础鎶ョ墝瑙勫垯
鈹斺攢鈹 skills/              # 鎶宸х煡璇嗭紙鎸夐渶鏌ヨ㈠眰锛- 瀵瑰簲鎶宸у簱
    鈹溾攢鈹 01_foundation/        # 鍩虹鎶宸
    鈹溾攢鈹 02_main_attack/       # 涓绘敾鎶宸
    鈹溾攢鈹 03_assist_attack/     # 鍔╂敾鎶宸
    鈹溾攢鈹 04_common_skills/     # 閫氱敤鎶宸
    鈹溾攢鈹 05_psychology/        # 蹇冪悊鐭ヨ瘑
    鈹溾攢鈹 06_advanced/          # 楂樼骇鎶宸
    鈹溾攢鈹 07_opening/          # 寮灞鎶宸
    鈹斺攢鈹 08_endgame/          # 娈嬪眬鎶宸
```

**璇存槑**锛
- `rules/` 瀵瑰簲"瑙勫垯搴 (Rules Library)"锛屽疄鐜颁负纭缂栫爜灞傦紝鏄瑙勫垯鐭ヨ瘑鐨勬渶楂樺噯鍒
- 鍘 `basics/` 鐩褰曞凡鏁村悎鍒 `rules/01_basic_rules/` 鐩褰曚腑锛屼笉鍐嶅崟鐙瀛樺湪
- `skills/` 瀵瑰簲"鎶宸у簱 (Skills Library)"锛屽疄鐜颁负鎸夐渶鏌ヨ㈠眰
- 绛栫暐鐭ヨ瘑锛圫trategy锛夊瑰簲"绛栫暐搴 (Strategy Library)"锛屽疄鐜颁负鍐呭瓨鍔犺浇灞傦紝閫氬父涓嶅瓨鍌ㄥ湪鏂囦欢绯荤粺涓锛岃屾槸绋嬪簭鍚鍔ㄦ椂浠庨厤缃鎴栦唬鐮佷腑鍔犺浇

##### 3.4.2 瑙勫垯搴 (Rules Library)

**鍔熻兘**锛
- 鐗屽瀷瀹氫箟鍜岃瘑鍒瑙勫垯锛坄Single`, `Pair`, `Trips`, `ThreePair`, `ThreeWithTwo`, `TwoTrips`, `Straight`, `StraightFlush`, `Bomb`锛
- 鍘嬬墝瑙勫垯鍜屽ぇ灏忓叧绯伙紙鍚岀墝鍨嬫瘮杈冦佺偢寮瑰帇鐗屻佸悓鑺遍『鍘嬬墝锛
- 杩涜础瑙勫垯鍜屽崌绾ц勫垯锛堟ｅ父杩涜础銆佸弻涓嬭繘璐°佸崌绾ф潯浠讹級
- 娓告垙娴佺▼瑙勫垯锛堝眬銆佸満銆佽疆鐨勫畾涔夛級

**瀹炵幇鏂瑰紡**锛氱‖缂栫爜鍒癭GameRules`绫讳腑

**鎺ュ彛璁捐**锛
```python
class GameRules:
    # 鐗屽瀷璇嗗埆
    def recognize_card_type(self, cards: List[str]) -> Tuple[str, str, List[str]]
    
    # 鍘嬬墝鍒ゆ柇
    def can_beat(self, action1: List, action2: List) -> bool
    
    # 鐗岀偣澶у皬姣旇緝
    def compare_rank(self, rank1: str, rank2: str, cur_rank: str) -> int
    
    # 杩涜础瑙勫垯
    def get_tribute_rules(self, order: List[int]) -> Dict
    
    # 鍗囩骇瑙勫垯
    def get_upgrade_rules(self, order: List[int]) -> int
```

##### 3.4.3 绛栫暐搴 (Strategy Library)

**鍔熻兘**锛
- 缁勭墝鎶宸у拰浼樺厛绾э紙鍚岃姳椤 > 鐐稿脊 > 椤哄瓙/涓夊甫浜岋級
- 甯哥敤绛栫暐妯″紡锛堜富鏀荤瓥鐣ャ佸姪鏀荤瓥鐣ワ級
- 寮灞銆佷腑灞銆佹畫灞绛栫暐
- 閰嶇伀鍘熷垯锛堝洓澶寸伀銆佸疁閰嶄腑灏忎笉閰嶅ぇ锛

**瀹炵幇鏂瑰紡**锛氬惎鍔ㄦ椂鍔犺浇鍒板唴瀛

**鎺ュ彛璁捐**锛
```python
class StrategyLibrary:
    def __init__(self):
        # 鍚鍔ㄦ椂鍔犺浇
        self.grouping_priorities = self.load_grouping_priorities()
        self.strategy_patterns = self.load_strategy_patterns()
    
    # 缁勭墝浼樺厛绾
    def get_grouping_priority(self) -> Dict[str, int]
    
    # 閰嶇伀鍘熷垯
    def get_bomb_grouping_rules(self) -> Dict
    
    # 绛栫暐妯″紡鍖归厤
    def match_strategy_pattern(self, situation: Dict) -> List[str]
```

**鍔犺浇鍐呭**锛
- 缁勭墝浼樺厛绾ц勫垯锛堝悓鑺遍『 > 鐐稿脊 > 椤哄瓙/涓夊甫浜岋級
- 閰嶇伀鍘熷垯锛堝洓澶寸伀銆佸疁閰嶄腑灏忎笉閰嶅ぇ銆佺牬浜岀偢寮逛笉鑳芥惌锛
- 鐧炬惌浣跨敤鍘熷垯锛堥勭暀3涓閰嶇櫨鎼銆佺櫨鎼閰3鏀惧悗鍘嬶級
- 鍘诲崟鍖栧師鍒欙紙鏃犺哄皬涓庡ぇ锛屽潥鎸佸幓鍗曞寲锛

##### 3.4.4 鎶宸у簱 (Skills Library)

**鍔熻兘**锛
- 楂樼骇鎶宸ф枃绔狅紙寮灞鎶宸с佹畫灞鎶宸с佸嶆潅绛栫暐锛
- 鐗规畩鎯呭喌澶勭悊锛堣竟缂樻堜緥銆佸嶆潅灞闈锛
- 澶嶆潅绛栫暐鍒嗘瀽锛堝氬洜绱犲喅绛栵級
- 鎸夐渶鏌ヨ㈠拰缂撳瓨

**瀹炵幇鏂瑰紡**锛氭寜闇鏌ヨ㈢煡璇嗗簱鏂囦欢锛岀粨鏋滅紦瀛

**瀵瑰簲鐭ヨ瘑搴撴牸寮忓寲鏂规**锛
- 瀵瑰簲鏍煎紡鍖栨柟妗堢殑"鎶宸х煡璇 (Skills)"鍜"蹇冪悊鐭ヨ瘑 (Psychology)"
- 鐭ヨ瘑搴撴枃浠跺瓨鍌ㄥ湪`docs/knowledge/skills/`鐩褰曚笅
- 鏂囦欢鏍煎紡閬靛惊鏍煎紡鍖栨柟妗堢殑Markdown妯℃澘锛堝惈YAML鍏冩暟鎹锛
- 鏀鎸佹寜娓告垙闃舵碉紙opening/midgame/endgame锛夎繃婊ゆ煡璇

**鎺ュ彛璁捐**锛
```python
class SkillsLibrary:
    def __init__(self, knowledge_base_path: str):
        self.kb_path = knowledge_base_path
        self.cache = {}
        self.index = self.build_index()  # 寤虹珛绱㈠紩
    
    # 鏌ヨ㈡妧宸
    def query_skill(self, situation: str, game_phase: str) -> Dict
    
    # 璇涔夋悳绱
    def semantic_search(self, query: str, limit: int = 5) -> List[Dict]
    
    # 缂撳瓨绠＄悊
    def get_cached(self, key: str) -> Optional[Dict]
    def cache_result(self, key: str, result: Dict)
```

**鏌ヨ㈢瓥鐣**锛
- 鏍规嵁娓告垙闃舵碉紙opening/midgame/endgame锛夎繃婊
- 鏍规嵁鏍囩撅紙tags锛夊尮閰
- 鏍规嵁浼樺厛绾э紙priority锛夋帓搴
- 缁撴灉缂撳瓨锛岄伩鍏嶉噸澶嶆煡璇

##### 3.4.5 鐭ヨ瘑妫绱㈠櫒 (Knowledge Retriever)

**鍔熻兘**锛
- 鐭ヨ瘑搴撴枃浠惰В鏋愶紙Markdown鏍煎紡锛孻AML鍏冩暟鎹锛
- 璇涔夋悳绱㈠拰鍖归厤锛堝叧閿璇嶃佹爣绛俱侀樁娈靛尮閰嶏級
- 缁撴灉缂撳瓨绠＄悊锛圠RU缂撳瓨锛岄伩鍏嶉噸澶嶆煡璇锛
- 鐭ヨ瘑鍏宠仈鏌ヨ锛堝墠缃鐭ヨ瘑銆佸悗缁鐭ヨ瘑銆佺浉鍏崇煡璇嗙偣锛

**瀵瑰簲鐭ヨ瘑搴撴牸寮忓寲鏂规**锛
- 瑙ｆ瀽鏍煎紡鍖栨柟妗堝畾涔夌殑Markdown鏂囨。锛堝惈YAML鍏冩暟鎹锛
- 鏀鎸佹寜鏍煎紡鍖栨柟妗堢殑鍒嗙被浣撶郴鏌ヨ锛圧ules/Basics/Skills/Psychology锛
- 鏀鎸佹寜鏍煎紡鍖栨柟妗堢殑鏍囩撅紙tags锛夊拰娓告垙闃舵碉紙game_phase锛夎繃婊
- 鏀鎸佹寜鏍煎紡鍖栨柟妗堢殑浼樺厛绾э紙priority锛夊拰闅惧害锛坉ifficulty锛夋帓搴

**鎺ュ彛璁捐**锛
```python
class KnowledgeRetriever:
    def __init__(self, knowledge_base_path: str):
        self.kb_path = knowledge_base_path
        self.cache = LRUCache(maxsize=100)
        self.index = self.build_index()
    
    # 瑙ｆ瀽鐭ヨ瘑搴撴枃浠
    def parse_knowledge_file(self, file_path: str) -> Dict
    
    # 寤虹珛绱㈠紩
    def build_index(self) -> Dict
    
    # 璇涔夋悳绱
    def search(self, query: str, filters: Dict = None) -> List[Dict]
    
    # 鎸夋爣绛炬煡璇
    def query_by_tags(self, tags: List[str]) -> List[Dict]
    
    # 鎸夐樁娈垫煡璇
    def query_by_phase(self, phase: str) -> List[Dict]
    
    # 鍏宠仈鏌ヨ
    def get_related_knowledge(self, knowledge_id: str) -> Dict
```

**鎬ц兘浼樺寲**锛
- 鍚鍔ㄦ椂寤虹珛绱㈠紩锛堥伩鍏嶆瘡娆℃煡璇㈤兘鎵鎻忔枃浠讹級
- LRU缂撳瓨锛堟渶杩戜娇鐢ㄧ殑鐭ヨ瘑浼樺厛锛
- 寮傛ユ煡璇锛堜笉闃诲炲喅绛栨祦绋嬶級
- 鎵归噺鍔犺浇锛堝父鐢ㄧ煡璇嗛勫姞杞斤級

##### 3.4.6 鐭ヨ瘑搴旂敤妗嗘灦 (Knowledge Application Framework)

**闂棰樿儗鏅**锛
鎴戜滑宸茬粡鏁寸悊浜17涓鐭ヨ瘑鏂囦欢锛屽寘鍚绾850涓鐭ヨ瘑鐐癸紙鏍稿績鍘熷垯50鏉°佺瓥鐣ヨ勫垯200鏉°佹妧宸ц佺偣500鏉°佹堜緥绀轰緥100涓锛夈傝繖浜涚煡璇嗗傛灉鐔熺粌杩愮敤锛屽彲浠ユ墦璐85%浠ヤ笂鐨勫规墜銆備絾闂棰樻槸锛**杩欎箞澶氱煡璇嗭紝鎺艰泲AI鎬庝箞鐔熺粌鎺屾彙鍛锛**

**鐭ヨ瘑瑙勬ā缁熻**锛
- **宸叉牸寮忓寲鐭ヨ瘑鏂囦欢**锛17涓
  - 鍩虹绫伙細2涓锛堝師鍒欍佹垬鐣ワ級
  - 涓绘敾绫伙細1涓锛堢偢寮规妧宸э級
  - 鍔╂敾绫伙細1涓锛堜紶鐗屾妧宸э級
  - 閫氱敤鎶宸х被锛11涓锛堝瑰瓙銆佺墝璇銆佺浉鐢熺浉鍏嬨佺畻鐗屻佽扮墝銆佺孩妗冮厤銆侀挗鏉裤侀『瀛愩佷笁杩炲广佷笁甯︿簩銆佷笁寮狅級
  - 寮灞绫伙細2涓锛堥栧彂瑙ｈ汇佺粍鐗屾妧宸э級
- **鐭ヨ瘑鐐规暟閲**锛氱害850涓
  - 鏍稿績鍘熷垯锛氱害50鏉
  - 绛栫暐瑙勫垯锛氱害200鏉
  - 鎶宸ц佺偣锛氱害500鏉
  - 妗堜緥绀轰緥锛氱害100涓

**鐭ヨ瘑灞傛＄粨鏋**锛堝瑰簲鍒嗗眰璁板繂绛栫暐锛夛細

```
鐭ヨ瘑灞傛
鈹溾攢鈹 L1: 纭缂栫爜瑙勫垯锛堝繀椤婚伒瀹堬級- 瀵瑰簲纭缂栫爜灞
鈹   鈹溾攢鈹 娓告垙瑙勫垯锛堝嚭鐗岃勫垯銆佺墝鍨嬪畾涔夛級
鈹   鈹溾攢鈹 骞冲彴鎺ュ彛瑙勮寖
鈹   鈹斺攢鈹 鍩虹绾︽潫锛堝"鐏涓嶆墦鍥"銆"杩涜础鎱庡嚭鍗"锛
鈹
鈹溾攢鈹 L2: 鏍稿績绛栫暐锛堥珮棰戜娇鐢锛- 瀵瑰簲鍐呭瓨鍔犺浇灞
鈹   鈹溾攢鈹 缁勭墝鍘熷垯锛堢偢寮硅秺澶氳秺濂斤紝鍗曠墝瓒婂皯瓒婂ソ锛
鈹   鈹溾攢鈹 瑙掕壊瀹氫綅锛堜富鏀/鍔╂敾鍒ゆ柇锛
鈹   鈹斺攢鈹 鐗屽姏璇勪及锛8鍒嗕互涓婁富鏀伙紝2-4鍒嗗姪鏀伙級
鈹
鈹溾攢鈹 L3: 鍦烘櫙绛栫暐锛堟寜闇鍖归厤锛- 瀵瑰簲鎸夐渶鏌ヨ㈠眰
鈹   鈹溾攢鈹 寮灞绛栫暐锛堥栧彂瑙ｈ汇佺粍鐗屾妧宸э級
鈹   鈹溾攢鈹 涓灞绛栫暐锛堢浉鐢熺浉鍏嬨佺畻鐗岃扮墝锛
鈹   鈹斺攢鈹 娈嬪眬绛栫暐锛堜紶鐗屾妧宸с佸嚭鐐告妧宸э級
鈹
鈹斺攢鈹 L4: 楂樼骇鎶宸э紙娣卞害搴旂敤锛- 瀵瑰簲鎸夐渶鏌ヨ㈠眰
    鈹溾攢鈹 鐗岃瑙ｈ伙紙鍒ゆ柇瀵规墜鐗屽姏锛
    鈹溾攢鈹 鐩哥敓鐩稿厠锛堝弽鎵撶瓥鐣ワ級
    鈹斺攢鈹 蹇冪悊鎴樻湳锛堣遍獥銆佸畧鏍寰呭厰锛
```

**鐭ヨ瘑搴旂敤鏂规堬細鍒嗗眰鍐崇瓥绯荤粺**

**鏍稿績鎬濇兂**锛氬皢鐭ヨ瘑鍒嗗眰锛屼笉鍚屽眰娆￠噰鐢ㄤ笉鍚岀殑搴旂敤鏂瑰紡銆

**1. 纭缂栫爜灞傦紙L1瑙勫垯锛**

**瀹炵幇鏂瑰紡**锛氱洿鎺ュ啓鍦ㄤ唬鐮佷腑锛屼綔涓哄熀纭绾︽潫銆

```python
# src/core/game_rules.py
class GameRules:
    """纭缂栫爜鐨勬父鎴忚勫垯"""
    
    # 鍩虹瑙勫垯
    MAX_HAND_CARDS = 27
    MIN_STRAIGHT_LENGTH = 5
    MIN_BOMB_COUNT = 4
    
    # 楂樺帇绾胯勫垯锛堝繀椤婚伒瀹堬級
    def check_high_voltage_rules(self, action, game_state):
        """妫鏌ヤ簲鏉￠珮鍘嬬嚎"""
        # 1. 杩涜础鎱庡嚭鍗
        if game_state.stage == "tribute" and action.type == "Single":
            return False, "杩涜础鎱庡嚭鍗"
        
        # 2. 鐏涓嶆墦鍥
        if opponent_remain == 4 and action.type == "Bomb":
            return False, "鐏涓嶆墦鍥"
        
        # 3. 灏介噺閬垮厤涓鎵撲簩
        # 4. 涓嶆墦璧屾皵鐗
        # 5. 椤哄瓙鎱庡嬪彂
        return True, None
```

**鐗圭偣**锛
- 鉁 鎵ц屾晥鐜囨渶楂橈紙O(1)锛
- 鉁 100%鍑嗙‘锛屼笉浼氬嚭閿
- 鉁 浣滀负鎵鏈夊喅绛栫殑鍩虹绾︽潫

**2. 绛栫暐寮曟搸灞傦紙L2鏍稿績绛栫暐锛**

**瀹炵幇鏂瑰紡**锛氬惎鍔ㄦ椂鍔犺浇鍒板唴瀛橈紝鏋勫缓鍐崇瓥鏍戙

```python
# src/core/strategy_engine.py
class StrategyEngine:
    """绛栫暐寮曟搸 - 鏍稿績绛栫暐鍐崇瓥"""
    
    def __init__(self):
        # 鍚鍔ㄦ椂鍔犺浇鏍稿績绛栫暐
        self.card_grouping_rules = self._load_card_grouping_rules()
        self.role_determination = self._load_role_determination()
        self.bomb_strategy = self._load_bomb_strategy()
    
    def determine_role(self, handcards, game_state):
        """瑙掕壊瀹氫綅锛氫富鏀/鍔╂敾"""
        score = self._calculate_power_score(handcards)
        
        if score >= 8:
            return "涓绘敾"
        elif score >= 5:
            return "鏀诲畧鍏煎"
        elif score >= 2:
            return "鍔╂敾"
        else:
            return "鏈娓"
    
    def group_cards(self, handcards, role):
        """缁勭墝鍐崇瓥"""
        # 搴旂敤"鐐稿脊瓒婂氳秺濂斤紝鍗曠墝瓒婂皯瓒婂ソ"鍘熷垯
        # 搴旂敤"杞娆′紭鍏"鍘熷垯
        # 鏍规嵁瑙掕壊璋冩暣绛栫暐
        pass
```

**鐗圭偣**锛
- 鉁 鍚鍔ㄦ椂鍔犺浇锛屽唴瀛樿块棶锛圤(1)锛
- 鉁 鏀鎸佺儹鏇存柊
- 鉁 鏍稿績绛栫暐蹇閫熷喅绛

**3. 鐭ヨ瘑妫绱㈠眰锛圠3鍦烘櫙绛栫暐锛**

**瀹炵幇鏂瑰紡**锛氭寜闇鏌ヨ㈢煡璇嗗簱锛岀粨鏋滅紦瀛樸

```python
# src/core/knowledge_retriever.py
class KnowledgeRetriever:
    """鐭ヨ瘑妫绱㈠櫒 - 鎸夐渶鏌ヨ㈢煡璇嗗簱"""
    
    def __init__(self):
        self.cache = {}  # 鏌ヨ㈢粨鏋滅紦瀛
        self.knowledge_index = self._build_index()
    
    def get_relevant_knowledge(self, situation):
        """鏍规嵁褰撳墠灞闈㈡绱㈢浉鍏崇煡璇"""
        # 1. 鏋勫缓鏌ヨ㈠叧閿璇
        keywords = self._extract_keywords(situation)
        # 鍏抽敭璇嶇ず渚嬶細["娈嬪眬", "瀵瑰跺墿5寮", "涓夊甫浜"]
        
        # 2. 妫绱㈢煡璇嗗簱
        knowledge = self._search_knowledge(keywords)
        
        # 3. 缂撳瓨缁撴灉
        cache_key = self._build_cache_key(situation)
        self.cache[cache_key] = knowledge
        
        return knowledge
    
    def _search_knowledge(self, keywords):
        """鎼滅储鐭ヨ瘑搴"""
        # 浣跨敤璇涔夋悳绱㈡垨鍏抽敭璇嶅尮閰
        # 杩斿洖鐩稿叧鐨勭煡璇嗙墖娈
        results = []
        
        # 绀轰緥锛氭悳绱"娈嬪眬浼犵墝"鐩稿叧鐭ヨ瘑
        if "娈嬪眬" in keywords and "浼犵墝" in keywords:
            results.append(self._load_knowledge("skills/03_assist_attack/01_passing_skills.md"))
        
        return results
```

**鐗圭偣**锛
- 鉁 鎸夐渶鍔犺浇锛岃妭鐪佸唴瀛
- 鉁 鏀鎸佽涔夋悳绱
- 鉁 缁撴灉缂撳瓨锛屾彁楂樻晥鐜

**4. 鎺ㄧ悊搴旂敤灞傦紙L4楂樼骇鎶宸э級**

**瀹炵幇鏂瑰紡**锛氱粨鍚堝眬闈㈠垎鏋愶紝搴旂敤楂樼骇鎶宸с

```python
# src/core/advanced_reasoning.py
class AdvancedReasoning:
    """楂樼骇鎺ㄧ悊 - 搴旂敤楂樼骇鎶宸"""
    
    def analyze_card_language(self, opponent_actions):
        """鐗岃鍒嗘瀽"""
        # 鍒嗘瀽瀵规墜鍑虹墝锛屽垽鏂鐗屽姏
        if opponent_actions[0].type == "Single" and opponent_actions[0].rank < "T":
            return {
                "card_power": "寮",
                "intent": "鎯冲綋涓婃父",
                "suggestion": "閰嶅悎璁╅槦鍙嬩簤澶存父"
            }
    
    def apply_interaction_rules(self, my_cards, opponent_cards):
        """搴旂敤鐩哥敓鐩稿厠瑙勫垯"""
        # 鍒ゆ柇鐗屽瀷鐩哥敓鐩稿厠鍏崇郴
        if self._has_many_straight(my_cards):
            # 椤哄瓙澶氾紝鍒3+2鍙鑳藉皯
            return "瀵规墜鍙鑳芥病鏈変笁甯︿簩"
        
        if self._has_many_three_with_two(my_cards):
            # 3+2澶氾紝鍒欓『瀛愬彲鑳藉皯
            return "瀵规墜鍙鑳芥病鏈夐『瀛"
```

**鐗圭偣**锛
- 鉁 娣卞害鍒嗘瀽锛岀伒娲诲簲鐢
- 鉁 缁撳悎灞闈㈠姩鎬佹帹鐞
- 鉁 鏀鎸佸嶆潅绛栫暐缁勫悎

**鐭ヨ瘑搴旂敤娴佺▼**锛

```python
# src/core/ai_decision_maker.py
class AIDecisionMaker:
    """AI鍐崇瓥鍣 - 鏁村悎鎵鏈夌煡璇"""
    
    def make_decision(self, game_state):
        """瀹屾暣鍐崇瓥娴佺▼"""
        
        # 1. 纭缂栫爜瑙勫垯妫鏌ワ紙L1锛
        valid_actions = self.game_rules.filter_valid_actions(
            game_state.available_actions
        )
        
        # 2. 鏍稿績绛栫暐鍐崇瓥锛圠2锛
        role = self.strategy_engine.determine_role(
            game_state.handcards, game_state
        )
        grouped_cards = self.strategy_engine.group_cards(
            game_state.handcards, role
        )
        
        # 3. 鍦烘櫙绛栫暐鍖归厤锛圠3锛
        situation = self._analyze_situation(game_state)
        relevant_knowledge = self.knowledge_retriever.get_relevant_knowledge(
            situation
        )
        
        # 4. 楂樼骇鎶宸у簲鐢锛圠4锛
        if situation["phase"] == "endgame":
            # 搴旂敤娈嬪眬鎶宸
            advanced_strategy = self.advanced_reasoning.analyze_endgame(
                game_state
            )
        
        # 5. 缁煎悎鍐崇瓥
        best_action = self._evaluate_actions(
            valid_actions,
            role,
            relevant_knowledge,
            advanced_strategy
        )
        
        return best_action
```

**鐭ヨ瘑搴旂敤绀轰緥**锛

**绀轰緥1锛氬紑灞缁勭墝鍐崇瓥**
```python
def group_cards_decision(handcards, game_state):
    """缁勭墝鍐崇瓥绀轰緥"""
    
    # 1. 纭缂栫爜瑙勫垯锛氭鏌ョ墝鍨嬪悎娉曟
    if not is_valid_card_combination(handcards):
        return None
    
    # 2. 鏍稿績绛栫暐锛氳＄畻鐗屽姏锛岀‘瀹氳掕壊
    power_score = calculate_power_score(handcards)
    role = "涓绘敾" if power_score >= 8 else "鍔╂敾"
    
    # 3. 搴旂敤缁勭墝鍘熷垯
    # "鐐稿脊瓒婂氳秺濂斤紝鍗曠墝瓒婂皯瓒婂ソ"
    grouped = optimize_card_grouping(
        handcards,
        principle="bomb_max_single_min"
    )
    
    # 4. 妫绱㈢浉鍏崇煡璇
    knowledge = knowledge_retriever.get_knowledge(
        keywords=["缁勭墝", "寮灞", role]
    )
    
    # 5. 搴旂敤鐭ヨ瘑
    # "缁勯『鐢熶袱鍗曪紝鑲瀹氭病鐪煎厜"
    if will_create_two_singles(grouped):
        grouped = avoid_creating_singles(grouped)
    
    return grouped
```

**绀轰緥2锛氭畫灞浼犵墝鍐崇瓥**
```python
def endgame_passing_decision(game_state):
    """娈嬪眬浼犵墝鍐崇瓥绀轰緥"""
    
    # 1. 鍒ゆ柇鍦烘櫙
    if game_state.partner_remain == 5:
        # 2. 妫绱㈢浉鍏崇煡璇
        knowledge = knowledge_retriever.get_knowledge(
            keywords=["娈嬪眬", "浼犵墝", "瀵瑰跺墿5寮"]
        )
        
        # 3. 搴旂敤鐭ヨ瘑
        # "瀵瑰跺墿浜斿紶锛屾槑鏄炬槸3+2"
        if is_likely_three_with_two(game_state.partner_history):
            # "閫佷笁甯︿簩"
            return find_three_with_two_to_pass(game_state.handcards)
        elif is_likely_straight(game_state.partner_history):
            # "閫侀『瀛"
            return find_straight_to_pass(game_state.handcards)
    
    return None
```

**鐭ヨ瘑妫绱浼樺寲**锛

**1. 绱㈠紩鏋勫缓**
```python
# 鏋勫缓鐭ヨ瘑绱㈠紩锛屾彁楂樻绱㈡晥鐜
knowledge_index = {
    "鍏抽敭璇": ["鐭ヨ瘑鏂囦欢璺寰"],
    "娈嬪眬": ["skills/03_assist_attack/01_passing_skills.md", ...],
    "浼犵墝": ["skills/03_assist_attack/01_passing_skills.md", ...],
    "瀵瑰跺墿5寮": ["skills/03_assist_attack/01_passing_skills.md", ...]
}
```

**2. 缂撳瓨绛栫暐**
```python
# 缂撳瓨甯哥敤鐭ヨ瘑锛岄伩鍏嶉噸澶嶆煡璇
cache = {
    "娈嬪眬_瀵瑰跺墿5寮燺涓夊甫浜": {
        "knowledge": "...",
        "timestamp": "...",
        "hit_count": 10
    }
}
```

**3. 浼樺厛绾ф帓搴**
```python
# 鏍规嵁鐭ヨ瘑浼樺厛绾ф帓搴
def sort_knowledge_by_priority(knowledge_list):
    """鎸変紭鍏堢骇鎺掑簭"""
    priority_map = {
        "楂樺帇绾胯勫垯": 10,  # 鏈楂樹紭鍏堢骇
        "鏍稿績绛栫暐": 8,
        "鍦烘櫙绛栫暐": 6,
        "楂樼骇鎶宸": 4
    }
    return sorted(knowledge_list, key=lambda k: priority_map.get(k.priority, 0))
```

**鐭ヨ瘑鎺屾彙绋嬪害璇勪及**锛

**1. 鐭ヨ瘑瑕嗙洊鐜**
```python
def calculate_knowledge_coverage(ai_actions, knowledge_base):
    """璁＄畻鐭ヨ瘑瑕嗙洊鐜"""
    applied_knowledge = set()
    total_knowledge = len(knowledge_base)
    
    for action in ai_actions:
        # 妫鏌ュ簲鐢ㄤ簡鍝浜涚煡璇
        knowledge_used = identify_applied_knowledge(action)
        applied_knowledge.update(knowledge_used)
    
    coverage = len(applied_knowledge) / total_knowledge
    return coverage
```

**2. 鍐崇瓥鍑嗙‘鐜**
```python
def evaluate_decision_accuracy(ai_decisions, expert_decisions):
    """璇勪及鍐崇瓥鍑嗙‘鐜"""
    correct = 0
    total = len(ai_decisions)
    
    for ai_decision, expert_decision in zip(ai_decisions, expert_decisions):
        if ai_decision == expert_decision:
            correct += 1
    
    accuracy = correct / total
    return accuracy
```

**3. 鑳滅巼鎻愬崌**
```python
def measure_win_rate_improvement(baseline_ai, knowledge_ai):
    """娴嬮噺鑳滅巼鎻愬崌"""
    baseline_win_rate = test_ai(baseline_ai, num_games=1000)
    knowledge_win_rate = test_ai(knowledge_ai, num_games=1000)
    
    improvement = knowledge_win_rate - baseline_win_rate
    return improvement
```

**棰勬湡鏁堟灉**锛
- **闃舵典竴**锛堝熀纭瑙勫垯寮曟搸锛夛細鑳滅巼 40-50%
- **闃舵典簩**锛堝姞鍏ョ煡璇嗘绱锛夛細鑳滅巼 55-65%
- **闃舵典笁**锛堝姞鍏ラ珮绾ф帹鐞嗭級锛氳儨鐜 70-80%
- **闃舵靛洓**锛堟寔缁浼樺寲锛夛細鑳滅巼 85%+

**鍏抽敭鎴愬姛鍥犵礌**锛
1. 鉁 鐭ヨ瘑缁撴瀯鍖栵紙宸插畬鎴愶級
2. 鉁 鐭ヨ瘑绱㈠紩鏋勫缓锛堝緟瀹炵幇锛
3. 鉁 鍐崇瓥绯荤粺璁捐★紙寰呭疄鐜帮級
4. 鉁 鐭ヨ瘑搴旂敤娴佺▼锛堝緟瀹炵幇锛
5. 鉁 鎸佺画浼樺寲鏈哄埗锛堝緟瀹炵幇锛

**AI鎺屾彙鐭ヨ瘑鐨勬牳蹇冩柟娉**锛
1. **鍒嗗眰搴旂敤**锛氫笉鍚屽眰娆＄殑鐭ヨ瘑閲囩敤涓嶅悓鐨勫簲鐢ㄦ柟寮
   - 纭缂栫爜灞傦細鐩存帴鍐欏湪浠ｇ爜涓
   - 绛栫暐寮曟搸灞傦細鍚鍔ㄦ椂鍔犺浇鍒板唴瀛
   - 鐭ヨ瘑妫绱㈠眰锛氭寜闇鏌ヨ锛岀粨鏋滅紦瀛
   - 鎺ㄧ悊搴旂敤灞傦細娣卞害鍒嗘瀽锛岀伒娲诲簲鐢
2. **蹇閫熸绱**锛氭瀯寤虹煡璇嗙储寮曪紝鏀鎸佸叧閿璇嶅拰璇涔夋悳绱
3. **鏅鸿兘鍖归厤**锛氭牴鎹褰撳墠灞闈锛岃嚜鍔ㄥ尮閰嶇浉鍏崇煡璇
4. **浼樺厛绾х＄悊**锛氱煡璇嗘湁浼樺厛绾э紝楂樹紭鍏堢骇鐭ヨ瘑浼樺厛搴旂敤
5. **鎸佺画浼樺寲**锛氶氳繃瀵瑰眬鏁版嵁鍒嗘瀽锛屼笉鏂浼樺寲鐭ヨ瘑搴旂敤

閫氳繃杩欎釜妗嗘灦锛孉I鍙浠ョ郴缁熷寲鍦版帉鎻″拰搴旂敤杩850+涓鐭ヨ瘑鐐癸紝閫愭ユ彁鍗囧埌鑳藉熸墦璐85%浠ヤ笂瀵规墜鐨勬按骞炽

#### 3.5 鏁版嵁鏀堕泦妯″潡 (Data Collection Module)

##### 3.4.1 瀵瑰眬璁板綍鍣 (GameRecorder)
- **鍔熻兘**:
  - 璁板綍瀹屾暣瀵瑰眬杩囩▼
  - 淇濆瓨JSON鏍煎紡鏁版嵁
  - 璁板綍鍐崇瓥杩囩▼
  - 璁板綍鑳滆礋缁撴灉

##### 3.4.2 鏁版嵁瀛樺偍 (DataStorage)
- **鍔熻兘**:
  - 淇濆瓨瀵瑰眬鏂囦欢
  - 鏁版嵁鏍煎紡鏍囧噯鍖
  - 鏁版嵁绱㈠紩绠＄悊
  - 鏁版嵁缁熻″垎鏋

#### 3.6 淇℃伅鐩戞帶妯″潡 (Info Monitor Module)

##### 3.5.1 骞冲彴淇℃伅鎶撳彇鍣 (PlatformInfoFetcher)
- **鍔熻兘**:
  - 瀹氭湡璁块棶骞冲彴缃戠珯
  - 鎶撳彇骞冲彴鍔ㄦ佷俊鎭
  - 鎶撳彇姣旇禌鐩稿叧娑堟伅
  - 妫娴嬪钩鍙扮増鏈鏇存柊
  - 妫娴嬫枃妗ｆ洿鏂

- **鎶撳彇鍐呭**:
  - 骞冲彴鍏鍛婂拰閫氱煡
  - 姣旇禌淇℃伅锛堟姤鍚嶆椂闂淬佹瘮璧涙椂闂寸瓑锛
  - 骞冲彴鐗堟湰鏇存柊
  - 鏂囨。鏇存柊锛堜娇鐢ㄨ存槑涔︾瓑锛
  - 閲嶈侀氱煡鍜岃勫垯鍙樻洿

- **鎶鏈瀹炵幇**:
  - HTTP璇锋眰鑾峰彇缃戦〉鍐呭
  - HTML瑙ｆ瀽鎻愬彇鍏抽敭淇℃伅
  - 鍐呭瑰彉鍖栨娴
  - 瀹氭椂浠诲姟璋冨害

- **鎺ュ彛璁捐**:
  ```python
  class PlatformInfoFetcher:
      - fetch_platform_info() -> dict
      - check_updates() -> List[UpdateInfo]
      - get_competition_info() -> dict
      - get_announcements() -> List[Announcement]
      - is_quiet_hours() -> bool  # 妫鏌ユ槸鍚﹀湪闈欓粯鏃舵
      - start_monitoring(interval: int, quiet_hours: dict)
      - stop_monitoring()
      - schedule_next_check() -> datetime  # 璁＄畻涓嬫℃鏌ユ椂闂达紙閬垮紑闈欓粯鏃舵碉級
  ```

##### 3.5.2 淇℃伅瑙ｆ瀽鍣 (InfoParser)
- **鍔熻兘**:
  - 瑙ｆ瀽HTML鍐呭
  - 鎻愬彇鍏抽敭淇℃伅
  - 璇嗗埆淇℃伅绫诲瀷锛堝叕鍛/姣旇禌/鏇存柊绛夛級
  - 鏍煎紡鍖栦俊鎭鍐呭

- **瑙ｆ瀽绛栫暐**:
  - 鍩轰簬HTML鏍囩剧粨鏋勮В鏋
  - 鍏抽敭璇嶅尮閰嶈瘑鍒閲嶈佷俊鎭
  - 鏃堕棿淇℃伅鎻愬彇
  - 閾炬帴鍜岄檮浠舵彁鍙

##### 3.5.3 淇℃伅瀛樺偍 (InfoStorage)
- **鍔熻兘**:
  - 瀛樺偍鎶撳彇鐨勪俊鎭
  - 璁板綍淇℃伅鏃堕棿鎴
  - 鍘婚噸澶勭悊
  - 淇℃伅鍘嗗彶璁板綍

- **鏁版嵁缁撴瀯**:
  - 淇℃伅ID
  - 淇℃伅绫诲瀷
  - 鏍囬樺拰鍐呭
  - 鍙戝竷鏃堕棿
  - 鎶撳彇鏃堕棿
  - 鏄鍚﹀凡璇

##### 3.5.4 閫氱煡绠＄悊鍣 (NotificationManager)
- **鍔熻兘**:
  - 妫娴嬫柊淇℃伅
  - 鍙戦侀氱煡鎻愰啋
  - 鏀鎸佸氱嶉氱煡鏂瑰紡
  - 閫氱煡浼樺厛绾х＄悊

- **閫氱煡鏂瑰紡**:
  - 鎺у埗鍙拌緭鍑
  - 鏃ュ織璁板綍
  - 妗岄潰閫氱煡锛堝彲閫夛級
  - 閭浠堕氱煡锛堝彲閫夛級
  - 鏂囦欢淇濆瓨

- **閫氱煡鍐呭**:
  - 鏂板叕鍛
  - 姣旇禌淇℃伅
  - 骞冲彴鏇存柊
  - 閲嶈佽勫垯鍙樻洿

### 鍥涖佹暟鎹缁撴瀯璁捐

#### 4.1 鍗＄墝琛ㄧず
```python
Card:
    - suit: str  # 鑺辫壊 (S/H/D/C/R/B) - 骞冲彴鏍囧噯
    - rank: str  # 鐐规暟 (A/2-9/T/J/Q/K/B/R) - 骞冲彴鏍囧噯
    - is_main: bool  # 鏄鍚︿负涓荤墝 (curRank)
```

#### 4.2 鐗屽瀷琛ㄧず
```python
CardType:
    - type: str  # 鐗屽瀷绫诲瀷 (Single/Pair/Trips/ThreePair/ThreeWithTwo/TwoTrips/Straight/StraightFlush/Bomb/tribute/back/PASS) - 骞冲彴鏍囧噯
    - cards: List[Card]  # 鐗屽垪琛 (handCards鏍煎紡)
    - main_rank: str  # 涓荤墝绾у埆 (curRank)
```

#### 4.3 娓告垙鐘舵
```python
GameState:
    - my_hand: List[Card]  # 鎴戠殑鎵嬬墝 (handCards)
    - played_cards: List[CardType]  # 宸插嚭鐗 (actionList)
    - current_player: int  # 褰撳墠鐜╁ (curPos, 0-3)
    - current_card_type: CardType  # 褰撳墠鐗屽瀷 (curAction)
    - teammate_seat: int  # 闃熷弸搴т綅 (myPos瀵瑰簲: 0-2, 1-3)
    - game_phase: str  # 娓告垙闃舵 (stage: beginning/play/tribute/back/episodeOver/gameOver)
```

#### 4.4 骞冲彴淇℃伅
```python
PlatformInfo:
    - id: str  # 淇℃伅ID
    - type: str  # 淇℃伅绫诲瀷锛坅nnouncement/competition/update锛
    - title: str  # 鏍囬
    - content: str  # 鍐呭
    - publish_time: datetime  # 鍙戝竷鏃堕棿
    - fetch_time: datetime  # 鎶撳彇鏃堕棿
    - url: str  # 鍘熸枃閾炬帴
    - is_read: bool  # 鏄鍚﹀凡璇
    - priority: int  # 浼樺厛绾

UpdateInfo:
    - version: str  # 鐗堟湰鍙 (e.g., v1006)
    - update_time: datetime  # 鏇存柊鏃堕棿
    - changelog: str  # 鏇存柊鏃ュ織
    - download_url: str  # 涓嬭浇閾炬帴

CompetitionInfo:
    - name: str  # 姣旇禌鍚嶇О
    - registration_start: datetime  # 鎶ュ悕寮濮嬫椂闂
    - registration_end: datetime  # 鎶ュ悕缁撴潫鏃堕棿
    - competition_start: datetime  # 姣旇禌寮濮嬫椂闂
    - competition_end: datetime  # 姣旇禌缁撴潫鏃堕棿
    - description: str  # 姣旇禌鎻忚堪
    - requirements: str  # 鍙傝禌瑕佹眰
```

### 浜斻佹秷鎭娴佺▼璁捐

#### 5.1 杩炴帴娴佺▼
```
1. 寤虹珛WebSocket杩炴帴
   - 鏈鍦帮細ws://127.0.0.1:23456/game/{user_info}
   - 灞鍩熺綉锛歸s://[IP]:23456/game/{user_info}
2. 鍙戦佺敤鎴蜂俊鎭 (type: notify)
3. 绛夊緟娓告垙寮濮嬫秷鎭 (stage: beginning)
4. 璇嗗埆闃熷弸锛堟牴鎹杩炴帴椤哄簭锛1-3涓闃 (myPos 0-2)锛2-4涓闃 (myPos 1-3)锛
5. 杩涘叆娓告垙寰鐜 (stage: play)
```

#### 5.2 娓告垙娴佺▼
```
1. 鎺ユ敹鍙戠墝娑堟伅 鈫 鏇存柊鎵嬬墝 (handCards)
2. 鎺ユ敹鍑虹墝璇锋眰 鈫 鍐崇瓥鍑虹墝 鈫 鍙戦佸嚭鐗屾秷鎭 (type: act, curAction)
3. 鎺ユ敹鍏朵粬鐜╁跺嚭鐗 鈫 鏇存柊娓告垙鐘舵 (actionList)
4. 鎺ユ敹娓告垙缁撴潫娑堟伅 鈫 淇濆瓨瀵瑰眬鏁版嵁 (stage: gameOver)
```

#### 5.3 瀹屾暣鏁版嵁娴佽捐

**鏁版嵁娴佸浘**:
```
WebSocket娑堟伅鎺ユ敹
    鈫
娑堟伅瑙ｆ瀽 (JSON)
    鈫
鐘舵佹洿鏂 (EnhancedGameStateManager.update_from_message)
    鈹溾攢> 鏇存柊鍩虹鐘舵 (myPos, handCards, curPos, etc.)
    鈹溾攢> 鏇存柊璁扮墝淇℃伅 (CardTracker.update_from_play)
    鈹   鈹溾攢> 鏇存柊鐜╁跺巻鍙
    鈹   鈹溾攢> 鏇存柊鍓╀綑鐗屽簱
    鈹   鈹斺攢> 鏇存柊PASS娆℃暟
    鈹斺攢> 鏇存柊鍏鍏变俊鎭 (publicInfo)
    鈫
鍐崇瓥寮曟搸 (DecisionEngine.decide)
    鈹溾攢> 寮濮嬭℃椂 (AdaptiveDecisionTimer.start)
    鈹溾攢> 缂栫爜娓告垙鐘舵 (StateFeatureEncoder.encode_state)
    鈹   鈹溾攢> 缂栫爜鎵嬬墝鐗瑰緛
    鈹   鈹溾攢> 缂栫爜鍑虹墝鍘嗗彶鐗瑰緛
    鈹   鈹溾攢> 缂栫爜鐜╁剁姸鎬佺壒寰
    鈹   鈹斺攢> 缂栫爜娓告垙闃舵电壒寰
    鈹溾攢> 鍒ゆ柇涓诲姩/琚鍔 (EnhancedGameStateManager.is_passive_play)
    鈹
    鈹溾攢> [琚鍔ㄥ嚭鐗屽垎鏀痌
    鈹   鈹溾攢> 璇勪及閰嶅悎鏈轰細 (CooperationStrategy.get_cooperation_strategy)
    鈹   鈹   鈹斺攢> 鏌ヨ㈢姸鎬佷俊鎭 (EnhancedGameStateManager)
    鈹   鈹       鈹斺攢> 鏌ヨ㈣扮墝淇℃伅 (CardTracker)
    鈹   鈹
    鈹   鈹溾攢> 浣跨敤鐗屽瀷涓撻棬澶勭悊鍣 (CardTypeHandlerFactory.get_handler)
    鈹   鈹   鈹溾攢> 鍒嗘瀽鎵嬬墝缁撴瀯 (HandCombiner.combine_handcards)
    鈹   鈹   鈹斺攢> 澶勭悊琚鍔ㄥ嚭鐗 (Handler.handle_passive)
    鈹   鈹
    鈹   鈹溾攢> 鐢熸垚鍊欓夊姩浣 (PlayDecisionMaker.generate_candidates)
    鈹   鈹
    鈹   鈹溾攢> 鍔ㄤ綔绌洪棿浼樺寲 (ActionSpaceOptimizer.filter_actions)
    鈹   鈹   鈹溾攢> 鍒ゆ柇鍔ㄤ綔绌洪棿澶у皬
    鈹   鈹   鈹溾攢> [澶у姩浣滅┖闂碷 蹇閫熺瓫閫塗op-K鍊欓
    鈹   鈹   鈹   鈹溾攢> 缂栫爜鍔ㄤ綔鐗瑰緛 (ActionFeatureEncoder.encode_action)
    鈹   鈹   鈹   鈹斺攢> 蹇閫熻瘎浼板苟鎺掑簭
    鈹   鈹   鈹斺攢> [灏忓姩浣滅┖闂碷 淇濈暀鎵鏈夊欓
    鈹   鈹
    鈹   鈹斺攢> 澶氬洜绱犺瘎浼 (MultiFactorEvaluator.evaluate_all_actions)
    鈹       鈹溾攢> 缂栫爜鍔ㄤ綔鐗瑰緛 (ActionFeatureEncoder.encode_action) - 鍙閫
    鈹       鈹溾攢> 璇勪及鍓╀綑鐗屾暟鍥犵礌 (鏌ヨ CardTracker)
    鈹       鈹溾攢> 璇勪及鐗屽瀷澶у皬鍥犵礌
    鈹       鈹溾攢> 璇勪及閰嶅悎鍥犵礌 (鏌ヨ CooperationStrategy)
    鈹       鈹溾攢> 璇勪及椋庨櫓鍥犵礌
    鈹       鈹溾攢> 璇勪及鏃舵満鍥犵礌
    鈹       鈹斺攢> 璇勪及鎵嬬墝缁撴瀯鍥犵礌 (鏌ヨ HandCombiner)
    鈹
    鈹斺攢> [涓诲姩鍑虹墝鍒嗘敮]
        鈹溾攢> 鐢熸垚鍊欓夊姩浣 (PlayDecisionMaker.generate_candidates)
        鈹溾攢> 鍔ㄤ綔绌洪棿浼樺寲 (ActionSpaceOptimizer.filter_actions)
        鈹   鈹斺攢> (鍚屼笂)
        鈹斺攢> 澶氬洜绱犺瘎浼 (MultiFactorEvaluator.evaluate_all_actions)
            鈹斺攢> (鍚屼笂)
    鈫
妫鏌ヨ秴鏃 (AdaptiveDecisionTimer.check_timeout)
    鈹溾攢> 鏍规嵁鍔ㄤ綔绌洪棿澶у皬鍔ㄦ佽皟鏁存椂闂撮勭畻
    鈹斺攢> 瓒呮椂淇濇姢鏈哄埗
    鈫
閫夋嫨鏈浣冲姩浣
    鈫
鏋勫缓鍝嶅簲娑堟伅 ({"actIndex": X})
    鈫
WebSocket娑堟伅鍙戦
```

#### 5.4 鍐崇瓥娴佺▼锛堣︾粏锛
```
1. 鎺ユ敹鍑虹墝璇锋眰 (type: act, stage: play)
2. 寮濮嬭℃椂 (AdaptiveDecisionTimer.start)
3. 缂栫爜娓告垙鐘舵 (StateFeatureEncoder.encode_state)
4. 鍒ゆ柇涓诲姩/琚鍔 (EnhancedGameStateManager.is_passive_play)
5. [琚鍔ㄥ嚭鐗宂:
   - 璇勪及閰嶅悎鏈轰細 (CooperationStrategy)
   - 浣跨敤鐗屽瀷涓撻棬澶勭悊鍣 (CardTypeHandlerFactory)
   - 鐢熸垚鍊欓夊姩浣 (PlayDecisionMaker.generate_candidates)
   - 鍔ㄤ綔绌洪棿浼樺寲 (ActionSpaceOptimizer.filter_actions)
     - 鍒ゆ柇鍔ㄤ綔绌洪棿澶у皬
     - [澶у姩浣滅┖闂碷 蹇閫熺瓫閫塗op-K鍊欓夛紙浣跨敤ActionFeatureEncoder锛
     - [灏忓姩浣滅┖闂碷 淇濈暀鎵鏈夊欓
   - 澶氬洜绱犺瘎浼 (MultiFactorEvaluator.evaluate_all_actions)
6. [涓诲姩鍑虹墝]:
   - 鐢熸垚鍊欓夊姩浣 (PlayDecisionMaker.generate_candidates)
   - 鍔ㄤ綔绌洪棿浼樺寲 (ActionSpaceOptimizer.filter_actions)
   - 澶氬洜绱犺瘎浼 (MultiFactorEvaluator.evaluate_all_actions)
7. 妫鏌ヨ秴鏃 (AdaptiveDecisionTimer.check_timeout)
   - 鏍规嵁鍔ㄤ綔绌洪棿澶у皬鍔ㄦ佽皟鏁存椂闂撮勭畻
8. 閫夋嫨鏈浼樻柟妗
9. 鍙戦佸喅绛栫粨鏋 (type: act, {"actIndex": X})
```

#### 5.5 妯″潡渚濊禆鍏崇郴

**渚濊禆鍏崇郴鍥**:
```
DecisionEngine (鍐崇瓥寮曟搸)
鈹溾攢鈹 AdaptiveDecisionTimer (鑷閫傚簲鏃堕棿鎺у埗)
鈹   鈹斺攢鈹 (鏃犱緷璧)
鈹溾攢鈹 StateFeatureEncoder (鐘舵佺壒寰佺紪鐮)
鈹   鈹斺攢鈹 EnhancedGameStateManager (鐘舵佺＄悊)
鈹       鈹斺攢鈹 CardTracker (璁扮墝妯″潡)
鈹           鈹斺攢鈹 (鏃犱緷璧)
鈹溾攢鈹 ActionSpaceOptimizer (鍔ㄤ綔绌洪棿浼樺寲)
鈹   鈹溾攢鈹 EnhancedGameStateManager (鐘舵佺＄悊)
鈹   鈹斺攢鈹 ActionFeatureEncoder (鍔ㄤ綔鐗瑰緛缂栫爜)
鈹       鈹斺攢鈹 EnhancedGameStateManager (鐘舵佺＄悊)
鈹溾攢鈹 ActionFeatureEncoder (鍔ㄤ綔鐗瑰緛缂栫爜)
鈹   鈹斺攢鈹 EnhancedGameStateManager (鐘舵佺＄悊)
鈹       鈹斺攢鈹 CardTracker (璁扮墝妯″潡)
鈹溾攢鈹 CooperationStrategy (閰嶅悎绛栫暐)
鈹   鈹斺攢鈹 EnhancedGameStateManager (鐘舵佺＄悊)
鈹       鈹斺攢鈹 CardTracker (璁扮墝妯″潡)
鈹溾攢鈹 MultiFactorEvaluator (澶氬洜绱犺瘎浼)
鈹   鈹溾攢鈹 EnhancedGameStateManager (鐘舵佺＄悊)
鈹   鈹   鈹斺攢鈹 CardTracker (璁扮墝妯″潡)
鈹   鈹溾攢鈹 HandCombiner (鎵嬬墝缁勫悎)
鈹   鈹   鈹斺攢鈹 (鏃犱緷璧)
鈹   鈹溾攢鈹 CooperationStrategy (閰嶅悎绛栫暐)
鈹   鈹斺攢鈹 ActionFeatureEncoder (鍔ㄤ綔鐗瑰緛缂栫爜) - 鍙閫
鈹斺攢鈹 CardTypeHandlerFactory (鐗屽瀷澶勭悊鍣ㄥ伐鍘)
    鈹溾攢鈹 EnhancedGameStateManager (鐘舵佺＄悊)
    鈹   鈹斺攢鈹 CardTracker (璁扮墝妯″潡)
    鈹斺攢鈹 HandCombiner (鎵嬬墝缁勫悎)
        鈹斺攢鈹 (鏃犱緷璧)
```

**渚濊禆璇存槑**:
- **鍐崇瓥寮曟搸 鈫 鐘舵佺＄悊 鈫 璁扮墝妯″潡**: `DecisionEngine` 閫氳繃 `EnhancedGameStateManager` 璁块棶娓告垙鐘舵侊紝`EnhancedGameStateManager` 鍐呴儴浣跨敤 `CardTracker` 缁存姢璁扮墝淇℃伅
- **鍐崇瓥寮曟搸 鈫 鐘舵佺壒寰佺紪鐮 鈫 鐘舵佺＄悊**: `DecisionEngine` 浣跨敤 `StateFeatureEncoder` 缂栫爜娓告垙鐘舵侊紝`StateFeatureEncoder` 閫氳繃 `EnhancedGameStateManager` 鑾峰彇鐘舵佷俊鎭
- **鍐崇瓥寮曟搸 鈫 鍔ㄤ綔绌洪棿浼樺寲 鈫 鍔ㄤ綔鐗瑰緛缂栫爜**: `DecisionEngine` 浣跨敤 `ActionSpaceOptimizer` 浼樺寲鍔ㄤ綔绌洪棿锛宍ActionSpaceOptimizer` 浣跨敤 `ActionFeatureEncoder` 杩涜屽揩閫熻瘎浼
- **鍐崇瓥寮曟搸 鈫 閰嶅悎绛栫暐 鈫 鐘舵佺＄悊**: `DecisionEngine` 璋冪敤 `CooperationStrategy` 璇勪及閰嶅悎鏈轰細锛宍CooperationStrategy` 閫氳繃 `EnhancedGameStateManager` 鑾峰彇鐘舵佷俊鎭
- **鍐崇瓥寮曟搸 鈫 鎵嬬墝缁勫悎 鈫 娓告垙瑙勫垯**: `DecisionEngine` 浣跨敤 `HandCombiner` 鍒嗘瀽鎵嬬墝缁撴瀯锛宍HandCombiner` 鍩轰簬娓告垙瑙勫垯璇嗗埆鐗屽瀷

#### 5.4 淇℃伅鐩戞帶娴佺▼
```
1. 鍚鍔ㄥ畾鏃朵换鍔★紙鍚庡彴杩愯岋級
   鈫
2. 妫鏌ュ綋鍓嶆椂闂存槸鍚﹀湪闈欓粯鏃舵碉紙0:00-6:00锛 (quiet_hours)
   - 濡傛灉鍦ㄩ潤榛樻椂娈碉紝璺宠繃鏈娆℃鏌ワ紝绛夊緟涓嬫
   鈫
3. 瀹氭湡璁块棶骞冲彴缃戠珯锛堟瘡6灏忔椂锛屸墺6灏忔椂锛 (check_interval: 21600s)
   鈫
4. 鎶撳彇缃戦〉鍐呭 (requests/httpx)
   鈫
5. 瑙ｆ瀽HTML鎻愬彇淇℃伅 (BeautifulSoup)
   鈫
6. 涓庡巻鍙蹭俊鎭瀵规瘮锛屾娴嬫柊鍐呭 (鍐呭瑰搱甯屾垨鏃堕棿鎴)
   鈫
7. 濡傛湁鏂颁俊鎭锛
   - 淇濆瓨鍒版暟鎹搴 (data/platform_info)
   - 鍙戦侀氱煡 (console/log/desktop/email)
   - 璁板綍鏃ュ織
   鈫
8. 绛夊緟妫鏌ラ棿闅旓紙6灏忔椂锛夊悗缁х画寰鐜
   - 娉ㄦ剰锛氬傛灉涓嬫℃鏌ユ椂闂磋惤鍦ㄩ潤榛樻椂娈碉紝鑷鍔ㄥ欢鍚庡埌闈欓粯鏃舵电粨鏉 (schedule_next_check)
```

### 鍏銆侀厤缃绠＄悊

#### 6.1 閰嶇疆鏂囦欢缁撴瀯
```yaml
# config.yaml
platform:
  name: "鍗椾含閭鐢靛ぇ瀛︽幖铔婣I骞冲彴"
  version: "v1006"
  url: "https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html"

websocket:
  # 鏈鍦拌繛鎺
  local_url: "ws://127.0.0.1:23456/game/{user_info}"
  # 灞鍩熺綉杩炴帴锛堥渶瑕佹椂鏇挎崲IP锛
  network_url: "ws://[灞鍩熺綉IP]:23456/game/{user_info}"
  reconnect_interval: 5
  heartbeat_interval: 30
  timeout: 10  # 杩炴帴瓒呮椂鏃堕棿锛堢掞級

decision:
  # 鏈澶у喅绛栨椂闂达紙绉掞級
  max_decision_time: 0.8
  # 鍚鐢ㄨ扮墝鍔熻兘
  enable_card_tracking: true
  # 鍚鐢ㄦ帹鐞嗗姛鑳
  enable_inference: true
  # 鍚鐢ㄩ厤鍚堢瓥鐣
  enable_cooperation: true
  # 鍐崇瓥缂撳瓨澶у皬
  cache_size: 1000
  # 鍚鐢ㄥ姩浣滅┖闂翠紭鍖
  enable_action_space_optimization: true
  # 鍚鐢ㄧ壒寰佺紪鐮
  enable_feature_encoding: true

# 鍔ㄤ綔绌洪棿浼樺寲閰嶇疆
action_space_optimizer:
  # 澶у姩浣滅┖闂撮槇鍊硷紙瓒呰繃姝ゅ间娇鐢ㄥ揩閫熺瓫閫夛級
  large_space_threshold: 100
  # 鍊欓夊姩浣滄瘮渚嬶紙澶у姩浣滅┖闂存椂淇濈暀鐨勬瘮渚嬶級
  candidate_ratio: 0.1
  # 鏈灏忓欓夋暟閲忥紙鍗充娇姣斾緥寰堝皬涔熻嚦灏戜繚鐣欑殑鏁伴噺锛
  min_candidates: 10
  # 蹇閫熻瘎浼版ā寮忥紙true: 浣跨敤鐗瑰緛缂栫爜蹇閫熻瘎浼, false: 浣跨敤瀹屾暣璇勪及锛
  fast_evaluation_mode: true

# 鐗瑰緛缂栫爜閰嶇疆
feature_encoding:
  # 鍚鐢ㄧ姸鎬佺壒寰佺紪鐮
  enable_state_encoding: true
  # 鍚鐢ㄥ姩浣滅壒寰佺紪鐮
  enable_action_encoding: true
  # 鐘舵佺壒寰佺淮搴︼紙鑷鍔ㄨ＄畻锛屾ゅ勪负鍙傝冿級
  state_feature_dim: 200
  # 鍔ㄤ綔鐗瑰緛缁村害锛堣嚜鍔ㄨ＄畻锛屾ゅ勪负鍙傝冿級
  action_feature_dim: 50
  # 鐗瑰緛缂撳瓨澶у皬
  feature_cache_size: 1000

# 璁扮墝妯″潡閰嶇疆
card_tracking:
  # 璺熻釜鍘嗗彶
  track_history: true
  # 璺熻釜鍓╀綑鐗
  track_remaining: true
  # 鍚鐢ㄦ傜巼璁＄畻
  enable_probability: true

# 澶氬洜绱犺瘎浼版潈閲嶉厤缃
evaluation:
  weights:
    # 鍓╀綑鐗屾暟鍥犵礌鏉冮噸
    remaining_cards: 0.25
    # 鐗屽瀷澶у皬鍥犵礌鏉冮噸
    card_type_value: 0.20
    # 閰嶅悎鍥犵礌鏉冮噸
    cooperation: 0.20
    # 椋庨櫓鍥犵礌鏉冮噸
    risk: 0.15
    # 鏃舵満鍥犵礌鏉冮噸
    timing: 0.10
    # 鎵嬬墝缁撴瀯鍥犵礌鏉冮噸
    hand_structure: 0.10

# 閰嶅悎绛栫暐閰嶇疆
cooperation:
  # 闃熷弸鐗屽瀷鍊奸槇鍊硷紙澶т簬姝ゅ煎簲璇PASS閰嶅悎锛
  support_threshold: 15
  # 瀵规墜鍓╀綑鐗屾暟鍗遍櫓闃堝硷紙灏忎簬姝ゅ煎簲璇ラ厤鍚堬級
  danger_threshold: 4
  # 鏈澶х墝鍊奸槇鍊
  max_val_threshold: 14

# 鎵嬬墝缁勫悎閰嶇疆
hand_combiner:
  # 缁勭墝浼樺厛绾э紙鏁板艰秺澶т紭鍏堢骇瓒婇珮锛
  priorities:
    StraightFlush: 100  # 鍚岃姳椤
    Bomb: 80            # 鐐稿脊
    Straight: 60        # 椤哄瓙
    ThreeWithTwo: 50    # 涓夊甫浜
    TwoTrips: 45        # 閽㈡澘
    ThreePair: 40       # 涓夎繛瀵
    Trips: 30           # 涓夊紶
    Pair: 20            # 瀵瑰瓙
    Single: 10          # 鍗曞紶

ai:
  strategy_level: "medium"  # basic/medium/advanced
  cooperation_enabled: true
  risk_tolerance: 0.5

data:
  save_path: "./replays"
  auto_save: true
  format: "json"

logging:
  level: "INFO"  # DEBUG/INFO/WARNING/ERROR
  file: "ai_client.log"
  console: true  # 鏄鍚﹁緭鍑哄埌鎺у埗鍙

contact:
  research: "chenxg@njupt.edu.cn"
  feedback: "wuguduofeng@gmail.com"
  qq: "519301156"

info_monitor:
  enabled: true  # 鏄鍚﹀惎鐢ㄤ俊鎭鐩戞帶
  check_interval: 21600  # 妫鏌ラ棿闅旓紙绉掞級锛岄粯璁6灏忔椂锛堚墺6灏忔椂锛
  quiet_hours:  # 闈欓粯鏃舵碉紝涓嶈繘琛屾鏌
    enabled: true  # 鏄鍚﹀惎鐢ㄩ潤榛樻椂娈
    start: "00:00"  # 闈欓粯寮濮嬫椂闂达紙24灏忔椂鍒讹級
    end: "06:00"    # 闈欓粯缁撴潫鏃堕棿锛24灏忔椂鍒讹級
  platforms:
    - name: "鍗椾含閭鐢靛ぇ瀛︽幖铔婣I骞冲彴"
      url: "https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html"
      check_version: true  # 鏄鍚︽鏌ョ増鏈鏇存柊
      check_announcements: true  # 鏄鍚︽鏌ュ叕鍛
      check_competitions: true  # 鏄鍚︽鏌ユ瘮璧涗俊鎭
  notification:
    console: true  # 鎺у埗鍙伴氱煡
    log: true  # 鏃ュ織璁板綍
    desktop: false  # 妗岄潰閫氱煡锛堥渶瑕侀濆栧簱锛
    email: false  # 閭浠堕氱煡锛堥渶瑕侀厤缃锛
    email_config:
      smtp_server: ""
      smtp_port: 587
      username: ""
      password: ""
      to_email: ""
  storage:
    path: "./data/platform_info"  # 淇℃伅瀛樺偍璺寰
    format: "json"  # 瀛樺偍鏍煎紡
    keep_history: true  # 淇濈暀鍘嗗彶璁板綍
    max_history_days: 90  # 鍘嗗彶璁板綍淇濈暀澶╂暟
```

### 涓冦侀敊璇澶勭悊

#### 7.1 杩炴帴閿欒
- WebSocket杩炴帴澶辫触
- 杩炴帴涓鏂
- 閲嶈繛鏈哄埗

#### 7.2 鏁版嵁閿欒
- JSON瑙ｆ瀽閿欒
- 娑堟伅鏍煎紡閿欒
- 鏁版嵁楠岃瘉澶辫触

#### 7.3 閫昏緫閿欒
- 鐗屽瀷璇嗗埆閿欒
- 鍐崇瓥寮傚父
- 鐘舵佷笉涓鑷

### 鍏銆佹棩蹇楀拰璋冭瘯

#### 8.1 鏃ュ織绾у埆
- DEBUG: 璇︾粏璋冭瘯淇℃伅
- INFO: 涓鑸淇℃伅
- WARNING: 璀﹀憡淇℃伅
- ERROR: 閿欒淇℃伅

#### 8.2 鏃ュ織鍐呭
- 杩炴帴鐘舵
- 鎺ユ敹/鍙戦佺殑娑堟伅 (type/stage/handCards/curPos/curAction)
- 鍐崇瓥杩囩▼
- 閿欒淇℃伅

### 涔濄佹祴璇曠瓥鐣

#### 9.1 鍗曞厓娴嬭瘯
- 鐗屽瀷璇嗗埆娴嬭瘯 (Single/Pair/Bomb绛)
- 鐗屽瀷姣旇緝娴嬭瘯
- 鍐崇瓥閫昏緫娴嬭瘯

#### 9.2 闆嗘垚娴嬭瘯
- **WebSocket閫氫俊娴嬭瘯**
  - 鏈鍦拌繛鎺ユ祴璇 (ws://127.0.0.1:23456)
  - 灞鍩熺綉杩炴帴娴嬭瘯
  - 杩炴帴閲嶈繛娴嬭瘯
  - 娑堟伅鏀跺彂娴嬭瘯 (notify/act)

- **瀹屾暣瀵瑰眬娴嬭瘯**
  - 鍚鍔4涓狝I瀹㈡埛绔
  - 瀹屾垚涓灞瀹屾暣娓告垙 (stage: beginning -> play -> gameOver)
  - 楠岃瘉缁勯槦鍏崇郴锛1-3涓闃 (myPos 0-2)锛2-4涓闃 (myPos 1-3)锛
  - 妫鏌ョ墝鍨嬭瘑鍒鍑嗙‘鎬
  - 妫鏌ュ喅绛栧悎鐞嗘
  - 楠岃瘉璁扮墝妯″潡鍑嗙‘鎬
  - 楠岃瘉閰嶅悎绛栫暐鏈夋晥鎬

- **妯″潡闆嗘垚娴嬭瘯**
  - 娴嬭瘯鐘舵佺＄悊 鈫 璁扮墝妯″潡鐨勯泦鎴
  - 娴嬭瘯鍐崇瓥寮曟搸 鈫 澶氬洜绱犺瘎浼扮殑闆嗘垚
  - 娴嬭瘯鍐崇瓥寮曟搸 鈫 閰嶅悎绛栫暐鐨勯泦鎴
  - 娴嬭瘯鍐崇瓥寮曟搸 鈫 鐗屽瀷澶勭悊鍣ㄧ殑闆嗘垚
  - 娴嬭瘯瀹屾暣鍐崇瓥娴佺▼

- **澶氬眬绋冲畾鎬ф祴璇**
  - 杩炵画澶氬眬瀵规垬
  - 鍐呭瓨娉勬紡妫鏌
  - 闀挎椂闂磋繍琛岀ǔ瀹氭
  - 鐘舵侀噸缃娴嬭瘯

- **寮傚父鍦烘櫙娴嬭瘯**
  - 缃戠粶涓鏂鎭㈠
  - 娑堟伅鏍煎紡閿欒澶勭悊
  - 瓒呮椂澶勭悊
  - 寮傚父閫鍑烘仮澶
  - 鍐崇瓥瓒呮椂淇濇姢娴嬭瘯

#### 9.3 鎬ц兘娴嬭瘯
- **鍐崇瓥鍝嶅簲鏃堕棿**
  - 鐩鏍囷細< 0.8绉掞紙榛樿ら厤缃锛
  - 骞冲潎鍝嶅簲鏃堕棿
  - 鏈澶у搷搴旀椂闂
  - 瓒呮椂鎯呭喌缁熻
  - 鏃堕棿鎺у埗鏈哄埗楠岃瘉

- **鍐呭瓨浣跨敤**
  - 鍗曞眬鍐呭瓨鍗犵敤
  - 澶氬眬杩愯屽唴瀛樺為暱
  - 鍐呭瓨娉勬紡妫娴
  - 璁扮墝妯″潡鍐呭瓨鍗犵敤

- **骞跺彂澶勭悊鑳藉姏**
  - 鍚屾椂澶勭悊澶氫釜娑堟伅
  - 寮傛ュ勭悊鎬ц兘
  - 杩炴帴骞跺彂鏁

#### 9.4 绛栫暐娴嬭瘯
- **澶氬洜绱犺瘎浼版祴璇**
  - 娴嬭瘯涓嶅悓鏉冮噸閰嶇疆鐨勬晥鏋
  - 娴嬭瘯鍚勫洜绱犺瘎鍒嗙殑鍑嗙‘鎬
  - 娴嬭瘯鏈浣冲姩浣滈夋嫨鐨勬ｇ‘鎬

- **閰嶅悎绛栫暐娴嬭瘯**
  - 娴嬭瘯閰嶅悎鍒ゆ柇鐨勫噯纭鎬
  - 娴嬭瘯涓嶅悓鍙傛暟閰嶇疆鐨勬晥鏋
  - 娴嬭瘯鎺ユ浛鍒ゆ柇鐨勯昏緫

- **鐗屽瀷澶勭悊鍣ㄦ祴璇**
  - 娴嬭瘯姣忕嶇墝鍨嬪勭悊鍣ㄧ殑閫昏緫
  - 娴嬭瘯涓诲姩/琚鍔ㄥ嚭鐗岀殑姝ｇ‘鎬
  - 娴嬭瘯鎵嬬墝缁撴瀯鍒嗘瀽鐨勫噯纭鎬

### 鍗併佹墿灞曟ц捐

#### 10.1 绛栫暐鎻掍欢鍖
- 鏀鎸佸氱嶇瓥鐣ョ畻娉
- 绛栫暐鍙鎻掓嫈
- 绛栫暐鍔ㄦ佸垏鎹

#### 10.2 鏈哄櫒瀛︿範闆嗘垚
- 棰勭暀ML妯″瀷鎺ュ彛
- 鏀鎸佹ā鍨嬫帹鐞
- 鏀鎸佸湪绾垮︿範

#### 10.3 澶欰I鏀鎸
- 鏀鎸佸悓鏃惰繍琛屽氫釜AI瀹炰緥
- 鏀鎸佷笉鍚岀瓥鐣ョ殑AI瀵规垬
- 鏀鎸丄I姘村钩璇勪及

### 鍗佷竴銆侀」鐩鐩褰曠粨鏋

```
guandan_ai_client/
鈹溾攢鈹 main.py                 # 涓荤▼搴忓叆鍙
鈹溾攢鈹 config.yaml             # 閰嶇疆鏂囦欢
鈹溾攢鈹 requirements.txt        # 渚濊禆鍖
鈹溾攢鈹 README.md              # 璇存槑鏂囨。
鈹
鈹溾攢鈹 src/
鈹   鈹溾攢鈹 communication/      # 閫氫俊妯″潡
鈹   鈹   鈹溾攢鈹 __init__.py
鈹   鈹   鈹溾攢鈹 websocket_client.py
鈹   鈹   鈹斺攢鈹 message_handler.py
鈹   鈹
鈹   鈹溾攢鈹 game_logic/         # 娓告垙閫昏緫妯″潡
鈹   鈹   鈹溾攢鈹 __init__.py
鈹   鈹   鈹溾攢鈹 card.py
鈹   鈹   鈹溾攢鈹 card_type.py
鈹   鈹   鈹溾攢鈹 recognizer.py
鈹   鈹   鈹溾攢鈹 comparator.py
鈹   鈹   鈹斺攢鈹 state_manager.py
鈹   鈹
鈹   鈹溾攢鈹 decision/           # 鍐崇瓥寮曟搸妯″潡
鈹   鈹   鈹溾攢鈹 __init__.py
鈹   鈹   鈹溾攢鈹 evaluator.py
鈹   鈹   鈹溾攢鈹 decision_maker.py
鈹   鈹   鈹溾攢鈹 cooperation.py
鈹   鈹   鈹溾攢鈹 action_space_optimizer.py  # 鍔ㄤ綔绌洪棿浼樺寲鍣
鈹   鈹   鈹溾攢鈹 action_feature_encoder.py  # 鍔ㄤ綔鐗瑰緛缂栫爜鍣
鈹   鈹   鈹溾攢鈹 state_feature_encoder.py    # 鐘舵佺壒寰佺紪鐮佸櫒
鈹   鈹   鈹斺攢鈹 adaptive_timer.py          # 鑷閫傚簲鍐崇瓥鏃堕棿鎺у埗鍣
鈹   鈹
鈹   鈹溾攢鈹 data/               # 鏁版嵁鏀堕泦妯″潡
鈹   鈹   鈹溾攢鈹 __init__.py
鈹   鈹   鈹溾攢鈹 recorder.py
鈹   鈹   鈹斺攢鈹 storage.py
鈹   鈹
鈹   鈹溾攢鈹 monitor/            # 淇℃伅鐩戞帶妯″潡
鈹   鈹   鈹溾攢鈹 __init__.py
鈹   鈹   鈹溾攢鈹 fetcher.py      # 淇℃伅鎶撳彇鍣
鈹   鈹   鈹溾攢鈹 parser.py       # 淇℃伅瑙ｆ瀽鍣
鈹   鈹   鈹溾攢鈹 storage.py      # 淇℃伅瀛樺偍
鈹   鈹   鈹斺攢鈹 notification.py # 閫氱煡绠＄悊鍣
鈹   鈹
鈹   鈹斺攢鈹 utils/              # 宸ュ叿妯″潡
鈹       鈹溾攢鈹 __init__.py
鈹       鈹溾攢鈹 logger.py
鈹       鈹斺攢鈹 config.py
鈹
鈹溾攢鈹 tests/                  # 娴嬭瘯浠ｇ爜
鈹   鈹溾攢鈹 test_card_type.py
鈹   鈹溾攢鈹 test_decision.py
鈹   鈹斺攢鈹 test_communication.py
鈹
鈹溾攢鈹 data/                   # 鏁版嵁鐩褰
鈹   鈹溾攢鈹 replays/           # 鍥炴斁鏂囦欢
鈹   鈹斺攢鈹 platform_info/     # 骞冲彴淇℃伅瀛樺偍
鈹       鈹溾攢鈹 announcements.json  # 鍏鍛婁俊鎭
鈹       鈹溾攢鈹 competitions.json   # 姣旇禌淇℃伅
鈹       鈹溾攢鈹 updates.json        # 鏇存柊淇℃伅
鈹       鈹斺攢鈹 history/            # 鍘嗗彶璁板綍
鈹
鈹斺攢鈹 logs/                   # 鏃ュ織鐩褰
    鈹斺攢鈹 ai_client.log
```

### 鍗佷簩銆佸紑鍙戣″垝

#### 闃舵典竴锛氬熀纭妗嗘灦锛1-2鍛锛
- [ ] 鎼寤洪」鐩缁撴瀯
- [ ] 瀹炵幇WebSocket閫氫俊
- [ ] 瀹炵幇JSON娑堟伅澶勭悊
- [ ] 瀹炵幇鍩虹鏃ュ織绯荤粺

#### 闃舵典簩锛氭父鎴忛昏緫锛2-3鍛锛
- [ ] 瀹炵幇鍗＄墝鍜岀墝鍨嬫暟鎹缁撴瀯
- [ ] 瀹炵幇鐗屽瀷璇嗗埆鍣
- [ ] 瀹炵幇鐗屽瀷姣旇緝鍣
- [ ] 瀹炵幇娓告垙鐘舵佺＄悊

#### 闃舵典笁锛氬喅绛栧紩鎿庯紙3-4鍛锛
- [ ] 瀹炵幇鍩虹鍐崇瓥閫昏緫
- [ ] 瀹炵幇绛栫暐璇勪及
- [ ] 瀹炵幇閰嶅悎绛栫暐
- [ ] 浼樺寲鍐崇瓥绠楁硶
- [ ] 瀹炵幇鍔ㄤ綔绌洪棿浼樺寲鍣锛圓ctionSpaceOptimizer锛
- [ ] 瀹炵幇鍔ㄤ綔鐗瑰緛缂栫爜鍣锛圓ctionFeatureEncoder锛
- [ ] 瀹炵幇鐘舵佺壒寰佺紪鐮佸櫒锛圫tateFeatureEncoder锛
- [ ] 瀹炵幇鑷閫傚簲鍐崇瓥鏃堕棿鎺у埗鍣锛圓daptiveDecisionTimer锛

#### 闃舵靛洓锛氭暟鎹鏀堕泦锛1鍛锛
- [ ] 瀹炵幇瀵瑰眬璁板綍
- [ ] 瀹炵幇鏁版嵁瀛樺偍
- [ ] 瀹炵幇缁熻″垎鏋

#### 闃舵典簲锛氫俊鎭鐩戞帶锛1鍛锛
- [ ] 瀹炵幇骞冲彴淇℃伅鎶撳彇鍣
- [ ] 瀹炵幇淇℃伅瑙ｆ瀽鍣
- [ ] 瀹炵幇淇℃伅瀛樺偍
- [ ] 瀹炵幇閫氱煡绠＄悊鍣
- [ ] 瀹炵幇瀹氭椂浠诲姟璋冨害
- [ ] 娴嬭瘯淇℃伅鎶撳彇鍜岄氱煡鍔熻兘

#### 闃舵靛叚锛氭祴璇曚紭鍖栵紙鎸佺画锛
- [ ] 鍗曞厓娴嬭瘯
- [ ] 闆嗘垚娴嬭瘯
- [ ] 鎬ц兘浼樺寲
- [ ] 绛栫暐浼樺寲
- [ ] 淇℃伅鐩戞帶娴嬭瘯

### 鍗佷笁銆佸叧閿鎶鏈鐐

#### 13.1 WebSocket寮傛ュ勭悊
- 浣跨敤寮傛IO鎻愰珮鎬ц兘
- 澶勭悊骞跺彂娑堟伅
- 閬垮厤闃诲

#### 13.2 鍐崇瓥绠楁硶
- 瑙勫垯寮曟搸锛堝垵鏈燂級
- 鎼滅储绠楁硶锛堜腑鏈燂級
- 鏈哄櫒瀛︿範锛堝悗鏈燂級
- **澶氬洜绱犺瘎浼扮郴缁**: 缁煎悎璇勪及6涓鍥犵礌锛堝墿浣欑墝鏁般佺墝鍨嬪ぇ灏忋侀厤鍚堛侀庨櫓銆佹椂鏈恒佹墜鐗岀粨鏋勶級锛岃＄畻鍔ㄤ綔璇勫垎
- **涓诲姩/琚鍔ㄥ喅绛栧垎绂**: 鍖哄垎涓诲姩鍑虹墝鍜岃鍔ㄥ嚭鐗岋紝閲囩敤涓嶅悓绛栫暐
- **鐗屽瀷涓撻棬澶勭悊**: 涓烘瘡绉嶇墝鍨嬶紙Single銆丳air銆乀rips銆丅omb銆丼traight绛夛級鍒涘缓涓撻棬鐨勫勭悊閫昏緫
- **鍔ㄤ綔绌洪棿浼樺寲**锛堝熼壌DanZero+璁烘枃锛:
  - 鏍规嵁鍔ㄤ綔绌洪棿澶у皬鍔ㄦ佺瓫閫夊欓夊姩浣
  - 澶у姩浣滅┖闂达紙>100锛夛細蹇閫熺瓫閫塗op-K鍊欓夛紝浣跨敤鍚鍙戝紡瑙勫垯蹇閫熻瘎浼
  - 灏忓姩浣滅┖闂达紙鈮100锛夛細绮剧粏璇勪及鎵鏈夊欓夊姩浣
  - 瑙ｅ喅鎺艰泲娓告垙鍒濆嬬姸鎬佸彲鑳>5000鍚堟硶鍔ㄤ綔鐨勬寫鎴
- **鐗瑰緛缂栫爜鎶鏈**锛堝熼壌DanZero+璁烘枃鐨凞MC鏂规硶锛:
  - **鐘舵佺壒寰佺紪鐮**: 灏嗘父鎴忕姸鎬佺紪鐮佷负缁撴瀯鍖栫壒寰佸悜閲忥紙鎵嬬墝銆佸巻鍙层佺帺瀹剁姸鎬佺瓑锛
  - **鍔ㄤ綔鐗瑰緛缂栫爜**: 灏嗗姩浣滅紪鐮佷负鐗瑰緛鍚戦噺锛堢墝鍨嬨佸ぇ灏忋佷富鐗屻佺櫨鎼鐗岀瓑锛
  - 鎻愬崌璇勪及鏁堢巼锛屼负鏈鏉ュ己鍖栧︿範闆嗘垚鍋氬噯澶
  - 鑰冭檻鎺艰泲鐗硅壊锛堣姳鑹查噸瑕佹с佺櫨鎼鐗屻佺骇鐗岋級

#### 13.3 鐘舵佸悓姝
- 纭淇濈姸鎬佷竴鑷存
- 澶勭悊娑堟伅涔卞簭
- 鐘舵佹仮澶嶆満鍒
- **澧炲己鐘舵佺＄悊**: 闆嗘垚璁扮墝妯″潡锛屾彁渚涘畬鏁寸姸鎬佹煡璇㈡帴鍙
- **闃熷弸璇嗗埆**: 浣跨敤鍏寮 `teammate_pos = (myPos + 2) % 4` 鑷鍔ㄨ瘑鍒闃熷弸锛堝弬鑰冭幏濂栦唬鐮侊級

#### 13.4 妯″潡渚濊禆鍏崇郴璁捐
- **渚濊禆娉ㄥ叆**: 鎵鏈夋ā鍧楅氳繃渚濊禆娉ㄥ叆鏂瑰紡杩炴帴锛岄伩鍏嶇‖缂栫爜渚濊禆
- **渚濊禆鍏崇郴**:
  - 鍐崇瓥寮曟搸 鈫 鐘舵佺＄悊 鈫 璁扮墝妯″潡
  - 鍐崇瓥寮曟搸 鈫 鐘舵佺壒寰佺紪鐮 鈫 鐘舵佺＄悊
  - 鍐崇瓥寮曟搸 鈫 鍔ㄤ綔绌洪棿浼樺寲 鈫 鍔ㄤ綔鐗瑰緛缂栫爜 鈫 鐘舵佺＄悊
  - 鍐崇瓥寮曟搸 鈫 閰嶅悎绛栫暐 鈫 鐘舵佺＄悊
  - 鍐崇瓥寮曟搸 鈫 鎵嬬墝缁勫悎 鈫 娓告垙瑙勫垯
  - 鍐崇瓥寮曟搸 鈫 澶氬洜绱犺瘎浼 鈫 鍔ㄤ綔鐗瑰緛缂栫爜锛堝彲閫夛級
- **鍒濆嬪寲椤哄簭**: 浠庡簳灞傚埌椤跺眰锛岀‘淇濅緷璧栧叧绯绘ｇ‘

#### 13.5 鏁版嵁娴佽捐
- **瀹屾暣鏁版嵁娴**: WebSocket娑堟伅 鈫 娑堟伅瑙ｆ瀽 鈫 鐘舵佹洿鏂 鈫 鍐崇瓥寮曟搸 鈫 鍔ㄤ綔閫夋嫨 鈫 娑堟伅鍙戦
- **鍏抽敭鑺傜偣**:
  - 鐘舵佹洿鏂版椂鑷鍔ㄦ洿鏂拌扮墝妯″潡
  - 鐘舵佺壒寰佺紪鐮侊紙StateFeatureEncoder锛: 缂栫爜娓告垙鐘舵佷负鐗瑰緛鍚戦噺
  - 鍔ㄤ綔绌洪棿浼樺寲锛圓ctionSpaceOptimizer锛: 鏍规嵁鍔ㄤ綔绌洪棿澶у皬鍔ㄦ佺瓫閫夊欓
  - 鍔ㄤ綔鐗瑰緛缂栫爜锛圓ctionFeatureEncoder锛: 缂栫爜鍔ㄤ綔涓虹壒寰佸悜閲忥紙澶у姩浣滅┖闂村揩閫熻瘎浼帮級
  - 鍐崇瓥寮曟搸璋冪敤閰嶅悎绛栫暐璇勪及
  - 鍐崇瓥寮曟搸璋冪敤澶氬洜绱犺瘎浼
  - 鑷閫傚簲鏃堕棿鎺у埗锛圓daptiveDecisionTimer锛: 鏍规嵁鍔ㄤ綔绌洪棿澶у皬鍔ㄦ佽皟鏁存椂闂撮勭畻
  - 瓒呮椂淇濇姢鏈哄埗
- **璇︾粏璇存槑**: 鍙傝"浜斻佹秷鎭娴佺▼璁捐"绔犺妭鐨"5.3 瀹屾暣鏁版嵁娴佽捐"

#### 13.6 鍙傝冭幏濂栦唬鐮佺殑鍏抽敭璁捐
- **闃熷弸璇嗗埆鍏寮**: `teammate_pos = (myPos + 2) % 4`锛堝弬鑰冭幏濂栦唬鐮侊級
- **鐘舵佹暟鎹缁撴瀯**: 鍙傝冭幏濂栦唬鐮佺殑 `history` 鍜 `remain_cards` 缁撴瀯
  - `history`: `{'0': {'send': [], 'remain': 27}, ...}` 璁板綍姣忎釜鐜╁剁殑鍑虹墝鍘嗗彶鍜屽墿浣欑墝鏁
  - `remain_cards`: 鎸夎姳鑹插拰鐐规暟鍒嗙被鐨勫墿浣欑墝搴
- **鍐崇瓥鍑芥暟鍒嗙**: 鍙傝冭幏濂栦唬鐮佺殑 `active()` 鍜 `passive()` 鍒嗙
  - `active_decision()`: 涓诲姩鍑虹墝鍐崇瓥锛堢巼鍏堝嚭鐗屾垨鎺ラ庯級
  - `passive_decision()`: 琚鍔ㄥ嚭鐗屽喅绛栵紙闇瑕佸帇鍒讹級
- **鎵嬬墝缁勫悎绠楁硶**: 鍙傝冭幏濂栦唬鐮佺殑 `combine_handcards()` 瀹屾暣瀹炵幇
  - 璇嗗埆鍗曞紶銆佸瑰瓙銆佷笁寮犮佺偢寮
  - 璇嗗埆椤哄瓙锛堣冭檻鍗曞紶銆佸瑰瓙銆佷笁寮犲垎甯冿級
  - 璇嗗埆鍚岃姳椤

#### 13.7 淇℃伅鎶撳彇鎶鏈
- **HTTP璇锋眰**: 浣跨敤requests/httpx鍙戦丠TTP璇锋眰
- **HTML瑙ｆ瀽**: 浣跨敤BeautifulSoup瑙ｆ瀽缃戦〉鍐呭
- **瀹氭椂浠诲姟**: 浣跨敤schedule/APScheduler瀹炵幇瀹氭椂鎶撳彇
- **鍐呭瑰规瘮**: 閫氳繃鍐呭瑰搱甯屾垨鏃堕棿鎴虫娴嬫洿鏂
- **寮傚父澶勭悊**: 澶勭悊缃戠粶閿欒銆佽В鏋愰敊璇绛
- **鍙嶇埇铏搴斿**: 璁剧疆鍚堢悊鐨勮锋眰闂撮殧鍜孶ser-Agent

### 鍗佸洓銆佸弬鑰冭祫鏂欎笌璧勬簮

#### 14.1 瀹樻柟璧勬簮
- **骞冲彴缃戠珯**: https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **骞冲彴鐗堟湰**: v1006锛堝綋鍓嶇増鏈锛
- **绂荤嚎骞冲彴**: 闇浠庡钩鍙扮綉绔欎笅杞
- **浣跨敤璇存槑涔**: 瀵瑰簲鐗堟湰v1006锛屽寘鍚锛
  - 浣跨敤璇存槑
  - JSON鏁版嵁鏍煎紡璇存槑 (type/stage/handCards/myPos/curPos/curAction/actionList)
  - JSON绀轰緥璇存槑

#### 14.2 娓告垙瑙勫垯
- **姹熻嫃鐪佷綋鑲插眬鎺艰泲绔炶禌绠鏄撹勫垯**
- **鐗规畩瑙勫垯娉ㄦ剰**:
  - v1006鐗堟湰璋冩暣浜嗘姉璐¤勫垯锛屼笌姣旇禌鐗堣勫垯涓鑷 (tribute/back)
  - 娉ㄦ剰鎵嬬墝鐨勮〃绀烘柟娉 (handCards: ["S2", "H2", ...])
  - 鎺ュ彛涓巚1003鐗堟湰淇濇寔涓鑷

#### 14.3 鑱旂郴鏂瑰紡
- **鐮旂┒鍏磋叮鍜ㄨ**: chenxg@njupt.edu.cn
- **闂棰樺弽棣**: wuguduofeng@gmail.com
- **QQ**: 519301156

#### 14.4 鎶鏈鍙傝
- WebSocket鍗忚鏂囨。
- JSON鏍煎紡瑙勮寖
- Python WebSocket搴撴枃妗ｏ紙websockets / websocket-client锛

### 鍗佷簲銆佹瘮璧涘弬璧涜佹眰涓庤瘎浼

#### 15.1 姣旇禌鍙傝禌璧勬牸纭璁

鉁 **褰撳墠鏋舵瀯婊¤冻姣旇禌瑕佹眰**锛

##### 鎶鏈鍚堣勬
- 鉁 WebSocket閫氫俊锛氬凡瀹炵幇
- 鉁 JSON鏁版嵁鏍煎紡锛氬凡鏀鎸 (骞冲彴鏍囧噯鍙橀噺)
- 鉁 4涓狝I鍙備笌锛氬凡璁捐 (myPos 0-3缁勯槦)
- 鉁 Windows/Linux鏀鎸侊細Python璺ㄥ钩鍙
- 鉁 瀹炴椂鍝嶅簲锛氬紓姝ュ勭悊鏈哄埗

##### 鍔熻兘瀹屾暣鎬
- 鉁 娓告垙瑙勫垯瀹炵幇锛氱墝鍨嬭瘑鍒鍜屾瘮杈 (Single/Bomb绛)
- 鉁 鍐崇瓥鑳藉姏锛氱瓥鐣ヨ瘎浼板拰鍑虹墝鍐崇瓥
- 鉁 閰嶅悎鑳藉姏锛氶槦鍙嬮厤鍚堢瓥鐣 (teammate_seat)
- 鉁 閿欒澶勭悊锛氬紓甯稿勭悊鍜屾仮澶
- 鉁 绋冲畾鎬э細閲嶈繛鍜岀姸鎬佸悓姝

#### 15.2 姣旇禌璇勫垎鏍囧噯锛堥勪及锛
鏍规嵁AI绠楁硶瀵规姉骞冲彴鐨勫父瑙佽瘎鍒嗘柟寮忥細

##### 璇勫垎缁村害
1. **鑳滅巼** (40-50%)
   - 涓庡叾浠朅I瀵规垬鐨勮儨鐜
   - 闇瑕佷紭鍖栧喅绛栫畻娉

2. **鍐崇瓥璐ㄩ噺** (20-30%)
   - 鍑虹墝鍚堢悊鎬
   - 閰嶅悎榛樺戝害
   - 绛栫暐娣卞害

3. **绋冲畾鎬** (15-20%)
   - 鏃犲紓甯搁鍑
   - 鍝嶅簲鏃堕棿绋冲畾
   - 閿欒澶勭悊鑳藉姏

4. **浠ｇ爜璐ㄩ噺** (10-15%)
   - 浠ｇ爜瑙勮寖鎬
   - 鍙缁存姢鎬
   - 鏂囨。瀹屾暣鎬

#### 15.3 姣旇禌鍓嶅繀椤诲畬鎴愮殑鍔熻兘

##### 鏍稿績鍔熻兘锛堝繀椤伙級
- [x] WebSocket杩炴帴鍜岄氫俊
- [x] JSON娑堟伅瑙ｆ瀽鍜屾瀯寤
- [x] 鎵鏈夌墝鍨嬭瘑鍒
- [x] 鐗屽瀷姣旇緝鍜屽帇鍒跺垽鏂
- [x] 鍩虹鍑虹墝鍐崇瓥
- [x] 娓告垙鐘舵佺＄悊 (stage/myPos/curPos)
- [x] 閿欒澶勭悊鍜岄噸杩

##### 杩涢樁鍔熻兘锛堝缓璁锛
- [ ] 閰嶅悎绛栫暐浼樺寲
- [ ] 璁扮墝鍜屾帹鐞
- [ ] 澶氱瓥鐣ヨ瀺鍚
- [ ] 鎬ц兘浼樺寲锛堝搷搴旀椂闂<1绉掞級
- [ ] 璇︾粏鏃ュ織璁板綍

##### 姣旇禌鍑嗗囷紙閲嶈侊級
- [ ] 鏈鍦版祴璇曪細涓庣荤嚎骞冲彴瀹屾暣娴嬭瘯
- [ ] 鍘嬪姏娴嬭瘯锛氶暱鏃堕棿杩愯岀ǔ瀹氭
- [ ] 瀵规垬娴嬭瘯锛氫笌鍏朵粬AI瀵规垬
- [ ] 鎬ц兘娴嬭瘯锛氬搷搴旀椂闂翠紭鍖
- [ ] 鏂囨。鍑嗗囷細鎻愪氦璇存槑鏂囨。

#### 15.4 姣旇禌绛栫暐寤鸿

##### 鐭鏈熺瓥鐣ワ紙蹇閫熷弬璧涳級
```
鐩鏍囷細鑳藉熸ｅ父鍙傝禌锛屼笉鐘浣庣骇閿欒
鏃堕棿锛2-3涓鏈
閲嶇偣锛
  - 瀹屽杽鍩虹鍔熻兘
  - 瀹炵幇鍩烘湰绛栫暐
  - 纭淇濈ǔ瀹氭
```

##### 涓鏈熺瓥鐣ワ紙鎻愬崌鎺掑悕锛
```
鐩鏍囷細杈惧埌涓涓婃按骞
鏃堕棿锛3-6涓鏈
閲嶇偣锛
  - 浼樺寲鍐崇瓥绠楁硶
  - 鍔犲己閰嶅悎绛栫暐
  - 鎻愬崌鑳滅巼
```

##### 闀挎湡绛栫暐锛堝啿鍑诲啝鍐涳級
```
鐩鏍囷細杈惧埌椤跺皷姘村钩
鏃堕棿锛6-12涓鏈
閲嶇偣锛
  - 寮曞叆鏈哄櫒瀛︿範
  - 娣卞害绛栫暐浼樺寲
  - 澶ч噺瀵规垬璁缁
```

#### 15.5 姣旇禌娉ㄦ剰浜嬮」

##### 鎶鏈娉ㄦ剰浜嬮」
1. **鍝嶅簲鏃堕棿闄愬埗**
   - 纭淇濆喅绛栨椂闂村湪鍚堢悊鑼冨洿鍐咃紙寤鸿<1绉掞級
   - 閬垮厤瓒呮椂瀵艰嚧鍒よ礋

2. **杩炴帴绋冲畾鎬**
   - 瀹炵幇瀹屽杽鐨勯噸杩炴満鍒
   - 澶勭悊缃戠粶娉㈠姩

3. **鏁版嵁鏍煎紡涓ユ牸鎬**
   - 涓ユ牸鎸夌収骞冲彴JSON鏍煎紡瑕佹眰 (["Bomb", "2", ["H2", "D2", "C2", "S2"]])
   - 楠岃瘉鎵鏈夋秷鎭鏍煎紡

4. **瑙勫垯鍑嗙‘鎬**
   - 涓ユ牸鎸夌収姹熻嫃鐪佷綋鑲插眬瑙勫垯
   - 鐗瑰埆娉ㄦ剰鎶楄础绛夌壒娈婅勫垯 (tribute/back)

##### 鎻愪氦瑕佹眰锛堟牴鎹鍙傝禌鎸囧崡锛
- **AI瀹㈡埛绔浠ｇ爜**锛堟垨鍙鎵ц岀▼搴忥級
- **婧愪唬鐮**锛堝傞渶瑕侊紝闇鑱旂郴涓诲姙鏂圭‘璁わ級
- **浣跨敤璇存槑鏂囨。**
  - 濡備綍杩愯岀▼搴
  - 閰嶇疆璇存槑
  - 浣跨敤姝ラ
- **鎶鏈鏂囨。**锛堟灦鏋勮存槑锛
  - 鎶鏈閫夊瀷
  - 鏋舵瀯璁捐
  - 鏍稿績绠楁硶璇存槑
- **娴嬭瘯鎶ュ憡**锛堝彲閫夛級
  - 娴嬭瘯缁撴灉
  - 鎬ц兘鏁版嵁
- **鑱旂郴鏂瑰紡**
  - 閭绠
  - 鐢佃瘽
  - QQ

##### 鎻愪氦娴佺▼
1. **鍑嗗囨彁浜ゆ潗鏂**锛堣佷笂杩版竻鍗曪級
2. **鍙戦佸弬璧涚敵璇烽偖浠**
   - 涓婚橈細鎺艰泲AI绠楁硶瀵规姉 - 鍙傝禌鐢宠
   - 鏀朵欢浜猴細chenxg@njupt.edu.cn锛堢爺绌跺叴瓒ｏ級鎴 wuguduofeng@gmail.com锛堥棶棰樺弽棣堬級
   - 鍐呭癸細浠嬬粛宸插畬鎴愬伐浣溿丄I鐗圭偣銆佸笇鏈涗簡瑙ｇ殑闂棰
3. **绛夊緟涓诲姙鏂瑰洖澶**
   - 鑾峰彇鍙傝禌纭璁
   - 浜嗚В鍏蜂綋姣旇禌瀹夋帓
   - 鑾峰彇鎻愪氦鏂瑰紡
4. **姝ｅ紡鎻愪氦浣滃搧**
   - 鏍规嵁涓诲姙鏂硅佹眰鎻愪氦鏉愭枡
5. **鍙備笌瀵规垬**
   - 骞冲彴鑷鍔ㄥ尮閰嶅规垬
   - 绯荤粺鑷鍔ㄨ瘎鍒
   - 鏌ョ湅鎺掑悕鍜岀粨鏋

#### 15.6 姣旇禌娴佺▼锛堟牴鎹鍙傝禌鎸囧崡锛

```
1. 璁块棶骞冲彴缃戠珯
   鈫
2. 涓嬭浇绂荤嚎骞冲彴锛坴1006锛夊拰浣跨敤璇存槑涔
   鈫
3. 闃呰诲拰鐞嗚В鏂囨。
   - 娓告垙瑙勫垯
   - JSON鏍煎紡
   - 鎶鏈鏂囨。
   鈫
4. 寮鍙慉I瀹㈡埛绔
   - WebSocket閫氫俊
   - 鐗屽瀷璇嗗埆
   - 鍐崇瓥閫昏緫
   鈫
5. 鏈鍦版祴璇
   - 杩炴帴娴嬭瘯
   - 瀹屾暣瀵瑰眬娴嬭瘯
   - 澶氬眬绋冲畾鎬ф祴璇
   鈫
6. 鑱旂郴涓诲姙鏂
   - 鍙戦佸弬璧涚敵璇烽偖浠
   - 绛夊緟鍥炲
   鈫
7. 姝ｅ紡鎻愪氦浣滃搧
   - 鏍规嵁瑕佹眰鎻愪氦鏉愭枡
   鈫
8. 鍙備笌瀵规垬
   - 骞冲彴鑷鍔ㄥ尮閰
   - 绯荤粺鑷鍔ㄨ瘎鍒
   鈫
9. 鏌ョ湅鎺掑悕鍜岀粨鏋
   鈫
10. 鎸佺画浼樺寲鎻愬崌
```

#### 15.7 褰撳墠鏋舵瀯鐨勫弬璧涘噯澶囧害璇勪及

| 妯″潡 | 瀹屾垚搴 | 姣旇禌灏辩华搴 | 澶囨敞 |
|------|--------|-----------|------|
| 閫氫俊妯″潡 | 鉁 100% | 鉁 灏辩华 | 鏍稿績鍔熻兘瀹屾暣 |
| 娓告垙閫昏緫 | 鉁 100% | 鉁 灏辩华 | 闇瑕佸疄闄呮祴璇曢獙璇 |
| 鍐崇瓥寮曟搸 | 鈿狅笍 70% | 鈿狅笍 闇浼樺寲 | 绛栫暐闇瑕佸疄鎴樹紭鍖 |
| 鏁版嵁鏀堕泦 | 鉁 100% | 鉁 灏辩华 | 鍙閫夊姛鑳 |
| 淇℃伅鐩戞帶 | 鉁 100% | 鉁 灏辩华 | 鏂板炲姛鑳斤紝鎺ㄨ崘鍚鐢 |
| 閿欒澶勭悊 | 鉁 90% | 鉁 灏辩华 | 闇瑕佸畬鍠勮竟鐣屾儏鍐 |
| 娴嬭瘯瑕嗙洊 | 鈿狅笍 50% | 鈿狅笍 闇鍔犲己 | 闇瑕佹洿澶氶泦鎴愭祴璇 |

**鎬讳綋璇勪及**锛氣渽 **鍙浠ュ弬璧**锛屼絾寤鸿鍦ㄥ喅绛栧紩鎿庡拰娴嬭瘯鏂归潰缁х画浼樺寲銆

### 鍗佸叚銆佸弬璧涙鏌ユ竻鍗

#### 16.1 寮鍙戦樁娈垫鏌ユ竻鍗
- [ ] 涓嬭浇绂荤嚎骞冲彴锛坴1006锛
- [ ] 涓嬭浇浣跨敤璇存槑涔︼紙v1006鐗堟湰锛
- [ ] 闃呰绘父鎴忚勫垯锛堟睙鑻忕渷浣撹偛灞瑙勫垯锛
- [ ] 鐞嗚ВJSON鏍煎紡锛堜弗鏍兼寜鐓у钩鍙版牸寮忥級
- [ ] 寮鍙慦ebSocket閫氫俊妯″潡
- [ ] 瀹炵幇鎵鏈夌墝鍨嬭瘑鍒锛圫ingle/Pair/Trips绛夛級
- [ ] 瀹炵幇鐗屽瀷姣旇緝鍜屽帇鍒跺垽鏂
- [ ] 瀹炵幇鍐崇瓥閫昏緫
- [ ] 瀹炵幇闃熷弸璇嗗埆锛1-3涓闃 (myPos 0-2)锛2-4涓闃 (myPos 1-3)锛
- [ ] 瀹炵幇閰嶅悎绛栫暐
- [ ] 瀹炵幇閿欒澶勭悊鍜岄噸杩炴満鍒
- [ ] 瀹炵幇鏃ュ織绯荤粺
- [ ] 瀹炵幇骞冲彴淇℃伅鐩戞帶妯″潡锛堝彲閫変絾鎺ㄨ崘锛
  - [ ] 淇℃伅鎶撳彇鍣
  - [ ] 淇℃伅瑙ｆ瀽鍣
  - [ ] 淇℃伅瀛樺偍
  - [ ] 閫氱煡绠＄悊鍣

#### 16.2 娴嬭瘯闃舵垫鏌ユ竻鍗
- [ ] 鏈鍦拌繛鎺ユ祴璇曪紙ws://127.0.0.1:23456锛
- [ ] 灞鍩熺綉杩炴帴娴嬭瘯锛堝傞渶瑕侊級
- [ ] 鍗曞眬瀹屾暣娴嬭瘯锛4涓狝I瀹屾暣瀵瑰眬锛
- [ ] 澶氬眬绋冲畾鎬ф祴璇曪紙杩炵画澶氬眬锛
- [ ] 寮傚父鍦烘櫙娴嬭瘯锛堢綉缁滀腑鏂銆佹秷鎭閿欒绛夛級
- [ ] 鎬ц兘娴嬭瘯锛堝搷搴旀椂闂<1绉掞級
- [ ] 缁勯槦鍏崇郴楠岃瘉锛1-3涓闃燂紝2-4涓闃燂級
- [ ] 鐗屽瀷璇嗗埆鍑嗙‘鎬ч獙璇
- [ ] 鍐崇瓥鍚堢悊鎬ч獙璇

#### 16.3 鎻愪氦闃舵垫鏌ユ竻鍗
- [ ] 鍑嗗嘇I瀹㈡埛绔浠ｇ爜/绋嬪簭
- [ ] 缂栧啓浣跨敤璇存槑鏂囨。
- [ ] 缂栧啓鎶鏈鏂囨。锛堟灦鏋勮存槑锛
- [ ] 鍑嗗囨祴璇曟姤鍛婏紙鍙閫夛級
- [ ] 鍑嗗囪仈绯绘柟寮忎俊鎭
- [ ] 鍙戦佸弬璧涚敵璇烽偖浠
  - [ ] 閭浠朵富棰橈細鎺艰泲AI绠楁硶瀵规姉 - 鍙傝禌鐢宠
  - [ ] 鏀朵欢浜猴細chenxg@njupt.edu.cn 鎴 wuguduofeng@gmail.com
  - [ ] 鍐呭瑰寘鍚锛氬凡瀹屾垚宸ヤ綔銆丄I鐗圭偣銆佸笇鏈涗簡瑙ｇ殑闂棰
- [ ] 绛夊緟涓诲姙鏂瑰洖澶
- [ ] 鏍规嵁瑕佹眰姝ｅ紡鎻愪氦浣滃搧

#### 16.4 鎶鏈瑕佺偣妫鏌
- [ ] WebSocket杩炴帴鍦板潃姝ｇ‘锛堟湰鍦/灞鍩熺綉锛
- [ ] JSON娑堟伅鏍煎紡涓ユ牸绗﹀悎骞冲彴瑕佹眰 (["Bomb", "2", ["H2", "D2", "C2", "S2"]])
- [ ] 鎵鏈夌墝鍨嬮兘鑳芥ｇ‘璇嗗埆
- [ ] 缁勯槦鍏崇郴姝ｇ‘璇嗗埆锛1-3涓闃燂紝2-4涓闃燂級
- [ ] 鎶楄础瑙勫垯姝ｇ‘澶勭悊锛坴1006鐗堟湰锛宼ribute/back锛
- [ ] 鍝嶅簲鏃堕棿鎺у埗鍦ㄥ悎鐞嗚寖鍥达紙<1绉掞級
- [ ] 閿欒澶勭悊鍜岄噸杩炴満鍒跺畬鍠
- [ ] 鏃ュ織璁板綍瀹屾暣
- [ ] 淇℃伅鐩戞帶鍔熻兘娴嬭瘯锛堝傚凡瀹炵幇锛
  - [ ] 淇℃伅鎶撳彇鍑嗙‘鎬
  - [ ] 閫氱煡鍔熻兘姝ｅ父
  - [ ] 淇℃伅瀛樺偍姝ｇ‘

### 鍗佷竷銆佸悗缁浼樺寲鏂瑰悜

#### 17.1 绠楁硶浼樺寲
1. **寮哄寲瀛︿範闆嗘垚**: 浣跨敤鏀堕泦鐨勬暟鎹璁缁僐L妯″瀷
2. **娣卞害瀛︿範**: 浣跨敤绁炵粡缃戠粶杩涜屽喅绛
3. **澶氱瓥鐣ヨ瀺鍚**: 缁撳悎澶氱嶇瓥鐣ョ畻娉
4. **瀹炴椂瀛︿範**: 鍦ㄧ嚎瀛︿範鍜岄傚簲
5. **閰嶅悎绛栫暐浼樺寲**: 鎻愬崌闃熷弸閰嶅悎榛樺戝害
6. **璁扮墝鍜屾帹鐞**: 瀹炵幇璁扮墝鍔熻兘鍜屽规墜鐗屾帹鐞

#### 17.2 鎬ц兘浼樺寲
1. **鍐崇瓥閫熷害**: 鎻愬崌鍐崇瓥閫熷害锛岀‘淇<1绉掑搷搴
2. **鍐呭瓨浼樺寲**: 鍑忓皯鍐呭瓨鍗犵敤锛岄伩鍏嶅唴瀛樻硠婕
3. **骞跺彂澶勭悊**: 浼樺寲寮傛ュ勭悊鎬ц兘
4. **浠ｇ爜浼樺寲**: 鎻愬崌浠ｇ爜鎵ц屾晥鐜

#### 17.3 姣旇禌浼樺寲
1. **閽堝硅瘎鍒嗘爣鍑嗕紭鍖**: 鏍规嵁姣旇禌璇勫垎缁村害浼樺寲绛栫暐
2. **鑳滅巼鎻愬崌**: 閫氳繃澶ч噺瀵规垬璁缁冩彁鍗囪儨鐜
3. **绋冲畾鎬ф彁鍗**: 纭淇濋暱鏃堕棿杩愯屾棤寮傚父
4. **绛栫暐娣卞害**: 鎻愬崌鍐崇瓥绛栫暐鐨勬繁搴﹀拰骞垮害

#### 17.4 鍙傝冨︿範鏂瑰悜
1. **鍗椾含澶у﹂珮闃冲洟闃**: 鐮旂┒SDMC鏂规硶锛堢浜屽眾涓鍥戒汉宸ユ櫤鑳藉崥寮堢畻娉曞ぇ璧涙幖铔嬮」鐩鍐犲啗锛
2. **娓呭崕澶у﹀攼鏉板洟闃**: 鐮旂┒澶у瀷璇瑷妯″瀷鍦ㄦ幖铔嬬瓑妫嬬墝娓告垙涓鐨勫簲鐢
3. **Botzone骞冲彴**: 鍙傝冩枟鍦颁富AI鐨勫疄鐜版柟娉
4. **瀛︽湳璁烘枃**: 鍏虫敞鐩稿叧AI鍗氬紙绠楁硶鐮旂┒

### 鍗佸叓銆佸揩閫熷紑濮嬫寚鍗

#### 18.1 绔嬪嵆琛屽姩锛堜粖澶╋級
1. 鉁 璁块棶骞冲彴缃戠珯锛歨ttps://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
2. 鉁 涓嬭浇绂荤嚎骞冲彴锛坴1006锛夊拰浣跨敤璇存槑涔
3. 鉁 寮濮嬮槄璇绘枃妗ｏ紝鐞嗚В娓告垙瑙勫垯鍜孞SON鏍煎紡

#### 18.2 鏈鍛ㄥ畬鎴
1. 鉁 鐞嗚В娓告垙瑙勫垯锛堟睙鑻忕渷浣撹偛灞瑙勫垯锛
2. 鉁 鐞嗚ВJSON鏍煎紡鍜屾秷鎭绫诲瀷 (type: notify/act, stage: beginning/play)
3. 鉁 鎼寤哄紑鍙戠幆澧冿紙Python + WebSocket搴擄級
4. 鉁 瀹炵幇鍩虹WebSocket閫氫俊

#### 18.3 鏈鏈堝畬鎴
1. 鉁 瀹炵幇鎵鏈夌墝鍨嬭瘑鍒
2. 鉁 瀹炵幇鐗屽瀷姣旇緝鍜屽帇鍒跺垽鏂
3. 鉁 瀹炵幇鍩虹鍐崇瓥閫昏緫
4. 鉁 瀹屾垚鏈鍦版祴璇曪紙杩炴帴鍜屽崟灞娴嬭瘯锛

#### 18.4 涓嬫湀瀹屾垚
1. 鉁 瀹炵幇閰嶅悎绛栫暐
2. 鉁 浼樺寲鍐崇瓥绠楁硶
3. 鉁 瀹屾垚澶氬眬绋冲畾鎬ф祴璇
4. 鉁 鍑嗗囨彁浜ゆ潗鏂

### 鍗佷節銆侀噸瑕佹彁閱

#### 19.1 鎶鏈瑕佺偣
- 鈿狅笍 **涓ユ牸鎸夌収JSON鏍煎紡**锛氬钩鍙板笿SON鏍煎紡瑕佹眰涓ユ牸锛屽繀椤诲畬鍏ㄧ﹀悎 (["Bomb", "2", ["H2", "D2", "C2", "S2"]])
- 鈿狅笍 **缁勯槦瑙勫垯**锛氱1銆3涓杩炴帴涓轰竴闃 (myPos 0-2)锛岀2銆4涓杩炴帴涓轰竴闃 (myPos 1-3)锛屽繀椤绘ｇ‘璇嗗埆
- 鈿狅笍 **鍝嶅簲鏃堕棿**锛氬缓璁鍐崇瓥鏃堕棿<1绉掞紝閬垮厤瓒呮椂
- 鈿狅笍 **鐗堟湰鍏煎**锛氬綋鍓嶄娇鐢╲1006鐗堟湰锛屾敞鎰忔姉璐¤勫垯璋冩暣 (tribute/back)
- 鈿狅笍 **淇℃伅鐩戞帶**锛氬缓璁鍚鐢ㄤ俊鎭鐩戞帶鍔熻兘锛屽強鏃朵簡瑙ｅ钩鍙板姩鎬佸拰姣旇禌淇℃伅
- 鈿狅笍 **鎶撳彇棰戠巼**锛氫俊鎭鎶撳彇搴旇剧疆鍚堢悊闂撮殧锛堟鏌ラ棿闅斺墺6灏忔椂锛夛紝涓旀瘡鏃0:00-6:00涓洪潤榛樻椂娈典笉杩涜屾鏌ワ紝閬垮厤杩囦簬棰戠箒璇锋眰

#### 19.2 寮鍙戝缓璁
- 鉁 **鍏堝疄鐜板熀纭鍔熻兘**锛氱‘淇濊兘姝ｅ父杩炴帴鍜岄氫俊
- 鉁 **閫愭ヤ紭鍖**锛氬厛瀹炵幇鍩烘湰绛栫暐锛屽啀閫愭ヤ紭鍖
- 鉁 **鍏呭垎娴嬭瘯**锛氭湰鍦板畬鏁存祴璇曞悗鍐嶆彁浜
- 鉁 **淇濇寔鑱旂郴**锛氶亣鍒伴棶棰樺強鏃惰仈绯讳富鍔炴柟

#### 19.3 鍙傝禌寤鸿
- 馃摟 **鎻愬墠鑱旂郴**锛氬紑鍙戝畬鎴愬悗鎻愬墠鑱旂郴涓诲姙鏂逛簡瑙ｆ彁浜よ佹眰
- 馃摑 **鍑嗗囨枃妗**锛氬噯澶囧ソ浣跨敤璇存槑鍜屾妧鏈鏂囨。
- 馃И **鍏呭垎娴嬭瘯**锛氱‘淇濈ǔ瀹氭у拰姝ｇ‘鎬
- 馃殌 **鎸佺画浼樺寲**锛氬弬璧涘悗鏍规嵁瀵规垬缁撴灉鎸佺画浼樺寲

### 浜屽崄銆佷俊鎭鐩戞帶鍔熻兘璇存槑

#### 20.1 鍔熻兘姒傝堪
淇℃伅鐩戞帶妯″潡鐢ㄤ簬鑷鍔ㄦ姄鍙栧崡浜閭鐢靛ぇ瀛︽幖铔婣I骞冲彴鐨勫姩鎬佷俊鎭锛屽府鍔╃敤鎴峰強鏃朵簡瑙ｏ細
- 骞冲彴鍏鍛婂拰閫氱煡
- 姣旇禌淇℃伅鍜屾椂闂村畨鎺
- 骞冲彴鐗堟湰鏇存柊
- 鏂囨。鏇存柊
- 閲嶈佽勫垯鍙樻洿

#### 20.2 浣跨敤鏂瑰紡

##### 鍚鐢ㄤ俊鎭鐩戞帶
鍦ㄩ厤缃鏂囦欢涓璁剧疆锛
```yaml
info_monitor:
  enabled: true  # 鍚鐢ㄤ俊鎭鐩戞帶
  check_interval: 21600  # 妫鏌ラ棿闅旓紙绉掞級锛岄粯璁6灏忔椂锛堚墺6灏忔椂锛
  quiet_hours:  # 闈欓粯鏃舵碉紝涓嶈繘琛屾鏌
    enabled: true  # 鏄鍚﹀惎鐢ㄩ潤榛樻椂娈
    start: "00:00"  # 闈欓粯寮濮嬫椂闂达紙24灏忔椂鍒讹級
    end: "06:00"    # 闈欓粯缁撴潫鏃堕棿锛24灏忔椂鍒讹級
```

##### 鏌ョ湅淇℃伅
- 鎺у埗鍙拌緭鍑猴細鏂颁俊鎭浼氳嚜鍔ㄥ湪鎺у埗鍙版樉绀
- 鏃ュ織鏂囦欢锛氫俊鎭浼氳板綍鍒版棩蹇楁枃浠
- 鏁版嵁鏂囦欢锛氫俊鎭淇濆瓨鍦 `data/platform_info/` 鐩褰

##### 鎵嬪姩妫鏌
鍙浠ラ氳繃API鎴栧懡浠よ屾墜鍔ㄨЕ鍙戞鏌ワ細
```python
from src.monitor.fetcher import PlatformInfoFetcher
fetcher = PlatformInfoFetcher()
updates = fetcher.check_updates()
```

#### 20.3 鎶鏈瀹炵幇瑕佺偣

##### 缃戦〉鎶撳彇
- 浣跨敤 `requests` 鎴 `httpx` 鍙戦丠TTP璇锋眰
- 璁剧疆鍚堢悊鐨刄ser-Agent鍜岃锋眰澶
- 澶勭悊缃戠粶瓒呮椂鍜岄噸璇曟満鍒
- 閬靛畧robots.txt瑙勫垯锛堝傛湁锛

##### HTML瑙ｆ瀽
- 浣跨敤 `BeautifulSoup` 瑙ｆ瀽HTML鍐呭
- 鏍规嵁缃戠珯缁撴瀯鎻愬彇鍏抽敭淇℃伅
- 澶勭悊鍔ㄦ佸唴瀹癸紙濡傞渶瑕侊紝鍙浣跨敤Selenium锛

##### 鍐呭规娴
- 閫氳繃鍐呭瑰搱甯屾垨鏃堕棿鎴虫娴嬫洿鏂
- 鍘婚噸澶勭悊锛岄伩鍏嶉噸澶嶉氱煡
- 璁板綍鍘嗗彶淇℃伅锛屾敮鎸佹煡璇

##### 閫氱煡鏈哄埗
- 鎺у埗鍙伴氱煡锛氬疄鏃舵樉绀烘柊淇℃伅
- 鏃ュ織璁板綍锛氳板綍鎵鏈夋姄鍙栫殑淇℃伅
- 鍙閫夋墿灞曪細妗岄潰閫氱煡銆侀偖浠堕氱煡绛

##### 闈欓粯鏃舵靛勭悊
- 妫鏌ュ綋鍓嶆椂闂存槸鍚﹀湪闈欓粯鏃舵碉紙0:00-6:00锛
- 濡傛灉鍦ㄩ潤榛樻椂娈碉紝璺宠繃鏈娆℃鏌
- 璁＄畻涓嬫℃鏌ユ椂闂存椂锛屽傛灉钀藉湪闈欓粯鏃舵碉紝鑷鍔ㄥ欢鍚庡埌闈欓粯鏃舵电粨鏉
- 瀹炵幇绀轰緥锛
  ```python
  def is_quiet_hours(self, current_time: datetime) -> bool:
      hour = current_time.hour
      return 0 <= hour < 6
  
  def schedule_next_check(self, current_time: datetime, interval: int) -> datetime:
      next_check = current_time + timedelta(seconds=interval)
      if self.is_quiet_hours(next_check):
          # 寤跺悗鍒伴潤榛樻椂娈电粨鏉燂紙6:00锛
          next_check = next_check.replace(hour=6, minute=0, second=0)
      return next_check
  ```

#### 20.4 娉ㄦ剰浜嬮」

##### 鍚堣勬
- 閬靛畧缃戠珯浣跨敤鏉℃
- 璁剧疆鍚堢悊鐨勬姄鍙栭戠巼锛堟鏌ラ棿闅斺墺6灏忔椂锛
- 闈欓粯鏃舵碉紙0:00-6:00锛変笉杩涜屾鏌ワ紝鍑忓皯瀵规湇鍔″櫒鐨勫奖鍝
- 涓嶈佸规湇鍔″櫒閫犳垚鍘嬪姏
- 灏婇噸缃戠珯鐨勫弽鐖铏鏈哄埗

##### 绋冲畾鎬
- 澶勭悊缃戠粶閿欒鍜岃秴鏃
- 澶勭悊HTML缁撴瀯鍙樺寲
- 瀹炵幇閿欒鎭㈠嶆満鍒
- 璁板綍鎶撳彇澶辫触鏃ュ織

##### 鍙缁存姢鎬
- 缃戠珯缁撴瀯鍙鑳藉彉鍖栵紝闇瑕佸強鏃舵洿鏂拌В鏋愰昏緫
- 寤鸿瀹氭湡妫鏌ユ姄鍙栧姛鑳芥槸鍚︽ｅ父
- 淇濇寔浠ｇ爜鐨勫彲鎵╁睍鎬

#### 20.5 鎵╁睍鍔熻兘锛堝彲閫夛級

##### 閭浠堕氱煡
閰嶇疆閭浠舵湇鍔★紝閲嶈佷俊鎭鑷鍔ㄥ彂閫侀偖浠讹細
```yaml
info_monitor:
  notification:
    email: true
    email_config:
      smtp_server: "smtp.example.com"
      smtp_port: 587
      username: "your_email@example.com"
      password: "your_password"
      to_email: "recipient@example.com"
```

##### 妗岄潰閫氱煡
浣跨敤绯荤粺閫氱煡鍔熻兘锛堥渶瑕侀濆栧簱锛夛細
```python
# 闇瑕佸畨瑁: plyer 鎴 win10toast (Windows)
from plyer import notification
notification.notify(
    title="骞冲彴鏇存柊",
    message="鍙戠幇鏂扮殑姣旇禌淇℃伅",
    timeout=10
)
```

##### 澶氬钩鍙扮洃鎺
鍙浠ユ墿灞曠洃鎺у叾浠栫浉鍏冲钩鍙帮細
- 涓鍥戒汉宸ユ櫤鑳藉︿細瀹樼綉
- 鍏朵粬鎺艰泲AI姣旇禌骞冲彴
- 鐩稿叧瀛︽湳浼氳缃戠珯

## 搴旂敤鍦烘櫙
- **寮鍙戦樁娈**锛氭寚瀵兼幖铔婣I瀹㈡埛绔鐨勬灦鏋勮捐″拰妯″潡瀹炵幇
- **娴嬭瘯闃舵**锛氫綔涓烘祴璇曞拰楠岃瘉鐨勬爣鍑嗗弬鑰
- **姣旇禌鍑嗗**锛氱‘淇濆弬璧涗綔鍝佺﹀悎骞冲彴瑕佹眰鍜屾妧鏈瑙勮寖
- **缁存姢闃舵**锛氫綔涓烘枃妗ｅ弬鑰冿紝渚夸簬鍚庣画浼樺寲鍜屾墿灞
- **淇℃伅鐩戞帶**锛氳嚜鍔ㄨ幏鍙栧钩鍙板姩鎬侊紝鍙婃椂鍝嶅簲姣旇禌鍜屾洿鏂颁俊鎭

## 绀轰緥/妗堜緥
- **瀹屾暣瀵瑰眬绀轰緥**锛4涓狝I瀹㈡埛绔杩炴帴锛屽畬鎴愪竴灞娓告垙锛岄獙璇佺粍闃 (myPos 0 vs 1-3闃)鍜屽喅绛 (curAction: ["Single", "2", ["H2"]])
- **淇℃伅鐩戞帶绀轰緥**锛氭娴嬪埌鏂版瘮璧涘叕鍛婏紝鑷鍔ㄩ氱煡骞朵繚瀛樺埌 data/platform_info/announcements.json
- **閿欒鎭㈠嶇ず渚**锛歐ebSocket鏂寮鍚庤嚜鍔ㄩ噸杩烇紝鎭㈠嶆父鎴忕姸鎬 (stage: play)

## 娉ㄦ剰浜嬮」
- **骞冲彴鍙橀噺缁熶竴**锛氭墍鏈夌墝鍨 (Single/Bomb)銆佽姳鑹 (S/H/D/C)銆佺姸鎬 (myPos/curPos/stage) 蹇呴』浣跨敤骞冲彴鏍囧噯鍙橀噺鍚
- **鏃堕棿澶勭悊**锛氭墍鏈夋椂闂村瓧娈典娇鐢ㄧ郴缁熸椂闂碅PI (datetime.now())锛岀佹㈢‖缂栫爜
- **鍝嶅簲鏃堕棿**锛氬喅绛栨椂闂存帶鍒跺湪1绉掍互鍐咃紝閬垮厤瓒呮椂
- **缁勯槦璇嗗埆**锛氫弗鏍兼寜鐓у钩鍙拌勫垯锛岀1/3杩炴帴涓轰竴闃 (myPos 0/2)
- **淇℃伅鎶撳彇鍚堣**锛氭鏌ラ棿闅斺墺6灏忔椂锛岄潤榛樻椂娈 (00:00-06:00) 涓嶆姄鍙
- **JSON鏍煎紡**锛氫弗鏍奸伒瀹堝钩鍙版牸寮忥紝绀轰緥锛歔"Bomb", "2", ["H2", "D2", "C2", "S2"]]
- **鍔ㄤ綔绌洪棿浼樺寲**锛氬垵濮嬬姸鎬佸彲鑳>5000鍚堟硶鍔ㄤ綔锛屽繀椤讳娇鐢ㄥ姩浣滅┖闂翠紭鍖栧櫒蹇閫熺瓫閫夛紝閬垮厤璇勪及鎵鏈夊欓夊艰嚧瓒呮椂
- **鐗瑰緛缂栫爜**锛氱姸鎬佸拰鍔ㄤ綔鐗瑰緛缂栫爜鍙鎻愬崌璇勪及鏁堢巼锛屼负鏈鏉ュ己鍖栧︿範闆嗘垚鎵撲笅鍩虹锛屽缓璁鍚鐢

## 鐩稿叧鐭ヨ瘑鐐
- [鎺艰泲AI鐭ヨ瘑搴撴牸寮忓寲鏂规圿 - 鐭ヨ瘑搴撴牸寮忓寲鏍囧噯锛屼笌鏈鏂囨。绗3.4鑺"鐭ヨ瘑搴撴ā鍧"瀹屽叏瀵归綈
- [鎺艰泲AI鐭ヨ瘑搴旂敤妗嗘灦] - 鐭ヨ瘑搴旂敤妗嗘灦璁捐★紝璇存槑AI濡備綍鎺屾彙鍜屽簲鐢850+涓鐭ヨ瘑鐐癸紝宸叉暣鍚堝埌鏈鏂囨。绗3.4.6鑺
- [姹熻嫃鎺艰泲瑙勫垯 - 鐗屽瀷瀹氫箟 (Single/Pair/Bomb)]
- [骞冲彴浣跨敤璇存槑涔 v1006 - JSON鏍煎紡鍜屾秷鎭绫诲瀷]
- [DanZero+璁烘枃鍒嗘瀽-鏋舵瀯鍊熼壌寤鸿甝 - 鍔ㄤ綔绌洪棿浼樺寲鍜岀壒寰佺紪鐮佹妧鏈

---

**鏂囨。鐗堟湰**: v2.5  
**鍒涘缓鏃堕棿**: 浣跨敤绯荤粺鏃堕棿API鑾峰彇锛坄datetime.now()`锛  
**鏈鍚庢洿鏂**: 浣跨敤绯荤粺鏃堕棿API鑾峰彇锛坄datetime.now()`锛- 鏁村悎鐭ヨ瘑搴旂敤妗嗘灦  
**缁存姢璐ｄ换**: AI寮鍙戝洟闃

## 馃摑 鏇存柊鏃ュ織

### v2.6 (2025-11-26)
- 鉁 鏇存柊鍑虹墝椤哄簭璇存槑锛堝钩鍙板疄闄呭疄鐜颁负椤烘椂閽堬級
- 鉁 娣诲姞浣嶇疆鍏崇郴璁＄畻鍏寮忥紙涓婂躲佷笅瀹躲佸瑰讹級
- 鉁 鏄庣‘骞冲彴鍑虹墝椤哄簭锛0 鈫 1 鈫 2 鈫 3 鈫 0...锛堥『鏃堕拡锛
- 鉁 璇存槑铏界劧瑙勫垯璇"閫嗘椂閽"锛屼絾骞冲彴瀹炵幇涓洪『鏃堕拡锛屽簲浠ュ钩鍙颁负鍑

### v2.5 (2025-01-27)
- 鉁 鏁村悎銆婃幖铔婣I鐭ヨ瘑搴旂敤妗嗘灦.md銆嬪埌鏋舵瀯鏂规
- 鉁 鍦ㄧ煡璇嗗簱妯″潡锛3.4.6鑺傦級娣诲姞鐭ヨ瘑搴旂敤妗嗘灦璁捐
- 鉁 娣诲姞鐭ヨ瘑瑙勬ā缁熻★紙17涓鏂囦欢锛岀害850涓鐭ヨ瘑鐐癸級
- 鉁 娣诲姞鐭ヨ瘑灞傛＄粨鏋勶紙L1纭缂栫爜灞傘丩2绛栫暐寮曟搸灞傘丩3鐭ヨ瘑妫绱㈠眰銆丩4鎺ㄧ悊搴旂敤灞傦級
- 鉁 娣诲姞鍒嗗眰鍐崇瓥绯荤粺瀹炵幇鏂规
- 鉁 娣诲姞鐭ヨ瘑搴旂敤娴佺▼鍜岀ず渚嬩唬鐮
- 鉁 娣诲姞鐭ヨ瘑妫绱浼樺寲绛栫暐锛堢储寮曟瀯寤恒佺紦瀛樼瓥鐣ャ佷紭鍏堢骇鎺掑簭锛
- 鉁 娣诲姞鐭ヨ瘑鎺屾彙绋嬪害璇勪及鏂规硶锛堢煡璇嗚嗙洊鐜囥佸喅绛栧噯纭鐜囥佽儨鐜囨彁鍗囷級
- 鉁 娣诲姞棰勬湡鏁堟灉锛堥樁娈典竴40-50%锛岄樁娈典簩55-65%锛岄樁娈典笁70-80%锛岄樁娈靛洓85%+锛
- 鉁 鏇存柊鐩稿叧鐭ヨ瘑鐐癸紝娣诲姞鐭ヨ瘑搴旂敤妗嗘灦寮曠敤

### v2.4 (2025-01-27)
- 鉁 瀵归綈銆婄煡璇嗗簱鏍煎紡鍖栨柟妗.md銆
- 鉁 鏇存柊鐭ヨ瘑搴撶洰褰曠粨鏋勶紝娣诲姞`rules/`鐩褰曪紝涓庢牸寮忓寲鏂规堜繚鎸佷竴鑷
- 鉁 鍦ㄧ煡璇嗗簱妯″潡閮ㄥ垎娣诲姞涓庢牸寮忓寲鏂规堢殑瀵归綈璇存槑
- 鉁 鏄庣‘鐭ヨ瘑鍒嗙被涓庢牸寮忓寲鏂规堢殑瀵瑰簲鍏崇郴
- 鉁 鏇存柊鎶宸у簱鍜岀煡璇嗘绱㈠櫒閮ㄥ垎锛屾坊鍔犳牸寮忓寲鏂规堝瑰簲璇存槑
- 鉁 鏇存柊鐩稿叧鐭ヨ瘑鐐癸紝娣诲姞鐭ヨ瘑搴撴牸寮忓寲鏂规堝紩鐢

### v2.3 (2025-01-27)
- 鉁 娣诲姞鍔ㄤ綔绌洪棿浼樺寲鍣锛圓ctionSpaceOptimizer锛夋ā鍧楄捐
  - 鏍规嵁鍔ㄤ綔绌洪棿澶у皬鍔ㄦ佺瓫閫夊欓夊姩浣
  - 澶у姩浣滅┖闂村揩閫熺瓫閫塗op-K鍊欓
  - 灏忓姩浣滅┖闂寸簿缁嗚瘎浼版墍鏈夊姩浣
  - 鍊熼壌DanZero+璁烘枃鐨勫姩浣滅┖闂村勭悊绛栫暐
- 鉁 娣诲姞鍔ㄤ綔鐗瑰緛缂栫爜鍣锛圓ctionFeatureEncoder锛夋ā鍧楄捐
  - 灏嗗姩浣滅紪鐮佷负缁撴瀯鍖栫壒寰佸悜閲
  - 鎻愬彇鐗屽瀷銆佸ぇ灏忋佷富鐗屻佺櫨鎼鐗岀瓑鐗瑰緛
  - 鏀鎸佸揩閫熻瘎浼板拰鐩镐技搴﹁＄畻
- 鉁 娣诲姞鐘舵佺壒寰佺紪鐮佸櫒锛圫tateFeatureEncoder锛夋ā鍧楄捐
  - 灏嗘父鎴忕姸鎬佺紪鐮佷负鐗瑰緛鍚戦噺
  - 鎻愬彇鎵嬬墝銆佸巻鍙层佺帺瀹剁姸鎬佺瓑鐗瑰緛
  - 涓烘湭鏉ュ己鍖栧︿範闆嗘垚鍋氬噯澶
- 鉁 澧炲己鍐崇瓥鏃堕棿鎺у埗鍣ㄤ负鑷閫傚簲鍐崇瓥鏃堕棿鎺у埗鍣锛圓daptiveDecisionTimer锛
  - 鏍规嵁鍔ㄤ綔绌洪棿澶у皬鍔ㄦ佽皟鏁存椂闂撮勭畻
  - 澶у姩浣滅┖闂达細鏇村氭椂闂寸敤浜庡揩閫熺瓫閫
  - 灏忓姩浣滅┖闂达細鏇村氭椂闂寸敤浜庣簿缁嗚瘎浼
- 鉁 鏇存柊鏁版嵁娴佽捐★紝闆嗘垚鍔ㄤ綔绌洪棿浼樺寲鍜岀壒寰佺紪鐮佹祦绋
- 鉁 鏇存柊妯″潡渚濊禆鍏崇郴锛屾坊鍔犳柊妯″潡鐨勪緷璧栬存槑
- 鉁 鏇存柊閰嶇疆绠＄悊锛屾坊鍔犲姩浣滅┖闂翠紭鍖栧拰鐗瑰緛缂栫爜閰嶇疆椤
- 鉁 鏇存柊鍏抽敭鎶鏈鐐癸紝璇存槑鍔ㄤ綔绌洪棿浼樺寲鍜岀壒寰佺紪鐮佹妧鏈
- 鉁 鏇存柊椤圭洰鐩褰曠粨鏋勶紝娣诲姞鏂版ā鍧楁枃浠
- 鉁 鏇存柊寮鍙戣″垝锛屾坊鍔犳柊妯″潡鐨勫紑鍙戜换鍔

### v2.2 (2025-11-25)
- 鉁 娣诲姞鐭ヨ瘑搴撴ā鍧楋紙Knowledge Base Module锛夎捐
- 鉁 鏇存柊鏁翠綋鏋舵瀯鍥撅紝澧炲姞鐭ヨ瘑搴撳眰
- 鉁 璁捐″垎灞傝板繂绛栫暐锛堢‖缂栫爜灞傘佸唴瀛樺姞杞藉眰銆佹寜闇鏌ヨ㈠眰锛
- 鉁 璁捐¤勫垯搴撱佺瓥鐣ュ簱銆佹妧宸у簱銆佺煡璇嗘绱㈠櫒
- 鉁 鏄庣‘鐭ヨ瘑搴撲娇鐢ㄧ瓥鐣ュ拰鎬ц兘浼樺寲鏂规
- 鉁 娣诲姞鐭ヨ瘑搴撶洰褰曠粨鏋勮存槑
- 鉁 娣诲姞鎺ュ彛璁捐″拰瀹炵幇鏂瑰紡
- 鉁 鏄庣‘鍩虹瑙勫垯纭缂栫爜銆佸父鐢ㄧ瓥鐣ュ唴瀛樺姞杞姐侀珮绾ф妧宸ф寜闇鏌ヨ㈢殑绛栫暐

### v2.1 (浣跨敤绯荤粺鏃堕棿API鑾峰彇)
- 鉁 瀵归綈鐭ヨ瘑搴撴牸寮忓寲鏂规堬紝娣诲姞YAML鍏冩暟鎹
- 鉁 鏍囧噯鍖栨枃妗ｇ粨鏋 (姒傝堪/璇︾粏鍐呭/搴旂敤鍦烘櫙/娉ㄦ剰浜嬮」)
- 鉁 缁熶竴浣跨敤骞冲彴鍙橀噺鍚 (Single/Bomb/myPos/curPos/stage)
- 鉁 澧炲己淇℃伅鐩戞帶妯″潡璇存槑锛屽寘鍚闈欓粯鏃舵靛勭悊
- 鉁 鏇存柊绀轰緥浠ｇ爜锛岀‘淇濈﹀悎骞冲彴JSON鏍煎紡
- 鉁 娣诲姞鍙傝禌妫鏌ユ竻鍗曞拰蹇閫熷紑濮嬫寚鍗

### v2.0 (浣跨敤绯荤粺鏃堕棿API鑾峰彇)
- 鉁 鍒濆嬫灦鏋勬柟妗堬紝鍖呭惈鍒嗗眰璁捐″拰鏍稿績妯″潡
- 鉁 娣诲姞淇℃伅鐩戞帶鍔熻兘璁捐
- 鉁 瀹屽杽姣旇禌鍙傝禌瑕佹眰鍜岃瘎浼

### v1.0 (浣跨敤绯荤粺鏃堕棿API鑾峰彇)
- 鍩虹鏋舵瀯妗嗘灦璁捐

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

