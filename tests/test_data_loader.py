#!/usr/bin/env python3
"""
Test script to debug the data loader issue
"""

import json
from pathlib import Path

def check_data_format():
    """Check what format the data files are in"""
    data_dir = Path("game_records")
    
    print(f"Checking data directory: {data_dir}")
    print(f"Directory exists: {data_dir.exists()}")
    
    if not data_dir.exists():
        print("Data directory does not exist!")
        return
    
    json_files = list(data_dir.glob("*.json"))
    print(f"Found {len(json_files)} JSON files")
    
    if not json_files:
        print("No JSON files found!")
        return
    
    # Check first few files
    for i, json_file in enumerate(json_files[:3]):
        print(f"\n--- File {i+1}: {json_file.name} ---")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"Keys in file: {list(data.keys())}")
            
            # Check if it has training_data
            if 'training_data' in data:
                print(f"Has training_data: {len(data['training_data'])} samples")
                if data['training_data']:
                    sample = data['training_data'][0]
                    print(f"Sample keys: {list(sample.keys())}")
            else:
                print("No training_data key found")
                
        except Exception as e:
            print(f"Error reading file: {e}")

if __name__ == "__main__":
    check_data_format()