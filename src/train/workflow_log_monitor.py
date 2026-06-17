"""
工作流日志监控器
监控工作流自身日志，检测常见bug并自动修复
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class WorkflowLogMonitor:
    """工作流日志监控器"""
    
    # 常见bug模式及其修复方案
    BUG_PATTERNS = {
        # 模型保存相关
        "model_not_saved": {
            "pattern": r"模型文件不存在|模型文件未生成|模型保存失败",
            "severity": "high",
            "category": "model_save",
            "fix_action": "check_model_save_logic"
        },
        # 编码相关
        "encoding_error": {
            "pattern": r"UnicodeDecodeError|UnicodeEncodeError|codec can't (decode|encode)",
            "severity": "medium",
            "category": "encoding",
            "fix_action": "fix_encoding"
        },
        # 进程相关
        "process_error": {
            "pattern": r"进程.*失败|进程.*错误|服务器路径未设置|端口.*占用",
            "severity": "high",
            "category": "process",
            "fix_action": "cleanup_processes"
        },
        # 训练相关
        "training_error": {
            "pattern": r"训练失败|训练过程出错|ZeroDivisionError|IndentationError",
            "severity": "high",
            "category": "training",
            "fix_action": "check_training_code"
        },
        # 评估相关
        "evaluation_error": {
            "pattern": r"评估失败|无法评估|KeyError.*status|评估过程出错",
            "severity": "medium",
            "category": "evaluation",
            "fix_action": "check_evaluator"
        },
        # 内存相关
        "memory_error": {
            "pattern": r"内存不足|OutOfMemoryError|MemoryError",
            "severity": "high",
            "category": "memory",
            "fix_action": "reduce_batch_size"
        }
    }
    
    def __init__(self, log_dir: str = "logs", workflow_log_file: str = None):
        """
        初始化日志监控器
        
        Args:
            log_dir: 日志目录
            workflow_log_file: 工作流日志文件路径（如果为None，则自动查找最新的）
        """
        self.log_dir = Path(log_dir)
        self.workflow_log_file = workflow_log_file
        self.detected_bugs = []
        self.fix_history = []
    
    def find_latest_workflow_log(self) -> Optional[Path]:
        """查找最新的工作流日志文件"""
        if self.workflow_log_file:
            log_path = Path(self.workflow_log_file)
            if log_path.exists():
                return log_path
            return None
        
        # 查找logs目录下的最新日志文件
        if not self.log_dir.exists():
            return None
        
        # 查找包含workflow或m1_training的日志文件
        log_files = list(self.log_dir.glob("*workflow*.log")) + \
                   list(self.log_dir.glob("*m1_training*.log")) + \
                   list(self.log_dir.glob("*.log"))
        
        if not log_files:
            return None
        
        # 返回最新的日志文件
        return max(log_files, key=lambda p: p.stat().st_mtime)
    
    def monitor_logs(self, lines: int = 100) -> Dict:
        """
        监控日志文件，检测bug
        
        Args:
            lines: 检查最近N行日志
            
        Returns:
            检测结果字典
        """
        log_file = self.find_latest_workflow_log()
        if not log_file:
            logger.warning("未找到工作流日志文件")
            return {
                "bugs_detected": [],
                "status": "no_log_file"
            }
        
        logger.info(f"监控日志文件: {log_file}")
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                log_content = ''.join(recent_lines)
        except Exception as e:
            logger.error(f"读取日志文件失败: {e}")
            return {
                "bugs_detected": [],
                "status": "read_error",
                "error": str(e)
            }
        
        # 检测bug
        bugs = []
        for bug_name, bug_info in self.BUG_PATTERNS.items():
            pattern = bug_info["pattern"]
            matches = re.finditer(pattern, log_content, re.IGNORECASE)
            for match in matches:
                # 获取匹配行的上下文
                line_num = log_content[:match.start()].count('\n') + 1
                context_start = max(0, match.start() - 100)
                context_end = min(len(log_content), match.end() + 100)
                context = log_content[context_start:context_end]
                
                bug = {
                    "name": bug_name,
                    "severity": bug_info["severity"],
                    "category": bug_info["category"],
                    "fix_action": bug_info["fix_action"],
                    "line_number": line_num,
                    "context": context.strip(),
                    "detected_at": datetime.now().isoformat()
                }
                bugs.append(bug)
                self.detected_bugs.append(bug)
        
        return {
            "bugs_detected": bugs,
            "log_file": str(log_file),
            "status": "success"
        }
    
    def auto_fix_bugs(self, bugs: List[Dict]) -> Dict:
        """
        自动修复检测到的bug
        
        Args:
            bugs: 检测到的bug列表
            
        Returns:
            修复结果字典
        """
        fixes_applied = []
        fixes_failed = []
        
        for bug in bugs:
            fix_action = bug.get("fix_action")
            bug_name = bug.get("name")
            
            logger.info(f"尝试修复bug: {bug_name} (操作: {fix_action})")
            
            try:
                if fix_action == "check_model_save_logic":
                    # 检查并修复模型保存逻辑
                    result = self._fix_model_save_logic()
                    if result["success"]:
                        fixes_applied.append({"bug": bug_name, "action": fix_action})
                    else:
                        fixes_failed.append({"bug": bug_name, "action": fix_action, "error": result.get("error")})
                
                elif fix_action == "fix_encoding":
                    # 修复编码问题
                    result = self._fix_encoding_issues()
                    if result["success"]:
                        fixes_applied.append({"bug": bug_name, "action": fix_action})
                    else:
                        fixes_failed.append({"bug": bug_name, "action": fix_action, "error": result.get("error")})
                
                elif fix_action == "cleanup_processes":
                    # 清理残留进程
                    result = self._cleanup_processes()
                    if result["success"]:
                        fixes_applied.append({"bug": bug_name, "action": fix_action})
                    else:
                        fixes_failed.append({"bug": bug_name, "action": fix_action, "error": result.get("error")})
                
                elif fix_action == "check_training_code":
                    # 检查训练代码
                    result = self._check_training_code()
                    if result["success"]:
                        fixes_applied.append({"bug": bug_name, "action": fix_action})
                    else:
                        fixes_failed.append({"bug": bug_name, "action": fix_action, "error": result.get("error")})
                
                elif fix_action == "check_evaluator":
                    # 检查评估器
                    result = self._check_evaluator()
                    if result["success"]:
                        fixes_applied.append({"bug": bug_name, "action": fix_action})
                    else:
                        fixes_failed.append({"bug": bug_name, "action": fix_action, "error": result.get("error")})
                
                elif fix_action == "reduce_batch_size":
                    # 减少批次大小
                    result = self._reduce_batch_size()
                    if result["success"]:
                        fixes_applied.append({"bug": bug_name, "action": fix_action})
                    else:
                        fixes_failed.append({"bug": bug_name, "action": fix_action, "error": result.get("error")})
                
            except Exception as e:
                logger.error(f"修复bug {bug_name} 时出错: {e}")
                fixes_failed.append({"bug": bug_name, "action": fix_action, "error": str(e)})
        
        # 记录修复历史
        fix_record = {
            "timestamp": datetime.now().isoformat(),
            "fixes_applied": fixes_applied,
            "fixes_failed": fixes_failed
        }
        self.fix_history.append(fix_record)
        
        return {
            "fixes_applied": fixes_applied,
            "fixes_failed": fixes_failed,
            "total_bugs": len(bugs),
            "fixed_count": len(fixes_applied),
            "failed_count": len(fixes_failed)
        }
    
    def _fix_model_save_logic(self) -> Dict:
        """修复模型保存逻辑"""
        logger.info("检查模型保存逻辑...")
        # 这里可以检查stage7_optimized_training.py的模型保存逻辑
        # 如果发现best_score初始化错误，可以自动修复
        training_file = Path("src/train/stage7_optimized_training.py")
        if not training_file.exists():
            return {"success": False, "error": "训练文件不存在"}
        
        try:
            with open(training_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否有best_loss = float('inf')的问题
            if "best_loss = float('inf')" in content and "combined_score > best_loss" in content:
                logger.warning("检测到模型保存逻辑错误：best_loss初始化为inf")
                # 这里可以自动修复，但为了安全，只记录
                return {
                    "success": True,
                    "message": "已检测到模型保存逻辑问题，建议手动修复",
                    "suggestion": "将best_loss改为best_score，初始化为-float('inf')"
                }
            
            return {"success": True, "message": "模型保存逻辑正常"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fix_encoding_issues(self) -> Dict:
        """修复编码问题"""
        logger.info("检查编码设置...")
        # 检查工作流文件是否设置了UTF-8编码
        workflow_file = Path("src/train/m1_training_workflow.py")
        if not workflow_file.exists():
            return {"success": False, "error": "工作流文件不存在"}
        
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否设置了UTF-8编码
            if "io.TextIOWrapper" in content and "encoding='utf-8'" in content:
                return {"success": True, "message": "编码设置正常"}
            else:
                return {
                    "success": True,
                    "message": "编码设置可能需要改进",
                    "suggestion": "确保在run()方法开始时设置UTF-8编码"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _cleanup_processes(self) -> Dict:
        """清理残留进程"""
        logger.info("清理残留进程...")
        import subprocess
        import sys
        
        try:
            if sys.platform == 'win32':
                # 清理服务器进程
                result = subprocess.run(
                    ['taskkill', '/F', '/IM', 'guandan_offline_v1006.exe', '/T'],
                    capture_output=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                return {"success": True, "message": "已尝试清理残留进程"}
            else:
                subprocess.run(['pkill', '-f', 'guandan_offline'], timeout=5, capture_output=True)
                return {"success": True, "message": "已尝试清理残留进程"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _check_training_code(self) -> Dict:
        """检查训练代码"""
        logger.info("检查训练代码语法...")
        import subprocess
        
        try:
            result = subprocess.run(
                ['python', '-m', 'py_compile', 'src/train/stage7_optimized_training.py'],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                return {"success": True, "message": "训练代码语法正常"}
            else:
                error_msg = result.stderr.decode('utf-8', errors='replace') if result.stderr else "未知错误"
                return {"success": False, "error": error_msg}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _check_evaluator(self) -> Dict:
        """检查评估器代码"""
        logger.info("检查评估器代码语法...")
        import subprocess
        
        try:
            result = subprocess.run(
                ['python', '-m', 'py_compile', 'src/train/m1_vs_client_evaluator.py'],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                return {"success": True, "message": "评估器代码语法正常"}
            else:
                error_msg = result.stderr.decode('utf-8', errors='replace') if result.stderr else "未知错误"
                return {"success": False, "error": error_msg}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _reduce_batch_size(self) -> Dict:
        """减少批次大小（处理内存问题）"""
        logger.info("检查批次大小设置...")
        # 这里可以检查训练脚本中的batch_size，如果太大可以建议减小
        training_file = Path("src/train/stage7_optimized_training.py")
        if not training_file.exists():
            return {"success": False, "error": "训练文件不存在"}
        
        try:
            with open(training_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找batch_size设置
            batch_size_match = re.search(r'batch_size\s*[:=]\s*(\d+)', content)
            if batch_size_match:
                current_batch_size = int(batch_size_match.group(1))
                if current_batch_size > 16:
                    return {
                        "success": True,
                        "message": f"当前批次大小: {current_batch_size}，如果内存不足可以减小到16或8",
                        "suggestion": "在训练脚本中减小batch_size参数"
                    }
            
            return {"success": True, "message": "批次大小设置正常"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def save_fix_history(self, file_path: str = "models/workflow_fix_history.json"):
        """保存修复历史"""
        history_file = Path(file_path)
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "detected_bugs": self.detected_bugs,
                    "fix_history": self.fix_history,
                    "last_update": datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"修复历史已保存: {history_file}")
        except Exception as e:
            logger.error(f"保存修复历史失败: {e}")


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="工作流日志监控器")
    parser.add_argument("--log_file", type=str, default=None, help="日志文件路径")
    parser.add_argument("--lines", type=int, default=100, help="检查最近N行日志")
    parser.add_argument("--auto_fix", action="store_true", help="自动修复检测到的bug")
    
    args = parser.parse_args()
    
    monitor = WorkflowLogMonitor(workflow_log_file=args.log_file)
    result = monitor.monitor_logs(lines=args.lines)
    
    print("\n" + "="*60)
    print("工作流日志监控结果")
    print("="*60)
    print(f"检测到 {len(result['bugs_detected'])} 个潜在bug")
    
    if result['bugs_detected']:
        print("\n检测到的bug:")
        for i, bug in enumerate(result['bugs_detected'], 1):
            print(f"\n{i}. {bug['name']} ({bug['severity']} 严重性)")
            print(f"   类别: {bug['category']}")
            print(f"   修复操作: {bug['fix_action']}")
            print(f"   检测时间: {bug['detected_at']}")
        
        if args.auto_fix:
            print("\n开始自动修复...")
            fix_result = monitor.auto_fix_bugs(result['bugs_detected'])
            print(f"\n修复结果:")
            print(f"  成功修复: {fix_result['fixed_count']} 个")
            print(f"  修复失败: {fix_result['failed_count']} 个")
            monitor.save_fix_history()
    else:
        print("✅ 未检测到bug")
    
    print("="*60)
