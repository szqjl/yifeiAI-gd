# batch_executor自动重启说明

## 问题背景

根据掼蛋平台使用说明书，**服务器每次启动只执行3场比赛**。但工作流需要完成50场（或更多）比赛。

## 解决方案

**batch_executor已经内置了自动重启功能**，无需手动重新运行！

### batch_executor的自动重启机制

1. **单次运行限制**：`DEFAULT_SINGLE_RUN_LIMIT = 3`（每次服务器启动只运行3场）

2. **自动重启循环**：
   ```python
   while state.completed_games < state.target_games:
       # 计算本批次要执行的场数
       remaining = state.target_games - state.completed_games
       batch_games = min(remaining, 3)  # 每次最多3场
       
       # 启动服务器（执行batch_games场）
       server_process = restart_server(server_path, batch_games)
       
       # 启动客户端
       client_processes = restart_clients(client_scripts)
       
       # 等待游戏完成
       wait_for_completion()
       
       # 更新已完成场数
       state.completed_games += batch_games
       
       # 如果还有剩余场数，自动重启
       if state.completed_games < state.target_games:
           state.restart_count += 1
           state.current_batch += 1
   ```

3. **自动计算重启次数**：
   - 50场游戏 = ceil(50/3) = 17次运行
   - 重启次数 = 17 - 1 = 16次

### 工作流中的使用

工作流（`auto_game_runner`）调用batch_executor时，**已经传递了`--target-games`参数**：

```python
cmd = [
    "python", "-m", "batch_executor",
    "--server-path", self.server_path,
    "--target-games", str(self.num_games),  # ✅ 已传递目标场数
    "--clients"
] + self.clients
```

因此，**batch_executor会自动重启服务器，直到完成所有50场比赛**。

## 验证方法

### 1. 查看batch_executor日志

运行工作流时，batch_executor会输出：

```
预计需要重启 16 次
开始批次 1，执行 3 场游戏
...
准备重启，已完成 3/50 场
开始批次 2，执行 3 场游戏
...
准备重启，已完成 6/50 场
...
所有游戏已完成!
```

### 2. 查看执行状态

batch_executor会创建`execution_state.json`文件，包含：
- `completed_games`: 已完成场数
- `target_games`: 目标场数
- `restart_count`: 重启次数
- `current_batch`: 当前批次

### 3. 查看游戏记录

检查`game_records`目录，应该看到50个（或更多）JSON文件。

## 常见问题

### Q: 为什么我看到batch_executor只运行了3场就停止了？

**A**: 可能的原因：
1. **没有传递`--target-games`参数** - 检查工作流调用
2. **batch_executor进程被中断** - 检查日志和进程状态
3. **服务器启动失败** - 检查服务器路径和权限

### Q: 如何确认batch_executor正在自动重启？

**A**: 查看日志输出：
- 应该看到"开始批次 X"的消息
- 应该看到"准备重启，已完成 X/50 场"的消息
- 应该看到多个批次的执行记录

### Q: 如果batch_executor没有自动重启怎么办？

**A**: 
1. 检查`--target-games`参数是否正确传递
2. 检查batch_executor版本（确保支持自动重启）
3. 查看`execution_state.json`文件，确认状态
4. 手动运行batch_executor测试：
   ```bash
   python -m batch_executor --server-path "D:\GDAI\server\windows\guandan_offline_v1006.exe" --target-games 50 --clients ...
   ```

## 总结

✅ **batch_executor已经支持自动重启**，无需手动操作
✅ **工作流已经正确传递了`--target-games`参数**
✅ **只需运行一次工作流，batch_executor会自动完成所有50场比赛**

---

**最后更新**: 2025-01-10
