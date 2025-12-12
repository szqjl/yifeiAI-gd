#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fine-tune hyperparameters around the best found values
"""

import sys
import os
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.rl_agent.model import GuandanPolicyNet
from src.train.pretrain import GuandanDataset, ReplayParser
from torch.utils.data import DataLoader


def fine_tune_search():
    """Fine-tune hyperparameters around best values"""
    print("Fine-tuning Hyperparameters")
    print("=" * 50)

    # Based on previous search, best values were:
    # lr=0.0005, dropout=0.2, top_k_weight=0.3, count_penalty_weight=0.1, k_multiplier=2.0

    # Fine-tune around these values
    fine_tune_space = {
        'lr': [0.0003, 0.0005, 0.0007],  # Around 0.0005
        'dropout_rate': [0.15, 0.2, 0.25],  # Around 0.2
        'top_k_weight': [0.2, 0.3, 0.4],  # Around 0.3
        'count_penalty_weight': [0.05, 0.1, 0.15],  # Around 0.1
        'k_multiplier': [1.8, 2.0, 2.2]  # Around 2.0
    }

    # Generate parameter combinations
    import itertools
    param_names = list(fine_tune_space.keys())
    param_values = list(fine_tune_space.values())
    combinations = list(itertools.product(*param_values))

    print(f"Testing {len(combinations)} fine-tuned combinations")

    results = []

    for i, params in enumerate(combinations):
        lr, dropout_rate, top_k_weight, count_penalty_weight, k_multiplier = params

        print(f"[{i+1}/{len(combinations)}] lr={lr}, dropout={dropout_rate}, tk_w={top_k_weight}, cp_w={count_penalty_weight}, k_mult={k_multiplier}")

        # Quick training and evaluation
        accuracy = quick_train_eval(lr, dropout_rate, top_k_weight, count_penalty_weight, k_multiplier)

        results.append({
            'lr': lr,
            'dropout_rate': dropout_rate,
            'top_k_weight': top_k_weight,
            'count_penalty_weight': count_penalty_weight,
            'k_multiplier': k_multiplier,
            'accuracy': accuracy
        })

        print(".2f")

    # Find best combination
    results.sort(key=lambda x: x['accuracy'], reverse=True)
    best = results[0]

    print("\nBest fine-tuned parameters:")    print(f"  Learning rate: {best['lr']}")
    print(f"  Dropout rate: {best['dropout_rate']}")
    print(f"  Top-K weight: {best['top_k_weight']}")
    print(f"  Count penalty weight: {best['count_penalty_weight']}")
    print(f"  K multiplier: {best['k_multiplier']}")
    print(".2f")

    # Show top 3
    print("\nTop 3 combinations:")    for i, result in enumerate(results[:3], 1):
        print(f"{i}. {result['accuracy']:.2f}% - lr={result['lr']}, dropout={result['dropout_rate']}, tk_w={result['top_k_weight']}")

    return best


def quick_train_eval(lr, dropout_rate, top_k_weight, count_penalty_weight, k_multiplier, epochs=15):
    """Quick training and evaluation"""
    device = torch.device("cpu")

    # Create model
    model = GuandanPolicyNet(
        input_dim=512, hidden_dim=256, output_dim=512,
        dropout_rate=dropout_rate, enable_strategy_head=False,
        use_separated_features=True
    ).to(device)

    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    # Load small dataset for quick testing
    parser = ReplayParser("game_records")
    raw_data = parser.load_replays()
    training_data = parser.extract_training_data(raw_data)
    train_data = training_data[:500]  # Small training set
    val_data = training_data[500:700]  # Small validation set

    train_dataset = GuandanDataset(train_data)
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)

    # Quick training
    for epoch in range(epochs):
        model.train()
        for batch in train_loader:
            states, actions, _, _ = batch
            states = states.to(device)
            actions = actions.to(device)

            logits = model(states)

            # BCE loss
            bce_loss = nn.functional.binary_cross_entropy_with_logits(logits, actions, reduction='mean')

            # Count penalty
            probs = torch.sigmoid(logits)
            predicted_counts = (probs > 0.3).sum(dim=1).float()
            true_counts = actions.sum(dim=1).float()
            count_loss = nn.functional.l1_loss(predicted_counts, true_counts) * count_penalty_weight

            # Top-K loss
            true_card_counts = actions.sum(dim=1).long()
            k_values = torch.max(true_card_counts + 2, torch.ceil(true_card_counts * k_multiplier).long())
            top_k_loss = compute_top_k_loss(logits, actions, k_values) * top_k_weight

            # Total loss
            loss = bce_loss + count_loss + top_k_loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        scheduler.step()

    # Quick evaluation
    val_dataset = GuandanDataset(val_data)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

    model.eval()
    matches = 0
    total = 0

    with torch.no_grad():
        for batch in val_loader:
            states, actions, _, _ = batch
            states = states.to(device)

            logits = model(states)
            probs = torch.sigmoid(logits)
            predictions = (probs > 0.3).float()

            for i in range(len(states)):
                if torch.equal(predictions[i], actions[i]):
                    matches += 1
                total += 1

    return matches / total * 100


def compute_top_k_loss(logits, targets, k_values):
    """Compute Top-K loss"""
    batch_size = logits.shape[0]
    total_loss = 0.0

    for i in range(batch_size):
        k = k_values[i].item()
        if k <= 0:
            continue

        sample_probs = torch.sigmoid(logits[i])
        sample_targets = targets[i]

        # Top-K
        topk_vals, topk_idx = torch.topk(sample_probs, min(k, sample_probs.shape[0]))

        # Create mask
        topk_mask = torch.zeros_like(sample_targets)
        topk_mask[topk_idx] = 1.0

        # Non-Top-K penalty
        non_topk_mask = 1.0 - topk_mask
        non_topk_penalty = torch.mean((sample_probs * non_topk_mask) ** 2)

        # Top-K BCE
        topk_logits = logits[i] * topk_mask
        topk_targets = sample_targets * topk_mask
        topk_bce = nn.functional.binary_cross_entropy_with_logits(topk_logits, topk_targets)

        total_loss += topk_bce + 0.1 * non_topk_penalty

    return total_loss / batch_size


if __name__ == "__main__":
    best_params = fine_tune_search()

    print("\nFine-tuning complete!")    print("Use these parameters for final training:"
    print(f"python src/train/pretrain.py \\")
    print(f"  --lr {best_params['lr']} \\")
    print(f"  --dropout_rate {best_params['dropout_rate']} \\")
    print(f"  --top_k_weight {best_params['top_k_weight']} \\")
    print(f"  --count_penalty_weight {best_params['count_penalty_weight']} \\")
    print(f"  --k_multiplier {best_params['k_multiplier']}")
