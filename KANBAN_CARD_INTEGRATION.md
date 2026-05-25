# 飞书Kanban任务推送卡片集成指南

## 🎯 概述

基于飞书JSON 2.0卡片规范，结合kanban技能构建的专业Kanban任务推送卡片系统。支持任务创建、状态更新、进度监控等多种场景。

## 📁 文件结构

```
C:/yifeGDBOT/
├── kanban-task-card.json          # 基础卡片模板
├── feishu_kanban_card_generator.py # 卡片生成器
├── yifeGDBOT-task-card.json       # yifeGDBOT任务示例卡片
└── integration_example.py        # 集成示例脚本
```

## 🔧 核心功能

### 1. 任务创建卡片
- 完整的任务信息展示
- 多种交互按钮
- 状态可视化
- 优先级标识

### 2. 状态更新卡片
- 实时状态变更通知
- 进度更新提醒
- 历史记录追踪

### 3. 进度监控卡片
- 实时进度监控
- 关键指标展示
- 错误和重试统计
- 预计完成时间

## 🎨 卡片设计特点

### 视觉设计
- **颜色模板**: 蓝色(任务)、黄色(更新)、绿色(进度)
- **图标使用**: Emoji增强视觉识别
- **布局优化**: 垂直布局，信息层次清晰

### 交互设计
- **四种操作按钮**: 查看详情、执行任务、评论、查看进度
- **响应式设计**: 适配不同屏幕尺寸
- **实时更新**: 支持卡片内容动态更新

### 信息架构
- **任务信息**: 名称、状态、优先级、负责人、类型
- **任务详情**: 目标描述、验收标准
- **元信息**: ID、创建时间、预计工时、技术栈

## 🚀 使用方法

### 1. 基础卡片生成
```python
from feishu_kanban_card_generator import FeishuKanbanCardGenerator

generator = FeishuKanbanCardGenerator()
card_json = generator.generate_task_card(task_data)
```

### 2. 状态更新卡片
```python
status_card = generator.create_status_update_card(
    task_data, 
    new_status="✅ 已完成", 
    message="PHASE4优化完成，胜率达到92%"
)
```

### 3. 进度监控卡片
```python
progress_data = {
    "current_step": "执行PHASE4-006",
    "completion_percentage": 75,
    "status": "运行中",
    "success_rate": 85,
    "error_count": 2
}

progress_card = generator.create_progress_card(task_data, progress_data)
```

## 📡 集成到Kanban系统

### 任务创建时自动推送
```python
def create_and_notify_task(task_data):
    # 1. 创建Kanban任务
    kanban_result = kanban_create(
        title=task_data['title'],
        assignee=task_data['assignee'],
        description=task_data['description']
    )
    
    if kanban_result['success']:
        # 2. 推送任务卡片到飞书
        generator = FeishuKanbanCardGenerator()
        card_json = generator.generate_task_card(task_data)
        
        # 3. 发送飞书消息
        send_message(
            target="feishu:oc_xxxxx",
            message=card_json
        )
    
    return kanban_result
```

### 任务状态变更通知
```python
def notify_task_status_change(task_id, new_status, message):
    task_data = get_task_data(task_id)
    
    generator = FeishuKanbanCardGenerator()
    status_card = generator.create_status_update_card(
        task_data, new_status, message
    )
    
    send_message(
        target="feishu:oc_xxxxx", 
        message=status_card
    )
```

## 🎯 yifeGDBOT应用场景

### PHASE4任务推送
- **任务类型**: 算法优化
- **目标**: 提升M1对lalala胜率到90%+
- **负责人**: cursor/opencode
- **优先级**: P0(最高)

### 监控指标
- **胜率监控**: 实时跟踪对局胜率
- **错误统计**: 记录策略执行错误
- **重试机制**: 失败任务重新分配
- **进度更新**: PHASE执行进度

## 🛠️ 技术实现

### 飞书API集成
```python
def send_feishu_card(card_json, chat_id, token):
    """发送飞书卡片"""
    payload = {
        "receive_id_type": "chat_id",
        "chat_id": chat_id,
        "msg_type": "interactive",
        "card": card_json
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages",
        json=payload,
        headers=headers
    )
    
    return response.json()
```

### 模板引擎
- **变量替换**: `{{variable_name}}` 语法
- **条件渲染**: 支持动态内容
- **国际化**: 多语言支持
- **格式化**: Markdown支持

## 🔍 最佳实践

### 1. 卡片设计原则
- **简洁明了**: 信息层次清晰，重点突出
- **交互友好**: 按钮布局合理，操作直观
- **状态可视化**: 使用颜色和图标直观显示状态
- **扩展性强**: 模板化设计，易于定制和扩展

### 2. 集成注意事项
- **API限制**: 飞书卡片大小和元素数量限制
- **错误处理**: 完善的异常处理机制
- **性能优化**: 批量发送和缓存机制
- **安全性**: API token的安全管理

### 3. 监控和维护
- **日志记录**: 完整的发送和接收日志
- **性能监控**: 卡片发送成功率和响应时间
- **用户反馈**: 收集用户使用反馈
- **版本管理**: 模板版本控制和更新机制

## 📊 示例效果

### 任务创建卡片
显示完整任务信息，包含交互按钮，便于团队成员快速了解任务详情和执行操作。

### 状态更新卡片
实时通知任务状态变更，保持团队信息同步，提高协作效率。

### 进度监控卡片
提供实时进度监控，帮助管理者了解任务执行情况，及时发现问题。

---

*这个集成方案结合了飞书JSON 2.0卡片的强大功能和Kanban任务管理的实际需求，为yifeGDBOT项目提供了专业的任务推送和监控解决方案。*