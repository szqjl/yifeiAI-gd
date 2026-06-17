## Learned User Preferences

- 始终使用简体中文回复。
- 希望 Agent 自动执行批跑与终端命令，不必每次手动点 Run；已配置 terminalAllowlist（git、python、pytest、pip、npm）。
- 仅在用户明确要求时才 git commit / push；推送前须读治理方案与 AGENT_PUSH_CHECKLIST。
- 改 M3 决策或解读批跑数据前，须先读 docs/guandan-brain/（ISSUES open、ITERATIONS 最新行）及 handoff。
- 接续任务时先读 docs/governance/分析接续-handoff.md 与 docs/analysis/handoffs/ 最新篇。
- 回放界面：可复制区仅保留【游戏记录】文件名；本步动作文本区宽约 200px，放右下。
- 用 replay_word.md 记录典型副的文字出牌步骤与完整 YF_REPLAY.bat 回放命令，便于沟通引用。
- 批跑或新迭代前常清空 game_records 与 replay_word.md；分析完的 game_records 可删除。
- 回放不得篡改真实出牌流水（不能实战输、回放赢）。
- 重视仓库目录整洁，按 docs/governance/M-V-Series-治理方案.md 归档整理。
- 掼蛋规则问答以 .cursor/rules/guandan-knowledge.mdc 为唯一标准；民间变体标注「非标准规则」。
- 新开 Agent 时复制 docs/guandan-brain/AGENT_FIRST_MESSAGE.md 默认首句。

## Learned Workspace Facts

- 掼蛋 AI 项目；改 AI 行为真源为 docs/guandan-brain/（ISSUES、ITERATIONS、EVAL）。
- 日常开发分支 m-dev（Gitee 真相源 origin/m-dev）；GitHub 仅 main 与 m-dev（default m-dev）；禁止 push main。
- M1 frozen（GUA-022 closed）；队胜率 KPI 只看 M3 批跑；P0 guard 改 m3_decision_engine，组牌/牌力走 V5+。
- M3 客户端 yf1_m3 / yf2_m3；对手 run_lalala_client3 / run_lalala_client4；离线 exe 为 offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe。
- 批跑入口 python -m batch_executor；--target-games 须为 3 的倍数（推荐 3 / 9 / 12，勿用 10）。
- v1006 exe 单次会话固定 3 局（argv 无效）；batch_games 真源为 current_batch.json；禁止裸信 gameResult.victoryNum。
- 局 ⊃ 多副；game_records 每条 JSON = 一副；completed_games = 平台局数；队胜看 victoryNum[0] vs [1]（0+2 一队，1+3 一队）。
- M3 须用 curPos / curAction / greaterPos 最新字段，不能盲信 JSON 内录制的 greaterPos / greaterAction。
- 回放工具 scripts/tools/yf_replay.py / YF_REPLAY.bat；Phase 5 仓库治理已结案。
- yf1 与 yf2 同队（pos 0+2）；队友公式 (myPos+2)%4。
- .batch_executor.lock 已加入 .gitignore。
- 批跑对账看 latest_victory_num.json 的 server_vn_raw / vn_source。
