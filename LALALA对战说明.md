# 使用lalala客户端对战

## 前提条件

1. **lalala代码位置**: `D:\NYGD\lalala`
2. **安装ws4py库**: 
   ```bash
   pip install ws4py
   ```

## 测试适配器

运行测试脚本：
```bash
TEST_LALALA.bat
```

## GUI配置

在GUI中配置客户端路径（按座位顺序）：
```
src/communication/Test1.py, src/communication/run_lalala_client3.py, src/communication/Test2.py, src/communication/run_lalala_client4.py
```

**座位和队伍分配**：
- 0号位：Test1（你的AI）
- 1号位：lalala client3（对手）
- 2号位：Test2（你的AI）
- 3号位：lalala client4（对手）

**队伍分组**（掼蛋规则：0+2对家，1+3对家）：
- 队伍A（你的队）：0号(Test1) + 2号(Test2)
- 队伍B（lalala队）：1号(client3) + 3号(client4)

## 命令行测试

单独测试lalala客户端：
```bash
python src/communication/run_lalala_client1.py
```

## 常见问题

**Q: 提示找不到lalala模块？**
A: 检查 `D:\NYGD\lalala` 是否存在，修改 `lalala_adapter.py` 中的路径

**Q: 提示没有ws4py？**
A: 运行 `pip install ws4py`

**Q: 客户端连接失败？**
A: 确保服务器已启动，URL格式正确
