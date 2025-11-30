# -*- coding: utf-8 -*-
"""
游戏回放选择工具 - 辅助批处理脚本选择游戏记录
"""

import sys
from pathlib import Path

# 由于批处理脚本已经设置了PYTHONPATH，这里可以直接导入
# 如果直接运行此脚本，需要添加路径
if __name__ == "__main__":
    src_path = Path(__file__).parent.parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

from communication.replay_game import list_games, replay_game_file
from communication.replay_game_interactive import replay_interactive


def select_and_replay(interactive: bool = False):
    """选择并回放游戏记录"""
    # 列出所有游戏记录
    games = list_games()
    
    if not games:
        print("\n未找到游戏记录！")
        print("请先运行游戏以生成记录文件。")
        return
    
    print(f"\n找到 {len(games)} 个游戏记录:\n")
    for i, game_file in enumerate(games[:30], 1):
        # 显示文件大小和修改时间
        stat = game_file.stat()
        size_kb = stat.st_size / 1024
        from datetime import datetime
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{i:2d}. {game_file.name}")
        print(f"    大小: {size_kb:.1f} KB, 时间: {mtime}")
    
    if len(games) > 30:
        print(f"\n... 还有 {len(games) - 30} 个记录未显示")
    
    print("\n" + "=" * 80)
    
    # 获取用户选择
    try:
        choice = input("\n请选择游戏记录 (输入编号 1-30，或输入文件名，或按回车退出): ").strip()
        
        if not choice:
            print("已取消")
            return
        
        # 尝试作为编号处理
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(games):
                selected_game = games[idx]
            else:
                print(f"无效的编号: {choice}")
                return
        except ValueError:
            # 作为文件名处理
            record_dir = Path(__file__).parent.parent.parent / "game_records"
            selected_game = record_dir / choice
            if not selected_game.exists():
                # 尝试添加.json扩展名
                selected_game = record_dir / f"{choice}.json"
                if not selected_game.exists():
                    print(f"文件不存在: {choice}")
                    return
        
        # 执行回放
        print("\n" + "=" * 80)
        print(f"正在回放: {selected_game.name}")
        print("=" * 80 + "\n")
        
        if interactive:
            replay_interactive(selected_game)
        else:
            replay_game_file(selected_game)
            
    except (EOFError, KeyboardInterrupt):
        print("\n\n已取消")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        select_and_replay(interactive=True)
    else:
        select_and_replay(interactive=False)


if __name__ == "__main__":
    main()

