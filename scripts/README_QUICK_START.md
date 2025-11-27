# 快速开始 - 比赛脚本

## 推荐使用的脚本

**使用完整版脚本**（已测试可用）：

```powershell
.\scripts\start_match_client12_vs_client34.ps1
```

这个脚本功能完整，已经修复了所有编码问题。

---

## 如果 start_match.ps1 有编码问题

如果 `start_match.ps1` 出现编码错误，请：

1. **直接使用完整版**：
   ```powershell
   .\scripts\start_match_client12_vs_client34.ps1
   ```

2. **或者手动修复编码**：
   ```powershell
   python -c "import codecs; f=codecs.open('scripts/start_match.ps1','r','gbk'); c=f.read(); f.close(); f=codecs.open('scripts/start_match.ps1','w','utf-8'); f.write(c); f.close()"
   ```

---

## 比赛配置

两个脚本的配置相同：
- **队伍1**: client1 (座位0) + client2 (座位2) - 知识库增强
- **队伍2**: client3 (座位1) + client4 (座位3) - 硬编码规则

---

## 使用步骤

```powershell
# 1. 进入项目目录
cd D:\guandanscore\YiFeiAI-GD

# 2. 运行脚本
.\scripts\start_match_client12_vs_client34.ps1
```

脚本会自动：
- 检查依赖
- 启动服务器
- 启动4个客户端
- 显示进程信息

---

## 注意事项

- 确保服务器目录路径正确
- 确保所有客户端文件存在
- 首次运行会安装依赖
- 使用 Alt+Tab 切换窗口查看输出

