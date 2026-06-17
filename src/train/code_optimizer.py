"""
训练代码自动优化器
根据MLflow监控指标自动优化训练代码参数
"""

import re
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CodeOptimizer:
    """训练代码自动优化器"""
    
    def __init__(self, code_file: str = "src/train/stage7_optimized_training.py"):
        """
        初始化代码优化器
        
        Args:
            code_file: 训练代码文件路径
        """
        self.code_file = Path(code_file)
        if not self.code_file.exists():
            raise FileNotFoundError(f"训练代码文件不存在: {code_file}")
        
        self.backup_file = self.code_file.with_suffix('.py.backup')
    
    def backup_code(self):
        """备份代码文件"""
        import shutil
        shutil.copy2(self.code_file, self.backup_file)
        logger.info(f"代码已备份到: {self.backup_file}")
    
    def optimize_from_mlflow_analysis(self, mlflow_analysis: Dict) -> bool:
        """
        根据MLflow分析结果优化代码
        
        Args:
            mlflow_analysis: MLflow分析结果
            
        Returns:
            是否成功优化
        """
        if not mlflow_analysis or "recommendations" not in mlflow_analysis:
            logger.warning("MLflow分析结果无效")
            return False
        
        recommendations = mlflow_analysis.get("recommendations", {})
        issues = mlflow_analysis.get("issues", [])
        
        if not recommendations and not issues:
            logger.info("无需优化")
            return False
        
        # 备份代码
        self.backup_code()
        
        # 读取代码
        with open(self.code_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        modified = False
        
        # 根据建议优化参数
        for param, action in recommendations.items():
            if param == "over_prediction_penalty":
                if action == "increase":
                    code, changed = self._increase_parameter(code, "over_prediction_penalty", 1.5)
                    modified = modified or changed
                elif action == "decrease":
                    code, changed = self._decrease_parameter(code, "over_prediction_penalty", 0.7)
                    modified = modified or changed
            
            elif param == "loss_alpha":
                if action == "increase":
                    code, changed = self._increase_parameter(code, "alpha", 1.2, context="EnhancedFocalLoss")
                    modified = modified or changed
                elif action == "decrease":
                    code, changed = self._decrease_parameter(code, "alpha", 0.8, context="EnhancedFocalLoss")
                    modified = modified or changed
            
            elif param == "sparsity_reward":
                if action == "increase":
                    code, changed = self._increase_parameter(code, "sparsity_reward", 1.5)
                    modified = modified or changed
                elif action == "decrease":
                    code, changed = self._decrease_parameter(code, "sparsity_reward", 0.7)
                    modified = modified or changed
            
            elif param == "learning_rate":
                if action == "decrease":
                    code, changed = self._decrease_parameter(code, "learning_rate", 0.5, context="default")
                    modified = modified or changed
                elif action == "increase":
                    code, changed = self._increase_parameter(code, "learning_rate", 1.5, context="default")
                    modified = modified or changed
        
        # 保存优化后的代码
        if modified:
            with open(self.code_file, 'w', encoding='utf-8') as f:
                f.write(code)
            logger.info(f"✅ 代码已优化: {self.code_file}")
            return True
        else:
            logger.info("代码无需修改")
            return False
    
    def _increase_parameter(self, code: str, param_name: str, factor: float, context: str = None) -> tuple:
        """增加参数值"""
        # 查找参数定义
        pattern = rf'{param_name}\s*[:=]\s*([\d.]+)'
        matches = list(re.finditer(pattern, code))
        
        if not matches:
            logger.warning(f"未找到参数: {param_name}")
            return code, False
        
        modified = False
        for match in reversed(matches):  # 从后往前替换
            old_value = float(match.group(1))
            new_value = old_value * factor
            
            # 检查上下文（如果指定）
            if context:
                context_start = max(0, match.start() - 100)
                context_text = code[context_start:match.end()]
                if context not in context_text:
                    continue
            
            code = code[:match.start()] + f"{param_name}={new_value}" + code[match.end():]
            logger.info(f"优化: {param_name} {old_value} -> {new_value} (x{factor})")
            modified = True
        
        return code, modified
    
    def _decrease_parameter(self, code: str, param_name: str, factor: float, context: str = None) -> tuple:
        """减少参数值"""
        return self._increase_parameter(code, param_name, 1.0/factor, context)


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="训练代码自动优化器")
    parser.add_argument("--code_file", type=str, default="src/train/stage7_optimized_training.py", help="训练代码文件")
    parser.add_argument("--analysis_file", type=str, help="MLflow分析结果JSON文件")
    
    args = parser.parse_args()
    
    optimizer = CodeOptimizer(args.code_file)
    
    if args.analysis_file:
        import json
        with open(args.analysis_file, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        optimizer.optimize_from_mlflow_analysis(analysis)
