# Implementation Plan

- [x] 1. 设置项目结构和基础工具





  - 创建目录结构：batch_executor/（诊断、监控、跟踪、日志模块）
  - 创建 requirements.txt（psutil, hypothesis, pytest）
  - 设置日志配置文件
  - _Requirements: 7.1, 7.2_

- [x] 2. 实现诊断模块核心功能




  - _Requirements: 0.1, 0.2, 0.3, 0.4, 0.5_

- [x] 2.1 实现配置文件检测器


  - 编写 check_config_files() 方法，扫描服务器目录
  - 支持检测 config.ini, config.json, settings.txt 等常见配置文件
  - _Requirements: 0.1_

- [x] 2.2 编写属性测试：配置文件检测完整性


  - **Property 1: 配置文件检测完整性**
  - **Validates: Requirements 0.1**

- [x] 2.3 实现服务器输出捕获器


  - 使用 subprocess.Popen 启动服务器进程
  - 通过 PIPE 捕获 stdout 和 stderr
  - 使用线程异步读取输出避免阻塞
  - _Requirements: 0.3_

- [x] 2.4 编写属性测试：输出捕获完整性


  - **Property 2: 输出捕获完整性**
  - **Validates: Requirements 0.3**

- [x] 2.5 实现游戏次数提取器


  - 编写正则表达式解析服务器输出
  - 支持多种输出格式（"Game count: 100", "游戏次数: 100"等）
  - _Requirements: 0.4_

- [x] 2.6 编写属性测试：游戏次数提取准确性



  - **Property 3: 游戏次数提取准确性**
  - **Validates: Requirements 0.4**

- [x] 2.7 实现参数验证和诊断报告生成


  - 比较命令行参数和实际游戏次数
  - 生成 DiagnosticReport 对象
  - 提供可能原因和建议
  - _Requirements: 0.5_

- [x] 2.8 编写属性测试：参数不匹配检测


  - **Property 4: 参数不匹配检测**
  - **Validates: Requirements 0.5**

- [x] 3. 实现输入验证和目标管理










  - _Requirements: 1.1, 1.2, 1.4, 1.5_

- [x] 3.1 实现目标场数输入验证




  - 验证输入为正整数
  - 存储目标场数
  - 处理默认值（100场）
  - _Requirements: 1.1, 1.4, 1.5_

- [x] 3.2 编写属性测试：目标场数验证


  - **Property 5: 目标场数验证**
  - **Validates: Requirements 1.1**

- [x] 3.3 编写属性测试：无效输入拒绝

  - **Property 7: 无效输入拒绝**
  - **Validates: Requirements 1.5**

- [x] 3.4 实现重启次数计算

  - 根据目标场数和单次限制计算重启次数
  - 使用 math.ceil() 向上取整
  - _Requirements: 1.2_

- [x] 3.5 编写属性测试：重启次数计算

  - **Property 6: 重启次数计算**
  - **Validates: Requirements 1.2**
-

- [x] 4. 实现进程监控器









  - _Requirements: 2.1, 2.3, 4.1_

- [x] 4.1 实现进程状态检查


  - 使用 psutil 检查进程是否运行
  - 支持按进程名称和PID查询
  - _Requirements: 2.1_

- [x] 4.2 编写属性测试：进程状态监控






  - **Property 8: 进程状态监控**
  - **Validates: Requirements 2.1**

- [x] 4.3 实现进程终止功能


  - 终止指定名称的所有进程
  - 使用 taskkill 命令（Windows）
  - 验证进程已终止
  - _Requirements: 4.1_

- [x] 4.4 编写属性测试：进程终止完整性


  - **Property 13: 进程终止完整性**
  - **Validates: Requirements 4.1**

- [x] 4.5 实现重启决策逻辑


  - 检测服务器终止
  - 根据剩余场数决定是否重启
  - _Requirements: 2.3_

- [x] 4.6 编写属性测试：重启决策


  - **Property 9: 重启决策**
  - **Validates: Requirements 2.3**


- [x] 5. 实现战绩跟踪器




  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 5.1 实现 ScoreTracker 类


  - 定义数据结构（team_a_wins, team_b_wins, total_games）
  - 实现 record_game() 方法
  - _Requirements: 3.1_

- [x] 5.2 编写属性测试：游戏结果记录


  - **Property 10: 游戏结果记录**
  - **Validates: Requirements 3.1**

- [x] 5.3 实现战绩持久化


  - 使用 JSON 格式保存到文件
  - 实现 save() 和 load() 方法
  - 使用临时文件+原子重命名确保安全
  - _Requirements: 3.2, 3.4, 3.5_

- [x] 5.4 编写属性测试：战绩持久化 round trip


  - **Property 11: 战绩持久化**
  - **Validates: Requirements 3.2, 3.5**

- [x] 5.5 实现战绩报告生成


  - 计算总胜场数、总负场数
  - 计算胜率
  - 生成格式化报告字符串
  - _Requirements: 3.3_

- [x] 5.6 编写属性测试：战绩报告计算


  - **Property 12: 战绩报告计算**
  - **Validates: Requirements 3.3**
-

- [x] 6. 实现重启管理器




  - _Requirements: 4.4, 6.1, 6.2, 6.3_

- [x] 6.1 实现服务器重启功能


  - 构建服务器启动命令
  - 使用 subprocess.Popen 启动
  - 等待服务器就绪（15秒）
  - 实现重试逻辑（最多3次）
  - _Requirements: 6.1, 6.2_

- [x] 6.2 实现客户端重启功能

  - 按顺序启动所有客户端
  - 每个客户端之间等待3秒
  - 处理启动失败，继续启动其他客户端
  - _Requirements: 4.4, 6.3_

- [x] 6.3 编写属性测试：客户端启动顺序


  - **Property 14: 客户端启动顺序**
  - **Validates: Requirements 4.4**

- [x] 6.4 编写属性测试：错误处理继续性

  - **Property 15: 错误处理继续性**
  - **Validates: Requirements 6.3**

- [x] 6.5 实现清理功能

  - 终止所有服务器和客户端进程
  - 释放资源
  - _Requirements: 4.1_
-

- [x] 7. 实现日志系统




  - _Requirements: 7.1, 7.2, 7.3, 7.5_

- [x] 7.1 配置日志系统


  - 设置日志格式（时间戳、级别、消息）
  - 配置控制台 handler
  - 配置文件 handler（RotatingFileHandler）
  - _Requirements: 7.1, 7.2, 7.5_

- [x] 7.2 编写属性测试：日志记录完整性


  - **Property 17: 日志记录完整性**
  - **Validates: Requirements 7.1**

- [x] 7.3 编写属性测试：日志格式正确性

  - **Property 18: 日志格式正确性**
  - **Validates: Requirements 7.2**

- [x] 7.4 编写属性测试：日志双输出

  - **Property 20: 日志双输出**
  - **Validates: Requirements 7.5**

- [x] 7.5 实现错误日志增强


  - 捕获异常堆栈信息
  - 使用 exc_info=True 记录完整堆栈
  - _Requirements: 7.3_

- [x] 7.6 编写属性测试：错误日志堆栈信息

  - **Property 19: 错误日志堆栈信息**
  - **Validates: Requirements 7.3**

- [x] 8. 实现异常处理和状态保存





  - _Requirements: 6.4_

- [x] 8.1 实现信号处理器


  - 捕获 SIGINT, SIGTERM 信号
  - 保存当前执行状态
  - 优雅退出
  - _Requirements: 6.4_
-

- [x] 8.2 编写属性测试：状态保存完整性




  - **Property 16: 状态保存完整性**
  - **Validates: Requirements 6.4**

- [x] 9. 实现主控制器和命令行接口








  - _Requirements: 1.3, 5.1, 5.2, 5.3_

- [x] 9.1 实现 BatchExecutor 主类


  - 整合所有模块
  - 实现主执行循环
  - 协调诊断和自动执行流程
  - _Requirements: 所有_


- [x] 9.2 实现命令行参数解析

  - 使用 argparse 解析参数
  - 支持 --target-games, --server-path, --diagnose-only 等选项
  - _Requirements: 1.1, 1.4_

- [x] 9.3 实现进度显示


  - 显示当前已完成场数和剩余场数
  - 显示累计战绩
  - 显示重启次数
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 10. 创建启动脚本







  - _Requirements: 所有_

- [x] 10.1 创建 Python 启动脚本


  - batch_executor.py 作为主入口
  - 处理命令行参数
  - 初始化日志系统
  - 启动主控制器
  - _Requirements: 所有_

- [x] 10.2 创建 Windows 批处理脚本


  - START_BATCH_100.bat
  - 设置环境变量
  - 调用 Python 脚本
  - 传递参数
  - _Requirements: 所有_

- [x] 11. 编写使用文档







  - _Requirements: 所有_

- [x] 11.1 创建 README.md


  - 功能说明
  - 安装步骤
  - 使用方法
  - 故障排除
  - _Requirements: 所有_


- [x] 11.2 创建示例配置文件

  - config.example.json
  - 包含所有可配置选项
  - 添加注释说明
  - _Requirements: 所有_


- [x] 12. 最终检查点






  - 确保所有测试通过，询问用户是否有问题
