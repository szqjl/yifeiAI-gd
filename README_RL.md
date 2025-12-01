# Self-Learning Guandan AI (V5) Guide

## Overview
The V5 architecture introduces a Reinforcement Learning (RL) based AI that learns from experience.

## Components
1. **The Brain**: `models/ppo_model_v1.pth` (The neural network).
2. **The Trainer**: `src/train/self_play.py` (Improves the brain).
3. **The Client**: `src/communication/yf1_v4.py` (Uses the brain to play).

## How to Train
1. Double-click `START_RL_TRAINING.bat`.
2. A console window will open showing training progress (Episodes and Rewards).
3. The model is saved automatically to `models/ppo_model_v1.pth` every 100 episodes.
4. Let it run for as long as possible (hours/days).

## How to Play
1. Start the game platform.
2. Run the client (e.g., `py src/communication/yf1_v4.py`).
3. The client will automatically load the latest `models/ppo_model_v1.pth`.

## Troubleshooting
- **Negative Rewards**: Normal at the beginning. The AI is learning valid moves.
- **Model Not Found**: Run training for at least one batch to generate the file.
