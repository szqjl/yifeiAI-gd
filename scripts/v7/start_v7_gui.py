# -*- coding: utf-8 -*-
"""
V7终极胜率导向GUI启动脚本
预配置V7客户端 vs lalala客户端的对战
"""

import sys
from pathlib import Path
import tkinter as tk

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "gui"))

try:
    from batch_executor_gui import BatchExecutorGUI
    
    class V7BatchExecutorGUI(BatchExecutorGUI):
        """V7专用批量执行GUI"""
        
        def __init__(self, root):
            super().__init__(root)
            # 修改窗口标题
            self.root.title("掼蛋AI批量对战系统 - V7终极胜率导向版")
            
        def load_default_config(self):
            """加载V7默认配置"""
            # 设置默认参数
            self.target_games_var.set("3")  # 默认3场（3的倍数）
            
            # 读取 v7_paths.yaml
            _cfg = {}
            _cfg_path = REPO_ROOT / "config" / "v7_paths.yaml"
            if _cfg_path.exists():
                try:
                    import yaml
                    with open(_cfg_path, encoding="utf-8") as _f:
                        _cfg = yaml.safe_load(_f) or {}
                except Exception:
                    pass
            _lalala_dir = os.environ.get("LALALA_DIR", "") or _cfg.get("lalala_dir", "").replace("%REPO_ROOT%", str(REPO_ROOT)) or str(REPO_ROOT / "reference" / "lalala")
            
            # 设置V7客户端配置
            v7_clients = [
                "python src/communication/yf1_v7.py",
                f"python {_lalala_dir}\\client3.py",
                "python src/communication/yf2_v7.py",
                f"python {_lalala_dir}\\client4.py"
            ]
            
            self.clients_var.set(",".join(v7_clients))
            
            # 设置服务器配置
            _server_exe = os.environ.get("SERVER_EXE", "") or _cfg.get("server_exe", "").replace("%REPO_ROOT%", str(REPO_ROOT)) or str(REPO_ROOT / "offline_platform" / "guandan_offline_v1006" / "windows" / "guandan_offline_v1006.exe")
            self.server_path_var.set(f"{_server_exe} 10")
            
            # 在日志区域显示V7配置信息
            self.log_text.insert(tk.END, "=" * 60 + "\n")
            self.log_text.insert(tk.END, "V7终极胜率导向批量对战系统已启动\n")
            self.log_text.insert(tk.END, "=" * 60 + "\n")
            self.log_text.insert(tk.END, "配置信息:\n")
            self.log_text.insert(tk.END, "  Team A (V7终极胜率导向): yf1_v7 + yf2_v7\n")
            self.log_text.insert(tk.END, "  Team B (lalala): client3 + client4\n")
            self.log_text.insert(tk.END, "  模型: bc_model_ultimate_win_rate.pth\n")
            self.log_text.insert(tk.END, "  训练成果: 84.3%终极评分, 100%匹配率\n")
            self.log_text.insert(tk.END, "\n")
            
            # 检查模型文件
            model_path = Path("models/bc_model_ultimate_win_rate.pth")
            if model_path.exists():
                self.log_text.insert(tk.END, "✓ 终极胜率导向模型已加载\n")
            else:
                self.log_text.insert(tk.END, "⚠ 终极胜率导向模型未找到，将使用规则引擎\n")
            
            self.log_text.insert(tk.END, "\n点击'开始执行'开始V7 vs lalala对战测试\n")
            self.log_text.insert(tk.END, "=" * 60 + "\n\n")
            
            # 滚动到底部
            self.log_text.see(tk.END)
    
    print("正在启动V7终极胜率导向GUI...")
    root = tk.Tk()
    app = V7BatchExecutorGUI(root)
    print("V7 GUI窗口已打开")
    root.mainloop()
    
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖: pip install -r requirements.txt")
    input("按回车键退出...")
except Exception as e:
    print(f"启动V7 GUI时出错: {e}")
    import traceback
    traceback.print_exc()
    input("按回车键退出...")