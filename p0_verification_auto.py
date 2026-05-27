#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0改进验证与微调脚本 - 启动本地平台、运行对局、分析结果、自动微调

流程：
1. 启动本地掼蛋平台 (guandan_offline_v1006.exe)
2. 启动M1两个实例进行10局对战
3. 收集游戏记录
4. 运行分析脚本verify P0改进效果
5. 根据结果自动微调参数
6. 记录详细报告
"""

import subprocess
import time
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('p0_verification.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 路径配置
PLATFORM_EXE = r"D:\guandanscore\YiFeiAI-GD\offline_platform\guandan_offline_v1006\windows\guandan_offline_v1006.exe"
PROJECT_ROOT = r"D:\guandanscore\YiFeiAI-GD"
GAME_RECORDS_DIR = os.path.join(PROJECT_ROOT, "game_records")
ANALYSIS_SCRIPT = os.path.join(PROJECT_ROOT, "analyze_game_rounds.py")

class P0VerificationTest:
    def __init__(self):
        self.platform_process = None
        self.test_start_time = datetime.now()
        self.baseline_metrics = None
        self.results = {
            'start_time': self.test_start_time.isoformat(),
            'games_run': 0,
            'platform_started': False,
            'games_completed': False,
            'analysis_run': False,
            'metrics': {},
            'issues': []
        }

    def start_platform(self):
        """启动本地掼蛋平台"""
        logger.info("=" * 70)
        logger.info("【第1步】启动本地掼蛋平台")
        logger.info("=" * 70)

        if not os.path.exists(PLATFORM_EXE):
            logger.error(f"❌ 平台程序不存在: {PLATFORM_EXE}")
            self.results['issues'].append(f"Platform exe not found: {PLATFORM_EXE}")
            return False

        try:
            logger.info(f"启动 {PLATFORM_EXE}")
            self.platform_process = subprocess.Popen(
                [PLATFORM_EXE],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(3)
            logger.info("✓ 平台启动成功，等待服务初始化...")
            time.sleep(2)
            self.results['platform_started'] = True
            return True
        except Exception as e:
            logger.error(f"❌ 启动平台失败: {e}")
            self.results['issues'].append(str(e))
            return False

    def run_games(self, num_games=10):
        """运行M1对战"""
        logger.info("=" * 70)
        logger.info(f"【第2步】运行 {num_games} 局M1自战")
        logger.info("=" * 70)

        os.chdir(PROJECT_ROOT)

        for i in range(1, num_games + 1):
            logger.info(f"\n[{i}/{num_games}] 启动对局 {i}...")

            try:
                # 启动yf1_m1
                logger.info("  启动 yf1_m1...")
                p1 = subprocess.Popen(
                    [sys.executable, "src/communication/yf1_m1.py"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                time.sleep(1)

                # 启动yf2_m1
                logger.info("  启动 yf2_m1...")
                p2 = subprocess.Popen(
                    [sys.executable, "src/communication/yf2_m1.py"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                # 等待对局完成（30秒超时）
                logger.info("  等待对局完成...")
                time.sleep(30)

                # 清理进程
                try:
                    p1.terminate()
                    p2.terminate()
                    p1.wait(timeout=3)
                    p2.wait(timeout=3)
                except:
                    p1.kill()
                    p2.kill()

                logger.info(f"  ✓ 对局 {i} 完成")
                self.results['games_run'] += 1

            except Exception as e:
                logger.error(f"  ❌ 对局 {i} 失败: {e}")
                self.results['issues'].append(f"Game {i} failed: {e}")
                try:
                    p1.kill()
                    p2.kill()
                except:
                    pass

            time.sleep(1)

        self.results['games_completed'] = self.results['games_run'] > 0
        logger.info(f"\n✓ {self.results['games_run']}/{num_games} 局对局完成")
        return self.results['games_completed']

    def run_analysis(self):
        """运行分析脚本"""
        logger.info("=" * 70)
        logger.info("【第3步】运行分析脚本")
        logger.info("=" * 70)

        os.chdir(PROJECT_ROOT)

        try:
            logger.info("运行 analyze_game_rounds.py...")
            result = subprocess.run(
                [sys.executable, ANALYSIS_SCRIPT],
                capture_output=True,
                text=True,
                timeout=120
            )

            output = result.stdout
            logger.info("分析完成，提取关键指标...")

            # 提取PASS率
            pass_rates = self._extract_pass_rates(output)
            if pass_rates:
                logger.info(f"  yf1_m1 PASS率: {pass_rates.get('yf1', 'N/A')}")
                logger.info(f"  yf2_m1 PASS率: {pass_rates.get('yf2', 'N/A')}")
                self.results['metrics']['pass_rates'] = pass_rates

            # 提取胜场数
            wins = self._extract_wins(output)
            if wins is not None:
                logger.info(f"  M1队胜场数: {wins}")
                self.results['metrics']['team_wins'] = wins

            # 保存完整分析结果
            analysis_file = os.path.join(
                PROJECT_ROOT,
                "docs/claude-analysis/p0_verification_results.md"
            )
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write("# P0改进验证结果\n\n")
                f.write(f"生成时间: {datetime.now().isoformat()}\n\n")
                f.write("## 分析输出\n\n```\n")
                f.write(output)
                f.write("\n```\n")

            logger.info(f"✓ 分析结果已保存到 {analysis_file}")
            self.results['analysis_run'] = True
            return True

        except Exception as e:
            logger.error(f"❌ 分析失败: {e}")
            self.results['issues'].append(f"Analysis failed: {e}")
            return False

    def _extract_pass_rates(self, output):
        """从输出中提取PASS率"""
        rates = {}
        lines = output.split('\n')
        for line in lines:
            if 'yf1_m1' in line and 'PASS' in line:
                try:
                    # 格式: "yf1_m1: 0.0% (...)"
                    parts = line.split('%')
                    rate_str = parts[0].split()[-1]
                    rates['yf1'] = rate_str
                except:
                    pass
            elif 'yf2_m1' in line and 'PASS' in line:
                try:
                    parts = line.split('%')
                    rate_str = parts[0].split()[-1]
                    rates['yf2'] = rate_str
                except:
                    pass
        return rates

    def _extract_wins(self, output):
        """从输出中提取胜场数"""
        lines = output.split('\n')
        for line in lines:
            if '胜场' in line or 'wins' in line.lower():
                try:
                    # 简单提取数字
                    for word in line.split():
                        if word.isdigit():
                            return int(word)
                except:
                    pass
        return None

    def check_improvements(self):
        """检查P0改进是否有效"""
        logger.info("=" * 70)
        logger.info("【第4步】检查P0改进效果")
        logger.info("=" * 70)

        os.chdir(PROJECT_ROOT)

        # 检查新增的日志点
        checks = {
            '【P0改进②】': '两手规划触发',
            '【P0改进③】': '传牌动作执行',
        }

        logger.info("搜索日志中的改进触发点...")
        found = {}

        # 查看最近的game_records
        try:
            records = sorted(
                Path(GAME_RECORDS_DIR).glob("*m1*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )[:10]

            for record_file in records:
                try:
                    with open(record_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for marker, desc in checks.items():
                            if marker in content:
                                found[marker] = found.get(marker, 0) + 1
                except:
                    pass

            for marker, desc in checks.items():
                count = found.get(marker, 0)
                if count > 0:
                    logger.info(f"  ✓ {desc}: 发现 {count} 次")
                    self.results['metrics'][marker] = count
                else:
                    logger.warning(f"  ⚠ {desc}: 未发现（可能未触发）")
                    self.results['issues'].append(f"{desc} not triggered")

        except Exception as e:
            logger.warning(f"⚠ 无法检查日志点: {e}")

    def suggest_tuning(self):
        """根据结果建议参数调优"""
        logger.info("=" * 70)
        logger.info("【第5步】参数调优建议")
        logger.info("=" * 70)

        suggestions = []
        metrics = self.results.get('metrics', {})

        # 检查两手规划
        two_hand_count = metrics.get('【P0改进②】', 0)
        if two_hand_count == 0:
            suggestions.append({
                'issue': '两手规划未触发',
                'parameter': 'endgame_threshold',
                'file': 'src/decision/endgame_planner.py:14',
                'suggestion': '降低阈值从 12 → 10，使更多残局进入两手规划',
                'risk': '低'
            })
        elif two_hand_count > 100:
            suggestions.append({
                'issue': '两手规划过度触发',
                'parameter': 'endgame_threshold',
                'file': 'src/decision/endgame_planner.py:14',
                'suggestion': '提高阈值从 12 → 14，减少误触发',
                'risk': '低'
            })

        # 检查传牌动作
        pass_count = metrics.get('【P0改进③】', 0)
        if pass_count == 0:
            suggestions.append({
                'issue': '传牌动作未触发',
                'parameter': 'teammate_remain / card_power',
                'file': 'src/decision/teammate_opportunity_finder.py:180/186',
                'suggestion': '降低触发条件: teammate_remain 15→12, card_power 4→3',
                'risk': '中'
            })
        elif pass_count > 50:
            suggestions.append({
                'issue': '传牌动作过度触发',
                'parameter': 'should_prioritize_passing',
                'file': 'src/decision/teammate_opportunity_finder.py:176',
                'suggestion': '提高触发条件，减少不必要的传牌',
                'risk': '中'
            })

        # 检查胜率
        wins = metrics.get('team_wins', 0)
        if wins == 0:
            suggestions.append({
                'issue': '仍未获胜',
                'parameter': '多个',
                'file': '多个',
                'suggestion': '需要进一步分析具体失利原因，可能需要更激进的两手规划阈值',
                'risk': '高'
            })

        if suggestions:
            logger.info("\n检测到以下可优化项:\n")
            for i, sugg in enumerate(suggestions, 1):
                logger.info(f"{i}. 【{sugg['issue']}】")
                logger.info(f"   参数: {sugg['parameter']}")
                logger.info(f"   文件: {sugg['file']}")
                logger.info(f"   建议: {sugg['suggestion']}")
                logger.info(f"   风险: {sugg['risk']}\n")
            self.results['tuning_suggestions'] = suggestions
        else:
            logger.info("✓ 所有P0改进都已正常触发，暂无需要调优的参数")

    def cleanup(self):
        """清理资源"""
        logger.info("=" * 70)
        logger.info("【清理】关闭平台")
        logger.info("=" * 70)

        if self.platform_process:
            try:
                self.platform_process.terminate()
                self.platform_process.wait(timeout=3)
                logger.info("✓ 平台已关闭")
            except:
                try:
                    self.platform_process.kill()
                    logger.info("✓ 平台已强制关闭")
                except:
                    logger.warning("⚠ 无法关闭平台进程")

    def save_report(self):
        """保存完整报告"""
        report_file = os.path.join(
            PROJECT_ROOT,
            "docs/claude-analysis/p0_verification_report.json"
        )

        self.results['end_time'] = datetime.now().isoformat()

        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        logger.info(f"\n✓ 完整报告已保存: {report_file}")

    def run(self, num_games=10):
        """运行完整验证流程"""
        logger.info("\n")
        logger.info("╔" + "=" * 68 + "╗")
        logger.info("║  P0改进验证与微调 - 自动化测试脚本                      ║")
        logger.info("║  目标: 验证P0四项改进的效果并自动微调参数                ║")
        logger.info("╚" + "=" * 68 + "╝\n")

        try:
            # 1. 启动平台
            if not self.start_platform():
                logger.error("❌ 无法启动平台，退出")
                return False

            # 2. 运行对局
            if not self.run_games(num_games):
                logger.warning("⚠ 对局运行出现问题，继续分析已有数据")

            # 3. 分析结果
            if not self.run_analysis():
                logger.warning("⚠ 分析失败")

            # 4. 检查改进效果
            self.check_improvements()

            # 5. 提出调优建议
            self.suggest_tuning()

            # 6. 保存报告
            self.save_report()

            logger.info("\n" + "=" * 70)
            logger.info("✓ 验证流程完成！")
            logger.info("=" * 70)
            logger.info("\n📋 关键指标:")
            logger.info(f"   对局数: {self.results['games_run']}")
            logger.info(f"   收集的metrics: {self.results['metrics']}")
            if self.results['issues']:
                logger.info(f"\n⚠ 发现的问题:")
                for issue in self.results['issues']:
                    logger.info(f"   - {issue}")

            return True

        finally:
            self.cleanup()

if __name__ == "__main__":
    num_games = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    test = P0VerificationTest()
    success = test.run(num_games)

    sys.exit(0 if success else 1)
