"""逐副统计批跑结果：每个游戏会话的每副胜负"""
import json, os, glob, re
from collections import defaultdict

records_dir = 'game_records_v7'
files = sorted(glob.glob(os.path.join(records_dir, '*.json')))
pattern = re.compile(r'(\d{20}) \[(yf\d_v7)\]-\[.*\]-\[(\d+)\]-\[(\d+)\]\.json')

# 解析所有文件 → (ts_prefix, deal_num) → {yf1/yf2: filename}
all_deals = {}
for f in files:
    fname = os.path.basename(f)
    m = pattern.match(fname)
    if not m:
        continue
    ts = m.group(1)
    player = m.group(2).split('_')[0]  # yf1 or yf2
    deal = int(m.group(3))
    key = (ts[:14], deal)
    if key not in all_deals:
        all_deals[key] = {}
    all_deals[key][player] = fname

# 聚会话：间隔 > 5分钟 = 新会话
timestamps = sorted(set(k[0] for k in all_deals.keys()))
sessions, cur = [], [timestamps[0]]
for i in range(1, len(timestamps)):
    if int(timestamps[i]) - int(timestamps[i-1]) > 500:
        sessions.append(cur)
        cur = [timestamps[i]]
    else:
        cur.append(timestamps[i])
sessions.append(cur)

print('=' * 58)
print(f'共 {len(sessions)} 个游戏会话 ({len(files)} 个JSON)')
print('=' * 58)

total_v7, total_opp = 0, 0

for si, session in enumerate(sessions):
    # 收集本会话所有副（去重的deal号）
    seen_deals = set()
    deal_data = []
    for ts in session:
        for deal in range(1, 200):
            key = (ts, deal)
            if key in all_deals and deal not in seen_deals:
                seen_deals.add(deal)
                deal_data.append((deal, all_deals[key]))

    if not deal_data:
        continue

    deal_data.sort()

    start_ts = session[0]
    print(f'\n会话{si+1}: {start_ts[4:6]}-{start_ts[6:8]} {start_ts[8:10]}:{start_ts[10:12]} | {len(deal_data)}副')
    print('-' * 58)

    v7_w, opp_w = 0, 0
    marks = []

    for deal, data in deal_data:
        yf_fn = data.get('yf1') or data.get('yf2')
        if not yf_fn:
            continue
        try:
            with open(os.path.join(records_dir, yf_fn), 'r', encoding='utf-8') as fh:
                rec = json.load(fh)
        except Exception:
            marks.append((deal, '?'))
            continue

        # 用 result.order[0] 判头游（谁先出完）
        # order = [头游, 二游, 三游, 末游]  pos0+2=V7队, pos1+3=对手
        result = rec.get('result', {})
        order = result.get('order', [])
        winner = '?'
        if order and len(order) >= 1:
            head = order[0]
            if head in (0, 2):
                winner = 'V'
                v7_w += 1
            elif head in (1, 3):
                winner = 'O'
                opp_w += 1
            else:
                winner = '?'

        marks.append((deal, winner))

    # 标题行
    total = v7_w + opp_w
    rate = v7_w / total * 100 if total > 0 else 0
    print(f'  V7:{v7_w}  对手:{opp_w}  胜率:{rate:.1f}%')

    # 逐副标记：每10副一行
    line_parts = []
    for deal, w in marks:
        line_parts.append(f'{deal:2d}{w}')
    for i in range(0, len(line_parts), 10):
        print('    ' + ' '.join(line_parts[i:i+10]))

    total_v7 += v7_w
    total_opp += opp_w

print()
print('=' * 58)
print(f'全5场总计: V7 {total_v7}副  对手 {total_opp}副  胜率 {total_v7/(total_v7+total_opp)*100:.1f}%' if (total_v7+total_opp) > 0 else '无数据')
print('=' * 58)
