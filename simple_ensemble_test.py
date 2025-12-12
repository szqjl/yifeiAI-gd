#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple model ensemble test
"""

import sys
import os
import torch
import numpy as np
from torch.utils.data import DataLoader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.rl_agent.model import GuandanPolicyNet
from src.train.pretrain import GuandanDataset, ReplayParser


def load_model(model_path):
    """Load model"""
    device = torch.device("cpu")
    model = GuandanPolicyNet(
        input_dim=512, hidden_dim=256, output_dim=512,
        dropout_rate=0.2, enable_strategy_head=False,
        use_separated_features=True
    ).to(device)

    checkpoint = torch.load(model_path, map_location=device)
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    model.eval()
    return model


def ensemble_predict(models, states):
    """Ensemble prediction"""
    all_probs = []
    for model in models:
        with torch.no_grad():
            logits = model(states)
            probs = torch.sigmoid(logits)
            all_probs.append(probs)

    avg_probs = torch.stack(all_probs).mean(dim=0)
    predictions = (avg_probs > 0.3).float()
    return predictions


def test_ensemble():
    """Test ensemble"""
    print("Testing Model Ensemble")

    # Load data
    parser = ReplayParser("game_records")
    raw_data = parser.load_replays()
    training_data = parser.extract_training_data(raw_data)
    test_data = training_data[:200]
    dataset = GuandanDataset(test_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)

    # Load models (use only models with separated features)
    model_paths = [
        "models/bc_model_v1_epoch_90.pth",
        "models/bc_model_v1_epoch_100.pth"
    ]

    models = []
    for path in model_paths:
        if os.path.exists(path):
            model = load_model(path)
            models.append(model)
            print(f"Loaded: {path}")

    print(f"Ensemble with {len(models)} models")

    # Test
    ensemble_matches = 0
    total_samples = 0

    for batch in dataloader:
        states, actions, _, _ = batch
        batch_size = len(states)
        total_samples += batch_size

        predictions = ensemble_predict(models, states)

        for i in range(batch_size):
            if torch.equal(predictions[i], actions[i]):
                ensemble_matches += 1

    accuracy = ensemble_matches / total_samples * 100
    print(".2f")

    return accuracy


if __name__ == "__main__":
    acc = test_ensemble()
    print(".2f")
