# -*- coding: utf-8 -*-
"""
danzero_nn - DanZero（DMC 版）真实模型推理模块。

移植自 DanZero+ 官方仓库 `wintest/torch/client1.py` + `wintest/torch/model.py` +
`wintest/torch/util.py`（源码备份在 offline_platform/danzero_plus/）：
- 模型：MLPQNetwork（torch，6 层 Linear 512×5 → 1），权重 models/danzero/q_network.ckpt
  （12 个 numpy 数组，load_tf_weights 加载）。
- 决策：对 actionList 每个合法动作构造 567 维 state（x_batch，N×567），argmax Q 的行索引 = actIndex。
- tribute/back 阶段走规则（client1 的 tribute / back_action）。

状态机字段与 client1 ExampleClient 对齐：history_action / action_seq / remaining / over / flag /
mypos / other_left_hands / count_A 等，须在 notify（beginning/play/episodeOver）时同步更新。
"""
from __future__ import annotations

import logging
import pickle
from collections import Counter
from functools import reduce
from random import randint
from pathlib import Path

import numpy as np

try:
    import torch
    import torch.nn as nn
    _TORCH_AVAILABLE = True
except Exception:  # pragma: no cover - 环境缺 torch 时降级
    _TORCH_AVAILABLE = False

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOGGER = logging.getLogger("danzero_nn")

RANK = {
    "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6, "8": 7, "9": 8,
    "T": 9, "J": 10, "Q": 11, "K": 12, "A": 13,
}

# ---------- 牌编码工具（移植自 util.py） ----------

CardToNum = {
    'H2': 0, 'H3': 1, 'H4': 2, 'H5': 3, 'H6': 4, 'H7': 5, 'H8': 6, 'H9': 7, 'HT': 8, 'HJ': 9, 'HQ': 10, 'HK': 11, 'HA': 12,
    'S2': 13, 'S3': 14, 'S4': 15, 'S5': 16, 'S6': 17, 'S7': 18, 'S8': 19, 'S9': 20, 'ST': 21, 'SJ': 22, 'SQ': 23, 'SK': 24, 'SA': 25,
    'C2': 26, 'C3': 27, 'C4': 28, 'C5': 29, 'C6': 30, 'C7': 31, 'C8': 32, 'C9': 33, 'CT': 34, 'CJ': 35, 'CQ': 36, 'CK': 37, 'CA': 38,
    'D2': 39, 'D3': 40, 'D4': 41, 'D5': 42, 'D6': 43, 'D7': 44, 'D8': 45, 'D9': 46, 'DT': 47, 'DJ': 48, 'DQ': 49, 'DK': 50, 'DA': 51,
    'SB': 52, 'HR': 53,
}


def card2num(list_cards):
    """字符串牌列表 → 数字列表（平台 action 内码 ↔ DanZero 编码）。"""
    res = []
    if list_cards is None:
        return res
    if list_cards == -1:
        return [-1]
    for ele in list_cards:
        if ele in CardToNum:
            res.append(CardToNum[ele])
    return res


def card2array(list_cards):
    """数字牌列表 → 54 维计数数组（matrix 4×13 按列展开 + 2 王）。"""
    if len(list_cards) == 0:
        return np.zeros(54, dtype=np.int8)
    if list_cards == [-1]:
        return -1 * np.ones(54, dtype=np.int8)
    matrix = np.zeros([4, 13], dtype=np.int8)
    jokers = np.zeros(2, dtype=np.int8)
    counter = Counter(list_cards)
    for card, num_times in counter.items():
        if card == -1:
            continue
        if 0 <= card < 52:
            matrix[card // 13, card % 13] = num_times
        elif card == 52:
            jokers[0] = num_times
        elif card == 53:
            jokers[1] = num_times
    return np.concatenate((matrix.flatten('F'), jokers))


def combine_handcards(handcards, rank, card_val):
    """组合手牌 → {Single, Pair, Trips, Bomb, Straight, StraightFlush} + bomb_info。"""
    cards = {"Single": [], "Pair": [], "Trips": [], "Bomb": []}
    bomb_info = {}

    handcards = sorted(handcards, key=lambda item: card_val[item[1]])
    start = 0
    for i in range(1, len(handcards) + 1):
        if i == len(handcards) or handcards[i][-1] != handcards[i - 1][-1]:
            if (i - start == 1):
                cards["Single"].append(handcards[i - 1])
            elif (i - start == 2):
                cards["Pair"].append(handcards[start:i])
            elif (i - start) == 3:
                cards["Trips"].append(handcards[start:i])
            else:
                cards["Bomb"].append(handcards[start:i])
                bomb_info[handcards[start][-1]] = i - start
            start = i

    temp = []
    for i in handcards:
        if i[-1] != rank and i[-1] != 'B' and i[-1] != 'R':
            temp.append(i)
    for i in cards['Bomb']:
        if i[0][-1] != rank and i[0][-1] != 'B' and i[0][-1] != 'R':
            for j in i:
                temp.remove(j)
    cardre = [0] * 14
    cardre_value_s2v = {"A": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "T": 10, "J": 11,
                        "Q": 12, "K": 13}
    for i in temp:
        cardre[cardre_value_s2v[i[-1]]] += 1
    st = []
    minnum = 10
    mintwonum = 10

    for i in range(1, len(cardre) - 4):
        if 0 not in cardre[i:i + 5]:
            onenum = 0
            zeronum = 0
            twonum = 0
            for j in cardre[i:i + 5]:
                if j - 1 == 0:
                    zeronum += 1
                if j - 1 == 1:
                    onenum += 1
                if j - 1 == 2:
                    twonum += 1

            if zeronum > onenum and minnum >= onenum:
                if len(st) == 0:
                    if zeronum >= onenum + twonum:
                        st.append(i)
                        minnum = onenum
                        mintwonum = twonum
                else:
                    if minnum == onenum:
                        if i == 1:
                            if mintwonum > twonum:
                                if zeronum >= onenum + twonum:
                                    st = []
                                    st.append(i)
                                    minnum = onenum
                                    mintwonum = twonum
                        else:
                            if mintwonum >= twonum:
                                if zeronum >= onenum + twonum:
                                    st = []
                                    st.append(i)
                                    minnum = onenum
                                    mintwonum = twonum
                    else:
                        if zeronum >= onenum + twonum:
                            st = []
                            st.append(i)
                            minnum = onenum
                            mintwonum = twonum

    if 0 not in cardre[10:] and cardre[1] != 0:
        onenum = 0
        zeronum = 0
        twonum = 0
        for j in cardre[10:]:
            if j - 1 == 0:
                zeronum += 1
            if j - 1 == 1:
                onenum += 1
            if j - 1 == 2:
                twonum += 1
        if cardre[1] - 1 == 0:
            zeronum += 1
        if cardre[1] - 1 == 1:
            onenum += 1
        if cardre[1] - 1 == 2:
            twonum += 1
        if zeronum > onenum and minnum >= onenum:
            if len(st) == 0:
                if zeronum >= onenum + twonum:
                    st.append(10)
            else:
                if minnum == onenum:
                    if mintwonum >= twonum:
                        if zeronum >= onenum + twonum:
                            st = []
                            st.append(10)
                else:
                    if zeronum >= onenum + twonum:
                        st = []
                        st.append(10)

    tmp = []
    Flushtmp = []
    nowhandcards = []
    Straight = []
    if len(st) > 0:
        for i in range(st[0], st[0] + 5):
            if 1 < i < 10:
                Straight.append(str(i))
            if i % 13 == 1:
                Straight.append('A')
            if i == 10:
                Straight.append('T')
            if i == 11:
                Straight.append('J')
            if i == 12:
                Straight.append('Q')
            if i == 13:
                Straight.append('K')
    sttemp = []
    for i in range(4):
        sttemp.append([0] * 5)
    counttemp = 0

    colortemp = {"S": 0, "H": 1, "C": 2, "D": 3}
    rev_colortemp = {0: 'S', 1: 'H', 2: 'C', 3: 'D'}
    for i in range(0, len(handcards) - 1):
        if handcards[i][-1] in Straight:
            sttemp[colortemp[handcards[i][0]]][counttemp] += 1
            if handcards[i][-1] != handcards[i + 1][-1]:
                counttemp += 1

    StraightFlushflag = -1

    for i in range(4):
        if sttemp[i][0] > 0 and sttemp[i][1] > 0 and sttemp[i][2] > 0 and sttemp[i][3] > 0 and sttemp[i][4] > 0:
            StraightFlushflag = i
    if StraightFlushflag >= 0:
        for i in Straight:
            Flushtmp.append(rev_colortemp[StraightFlushflag] + i)
        for i in range(0, len(handcards)):
            if handcards[i] not in Flushtmp:
                nowhandcards.append(handcards[i])

    else:
        for i in range(0, len(handcards)):
            if handcards[i][-1] in Straight:
                tmp.append(handcards[i])
                Straight.remove(handcards[i][-1])
            else:
                nowhandcards.append(handcards[i])

    newcards = {}
    newcards["Single"] = []
    newcards["Pair"] = []
    newcards["Trips"] = []
    newcards["Bomb"] = []
    newcards['Straight'] = []
    newcards['StraightFlush'] = []

    if len(tmp) == 5:
        if tmp[-1][-1] == 'A' and tmp[-2][-1] == '5':
            tmpptmp = [tmp[-1]]
            for kkk in tmp[:-1]:
                tmpptmp.append(kkk)
            newcards['Straight'].append(tmpptmp)
        else:
            newcards['Straight'].append(tmp)
    if len(Flushtmp) == 5:
        newcards['StraightFlush'].append(Flushtmp)
    start = 0
    for i in range(1, len(nowhandcards) + 1):
        if i == len(nowhandcards) or nowhandcards[i][-1] != nowhandcards[i - 1][-1]:
            if (i - start == 1):
                newcards["Single"].append(nowhandcards[i - 1])
            elif (i - start == 2):
                newcards["Pair"].append(nowhandcards[start:i])
            elif (i - start) == 3:
                newcards["Trips"].append(nowhandcards[start:i])
            else:
                newcards["Bomb"].append(nowhandcards[start:i])
            start = i
    return newcards, bomb_info


# ---------- 模型定义（移植自 wintest/torch/model.py，仅 DMC Q-net） ----------

def mlp(sizes, activation, output_activation=None):
    if output_activation is None:
        output_activation = nn.Identity
    layers = []
    for j in range(len(sizes) - 1):
        act = activation if j < len(sizes) - 2 else output_activation
        layers += [nn.Linear(sizes[j], sizes[j + 1]), act()]
    return nn.Sequential(*layers)


class MLPQ(nn.Module):
    def __init__(self, obs_dim, hidden_sizes, activation):
        super().__init__()
        self.q_net = mlp([obs_dim] + list(hidden_sizes) + [1], activation)

    def forward(self, obs):
        return torch.squeeze(self.q_net(obs), -1)


class MLPQNetwork(nn.Module):
    """DMC Q-net：输入 567 维 state（N×567），输出 N 个 Q 值。"""

    def __init__(self, observation_space, hidden_sizes=(512, 512, 512, 512, 512), activation=nn.Tanh):
        super().__init__()
        self.q = MLPQ(observation_space, hidden_sizes, activation)

    def load_tf_weights(self, weights):
        name = ['q_net.0.weight', 'q_net.0.bias', 'q_net.2.weight', 'q_net.2.bias', 'q_net.4.weight', 'q_net.4.bias',
                'q_net.6.weight', 'q_net.6.bias', 'q_net.8.weight', 'q_net.8.bias', 'q_net.10.weight', 'q_net.10.bias']
        tensor_weights = []
        for weight in weights:
            t = torch.tensor(np.asarray(weight))
            tensor_weights.append(t.T if t.ndim == 2 else t)
        new_weights = dict(zip(name, tensor_weights))
        self.q.load_state_dict(new_weights)
        _LOGGER.info("load tf weights success (DMC Q-net, 6 layers)")

    def get_max_n_index(self, data, n):
        q_list = self.q(torch.tensor(np.asarray(data)).to(torch.float32))
        q_list = q_list.detach().numpy()
        return q_list.argsort()[-n:][::-1].tolist()


def _get_one_hot_array(num_left_cards, max_num_cards, flag):
    if flag == 0:
        one_hot = np.zeros(max_num_cards)
        one_hot[num_left_cards - 1] = 1
    else:
        one_hot = np.zeros(max_num_cards + 1)
        one_hot[num_left_cards] = 1
    return one_hot


# ---------- 决策器（移植自 client1.py ExampleClient，去 websocket/zmq） ----------

class DanZeroNN:
    """DanZero（DMC）决策器：维护完整对局状态，act 时返回 actIndex。"""

    MODEL_PATH = _REPO_ROOT / "models" / "danzero" / "q_network.ckpt"

    def __init__(self, user_info: str):
        self.user_info = user_info
        self.mypos = 0
        self.history_action = {0: [], 1: [], 2: [], 3: []}
        self.action_seq = []
        self.action_order = []
        self.remaining = {0: 27, 1: 27, 2: 27, 3: 27}
        self.other_left_hands = [2 for _ in range(54)]
        self.flag = 0
        self.over = []
        self.rank = 1
        self.oppo_rank = 1
        self.count_A = 0
        self.count_A_self = 0
        self.count_A_oppo = 0
        self.tribute_result = None

        self.model_q: MLPQNetwork | None = None
        self._load_model()

    # ---- 模型加载 ----

    def _load_model(self) -> None:
        if not _TORCH_AVAILABLE:
            _LOGGER.warning("torch 不可用，DanZeroNN 降级（decide 返回 0）")
            return
        ckpt = self.MODEL_PATH
        if not ckpt.exists():
            _LOGGER.error("DMC Q-net 权重缺失: %s", ckpt)
            return
        with open(ckpt, "rb") as f:
            tf_weights = pickle.load(f)
        self.model_q = MLPQNetwork(567)
        self.model_q.load_tf_weights(tf_weights)
        self.model_q.eval()
        _LOGGER.info("[%s] DanZero DMC Q-net 加载完成: %s", self.user_info, ckpt)

    @property
    def ready(self) -> bool:
        return self.model_q is not None

    # ---- notify 状态更新（移植 client1.received_message notify 分支） ----

    def preprocess(self, data: dict) -> dict:
        msg_type = data.get("type", "")
        if msg_type != "notify":
            return data
        stage = data.get("stage", "")
        if stage == "beginning":
            self.count_A += int(data.get("curRank") == "A")
            self.count_A_self += int(data.get("selfRank") == "A")
            self.count_A_oppo += int(data.get("oppoRank") == "A")
            self.mypos = data.get("myPos", self.mypos)
        elif stage == "tribute":
            self.tribute_result = data.get("result")
        elif stage == "play":
            self._notify_play(data)
        elif stage == "episodeOver":
            self.history_action = {0: [], 1: [], 2: [], 3: []}
            self.action_seq = []
            self.other_left_hands = [2 for _ in range(54)]
            self.remaining = {0: 27, 1: 27, 2: 27, 3: 27}
            self.flag = 0
            self.over = []
            self.rank = 1
            self.oppo_rank = 1
        return data

    def _notify_play(self, message: dict) -> None:
        just_play = message.get("curPos")
        cur_action = message.get("curAction") or ["PASS", "PASS", ["PASS"]]
        if not isinstance(cur_action, (list, tuple)) or len(cur_action) < 3:
            cur_action = ["PASS", "PASS", ["PASS"]]
        action = card2num(cur_action[2])
        if just_play is None or not isinstance(just_play, int) or not (0 <= just_play <= 3):
            return
        if message.get("curPos") != self.mypos:
            for ele in action:
                self.other_left_hands[ele] -= 1
        if len(self.over) == 0:
            self.action_order.append(just_play)
            self.action_seq.append(action)
            self.history_action[message.get("curPos")].append(action)
        elif len(self.over) == 1:
            if len(action) > 0 and self.flag == 1:
                self.flag = 2
                if just_play == (self.over[0] + 3) % 4:
                    self.action_order.append(just_play)
                    self.action_seq.append(action)
                    self.history_action[message.get("curPos")].append(action)
                    self.action_order.append(self.over[0])
                    self.history_action[self.over[0]].append([-1])
                    self.action_seq.append([-1])
                else:
                    self.action_order.append(just_play)
                    self.action_seq.append(action)
                    self.history_action[message.get("curPos")].append(action)
            elif self.flag == 1 and (just_play + 1) % 4 == self.over[0]:
                self.flag = 2
                self.action_order.append(just_play)
                self.action_seq.append(action)
                self.history_action[message.get("curPos")].append(action)
                self.action_order.append(self.over[0])
                self.history_action[self.over[0]].append([-1])
                self.action_seq.append([-1])
                self.action_order.append((just_play + 2) % 4)
                self.history_action[(just_play + 2) % 4].append([])
                self.action_seq.append([])
            elif just_play == (self.over[0] + 3) % 4 and self.flag == 2:
                self.action_order.append(just_play)
                self.action_seq.append(action)
                self.history_action[message.get("curPos")].append(action)
                self.action_order.append(self.over[0])
                self.history_action[self.over[0]].append([-1])
                self.action_seq.append([-1])
            else:
                self.action_order.append(just_play)
                self.action_seq.append(action)
                self.history_action[message.get("curPos")].append(action)
        elif len(self.over) == 2:
            if len(action) > 0 and self.flag <= 2:
                if (just_play + 1) % 4 not in self.over:
                    self.flag = 3
                    self.action_order.append(just_play)
                    self.action_seq.append(action)
                    self.history_action[message.get("curPos")].append(action)
                else:
                    self.flag = 3
                    self.action_order.append(just_play)
                    self.action_seq.append(action)
                    self.history_action[message.get("curPos")].append(action)
                    self.action_order.append((just_play + 1) % 4)
                    self.history_action[(just_play + 1) % 4].append([-1])
                    self.action_seq.append([-1])
                    self.action_order.append((just_play + 2) % 4)
                    self.history_action[(just_play + 2) % 4].append([-1])
                    self.action_seq.append([-1])
            elif self.flag <= 2 and (just_play + 1) % 4 in self.over:
                self.flag = 3
                self.action_order.append(just_play)
                self.action_seq.append(action)
                self.history_action[message.get("curPos")].append(action)
                self.action_order.append((just_play + 1) % 4)
                self.history_action[(just_play + 1) % 4].append([-1])
                self.action_seq.append([-1])
                self.action_order.append((just_play + 2) % 4)
                self.history_action[(just_play + 2) % 4].append([-1])
                self.action_seq.append([-1])
                if just_play == (self.over[-1] + 2) % 4:
                    self.action_order.append((just_play + 3) % 4)
                    self.history_action[(just_play + 3) % 4].append([])
                    self.action_seq.append([])
            elif (just_play + 1) % 4 in self.over and self.flag == 3:
                self.action_order.append(just_play)
                self.action_seq.append(action)
                self.history_action[message.get("curPos")].append(action)
                self.action_order.append((just_play + 1) % 4)
                self.history_action[(just_play + 1) % 4].append([-1])
                self.action_seq.append([-1])
                self.action_order.append((just_play + 2) % 4)
                self.history_action[(just_play + 2) % 4].append([-1])
                self.action_seq.append([-1])
            else:
                self.action_order.append(just_play)
                self.action_seq.append(action)
                self.history_action[message.get("curPos")].append(action)

        self.remaining[just_play] -= len(action)
        if self.remaining[just_play] == 0:
            self.over.append(just_play)

    # ---- act 决策（移植 client1.received_message act 分支 + prepare + DMC sample） ----

    def decide(self, data: dict) -> int:
        stage = data.get("stage", "")
        if stage == "back":
            return self._back_action(data, self.mypos, self.tribute_result or [])
        if stage == "tribute":
            action_list = data.get("actionList") or []
            rank = data.get("curRank", "2")
            if not action_list:
                return 0
            return self._tribute(action_list, rank)
        if stage == "play":
            if self.flag == 0:
                init_hand = card2num(data.get("handCards"))
                for ele in init_hand:
                    self.other_left_hands[ele] -= 1
                self.flag = 1
            action_list = data.get("actionList") or []
            if len(action_list) == 1:
                return 0
            state = self._prepare(data)
            if self.model_q is None:
                return 0
            index = self.model_q.get_max_n_index(state["x_batch"], 1)[-1]
            return int(index)
        return 0

    def _prepare(self, message: dict) -> dict:
        legal_actions = [card2num(i[2]) for i in message["actionList"]]
        num_legal_actions = len(legal_actions)
        my_handcards = card2array(card2num(message["handCards"]))
        my_handcards_batch = np.repeat(my_handcards[np.newaxis, :], num_legal_actions, axis=0)

        universal_card_flag = self._proc_universal(my_handcards, RANK[message["curRank"]])
        universal_card_flag_batch = np.repeat(universal_card_flag[np.newaxis, :], num_legal_actions, axis=0)

        count_a = np.array([self.count_A])
        count_a_batch = np.repeat(count_a[np.newaxis, :], num_legal_actions, axis=0)

        count_a_self = np.array([self.count_A_self])
        count_a_self_batch = np.repeat(count_a_self[np.newaxis, :], num_legal_actions, axis=0)

        count_a_oppo = np.array([self.count_A_oppo])
        count_a_oppo_batch = np.repeat(count_a_oppo[np.newaxis, :], num_legal_actions, axis=0)

        other_hands = []
        for i in range(54):
            if self.other_left_hands[i] == 1:
                other_hands.append(i)
            elif self.other_left_hands[i] == 2:
                other_hands.append(i)
                other_hands.append(i)
        other_handcards = card2array(other_hands)
        other_handcards_batch = np.repeat(other_handcards[np.newaxis, :], num_legal_actions, axis=0)

        last_action = []
        if len(self.action_seq) > 0:
            last_action = card2array(self.action_seq[-1])
        else:
            last_action = card2array([-1])
        last_action_batch = np.repeat(last_action[np.newaxis, :], num_legal_actions, axis=0)

        last_teammate_action = []
        if len(self.history_action[(self.mypos + 2) % 4]) > 0 and (self.mypos + 2) % 4 not in self.over:
            last_teammate_action = card2array(self.history_action[(self.mypos + 2) % 4][-1])
        else:
            last_teammate_action = card2array([-1])
        last_teammate_action_batch = np.repeat(last_teammate_action[np.newaxis, :], num_legal_actions, axis=0)

        my_action_batch = np.zeros(my_handcards_batch.shape)
        for j, action in enumerate(legal_actions):
            my_action_batch[j, :] = card2array(action)

        down_num_cards_left = _get_one_hot_array(self.remaining[(self.mypos + 1) % 4], 27, 1)
        down_num_cards_left_batch = np.repeat(down_num_cards_left[np.newaxis, :], num_legal_actions, axis=0)

        teammate_num_cards_left = _get_one_hot_array(self.remaining[(self.mypos + 2) % 4], 27, 1)
        teammate_num_cards_left_batch = np.repeat(teammate_num_cards_left[np.newaxis, :], num_legal_actions, axis=0)

        up_num_cards_left = _get_one_hot_array(self.remaining[(self.mypos + 3) % 4], 27, 1)
        up_num_cards_left_batch = np.repeat(up_num_cards_left[np.newaxis, :], num_legal_actions, axis=0)

        down_played_cards = card2array([])
        if len(self.history_action[(self.mypos + 1) % 4]) > 0:
            down_played_cards = card2array(reduce(lambda x, y: x + y, self.history_action[(self.mypos + 1) % 4]))
        down_played_cards_batch = np.repeat(down_played_cards[np.newaxis, :], num_legal_actions, axis=0)

        teammate_played_cards = card2array([])
        if len(self.history_action[(self.mypos + 2) % 4]) > 0:
            teammate_played_cards = card2array(reduce(lambda x, y: x + y, self.history_action[(self.mypos + 2) % 4]))
        teammate_played_cards_batch = np.repeat(teammate_played_cards[np.newaxis, :], num_legal_actions, axis=0)

        up_played_cards = card2array([])
        if len(self.history_action[(self.mypos + 3) % 4]) > 0:
            up_played_cards = card2array(reduce(lambda x, y: x + y, self.history_action[(self.mypos + 3) % 4]))
        up_played_cards_batch = np.repeat(up_played_cards[np.newaxis, :], num_legal_actions, axis=0)

        self_rank = _get_one_hot_array(RANK[message["selfRank"]], 13, 0)
        self.rank = RANK[message["selfRank"]]
        self_rank_batch = np.repeat(self_rank[np.newaxis, :], num_legal_actions, axis=0)

        oppo_rank = _get_one_hot_array(RANK[message["oppoRank"]], 13, 0)
        self.oppo_rank = RANK[message["oppoRank"]]
        oppo_rank_batch = np.repeat(oppo_rank[np.newaxis, :], num_legal_actions, axis=0)

        cur_rank = _get_one_hot_array(RANK[message["curRank"]], 13, 0)
        cur_rank_batch = np.repeat(cur_rank[np.newaxis, :], num_legal_actions, axis=0)

        x_batch = np.hstack((my_handcards_batch,
                             universal_card_flag_batch,
                             other_handcards_batch,
                             last_action_batch,
                             last_teammate_action_batch,
                             down_played_cards_batch,
                             teammate_played_cards_batch,
                             up_played_cards_batch,
                             down_num_cards_left_batch,
                             teammate_num_cards_left_batch,
                             up_num_cards_left_batch,
                             self_rank_batch,
                             oppo_rank_batch,
                             cur_rank_batch,
                             my_action_batch))
        x_no_action = np.hstack((my_handcards,
                                 universal_card_flag,
                                 other_handcards,
                                 last_action,
                                 last_teammate_action,
                                 down_played_cards,
                                 teammate_played_cards,
                                 up_played_cards,
                                 down_num_cards_left,
                                 teammate_num_cards_left,
                                 up_num_cards_left,
                                 self_rank,
                                 oppo_rank,
                                 cur_rank,
                                 count_a,
                                 count_a_self,
                                 count_a_oppo))
        return {
            "x_batch": x_batch.astype(np.int8),
            "x_no_action": x_no_action.astype(np.float32),
        }

    def _proc_universal(self, handCards, cur_rank):
        """万能牌标志位，12 维（cur_rank 为 1-13 数字）。"""
        res = np.zeros(12, dtype=np.int8)
        if handCards[(cur_rank - 1) * 4] == 0:
            return res
        res[0] = 1
        rock_flag = 0
        for i in range(4):
            left, right = 0, 5
            temp = [handCards[i + j * 4] if i + j * 4 != (cur_rank - 1) * 4 else 0 for j in range(5)]
            while right <= 12:
                zero_num = temp.count(0)
                if zero_num <= 1:
                    rock_flag = 1
                    break
                else:
                    temp.append(handCards[i + right * 4] if i + right * 4 != (cur_rank - 1) * 4 else 0)
                    temp.pop(0)
                    left += 1
                    right += 1
            if rock_flag == 1:
                break
        res[1] = rock_flag

        num_count = [0] * 13
        for i in range(4):
            for j in range(13):
                if handCards[i + j * 4] != 0 and i + j * 4 != (cur_rank - 1) * 4:
                    num_count[j] += 1
        num_max = max(num_count)
        if num_max >= 6:
            res[2:8] = 1
        elif num_max == 5:
            res[3:8] = 1
        elif num_max == 4:
            res[4:8] = 1
        elif num_max == 3:
            res[5:8] = 1
        elif num_max == 2:
            res[6:8] = 1
        else:
            res[7] = 1
        temp = 0
        for i in range(13):
            if num_count[i] != 0:
                temp += 1
                if i >= 1:
                    if num_count[i] == 2 and num_count[i - 1] >= 3 or num_count[i] >= 3 and num_count[i - 1] == 2:
                        res[9] = 1
                    elif num_count[i] == 2 and num_count[i - 1] == 2:
                        res[11] = 1
                if i >= 2:
                    if num_count[i - 2] == 1 and num_count[i - 1] >= 2 and num_count[i] >= 2 or \
                            num_count[i - 2] >= 2 and num_count[i - 1] == 1 and num_count[i] >= 2 or \
                            num_count[i - 2] >= 2 and num_count[i - 1] >= 2 and num_count[i] == 1:
                        res[10] = 1
            else:
                temp = 0
        if temp >= 4:
            res[8] = 1
        return res

    # ---- tribute / back 规则（移植 client1） ----

    def _tribute(self, action_list, rank):
        rank_card = "H" + rank
        first_action = action_list[0]
        if rank_card in first_action[2] and len(action_list) > 1:
            return 1
        return 0

    def _back_action(self, msg, mypos, tribute_result):
        rank = msg["curRank"]
        self.action = msg["actionList"]
        handCards = msg["handCards"]
        card_val = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "T": 10, "J": 11,
                    "Q": 12, "K": 13, "A": 14, "B": 16, "R": 17}
        card_val[rank] = 15

        def flag_TJQ(handCards_X):
            flag_T, flag_J, flag_Q = False, False, False
            for i in range(len(handCards_X)):
                if handCards_X[i][0][-1] == "T":
                    flag_T = True
                if handCards_X[i][0][-1] == "J":
                    flag_J = True
                if handCards_X[i][0][-1] == "Q":
                    flag_Q = True
            return flag_T, flag_J, flag_Q

        def get_card_index(target: str) -> int:
            for i in range(len(self.action)):
                if self.action[i][2][0] == target:
                    return i
            return 0

        def choose_in_single(single_list) -> str:
            tribute_pos = 0
            for my_pos in tribute_result:
                if my_pos[1] == mypos:
                    tribute_pos = my_pos[0]
            n = len(single_list)
            if (int(tribute_pos) + int(mypos)) % 2 != 0:
                for card in single_list:
                    if card in ["H5", "HT"]:
                        return card
                    elif card in ["S5", "C5", "D5", "ST", "CT", "DT"]:
                        return card
                return single_list[randint(0, n - 1)]
            else:
                back_list = []
                for card in single_list:
                    if card[-1] != "T":
                        if int(card[-1]) < 5:
                            back_list.append(card)
                if back_list:
                    return back_list[randint(0, len(back_list) - 1)]
                return single_list[randint(0, n - 1)]

        def choose_in_pair(pair_list, pair_list_from_handcards) -> str:
            val_dict = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "T": 10}
            if len(pair_list) < 3:
                return pair_list[0][0]
            for i in range(len(pair_list)):
                flag = False
                if i >= 2:
                    pair_first_val, pair_second_val, pair_third_val = pair_list[i - 2][0][-1], pair_list[i - 1][0][-1], pair_list[i][0][-1]
                    if val_dict[pair_first_val] == val_dict[pair_second_val] - 1 and val_dict[pair_second_val] == val_dict[pair_third_val] - 1:
                        flag = True
                if 1 <= i <= len(pair_list) - 2:
                    pair_first_val, pair_second_val, pair_third_val = pair_list[i - 1][0][-1], pair_list[i][0][-1], pair_list[i + 1][0][-1]
                    if val_dict[pair_first_val] == val_dict[pair_second_val] - 1 and val_dict[pair_second_val] == val_dict[pair_third_val] - 1:
                        flag = True
                if i <= len(pair_list) - 3:
                    pair_first_val, pair_second_val, pair_third_val = pair_list[i][0][-1], pair_list[i + 1][0][-1], pair_list[i + 2][0][-1]
                    if val_dict[pair_first_val] == val_dict[pair_second_val] - 1 and val_dict[pair_second_val] == val_dict[pair_third_val] - 1:
                        flag = True
                if pair_list[i][0][-1] == "9":
                    flag_T, flag_J, flag_Q = flag_TJQ(pair_list_from_handcards)
                    if flag_T and flag_J:
                        flag = True
                if pair_list[i][0][-1] == "T":
                    flag_T, flag_J, flag_Q = flag_TJQ(pair_list_from_handcards)
                    if flag_J and flag_Q:
                        flag = True
                if flag:
                    continue
                else:
                    return pair_list[i][0]
            return pair_list[0][0]

        def choose_in_trips(trips_list, trips_list_from_handcards) -> str:
            val_dict = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "T": 10}
            if len(trips_list) < 2:
                return trips_list[0][0]
            for i in range(len(trips_list)):
                flag = False
                if i >= 1:
                    pair_first_val, pair_second_val = trips_list[i - 1][0][-1], trips_list[i][0][-1]
                    if val_dict[pair_first_val] == val_dict[pair_second_val] - 1:
                        flag = True
                if i <= len(trips_list) - 2:
                    pair_first_val, pair_second_val = trips_list[i][0][-1], trips_list[i + 1][0][-1]
                    if val_dict[pair_first_val] == val_dict[pair_second_val] - 1:
                        flag = True
                if trips_list[i][0][-1] == "T":
                    flag_T, flag_J, flag_Q = flag_TJQ(trips_list_from_handcards)
                    if flag_J:
                        flag = True
                if flag:
                    continue
                else:
                    return trips_list[i][0]
            return trips_list[0][0]

        def choose_in_bomb(bomb_list, bomb_info) -> str:
            def get_card_from_bomb(bomb_list, key):
                for bomb in bomb_list:
                    for card in bomb:
                        if card[-1] == key:
                            return card

            for key, value in bomb_info.items():
                if value > 4:
                    return get_card_from_bomb(bomb_list, key)
            return bomb_list[0][0]

        combined_handcards, handCards_bomb_info = combine_handcards(handCards, rank, card_val)
        combined_temp = {"Single": [], "Trips": [], "Pair": [], "Bomb": []}
        temp_bomb_info = {}
        for card in combined_handcards["Single"]:
            if card_val[card[-1]] <= 10:
                combined_temp["Single"].append(card)
        for trips_card in combined_handcards["Trips"]:
            if card_val[trips_card[0][-1]] <= 10:
                combined_temp["Trips"].append(trips_card)
        for pair_card in combined_handcards["Pair"]:
            if card_val[pair_card[0][-1]] <= 10:
                combined_temp["Pair"].append(pair_card)
        for bomb_card in combined_handcards["Bomb"]:
            if card_val[bomb_card[0][-1]] <= 10:
                combined_temp["Bomb"].append(bomb_card)
        for key, values in handCards_bomb_info.items():
            if card_val[key] <= 10:
                temp_bomb_info[key] = values
        card = None
        if combined_temp["Single"]:
            card = choose_in_single(combined_temp["Single"])
        elif combined_temp["Trips"]:
            card = choose_in_trips(combined_temp["Trips"], combined_handcards["Trips"])
        elif combined_temp["Pair"]:
            card = choose_in_pair(combined_temp["Pair"], combined_handcards["Pair"])
        elif combined_temp["Bomb"]:
            card = choose_in_bomb(combined_temp["Bomb"], temp_bomb_info)
        else:
            temp = []
            for handCard in handCards:
                if card_val[handCard[-1]] <= 10:
                    temp.append(handCard)
            card = temp[randint(0, len(temp) - 1)]
        return get_card_index(card)
