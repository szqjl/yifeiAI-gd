#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced model ensemble test with weighted averaging
"""

import sys
import os
import torch
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.rl_agent.model import GuandanPolicyNet
from src.train.pretrain import GuandanDataset, ReplayParser
from torch.utils.data import DataLoader


def load_model_with_score(model_path):
    """Load model and return its individual performance score"""
    device = torch.device("cpu")

    # Create model
    model = GuandanPolicyNet(
        input_dim=512, hidden_dim=256, output_dim=512,
        dropout_rate=0.2, enable_strategy_head=False,
        use_separated_features=True
    ).to(device)

    # Load checkpoint
    checkpoint = torch.load(model_path, map_location=device)
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)

    model.eval()

    # Quick evaluation to get performance score
    parser = ReplayParser("game_records")
    raw_data = parser.load_replays()
    training_data = parser.extract_training_data(raw_data)
    test_data = training_data[:100]  # Small test set
    dataset = GuandanDataset(test_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)

    exact_matches = 0
    total_samples = 0

    with torch.no_grad():
        for batch in dataloader:
            states, actions, _, _ = batch
            states = states.to(device)

            logits = model(states)
            probs = torch.sigmoid(logits)
            predictions = (probs > 0.3).float()

            for i in range(len(states)):
                if torch.equal(predictions[i], actions[i]):
                    exact_matches += 1
                total_samples += 1

    accuracy = exact_matches / total_samples
    return model, accuracy


def weighted_ensemble_predict(models_and_weights, states):
    """Weighted ensemble prediction"""
    all_probs = []
    weights = []

    for model, weight in models_and_weights:
        with torch.no_grad():
            logits = model(states)
            probs = torch.sigmoid(logits)
            all_probs.append(probs)
            weights.append(weight)

    # Weighted average
    weights = torch.tensor(weights, dtype=torch.float32)
    weights = weights / weights.sum()  # Normalize

    weighted_probs = torch.zeros_like(all_probs[0])
    for probs, weight in zip(all_probs, weights):
        weighted_probs += probs * weight

    predictions = (weighted_probs > 0.3).float()
    return predictions


def test_weighted_ensemble():
    """Test weighted ensemble"""
    print("="*80)
    print("Advanced Weighted Model Ensemble Test")
    print("="*80)

    # Load and score models
    model_paths = [
        "models/bc_model_v1_epoch_80.pth",
        "models/bc_model_v1_epoch_90.pth",
        "models/bc_model_v1_epoch_100.pth",
        "models/bc_model_v1_epoch_110.pth",
        "models/bc_model_v1_epoch_120.pth"
    ]

    print("Loading and scoring individual models...")
    models_and_scores = []

    for path in model_paths:
        if os.path.exists(path):
            try:
                model, score = load_model_with_score(path)
                models_and_scores.append((model, score, path))
                print(".2f")
            except Exception as e:
                print(f"Failed to load {path}: {e}")
        else:
            print(f"Model not found: {path}")

    if len(models_and_scores) < 2:
        print("Need at least 2 models for ensemble")
        return

    # Sort by performance and select top models
    models_and_scores.sort(key=lambda x: x[1], reverse=True)
    top_models = models_and_scores[:3]  # Use top 3 models

    print("\nTop 3 models selected for ensemble:")    for model, score, path in top_models:
        print(".2f")

    # Create weighted ensemble (weight by performance)
    total_score = sum(score for _, score, _ in top_models)
    models_and_weights = [(model, score/total_score) for model, score, _ in top_models]

    print("\nEnsemble weights:")    for i, (model, weight, path) in enumerate(zip(models_and_weights, [s/total_score for _, s, _ in top_models], [p for _, _, p in top_models])):
        print(".3f")

    # Full evaluation
    parser = ReplayParser("game_records")
    raw_data = parser.load_replays()
    training_data = parser.extract_training_data(raw_data)
    test_data = training_data[1000:1500]  # Different test set
    dataset = GuandanDataset(test_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)

    print(f"\nEvaluating on {len(dataset)} samples...")

    ensemble_matches = 0
    ensemble_card_correct = 0
    ensemble_predicted_cards = []
    total_samples = 0

    for batch in dataloader:
        states, actions, _, _ = batch
        batch_size = len(states)
        total_samples += batch_size

        # Ensemble prediction
        predictions = weighted_ensemble_predict(models_and_weights, states)

        # Calculate metrics
        for i in range(batch_size):
            # Exact match
            if torch.equal(predictions[i], actions[i]):
                ensemble_matches += 1

            # Card-level accuracy
            pred_cards = torch.where(predictions[i] > 0)[0]
            true_cards = torch.where(actions[i] > 0)[0]

            if len(true_cards) > 0:
                correct_cards = len(set(pred_cards.tolist()) & set(true_cards.tolist()))
                ensemble_card_correct += correct_cards / len(true_cards)

        ensemble_predicted_cards.extend((predictions > 0).sum(dim=1).tolist())

    # Results
    ensemble_exact_acc = ensemble_matches / total_samples * 100
    ensemble_card_acc = ensemble_card_correct / total_samples * 100
    ensemble_avg_pred = np.mean(ensemble_predicted_cards)

    print("\nEnsemble Results:")    print(".2f")
    print(".2f")
    print(".1f")

    # Compare with best individual model
    best_individual_acc = max(score for _, score, _ in models_and_scores) * 100
    improvement = ensemble_exact_acc - best_individual_acc

    print("\nComparison:")    print(".2f")
    print(".2f")

    if improvement > 0:
        print(".2f"    elif improvement > -1.0:
        print("Ensemble performance similar to best individual model")
    else:
        print("Ensemble underperformed compared to best individual model")

    print("\n" + "="*80)


if __name__ == "__main__":
    test_weighted_ensemble()
