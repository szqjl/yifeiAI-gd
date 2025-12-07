[1mdiff --git a/src/communication/utils.py b/src/communication/utils.py[m
[1mindex 2bcc16d..35d8a32 100644[m
[1m--- a/src/communication/utils.py[m
[1m+++ b/src/communication/utils.py[m
[36m@@ -228,16 +228,26 @@[m [mdef combine_handcards(handcards, rank, card_val):[m
                 [m
             rank = card[-1][m
             if rank in Straight:[m
[31m-                # 如果这张牌有三张，且不是最后一张需要的牌，跳过[m
[31m-                if card_count[rank] >= 3 and len(Straight) > 1:[m
[31m-                    nowhandcards.append(card)[m
[31m-                    continue[m
[31m-                # 如果这张牌有三张，且是最后一张需要的牌，检查是否会导致剩余两张[m
[31m-                if card_count[rank] >= 3 and len(Straight) == 1:[m
[31m-                    # 检查剩余的牌中是否还有同点数的牌[m
[31m-                    remaining = card_count[rank] - 1[m
[31m-                    if remaining == 2:[m
[31m-                        # 拆三张牌会导致对子，跳过[m
[32m+[m[32m                # 如果这张牌有三张，需要检查拆三张的后果[m
[32m+[m[32m                if card_count[rank] >= 3:[m
[32m+[m[32m                    # 检查拆三张后是否会产生大量小单张[m
[32m+[m[32m                    # 统计拆三张后可能产生的小单张数量[m
[32m+[m[32m                    # 先假设拆这张牌[m
[32m+[m[32m                    temp_card_count = card_count.copy()[m
[32m+[m[32m                    temp_card_count[rank] -= 1[m
[32m+[m[41m                    [m
[32m+[m[32m                    # 统计拆牌后可能产生的小单张（<7）数量[m
[32m+[m[32m                    small_singles_after = 0[m
[32m+[m[32m                    for r, cnt in temp_card_count.items():[m
[32m+[m[32m                        if cnt == 1:  # 单张[m
[32m+[m[32m                            # 转换为数字比较[m
[32m+[m[32m                            if r in ['3', '4', '5', '6']:  # <7的单张[m
[32m+[m[32m                                small_singles_after += 1[m
[32m+[m[41m                    [m
[32m+[m[32m                    # 条件1：如果不是最后一张需要的牌，跳过[m
[32m+[m[32m                    # 条件2：如果拆三张会导致剩余两张，跳过[m
[32m+[m[32m                    # 条件3：如果拆三张后会产生2张以上<7的单张，跳过[m
[32m+[m[32m                    if (len(Straight) > 1) or (len(Straight) == 1 and card_count[rank] - 1 == 2) or (small_singles_after >= 2):[m
                         nowhandcards.append(card)[m
                         continue[m
                 tmp.append(card)[m
[36m@@ -245,7 +255,13 @@[m [mdef combine_handcards(handcards, rank, card_val):[m
             else:[m
                 nowhandcards.append(card)[m
         [m
[31m-        # 如果没有成功组成顺子，且有红桃配，尝试使用红桃配补顺子[m
[32m+[m[32m        # 如果没有成功组成顺子，且有红桃配，万不得已才尝试使用红桃配补顺子[m
[32m+[m[32m        # 万不得已的条件：[m
[32m+[m[32m        # 1. 无法组成任何其他有效牌型[m
[32m+[m[32m        # 2. 手牌中单张数量过多[m
[32m+[m[32m        # 3. 没有更好的出牌选择[m
[32m+[m[32m        # 万不得已才使用红桃配补顺子：当前没有成功组成顺子[m
[32m+[m[32m        # 暂时简化条件，后续再完善复杂的条件判断[m
         if len(tmp) < 5 and wild_card:[m
             # 重新收集可以组成顺子的牌，包括红桃配[m
             Straight = [][m
[36m@@ -269,6 +285,14 @@[m [mdef combine_handcards(handcards, rank, card_val):[m
             nowhandcards = [][m
             wild_used = False[m
             [m
[32m+[m[32m            # 重新统计每张牌的数量，用于检查拆三张牌[m
[32m+[m[32m            card_count = {}[m
[32m+[m[32m            for card in handcards:[m
[32m+[m[32m                rank = card[-1][m
[32m+[m[32m                if rank not in card_count:[m
[32m+[m[32m                    card_count[rank] = 0[m
[32m+[m[32m                card_count[rank] += 1[m
[32m+[m[41m            [m
             for i in range(0, len(handcards)):[m
                 card = handcards[i][m
                 rank = card[-1][m
[36m@@ -282,6 +306,28 @@[m [mdef combine_handcards(handcards, rank, card_val):[m
                     else:[m
                         nowhandcards.append(card)[m
                 elif rank in Straight:[m
[32m+[m[32m                    # 同样检查是否会拆三张牌，添加小单张检查[m
[32m+[m[32m                    if card_count[rank] >= 3:[m
[32m+[m[32m                        # 检查拆三张后是否会产生大量小单张[m
[32m+[m[32m                        # 统计拆三张后可能产生的小单张数量[m
[32m+[m[32m                        # 先假设拆这张牌[m
[32m+[m[32m                        temp_card_count = card_count.copy()[m
[32m+[m[32m                        temp_card_count[rank] -= 1[m
[32m+[m[41m                        [m
[32m+[m[32m                        # 统计拆牌后可能产生的小单张（<7）数量[m
[32m+[m[32m                        small_singles_after = 0[m
[32m+[m[32m                        for r, cnt in temp_card_count.items():[m
[32m+[m[32m                            if cnt == 1:  # 单张[m
[32m+[m[32m                                # 转换为数字比较[m
[32m+[m[32m                                if r in ['3', '4', '5', '6']:  # <7的单张[m
[32m+[m[32m                                    small_singles_after += 1[m
[32m+[m[41m                        [m
[32m+[m[32m                        # 条件1：如果不是最后一张需要的牌，跳过[m
[32m+[m[32m                        # 条件2：如果拆三张会导致剩余两张，跳过[m
[32m+[m[32m                        # 条件3：如果拆三张后会产生2张以上<7的单张，跳过[m
[32m+[m[32m                        if (len(Straight) > 1) or (len(Straight) == 1 and card_count[rank] - 1 == 2) or (small_singles_after >= 2):[m
[32m+[m[32m                            nowhandcards.append(card)[m
[32m+[m[32m                            continue[m
                     tmp.append(card)[m
                     Straight.remove(rank)[m
                 else:[m
