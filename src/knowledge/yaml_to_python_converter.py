# -*- coding: utf-8 -*-
"""
YAML规则转Python代码转换器

将YAML规则文件转换为Python字典，避免运行时依赖yaml模块。
这样yf_v4就可以完全独立，不需要外部依赖。
"""

import json
from pathlib import Path
from typing import Dict, List


def convert_yaml_to_python_dict(yaml_file: Path) -> Dict:
    """
    手动解析简单的YAML文件（仅支持基本结构）
    
    注意：这是一个简化版本，只支持知识库规则文件的基本格式。
    如果需要完整YAML支持，建议使用pyyaml。
    
    Args:
        yaml_file: YAML文件路径
        
    Returns:
        解析后的字典
    """
    with open(yaml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 简单的YAML解析（仅支持规则文件格式）
    result = {'rules': []}
    current_rule = None
    current_section = None
    
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        
        # 跳过注释和空行
        if not line or line.strip().startswith('#'):
            i += 1
            continue
        
        # 检测规则开始
        if line.startswith('- id:'):
            if current_rule:
                result['rules'].append(current_rule)
            current_rule = {}
            # 提取id
            id_value = line.split('id:')[1].strip().strip('"').strip("'")
            current_rule['id'] = id_value
            current_section = None
        elif line.startswith('  ') and current_rule:
            # 规则字段
            if line.startswith('  name:'):
                current_rule['name'] = line.split('name:')[1].strip().strip('"').strip("'")
            elif line.startswith('  description:'):
                current_rule['description'] = line.split('description:')[1].strip().strip('"').strip("'")
            elif line.startswith('  priority:'):
                priority_str = line.split('priority:')[1].strip()
                try:
                    current_rule['priority'] = int(priority_str)
                except ValueError:
                    current_rule['priority'] = 1
            elif line.startswith('  condition:'):
                current_section = 'condition'
                current_rule['condition'] = {}
            elif line.startswith('  actions:'):
                current_section = 'actions'
                current_rule['actions'] = []
            elif current_section == 'condition' and line.strip().startswith('-'):
                # 条件列表项
                if 'conditions' not in current_rule['condition']:
                    current_rule['condition']['type'] = 'and'
                    current_rule['condition']['conditions'] = []
                # 解析条件项
                condition_item = _parse_condition_item(lines, i)
                if condition_item:
                    current_rule['condition']['conditions'].append(condition_item)
                    # 跳过已处理的行
                    i = _skip_condition_lines(lines, i)
            elif current_section == 'actions' and line.strip().startswith('-'):
                # 动作项
                action_item = _parse_action_item(lines, i)
                if action_item:
                    current_rule['actions'].append(action_item)
                    i = _skip_action_lines(lines, i)
        
        i += 1
    
    # 添加最后一个规则
    if current_rule:
        result['rules'].append(current_rule)
    
    return result


def _parse_condition_item(lines: List[str], start_idx: int) -> Dict:
    """解析条件项"""
    condition = {}
    i = start_idx
    indent = len(lines[i]) - len(lines[i].lstrip())
    
    while i < len(lines):
        line = lines[i].rstrip()
        current_indent = len(line) - len(line.lstrip()) if line.strip() else 0
        
        if current_indent <= indent and i > start_idx:
            break
        
        if 'field:' in line:
            condition['field'] = line.split('field:')[1].strip().strip('"').strip("'")
        elif 'op:' in line:
            condition['op'] = line.split('op:')[1].strip().strip('"').strip("'")
        elif 'value:' in line:
            value_str = line.split('value:')[1].strip().strip('"').strip("'")
            # 尝试转换为数字
            try:
                if '.' in value_str:
                    condition['value'] = float(value_str)
                else:
                    condition['value'] = int(value_str)
            except ValueError:
                condition['value'] = value_str
        
        i += 1
    
    return condition if condition else None


def _parse_action_item(lines: List[str], start_idx: int) -> Dict:
    """解析动作项"""
    action = {}
    i = start_idx
    indent = len(lines[i]) - len(lines[i].lstrip())
    
    while i < len(lines):
        line = lines[i].rstrip()
        current_indent = len(line) - len(line.lstrip()) if line.strip() else 0
        
        if current_indent <= indent and i > start_idx:
            break
        
        if 'action_type:' in line:
            action['action_type'] = line.split('action_type:')[1].strip().strip('"').strip("'")
        elif 'score_adjust:' in line:
            score_str = line.split('score_adjust:')[1].strip()
            try:
                action['score_adjust'] = int(score_str)
            except ValueError:
                action['score_adjust'] = 0
        
        i += 1
    
    return action if action else None


def _skip_condition_lines(lines: List[str], start_idx: int) -> int:
    """跳过条件项的所有行"""
    i = start_idx + 1
    indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= indent:
            break
        i += 1
    
    return i - 1


def _skip_action_lines(lines: List[str], start_idx: int) -> int:
    """跳过动作项的所有行"""
    return _skip_condition_lines(lines, start_idx)


def convert_yaml_files_to_python_module(
    yaml_dir: Path,
    output_file: Path,
    module_name: str = "knowledge_rules"
):
    """
    将YAML规则文件转换为Python模块
    
    Args:
        yaml_dir: YAML文件目录
        output_file: 输出的Python文件路径
        module_name: 模块名称
    """
    yaml_files = list(yaml_dir.glob("*.yaml")) + list(yaml_dir.glob("*.yml"))
    
    all_rules = []
    file_info = []
    
    for yaml_file in sorted(yaml_files):
        try:
            # 尝试使用yaml模块解析（如果可用）
            try:
                import yaml
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            except ImportError:
                # 如果yaml不可用，使用简单解析器
                data = convert_yaml_to_python_dict(yaml_file)
            
            if data and 'rules' in data:
                rules = data['rules']
                all_rules.extend(rules)
                file_info.append({
                    'file': yaml_file.name,
                    'count': len(rules)
                })
        except Exception as e:
            print(f"Warning: Failed to convert {yaml_file}: {e}")
    
    # 生成Python代码（将JSON格式转换为Python格式）
    # 需要将JSON的true/false/null转换为Python的True/False/None
    json_str = json.dumps(all_rules, ensure_ascii=False, indent=2)
    # 替换JSON格式为Python格式
    json_str = json_str.replace(': true', ': True')
    json_str = json_str.replace(': false', ': False')
    json_str = json_str.replace(': null', ': None')
    
    python_code = f'''# -*- coding: utf-8 -*-
"""
知识库规则（从YAML文件转换）

此文件由 yaml_to_python_converter.py 自动生成。
包含所有从YAML规则文件转换而来的规则。

生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
源文件:
{chr(10).join(f"  - {info['file']} ({info['count']}条规则)" for info in file_info)}
"""

# 所有规则
KNOWLEDGE_RULES = {json_str}
'''
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(python_code)
    
    print(f"✅ 已转换 {len(all_rules)} 条规则到 {output_file}")
    print(f"   源文件: {len(file_info)} 个YAML文件")
    
    return len(all_rules)


if __name__ == "__main__":
    # 转换所有YAML规则文件
    knowledge_dir = Path(__file__).parent.parent.parent / "docs" / "knowledge"
    output_file = Path(__file__).parent / "knowledge_rules.py"
    
    if not knowledge_dir.exists():
        print(f"Error: Knowledge directory not found: {knowledge_dir}")
    else:
        convert_yaml_files_to_python_module(
            knowledge_dir,
            output_file,
            "knowledge_rules"
        )

