# 游戏记录保存逻辑修复

## 问题描述

根据M1客户端日志，发现以下问题：

1. **gameOver通知时保存记录**：在收到`gameOver`通知时，游戏记录就被保存了
2. **victoryNum缺失**：此时还没有收到`gameResult`通知，所以`victoryNum`还没有
3. **gameResult通知时current_game为None**：当收到`gameResult`通知时，`current_game`已经是None了（因为已经在`gameOver`时保存并清空）

### 日志证据

```
[10:55:25] [yf1_m1] [INFO] ✓ 识别到游戏结束通知: notification_key=gameOver
[10:55:25] [yf1_m1] [INFO] 游戏结束: {}, current_game=False
游戏记录已保存: ...json
[10:55:25] [yf1_m1] [WARNING] ⚠ 游戏结束通知收到，但current_game为None，可能已经保存过了
[10:55:25] [yf1_m1] [INFO] ✓ 识别到游戏结束通知: notification_key=gameResult
[10:55:25] [yf1_m1] [INFO] 游戏结束: {'victoryNum': [0, 3, 0, 3], ...}, current_game=False
[10:55:25] [yf1_m1] [WARNING] ⚠ 游戏结束通知收到，但current_game为None，可能已经保存过了
```

## 修复方案

### 1. 区分gameOver和gameResult通知

- **gameOver通知**：只记录日志，不保存记录
- **gameResult通知**：提取完整的`victoryNum`信息并保存

### 2. 延迟保存策略

- 只在收到`gameResult`通知时才保存游戏记录
- 确保`victoryNum`被正确保存到记录文件中

### 3. 回退机制

- 如果`current_game`为None（记录已保存），尝试更新已保存的文件
- 从最近保存的记录文件中添加`victoryNum`信息

## 修复内容

### 修改文件

1. **`src/communication/yf1_m1.py`**
   - 修改`_handle_game_over`方法，区分`gameOver`和`gameResult`
   - 添加`_update_latest_record_with_result`方法，用于更新已保存的记录
   - 在`handle_notification`中传递`notification_key`给`_handle_game_over`

2. **`src/communication/game_recorder.py`**
   - 修改`save_records`方法，避免在result为空时保存

## 预期效果

修复后：
- ✅ `gameOver`通知时不会保存记录
- ✅ `gameResult`通知时保存记录，包含完整的`victoryNum`
- ✅ 如果记录已保存，会尝试更新已保存的文件
- ✅ 评估器可以正确提取胜负信息

## 测试建议

1. 运行新的对战测试
2. 检查游戏记录文件，确认`result.victoryNum`字段存在
3. 运行评估器，验证可以正确计算胜率

---

**修复时间**: 2026-01-13  
**修复原因**: 游戏记录在收到victoryNum之前就被保存，导致评估器无法提取胜负信息
