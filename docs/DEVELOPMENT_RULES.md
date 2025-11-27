# 寮鍙戣勮寖涓庤勫垯

## 馃敶 鏍稿績瑙勫垯锛堝繀椤讳弗鏍奸伒瀹堬級

### 1. 鏃堕棿澶勭悊瑙勫垯 鈿狅笍 寮哄埗瑕佹眰

**鎵鏈夋秹鍙婂綋鍓嶆椂闂淬佸疄鏃舵椂闂寸殑鍦烘櫙蹇呴』璋冪敤绯荤粺鏃堕棿API锛岀佹浣跨敤纭缂栫爜鏃堕棿銆**

#### 瑙勫垯璇存槑
- 鉁 **蹇呴』浣跨敤**: `datetime.now()` 鑾峰彇绯荤粺褰撳墠鏃堕棿
- 鉂 **绂佹浣跨敤**: 纭缂栫爜鐨勬椂闂村瓧绗︿覆銆佸浐瀹氭椂闂存埑
- 鉁 **鍏佽镐娇鐢**: 鍥哄畾鐨勫巻鍙叉棩鏈燂紙濡"2025骞10鏈5鏃"杩欐牱鐨勫叿浣撳巻鍙叉椂闂达級

#### 姝ｇ‘绀轰緥

```python
from datetime import datetime, timedelta

# 鉁 鑾峰彇褰撳墠鏃堕棿
current_time = datetime.now()

# 鉁 鑾峰彇褰撳墠鏃堕棿鎴
timestamp = datetime.now().timestamp()

# 鉁 鏍煎紡鍖栧綋鍓嶆椂闂
formatted_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 鉁 鍒ゆ柇鏄鍚﹀湪闈欓粯鏃舵
def is_quiet_hours():
    now = datetime.now()  # 蹇呴』璋冪敤绯荤粺鏃堕棿
    hour = now.hour
    return 0 <= hour < 6

# 鉁 璁＄畻涓嬫℃鏌ユ椂闂
def schedule_next_check(interval):
    next_time = datetime.now() + timedelta(seconds=interval)
    return next_time

# 鉁 璁板綍鏃ュ織鏃堕棿
log_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 鉁 鏂囦欢鍛藉悕鏃堕棿鎴
filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
```

#### 閿欒绀轰緥

```python
# 鉂 閿欒锛氱‖缂栫爜鏃堕棿
current_time = "2025-01-01 12:00:00"

# 鉂 閿欒锛氫娇鐢ㄥ浐瀹氭椂闂存埑
timestamp = 1704067200

# 鉂 閿欒锛氬湪浠ｇ爜涓鍐欐绘椂闂
if hour == 12:  # 搴旇ヤ粠绯荤粺鏃堕棿鑾峰彇

# 鉂 閿欒锛氫娇鐢ㄥ浐瀹氱殑鏃堕棿瀵硅薄
fixed_time = datetime(2025, 1, 1, 12, 0, 0)  # 闄ら潪鏄鍘嗗彶鏃ユ湡
```

#### 閫傜敤鍦烘櫙

| 鍦烘櫙 | 蹇呴』浣跨敤绯荤粺鏃堕棿 | 绀轰緥 |
|------|----------------|------|
| 鏃ュ織鏃堕棿鎴 | 鉁 鏄 | `datetime.now()` |
| 淇℃伅鎶撳彇鏃堕棿 | 鉁 鏄 | `datetime.now()` |
| 闈欓粯鏃舵靛垽鏂 | 鉁 鏄 | `datetime.now().hour` |
| 瀹氭椂浠诲姟璋冨害 | 鉁 鏄 | `datetime.now() + timedelta(...)` |
| 鏁版嵁璁板綍鏃堕棿 | 鉁 鏄 | `datetime.now()` |
| 鏂囦欢鍛藉悕鏃堕棿鎴 | 鉁 鏄 | `datetime.now().strftime(...)` |
| 鍘嗗彶鏃ユ湡璁板綍 | 鉂 鍚 | 鍙浠ヤ娇鐢ㄥ浐瀹氭棩鏈 |

#### 鏃堕棿澶勭悊宸ュ叿鍑芥暟

寤鸿鍦ㄩ」鐩涓鍒涘缓缁熶竴鐨勬椂闂村勭悊宸ュ叿鍑芥暟锛

```python
from datetime import datetime, timedelta
from typing import Optional

class TimeUtils:
    """鏃堕棿澶勭悊宸ュ叿绫"""
    
    @staticmethod
    def get_current_time() -> datetime:
        """鑾峰彇褰撳墠绯荤粺鏃堕棿"""
        return datetime.now()
    
    @staticmethod
    def get_current_timestamp() -> float:
        """鑾峰彇褰撳墠鏃堕棿鎴"""
        return datetime.now().timestamp()
    
    @staticmethod
    def format_time(dt: Optional[datetime] = None, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
        """鏍煎紡鍖栨椂闂"""
        if dt is None:
            dt = datetime.now()  # 榛樿や娇鐢ㄥ綋鍓嶆椂闂
        return dt.strftime(fmt)
    
    @staticmethod
    def is_quiet_hours(current_time: Optional[datetime] = None) -> bool:
        """鍒ゆ柇鏄鍚﹀湪闈欓粯鏃舵碉紙0:00-6:00锛"""
        if current_time is None:
            current_time = datetime.now()  # 蹇呴』璋冪敤绯荤粺鏃堕棿
        hour = current_time.hour
        return 0 <= hour < 6
    
    @staticmethod
    def schedule_next_check(interval: int, current_time: Optional[datetime] = None) -> datetime:
        """璁＄畻涓嬫℃鏌ユ椂闂达紙閬垮紑闈欓粯鏃舵碉級"""
        if current_time is None:
            current_time = datetime.now()  # 蹇呴』璋冪敤绯荤粺鏃堕棿
        
        next_check = current_time + timedelta(seconds=interval)
        
        # 濡傛灉钀藉湪闈欓粯鏃舵碉紝寤跺悗鍒伴潤榛樻椂娈电粨鏉
        if TimeUtils.is_quiet_hours(next_check):
            next_check = next_check.replace(hour=6, minute=0, second=0)
        
        return next_check
```

### 2. JSON鏍煎紡瑙勫垯

- **涓ユ牸閬靛惊骞冲彴JSON鏍煎紡瑕佹眰**
- 鎵鏈夋秷鎭蹇呴』绗﹀悎骞冲彴瑙勮寖
- 娑堟伅鏍煎紡楠岃瘉蹇呴』閫氳繃
- 绂佹㈤殢鎰忎慨鏀笿SON缁撴瀯

### 3. 缁勯槦瑙勫垯

- **绗1涓鍜岀3涓杩炴帴**鐨凙I鑷鍔ㄤ负涓闃
- **绗2涓鍜岀4涓杩炴帴**鐨凙I鑷鍔ㄤ负涓闃
- 蹇呴』姝ｇ‘璇嗗埆闃熷弸骞堕厤鍚
- 缁勯槦鍏崇郴鍦ㄨ繛鎺ユ椂纭瀹氾紝涓嶅彲鏇存敼

### 4. 鍝嶅簲鏃堕棿瑙勫垯

- 鍐崇瓥鍝嶅簲鏃堕棿寤鸿 < 1绉
- 閬垮厤瓒呮椂瀵艰嚧鍒よ礋
- 浼樺寲绠楁硶纭淇濆強鏃跺搷搴

### 5. 淇℃伅鐩戞帶瑙勫垯

- 妫鏌ラ棿闅 鈮 6灏忔椂
- 姣忔棩 0:00-6:00 涓洪潤榛樻椂娈碉紝涓嶈繘琛屾鏌
- 閬靛畧缃戠珯浣跨敤鏉℃撅紝涓嶉犳垚鏈嶅姟鍣ㄥ帇鍔
- 浣跨敤绯荤粺鏃堕棿鍒ゆ柇闈欓粯鏃舵

## 馃摑 浠ｇ爜瑙勮寖

### Python浠ｇ爜瑙勮寖

- 閬靛惊 PEP 8 Python浠ｇ爜瑙勮寖
- 浣跨敤绫诲瀷鎻愮ず锛圱ype Hints锛
- 缂栧啓娓呮櫚鐨勬敞閲婂拰鏂囨。瀛楃︿覆
- 鍑芥暟鍜岀被瑕佹湁娓呮櫚鐨勫懡鍚

### 鏂囨。瑙勮寖

- **鏂囨。灏介噺绠娲**锛氶伩鍏嶄竴娆℃х敓鎴愯繃闀挎枃妗ｅ艰嚧瓒呮椂
- **鍏堝垪鎻愮翰鍐嶅～鍏**锛氬厛鍒涘缓鏂囨。妗嗘灦鍜屾彁绾插苟淇濆瓨锛屽啀閫愭ュ～鍏呭唴瀹
- **瀹氭湡淇濆瓨**锛氭瘡3鍒嗛挓淇濆瓨涓娆★紝閬垮厤闀挎椂闂寸紪杈戝艰嚧鍐呭逛涪澶
- **閬靛畧鏃堕棿瑙勮寖**锛氭枃妗ｄ腑鐨勬椂闂翠俊鎭搴斾娇鐢ㄧ郴缁熸椂闂碅PI锛岀佹㈢‖缂栫爜鏃堕棿

### 鏃堕棿澶勭悊瑙勮寖

#### 蹇呴』浣跨敤绯荤粺鏃堕棿API

```python
# 鉁 姝ｇ‘
from datetime import datetime
current_time = datetime.now()

# 鉂 閿欒
current_time = "2025-01-01 12:00:00"
```

#### 鏃堕棿澶勭悊宸ュ叿鍑芥暟

寤鸿浣跨敤缁熶竴鐨勬椂闂村勭悊宸ュ叿鍑芥暟锛岄伩鍏嶅湪浠ｇ爜涓鐩存帴璋冪敤 `datetime.now()`锛屼究浜庢祴璇曞拰缁存姢銆

### 閿欒澶勭悊瑙勮寖

- 鎵鏈夊彲鑳藉け璐ョ殑鎿嶄綔閮借佹湁寮傚父澶勭悊
- 璁板綍璇︾粏鐨勯敊璇鏃ュ織
- 鎻愪緵鏈夋剰涔夌殑閿欒淇℃伅

### 鏃ュ織瑙勮寖

- 浣跨敤缁熶竴鐨勬棩蹇楁牸寮
- 鏃ュ織鏃堕棿鎴冲繀椤讳娇鐢ㄧ郴缁熸椂闂
- 鍖哄垎涓嶅悓绾у埆鐨勬棩蹇楋紙DEBUG/INFO/WARNING/ERROR锛

## 馃И 娴嬭瘯瑙勮寖

### 鍗曞厓娴嬭瘯

- 鎵鏈夋牳蹇冨姛鑳介兘瑕佹湁鍗曞厓娴嬭瘯
- 娴嬭瘯鏃堕棿鐩稿叧鍔熻兘鏃讹紝鍙浠ヤ娇鐢╩ock鏃堕棿
- 纭淇濇祴璇曠殑鍙閲嶅嶆

### 鏃堕棿娴嬭瘯绀轰緥

```python
from unittest.mock import patch
from datetime import datetime

def test_is_quiet_hours():
    """娴嬭瘯闈欓粯鏃舵靛垽鏂"""
    # 娴嬭瘯鍑屾櫒3鐐癸紙鍦ㄩ潤榛樻椂娈碉級
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 1, 1, 3, 0, 0)
        assert is_quiet_hours() == True
    
    # 娴嬭瘯涓婂崍10鐐癸紙涓嶅湪闈欓粯鏃舵碉級
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 1, 1, 10, 0, 0)
        assert is_quiet_hours() == False
```

## 鈿狅笍 甯歌侀敊璇

### 鏃堕棿澶勭悊閿欒

1. **纭缂栫爜鏃堕棿**
   ```python
   # 鉂 閿欒
   if datetime.now().hour == 12:
       do_something()
   ```

2. **浣跨敤鍥哄畾鏃堕棿鎴**
   ```python
   # 鉂 閿欒
   timestamp = 1704067200
   ```

3. **蹇樿拌皟鐢ㄧ郴缁熸椂闂**
   ```python
   # 鉂 閿欒
   def get_time():
       return "2025-01-01 12:00:00"  # 搴旇ヨ繑鍥瀌atetime.now()
   ```

## 鉁 妫鏌ユ竻鍗

寮鍙戞椂璇风‘淇濓細
- [ ] 鎵鏈夋椂闂寸浉鍏充唬鐮侀兘浣跨敤 `datetime.now()`
- [ ] 娌℃湁纭缂栫爜鐨勬椂闂村瓧绗︿覆
- [ ] 娌℃湁浣跨敤鍥哄畾鐨勬椂闂存埑
- [ ] 鏃堕棿澶勭悊鍑芥暟閮芥湁閫傚綋鐨勬祴璇
- [ ] 鏃ュ織鏃堕棿鎴充娇鐢ㄧ郴缁熸椂闂
- [ ] 瀹氭椂浠诲姟鍩轰簬绯荤粺鏃堕棿璁＄畻

## 馃摎 鐩稿叧鏂囨。

- [README.md](../README.md) - 椤圭洰涓绘枃妗ｏ紙鍖呭惈鏃堕棿澶勭悊瑙勫垯锛
- [鏋舵瀯鏂规圿(鎺艰泲AI瀹㈡埛绔鏋舵瀯鏂规.md) - 璇︾粏鎶鏈鏂囨。

---

**閲嶈佹彁閱**: 鏃堕棿澶勭悊瑙勫垯鏄椤圭洰鐨勬牳蹇冭勫垯涔嬩竴锛屾墍鏈夊紑鍙戣呭繀椤讳弗鏍奸伒瀹堬紒

