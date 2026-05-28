#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书Kanban任务推送卡片生成器

基于飞书JSON 2.0卡片规范，结合kanban技能构建专业的任务推送卡片。
支持任务创建、状态更新、进度监控等多种场景。
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class FeishuKanbanCardGenerator:
    """飞书Kanban任务推送卡片生成器"""
    
    def __init__(self):
        self.card_template = self._load_card_template()
        
    def _load_card_template(self) -> Dict[str, Any]:
        """加载卡片模板"""
        template_path = "C:/yifeGDBOT/kanban-task-card.json"
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return self._get_default_template()
    
    def _get_default_template(self) -> Dict[str, Any]:
        """获取默认模板"""
        return {
            "schema": "2.0",
            "config": {
                "update_multi": True,
                "enable_forward": True,
                "width_mode": "default",
                "summary": {
                    "content": "新的Kanban任务已创建：{{task_title}}",
                    "i18n_content": {
                        "zh_cn": "新的Kanban任务已创建：{{task_title}}",
                        "en_us": "New Kanban task created: {{task_title}}"
                    }
                }
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🎯 yifeGDBOT任务推送"
                },
                "subtitle": {
                    "tag": "plain_text",
                    "content": "任务已分配到{{workflow_name}}"
                },
                "template": "blue",
                "padding": "12px 8px 12px 8px"
            },
            "body": {
                "direction": "vertical",
                "padding": "12px 8px 12px 8px",
                "vertical_spacing": "4px",
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**任务名称：** {{task_title}}\n\n**任务状态：** {{task_status}}\n\n**优先级：** {{priority}}\n\n**负责人：** {{assignee}}\n\n**任务类型：** {{task_type}}"
                        },
                        "margin": "8px 0 8px 0",
                        "element_id": "task_info"
                    },
                    {
                        "tag": "hr",
                        "element_id": "divider"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**任务目标：**\n\n{{task_description}}\n\n**验收标准：**\n{{acceptance_criteria}}"
                        },
                        "margin": "8px 0 8px 0",
                        "element_id": "task_desc"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**任务ID：** `{{task_id}}`\n\n**创建时间：** {{created_at}}\n\n**预计工时：** {{estimated_hours}}h\n\n**涉及技术：** {{technologies}}"
                        },
                        "margin": "8px 0 8px 0",
                        "element_id": "meta_info"
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "🔍 查看详情"
                                },
                                "type": "primary",
                                "url": "{{task_detail_url}}",
                                "action_id": "view_details"
                            },
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "🚀 执行任务"
                                },
                                "type": "default",
                                "action_id": "execute_task"
                            },
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "💬 评论"
                                },
                                "type": "default",
                                "action_id": "add_comment"
                            },
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "📊 查看进度"
                                },
                                "type": "default",
                                "action_id": "view_progress"
                            }
                        ],
                        "layout": "flow",
                        "element_id": "action_buttons"
                    }
                ]
            }
        }
    
    def generate_task_card(self, task_data: Dict[str, Any]) -> str:
        """生成任务卡片JSON"""
        # 替换模板变量
        card = self._render_template(self.card_template, task_data)
        return json.dumps(card, ensure_ascii=False, indent=2)
    
    def _render_template(self, template: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """渲染模板，替换变量"""
        result = json.loads(json.dumps(template))
        
        # 递归替换变量
        result = self._replace_variables(result, data)
        
        return result
    
    def _replace_variables(self, obj: Any, data: Dict[str, Any]) -> Any:
        """递归替换对象中的变量"""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if isinstance(value, str):
                    result[key] = self._replace_string(value, data)
                else:
                    result[key] = self._replace_variables(value, data)
            return result
        elif isinstance(obj, list):
            return [self._replace_variables(item, data) for item in obj]
        else:
            return obj
    
    def _replace_string(self, text: str, data: Dict[str, Any]) -> str:
        """替换字符串中的变量"""
        result = text
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result
    
    def create_status_update_card(self, task_data: Dict[str, Any], new_status: str, message: str) -> str:
        """创建状态更新卡片"""
        status_card = {
            "schema": "2.0",
            "config": {
                "update_multi": True,
                "enable_forward": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🔄 任务状态更新"
                },
                "template": "yellow"
            },
            "body": {
                "direction": "vertical",
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**任务：** {task_data['title']}\n\n**新状态：** {new_status}\n\n**更新信息：** {message}\n\n**更新时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        },
                        "margin": "8px 0 8px 0"
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "🔍 查看详情"
                                },
                                "type": "primary",
                                "url": task_data.get('detail_url', ''),
                                "action_id": "view_details"
                            },
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "📊 查看进度"
                                },
                                "type": "default",
                                "action_id": "view_progress"
                            }
                        ],
                        "layout": "flow"
                    }
                ]
            }
        }
        return json.dumps(status_card, ensure_ascii=False, indent=2)
    
    def create_progress_card(self, task_data: Dict[str, Any], progress: Dict[str, Any]) -> str:
        """创建进度监控卡片"""
        progress_card = {
            "schema": "2.0",
            "config": {
                "update_multi": True,
                "enable_forward": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📊 任务进度监控"
                },
                "template": "green"
            },
            "body": {
                "direction": "vertical",
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**任务：** {task_data['title']}\n\n**当前进度：** {progress.get('current_step', 'N/A')}\n\n**完成度：** {progress.get('completion_percentage', 0)}%\n\n**状态：** {progress.get('status', '运行中')}"
                        },
                        "margin": "8px 0 8px 0"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**开始时间：** {progress.get('start_time', 'N/A')}\n\n**运行时长：** {progress.get('duration', 'N/A')}\n\n**预计剩余时间：** {progress.get('estimated_remaining', 'N/A')}"
                        },
                        "margin": "8px 0 8px 0"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**关键指标：**\n- 成功率：{progress.get('success_rate', 0)}%\n- 错误次数：{progress.get('error_count', 0)}\n- 重试次数：{progress.get('retry_count', 0)}"
                        },
                        "margin": "8px 0 8px 0"
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "🔄 刷新进度"
                                },
                                "type": "default",
                                "action_id": "refresh_progress"
                            },
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "🚀 查看日志"
                                },
                                "type": "default",
                                "action_id": "view_logs"
                            }
                        ],
                        "layout": "flow"
                    }
                ]
            }
        }
        return json.dumps(progress_card, ensure_ascii=False, indent=2)


def generate_yifeGDBOT_task_card() -> str:
    """生成yifeGDBOT任务卡片示例"""
    generator = FeishuKanbanCardGenerator()
    
    # 任务数据示例
    task_data = {
        "task_id": "t_623fb825",
        "task_title": "PHASE4-006: 深度优化choose_bomb策略",
        "task_status": "🚀 进行中",
        "priority": "🔴 P0",
        "assignee": "cursor",
        "task_type": "算法优化",
        "workflow_name": "yifeGDBOT",
        "task_description": "基于PHASE4-001分析结果，深度优化choose_bomb函数，提升M1对lalala的胜率从0%到>90%\n\n**优化策略：**\n1. 改进炸弹选择算法\n2. 优化优先级计算\n3. 增强决策逻辑",
        "acceptance_criteria": "1. 胜率达到90%以上\n2. 通过16局真实对局验证\n3. 保持代码可读性和可维护性\n4. 编写详细的优化报告",
        "created_at": "2026-05-25 19:45:00",
        "estimated_hours": "16",
        "technologies": "Python, AI算法, 掼牌游戏, 机器学习",
        "task_detail_url": "https://kanban.example.com/task/t_623fb825"
    }
    
    # 生成卡片
    card_json = generator.generate_task_card(task_data)
    
    # 保存到文件
    output_path = "C:/yifeGDBOT/yifeGDBOT-task-card.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(card_json)
    
    return card_json, output_path


if __name__ == "__main__":
    # 生成yifeGDBOT任务卡片
    card_json, output_path = generate_yifeGDBOT_task_card()
    
    print("=" * 70)
    print("🎯 yifeGDBOT任务推送卡片生成完成")
    print("=" * 70)
    print(f"📄 卡片文件路径: {output_path}")
    print(f"📊 卡片大小: {len(card_json)} 字符")
    print("\n🔧 卡片预览:")
    print(card_json)
    print("\n" + "=" * 70)