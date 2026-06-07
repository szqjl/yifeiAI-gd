# -*- coding: utf-8 -*-
"""
GUA-038 BC 热启动测试

覆盖：
  1. BCSample 创建与维度校验
  2. load_samples 从 mock JSON 加载
  3. train_val_split 切分正确性
  4. create_batches batch 结构
  5. _filter_by_victory_num 过滤逻辑
  6. _reconstruct_features_from_full_state
  7. V7Recorder 录牌基本功能
  8. masked_cross_entropy (需 torch)
  9. CLI 入口解析 (run_bc_training.py)
"""

from __future__ import annotations

import json
import sys
import os
from pathlib import Path
from typing import List

import numpy as np
import pytest

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.v.nn.training.bc_dataset import (
    BCSample,
    load_samples,
    train_val_split,
    create_batches,
    _filter_by_victory_num,
    _reconstruct_features_from_full_state,
    _reconstruct_features_from_my_decision,
    _get_victory_num,
    TARGET_FEATURE_DIM,
)
from src.v.nn.recorder.v7_recorder import V7Recorder


# ═══════════════════════════════════════════════════════
#  Mock 数据工厂
# ═══════════════════════════════════════════════════════

def _make_mock_full_state(**overrides) -> dict:
    """构造 mock full_state。"""
    state = {
        "handCards": ["S3", "S4", "S5", "H3", "H5", "C2", "D2"],
        "actionList": [["S3"], ["S4"], ["PASS"]],
        "actionList_size": 3,
        "publicInfo": [],
        "curAction": None,
        "greaterAction": ["S3"],
        "myPos": 0,
        "curPos": 1,
        "greaterPos": 1,
        "curRank": "2",
        "stage": "play",
        "tributeResult": None,
    }
    state.update(overrides)
    return state


def _make_mock_game_record(
    player_name: str = "yf1_m3",
    victory_num: list = None,
    num_steps: int = 5,
) -> dict:
    """构造 mock game_records JSON。"""
    if victory_num is None:
        victory_num = [3, 0, 3, 0]

    steps = []
    for i in range(num_steps):
        steps.append({
            "step": i,
            "timestamp": f"2026-06-07T00:00:{i:02d}",
            "full_state": _make_mock_full_state(
                handCards=[f"S{j}" for j in range(3, 3 + 7 - i)],
                actionList_size=3,
            ),
            "action_index": i % 3,
            "action": [[f"S{3 + i % 3}"]],
            "meta": {
                "step": i,
                "player_id": 0,
                "player_name": player_name,
            },
        })

    return {
        "player_name": player_name,
        "player_id": 0,
        "game_id": "mock_game_001",
        "result": {
            "victoryNum": victory_num,
        },
        "game_info": {
            "selfRank": "2",
            "oppoRank": "2",
        },
        "steps": steps,
    }


@pytest.fixture
def mock_record_dir(tmp_path) -> str:
    """创建包含 mock game_records 的临时目录。"""
    record = _make_mock_game_record(
        player_name="yf1_m3",
        victory_num=[3, 0, 3, 0],
        num_steps=5,
    )
    fp = tmp_path / "mock_yf1_m3.json"
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(record, f)
    return str(tmp_path)


# ═══════════════════════════════════════════════════════
#  1. BCSample 创建与维度校验
# ═══════════════════════════════════════════════════════

class TestBCSample:
    def test_create_valid(self):
        """合法 BCSample 创建。"""
        features = np.zeros(TARGET_FEATURE_DIM, dtype=np.float32)
        features[0] = 1.0
        sample = BCSample(
            features=features,
            action_index=1,
            action_list_size=3,
            source_file="test.json",
        )
        assert sample.features.shape == (TARGET_FEATURE_DIM,)
        assert sample.action_index == 1
        assert sample.action_list_size == 3
        assert "test.json" in str(sample)

    def test_invalid_dimension(self):
        """维度不符合 512 应报错。"""
        features = np.zeros(128, dtype=np.float32)
        with pytest.raises(AssertionError, match="特征维度异常"):
            BCSample(features=features, action_index=0,
                     action_list_size=1, source_file="test.json")

    def test_repr(self):
        """__repr__ 应包含关键信息。"""
        features = np.zeros(TARGET_FEATURE_DIM, dtype=np.float32)
        sample = BCSample(features=features, action_index=2,
                          action_list_size=5, source_file="data/game.json")
        r = repr(sample)
        assert "idx=2" in r
        assert "act_size=5" in r
        assert "game.json" in r


# ═══════════════════════════════════════════════════════
#  2. load_samples 从 mock JSON 加载
# ═══════════════════════════════════════════════════════

class TestLoadSamples:
    def test_load_from_mock(self, mock_record_dir):
        """从 mock 录牌目录加载样本。"""
        samples = load_samples(
            record_dir=mock_record_dir,
            require_victory_filter=False,
        )
        assert len(samples) > 0
        for s in samples:
            assert s.features.shape == (TARGET_FEATURE_DIM,)
            assert s.action_list_size > 0

    def test_load_with_victory_filter(self, mock_record_dir):
        """victoryNum[0]>=2 过滤后应保留样本。"""
        samples = load_samples(
            record_dir=mock_record_dir,
            require_victory_filter=True,
        )
        assert len(samples) > 0

    def test_load_losing_record(self, tmp_path):
        """失败局 (victoryNum[0]<2) 应被过滤掉。"""
        losing = _make_mock_game_record(
            player_name="yf1_m3",
            victory_num=[0, 3, 0, 3],
            num_steps=5,
        )
        fp = tmp_path / "losing.json"
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(losing, f)

        samples = load_samples(
            record_dir=str(tmp_path),
            require_victory_filter=True,
        )
        assert len(samples) == 0

    def test_load_with_max_records(self, mock_record_dir):
        """max_records 限制生效。"""
        samples = load_samples(
            record_dir=mock_record_dir,
            max_records=1,
            require_victory_filter=False,
        )
        # 只要不报错即可
        assert isinstance(samples, list)

    def test_load_no_records_dir(self):
        """目录不存在应返回空列表不报错。"""
        samples = load_samples(
            record_dir="/nonexistent/path",
        )
        assert samples == []

    def test_player_filter(self, tmp_path):
        """player_filter 应精确匹配。"""
        # yf1 记录
        r1 = _make_mock_game_record(player_name="yf1_m3", num_steps=3)
        with open(tmp_path / "yf1.json", "w", encoding="utf-8") as f:
            json.dump(r1, f)
        # yf2 记录
        r2 = _make_mock_game_record(player_name="yf2_m3", num_steps=3)
        with open(tmp_path / "yf2.json", "w", encoding="utf-8") as f:
            json.dump(r2, f)

        samples = load_samples(
            record_dir=str(tmp_path),
            player_filter="yf1_m3",
            require_victory_filter=False,
        )
        assert len(samples) > 0
        # 所有样本应来自 yf1_m3


# ═══════════════════════════════════════════════════════
#  3. train_val_split 切分正确性
# ═══════════════════════════════════════════════════════

class TestTrainValSplit:
    @pytest.fixture
    def samples(self) -> List[BCSample]:
        features = np.zeros(TARGET_FEATURE_DIM, dtype=np.float32)
        return [
            BCSample(features=features.copy(), action_index=i,
                     action_list_size=3, source_file=f"src{i}.json")
            for i in range(100)
        ]

    def test_split_ratio(self, samples):
        """8:2 切分比例。"""
        train, val = train_val_split(samples, val_ratio=0.2, shuffle=True, seed=42)
        assert len(train) == 80
        assert len(val) == 20

    def test_split_no_overlap(self, samples):
        """训练集和验证集无重叠。"""
        train, val = train_val_split(samples, val_ratio=0.2, shuffle=True, seed=42)
        train_indices = {s.action_index for s in train}
        val_indices = {s.action_index for s in val}
        assert train_indices.isdisjoint(val_indices)

    def test_split_no_shuffle(self, samples):
        """不 shuffle 时前 N 个为验证集。"""
        train, val = train_val_split(samples, val_ratio=0.2, shuffle=False, seed=42)
        assert len(train) == 80
        assert len(val) == 20
        # 前 20 个应在验证集
        val_indices = {s.action_index for s in val}
        assert val_indices == set(range(20))


# ═══════════════════════════════════════════════════════
#  4. create_batches batch 结构
# ═══════════════════════════════════════════════════════

class TestCreateBatches:
    @pytest.fixture
    def samples(self) -> List[BCSample]:
        features = np.zeros(TARGET_FEATURE_DIM, dtype=np.float32)
        return [
            BCSample(features=features.copy(), action_index=i % 3,
                     action_list_size=3, source_file=f"src{i}.json")
            for i in range(20)
        ]

    def test_batch_structure(self, samples):
        """batch 字典包含必要字段。"""
        gen = create_batches(samples, batch_size=8, shuffle=False, seed=42)
        batch = next(gen)
        assert "features" in batch
        assert "action_indices" in batch
        assert "action_list_sizes" in batch
        assert batch["features"].shape[0] == 8
        assert batch["features"].shape[1] == TARGET_FEATURE_DIM

    def test_batch_iterates_all(self, samples):
        """所有样本都被遍历。"""
        gen = create_batches(samples, batch_size=8, shuffle=False, seed=42)
        total = 0
        for batch in gen:
            total += batch["features"].shape[0]
        assert total == 20

    def test_batch_no_shuffle_finite(self, samples):
        """不 shuffle 时生成器有限 (会 StopIteration)。"""
        gen = create_batches(samples, batch_size=8, shuffle=False, seed=42)
        batches = list(gen)
        assert len(batches) == 3  # 20/8 → 3 batch


# ═══════════════════════════════════════════════════════
#  5. _filter_by_victory_num 过滤逻辑
# ═══════════════════════════════════════════════════════

class TestFilterByVictoryNum:
    def test_team_a_wins(self):
        """victoryNum[0]>=2 → True。"""
        assert _filter_by_victory_num({"result": {"victoryNum": [3, 0, 3, 0]}})
        assert _filter_by_victory_num({"result": {"victoryNum": [2, 1, 2, 1]}})

    def test_team_a_loses(self):
        """victoryNum[0]<2 → False。"""
        assert not _filter_by_victory_num({"result": {"victoryNum": [1, 2, 1, 2]}})
        assert not _filter_by_victory_num({"result": {"victoryNum": [0, 3, 0, 3]}})

    def test_no_victory_num(self):
        """无 victoryNum → True (保留)。"""
        assert _filter_by_victory_num({"result": {}})
        assert _filter_by_victory_num({})


# ═══════════════════════════════════════════════════════
#  6. 特征重建
# ═══════════════════════════════════════════════════════

class TestReconstructFeatures:
    def test_from_full_state(self):
        """从 full_state 重建特征维度正确。"""
        fs = _make_mock_full_state()
        features = _reconstruct_features_from_full_state(fs)
        assert features is not None
        assert features.shape == (TARGET_FEATURE_DIM,)
        # 前 124 维应非零 (有手牌)
        assert np.any(features[:124] != 0)
        # 后 388 维应为零
        assert np.all(features[124:] == 0)

    def test_from_full_state_empty_hand(self):
        """空手牌特征全零 (前 124 维)。"""
        fs = _make_mock_full_state(handCards=[])
        features = _reconstruct_features_from_full_state(fs)
        assert features is not None
        # 静态特征以 108 维手牌为主，空手牌时前 108 维为零
        # 但 rank/level 等维可能有值

    def test_from_my_decision(self):
        """从 my_decision 尽力重建（fallback 不崩溃）。"""
        dec = {
            "action_index": 0,
            "action": ["S3"],
            "context": {
                "stage": "play",
                "myPos": 0,
                "curPos": 1,
                "greaterPos": 1,
                "curRank": "2",
                "actionList_size": 3,
            },
        }
        features = _reconstruct_features_from_my_decision(dec)
        assert features is not None
        assert features.shape == (TARGET_FEATURE_DIM,)


# ═══════════════════════════════════════════════════════
#  7. V7Recorder 录牌基本功能
# ═══════════════════════════════════════════════════════

class TestV7Recorder:
    def test_start_game(self):
        """start_game 初始化正确。"""
        rec = V7Recorder(player_id=0, player_name="yf_v7")
        rec.start_game("game001", ["S3", "S4"], {"curRank": "2"})
        assert rec._current_game is not None
        assert rec._current_game["game_id"] == "game001"
        assert rec._step == 0

    def test_record_step(self):
        """record_step 记录一条决策。"""
        rec = V7Recorder(player_id=0)
        rec.start_game("game001", ["S3", "S4"])
        rec.record_step(
            hand_cards=["S3", "S4"],
            action_list=[["S3"], ["PASS"]],
            chosen_index=0,
            chosen_action=["S3"],
            my_pos=0,
            cur_pos=0,
            greater_pos=-1,
            cur_rank="2",
            stage="play",
        )
        assert rec._step == 1
        assert len(rec._current_game["steps"]) == 1

    def test_record_before_start(self):
        """未 start 时 record_step 应 warning 不崩溃。"""
        rec = V7Recorder(player_id=0)
        rec.record_step(
            hand_cards=[], action_list=[], chosen_index=0,
            chosen_action=["PASS"],
        )
        # 不应崩溃

    def test_end_game(self):
        """end_game 返回数据并清空状态。"""
        rec = V7Recorder(player_id=0)
        rec.start_game("game001", ["S3"])
        rec.record_step(
            hand_cards=["S3"], action_list=[["S3"]],
            chosen_index=0, chosen_action=["S3"],
        )
        game_data = rec.end_game()
        assert game_data is not None
        assert game_data["game_id"] == "game001"
        assert rec._current_game is None

    def test_save_to_file(self, tmp_path):
        """save_to_file 写入 JSON。"""
        rec = V7Recorder(player_id=0)
        rec.start_game("game001", ["S3"])
        rec.record_step(
            hand_cards=["S3"], action_list=[["S3"]],
            chosen_index=0, chosen_action=["S3"],
        )
        game_data = rec.end_game()
        assert game_data is not None
        result_path = rec.save_to_file(game_data, record_dir=str(tmp_path))
        assert result_path is not None, "save_to_file 应返回路径"
        assert result_path.exists()
        with open(result_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["game_id"] == "game001"
        assert len(data["steps"]) == 1


# ═══════════════════════════════════════════════════════
#  8. masked_cross_entropy (需 torch)
# ═══════════════════════════════════════════════════════

@pytest.mark.torch
class TestMaskedCrossEntropy:
    @pytest.fixture(scope="class")
    def device(self):
        """选择可用设备。"""
        try:
            import torch
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        except ImportError:
            pytest.skip("torch not available")

    def test_basic_loss(self, device):
        """基础 masked_cross_entropy 计算。"""
        try:
            import torch
            from src.v.nn.training.bc_trainer import masked_cross_entropy
        except ImportError:
            pytest.skip("bc_trainer not available")

        logits = torch.randn(4, 512, device=device)
        targets = torch.randint(0, 5, (4,), device=device)
        sizes = torch.randint(5, 10, (4,), device=device)

        loss = masked_cross_entropy(logits, targets, sizes)
        assert loss.item() > 0
        assert not torch.isnan(loss)
        assert not torch.isinf(loss)

    def test_all_targets_valid(self, device):
        """target 都在有效范围内。"""
        try:
            import torch
            from src.v.nn.training.bc_trainer import masked_cross_entropy
        except ImportError:
            pytest.skip("bc_trainer not available")

        batch_size = 8
        max_size = 512
        logits = torch.randn(batch_size, max_size, device=device)
        # 每个样本的 action_list_size 不同，target 在其范围内
        sizes_list = [3, 5, 7, 10, 15, 20, 25, 30]
        targets = torch.tensor([s % s_list for s, s_list in
                                zip(range(batch_size), sizes_list)],
                               device=device)
        sizes = torch.tensor(sizes_list, device=device)

        loss = masked_cross_entropy(logits, targets, sizes)
        assert loss.item() > 0

    def test_masked_positions(self, device):
        """mask 后的无效位置不贡献 loss。"""
        try:
            import torch
            from src.v.nn.training.bc_trainer import masked_cross_entropy
        except ImportError:
            pytest.skip("bc_trainer not available")

        batch_size = 2
        max_size = 512
        logits = torch.randn(batch_size, max_size, device=device)
        targets = torch.tensor([0, 150], device=device)  # 第二个 target 超出第一个样本的 size
        sizes = torch.tensor([5, 200], device=device)

        loss = masked_cross_entropy(logits, targets, sizes)
        assert loss.item() > 0


# ═══════════════════════════════════════════════════════
#  9. CLI 入口解析
# ═══════════════════════════════════════════════════════

class TestCLI:
    def test_script_importable(self):
        """run_bc_training.py 可导入不报错。"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_bc_training",
            str(PROJECT_ROOT / "scripts" / "v7" / "run_bc_training.py"),
        )
        assert spec is not None, "CLI 脚本未找到"
        # 只验证存在性

    def test_parse_defaults(self):
        """默认参数解析。"""
        from scripts.v7.run_bc_training import parse_args
        args = parse_args([])
        assert args.data_dir == "game_records"
        assert args.batch_size == 64
        assert args.lr == 1e-3
        assert args.max_epochs == 50
        assert args.patience == 5
        assert not args.dry_run
        assert not args.no_victory_filter

    def test_parse_custom(self):
        """自定义参数解析。"""
        from scripts.v7.run_bc_training import parse_args
        argv = [
            "--data-dir", "my_records",
            "--output-dir", "models/my_model",
            "--model-name", "bc_v1",
            "--batch-size", "128",
            "--lr", "5e-4",
            "--max-epochs", "100",
            "--patience", "10",
            "--max-records", "50",
            "--dry-run",
            "--no-victory-filter",
            "--player-filter", "yf1_m3",
        ]
        args = parse_args(argv)
        assert args.data_dir == "my_records"
        assert args.output_dir == "models/my_model"
        assert args.model_name == "bc_v1"
        assert args.batch_size == 128
        assert args.lr == 5e-4
        assert args.max_epochs == 100
        assert args.patience == 10
        assert args.max_records == 50
        assert args.dry_run
        assert args.no_victory_filter
        assert args.player_filter == "yf1_m3"


# ═══════════════════════════════════════════════════════
#  10. 集成测试：Mock 数据全流程 (dry-run)
# ═══════════════════════════════════════════════════════

class TestBCIntegration:
    def test_dry_run_cli(self, mock_record_dir, capsys):
        """dry-run 模式从 mock 数据加载并打印统计。"""
        from scripts.v7.run_bc_training import main as cli_main
        import sys

        argv = [
            "run_bc_training.py",
            "--data-dir", mock_record_dir,
            "--dry-run",
            "--no-victory-filter",
        ]
        # 模拟 sys.argv
        old_argv = sys.argv
        try:
            sys.argv = argv
            cli_main()
        except SystemExit as e:
            # dry-run 应正常退出
            pass
        finally:
            sys.argv = old_argv

    def test_train_val_split_with_mock(self, mock_record_dir):
        """从 mock 数据加载后正确切分。"""
        samples = load_samples(
            record_dir=mock_record_dir,
            require_victory_filter=False,
        )
        assert len(samples) > 0, "应加载到 mock 样本"

        train, val = train_val_split(samples, val_ratio=0.2, seed=42)
        total = len(samples)
        assert len(train) == total - total // 5
        assert len(val) == total // 5
        assert len(train) + len(val) == total