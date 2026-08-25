# GUA-279 完成定义

**原则**（match [`6a8d4980`](https://www.botzone.org.cn/match/6a8d49800fbd680d7c830c1d)）：

> Bomb 若经 GUA-154 allocation **拆另一核 StraightFlush（补星抽张）→ 禁选**；  
> R16「队友剩1送单」**不**豁免此类补星炸。应优先完整 SF 或仅用炸组四星。

关联：GUA-154（事后 broken）、GUA-206（Bomb 豁免拆核误伤）、R16/GUA-063、GUA-078。

---

## 定音

| 项 | 内容 |
|----|------|
| 判定 | `_is_bomb_padding_break_other_sf`：`action[0]==Bomb` 且 `_get_broken_core_type==StraightFlush` |
| R16 | `_r16_bypass_except_bomb_pad_sf`：送单旁路仍放行，唯剔除补星 Bomb |
| 主攻滤网 | `broken_type in (Bomb, SF)` 分支优先拦补星 Bomb（先于 GUA-123/239） |
| 不停手 | 完整 SF；四星仅用炸组；非 Bomb 喂牌动作 |

## 停手

```bash
python -m pytest tests/test_gua279_bomb_pad_no_break_sf.py tests/test_gua069_weak_role_core_protection.py -k "R16 or gua279 or test_r16" -q
```
