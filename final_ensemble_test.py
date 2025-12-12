#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final ensemble test with best performing models
"""

import sys
import os
import torch
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.rl_agent.model import GuandanPolicyNet
from src.train.pretrain import GuandanDataset, ReplayParser
from torch.utils.data import DataLoader


def load_model(model_path):
    """Load model safely"""
    device = torch.device("cpu")

    model = GuandanPolicyNet(
        input_dim=512, hidden_dim=256, output_dim=512,
        dropout_rate=0.2, enable_strategy_head=False,
        use_separated_features=True
    ).to(device)

    try:
        checkpoint = torch.load(model_path, map_location=device)
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)
        model.eval()
        return model
    except Exception as e:
        print(f"Failed to load {model_path}: {e}")
        return None


def ensemble_predict(models, states):
    """Simple ensemble averaging"""
    all_probs = []

    for model in models:
        if model is None:
            continue
        with torch.no_grad():
            logits = model(states)
            probs = torch.sigmoid(logits)
            all_probs.append(probs)

    if not all_probs:
        return torch.zeros_like(torch.sigmoid(models[0](states)))

    avg_probs = torch.stack(all_probs).mean(dim=0)
    predictions = (avg_probs > 0.3).float()
    return predictions


def evaluate_ensemble():
    """Evaluate ensemble performance"""
    print("Final Ensemble Test")
    print("=" * 50)

    # Test individual models first
    model_paths = [
        "models/bc_model_v1_epoch_90.pth",
        "models/bc_model_v1_epoch_100.pth",
        "models/bc_model_v1_epoch_110.pth"
    ]

    print("Testing individual models...")
    individual_results = {}

    for path in model_paths:
        if os.path.exists(path):
            model = load_model(path)
            if model is None:
                continue

            # Quick evaluation
            parser = ReplayParser("game_records")
            raw_data = parser.load_replays()
            training_data = parser.extract_training_data(raw_data)
            test_data = training_data[:200]
            dataset = GuandanDataset(test_data)
            dataloader = DataLoader(dataset, batch_size=32, shuffle=False)

            matches = 0
            total = 0

            with torch.no_grad():
                for batch in dataloader:
                    states, actions, _, _ = batch
                    logits = model(states)
                    probs = torch.sigmoid(logits)
                    predictions = (probs > 0.3).float()

                    for i in range(len(states)):
                        if torch.equal(predictions[i], actions[i]):
                            matches += 1
                        total += 1

            accuracy = matches / total * 100
            individual_results[path] = accuracy
            print(".2f")
        else:
            print(f"Model not found: {path}")

    # Select best models for ensemble
    valid_models = [(path, acc) for path, acc in individual_results.items()]
    if len(valid_models) < 2:
        print("Need at least 2 valid models")
        return

    valid_models.sort(key=lambda x: x[1], reverse=True)
    best_paths = [path for path, _ in valid_models[:2]]  # Top 2 models

    print("
Using top 2 models for ensemble:"    for path in best_paths:
        print(".2f")

    # Load models for ensemble
    ensemble_models = []
    for path in best_paths:
        model = load_model(path)
        if model is not None:
            ensemble_models.append(model)

    if len(ensemble_models) < 2:
        print("Failed to load enough models for ensemble")
        return

    # Full ensemble evaluation
    print(f"\nEvaluating ensemble on larger test set...")

    parser = ReplayParser("game_records")
    raw_data = parser.load_replays()
    training_data = parser.extract_training_data(raw_data)
    test_data = training_data[500:1000]  # Different test set
    dataset = GuandanDataset(test_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)

    ensemble_matches = 0
    total_samples = 0

    for batch in dataloader:
        states, actions, _, _ = batch
        batch_size = len(states)
        total_samples += batch_size

        predictions = ensemble_predict(ensemble_models, states)

        for i in range(batch_size):
            if torch.equal(predictions[i], actions[i]):
                ensemble_matches += 1

    ensemble_accuracy = ensemble_matches / total_samples * 100
    best_individual = max(individual_results.values())

    print("
Final Results:"    print(".2f")
    print(".2f")
    print(".2f")

    if ensemble_accuracy > best_individual:
        print("SUCCESS: Ensemble improved performance!")
    else:
        print("Ensemble did not improve over best individual model")


if __name__ == "__main__":
    evaluate_ensemble()
