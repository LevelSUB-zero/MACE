#!/usr/bin/env python3
"""
MEM-SNN Training Script

Trains a demo MEM-SNN model on LR-01 training data.
Validates that the training data is learnable and diverse.
"""
import os
import sys
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

from mace.models.mem_snn import MEMSNN, MEMSNNLoss, count_parameters


# =============================================================================
# Label Mappings
# =============================================================================

GOVERNANCE_MAP = {"approved": 0, "rejected": 1}
TRUTH_MAP = {"correct": 0, "incorrect": 1, "uncertain": 2}
UTILITY_MAP = {"useful": 0, "redundant": 1, "premature": 2}
SAFETY_MAP = {"safe": 0, "unsafe": 1}


# =============================================================================
# Dataset
# =============================================================================

class MEMCandidateDataset(Dataset):
    """Dataset for MEM-SNN training."""
    
    def __init__(self, candidates: List[Dict], labels: List[Dict]):
        self.data = []
        
        # Match candidates with labels by candidate_id
        label_map = {l["candidate_id"]: l for l in labels}
        
        for candidate in candidates:
            cid = candidate["candidate_id"]
            if cid in label_map:
                label = label_map[cid]
                
                # Extract features
                features = candidate["features"]
                feature_vec = [
                    features.get("frequency", 0.0),
                    features.get("recency", 0.0),
                    features.get("consistency", 0.0),
                    features.get("semantic_novelty", 0.0),
                    features.get("source_diversity", 0.0),
                    float(features.get("governance_conflict_flag", False)),
                ]
                
                # Extract labels
                targets = {
                    "governance": GOVERNANCE_MAP.get(label["governance_decision"], 0),
                    "truth": TRUTH_MAP.get(label["truth_status"], 2),
                    "utility": UTILITY_MAP.get(label["utility_status"], 2),
                    "safety": SAFETY_MAP.get(label["safety_status"], 0),
                }
                
                self.data.append({
                    "features": torch.tensor(feature_vec, dtype=torch.float32),
                    "targets": {k: torch.tensor(v, dtype=torch.long) for k, v in targets.items()},
                    "candidate_id": cid,
                })
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.data[idx]


def collate_fn(batch: List[Dict]) -> Dict:
    """Collate batch of samples."""
    return {
        "features": torch.stack([b["features"] for b in batch]),
        "targets": {
            k: torch.stack([b["targets"][k] for b in batch])
            for k in ["governance", "truth", "utility", "safety"]
        },
    }


# =============================================================================
# Data Loading
# =============================================================================

def load_training_data(
    artifacts_dir: str = "training_artifacts"
) -> Tuple[List[Dict], List[Dict]]:
    """Load candidates and labels from training artifacts."""
    candidates = []
    labels = []
    
    # Load enhanced data first (preferred - better balanced)
    enhanced_cand_path = Path(artifacts_dir) / "enhanced_candidates.jsonl"
    enhanced_label_path = Path(artifacts_dir) / "enhanced_labels.jsonl"
    
    if enhanced_cand_path.exists() and enhanced_label_path.exists():
        with open(enhanced_cand_path) as f:
            for line in f:
                if line.strip():
                    candidates.append(json.loads(line))
        with open(enhanced_label_path) as f:
            for line in f:
                if line.strip():
                    labels.append(json.loads(line))
        print(f"Loaded enhanced data: {len(candidates)} candidates, {len(labels)} labels")
    
    # Also load base candidates if enhanced is small
    if len(candidates) < 50:
        base_cand_path = Path(artifacts_dir) / "base_candidates.jsonl"
        if base_cand_path.exists():
            with open(base_cand_path) as f:
                for line in f:
                    if line.strip():
                        candidates.append(json.loads(line))
        
        base_label_path = Path(artifacts_dir) / "base_labels.jsonl"
        if base_label_path.exists():
            with open(base_label_path) as f:
                for line in f:
                    if line.strip():
                        labels.append(json.loads(line))
    
    # Load sweep candidates and labels
    sweeps_dir = Path(artifacts_dir) / "sweeps"
    if sweeps_dir.exists():
        for f in sweeps_dir.glob("*_candidates.jsonl"):
            with open(f) as fp:
                for line in fp:
                    if line.strip():
                        candidates.append(json.loads(line))
        for f in sweeps_dir.glob("*_labels.jsonl"):
            with open(f) as fp:
                for line in fp:
                    if line.strip():
                        labels.append(json.loads(line))
    
    # Load policy sweep labels
    policy_dir = Path(artifacts_dir) / "policy_sweeps"
    if policy_dir.exists():
        for f in policy_dir.glob("*_labels.jsonl"):
            with open(f) as fp:
                for line in fp:
                    if line.strip():
                        labels.append(json.loads(line))
    
    # Load time shift labels
    time_dir = Path(artifacts_dir) / "time_shifts"
    if time_dir.exists():
        for f in time_dir.glob("*_labels.jsonl"):
            with open(f) as fp:
                for line in fp:
                    if line.strip():
                        labels.append(json.loads(line))
    
    print(f"Total: {len(candidates)} candidates, {len(labels)} labels")
    return candidates, labels


# =============================================================================
# Training Loop
# =============================================================================

def train_epoch(
    model: MEMSNN,
    loader: DataLoader,
    criterion: MEMSNNLoss,
    optimizer: torch.optim.Optimizer,
    device: str = "cpu"
) -> Dict[str, float]:
    """Train for one epoch."""
    model.train()
    total_loss = 0.0
    task_losses = {k: 0.0 for k in ["governance", "truth", "utility", "safety"]}
    
    for batch in loader:
        features = batch["features"].to(device)
        targets = {k: v.to(device) for k, v in batch["targets"].items()}
        
        optimizer.zero_grad()
        logits = model(features)
        loss, losses = criterion(logits, targets)
        
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        for k, v in losses.items():
            task_losses[k] += v
    
    n_batches = len(loader)
    return {
        "total": total_loss / n_batches,
        **{k: v / n_batches for k, v in task_losses.items()}
    }


def evaluate(
    model: MEMSNN,
    loader: DataLoader,
    device: str = "cpu"
) -> Dict[str, float]:
    """Evaluate model accuracy."""
    model.eval()
    correct = {k: 0 for k in ["governance", "truth", "utility", "safety"]}
    total = 0
    
    with torch.no_grad():
        for batch in loader:
            features = batch["features"].to(device)
            targets = {k: v.to(device) for k, v in batch["targets"].items()}
            
            preds = model.predict(features)
            
            for task in correct:
                correct[task] += (preds[task] == targets[task]).sum().item()
            total += features.size(0)
    
    return {k: v / total for k, v in correct.items()}


def train_mem_snn(
    epochs: int = 100,
    hidden_dim: int = 32,
    n_ssm_blocks: int = 2,
    lr: float = 0.001,
    batch_size: int = 8,
    artifacts_dir: str = "training_artifacts",
    save_path: str = "models/mem_snn_demo.pt"
):
    """Main training function."""
    print("=" * 60)
    print("MEM-SNN Training")
    print("=" * 60)
    
    # Device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    
    # Load data
    candidates, labels = load_training_data(artifacts_dir)
    
    if len(candidates) == 0 or len(labels) == 0:
        print("ERROR: No training data found!")
        print("Run: python tools/run_lr01_training.py first")
        return
    
    # Create dataset
    dataset = MEMCandidateDataset(candidates, labels)
    print(f"Dataset size: {len(dataset)}")
    
    # Split train/val (80/20)
    n_train = int(len(dataset) * 0.8)
    n_val = len(dataset) - n_train
    train_set, val_set = torch.utils.data.random_split(
        dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(42)
    )
    
    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)
    
    print(f"Train: {len(train_set)}, Val: {len(val_set)}")
    
    # Create model
    model = MEMSNN(
        input_dim=6,
        hidden_dim=hidden_dim,
        n_ssm_blocks=n_ssm_blocks,
        dropout=0.1
    ).to(device)
    
    print(f"Model parameters: {count_parameters(model):,}")
    
    # Loss and optimizer
    criterion = MEMSNNLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    # Training loop
    print("\n--- Training ---")
    best_acc = 0.0
    
    for epoch in range(epochs):
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
        val_acc = evaluate(model, val_loader, device)
        scheduler.step()
        
        avg_acc = sum(val_acc.values()) / len(val_acc)
        
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"Epoch {epoch+1:3d}: loss={train_loss['total']:.4f} | "
                  f"gov={val_acc['governance']:.2%} truth={val_acc['truth']:.2%} "
                  f"util={val_acc['utility']:.2%} safe={val_acc['safety']:.2%}")
        
        if avg_acc > best_acc:
            best_acc = avg_acc
            # Save model
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            torch.save({
                "model_state": model.state_dict(),
                "config": {
                    "hidden_dim": hidden_dim,
                    "n_ssm_blocks": n_ssm_blocks,
                },
                "metrics": val_acc,
            }, save_path)
    
    print("\n--- Final Results ---")
    final_acc = evaluate(model, val_loader, device)
    print(f"Validation Accuracy:")
    for task, acc in final_acc.items():
        print(f"  {task}: {acc:.2%}")
    
    # Feature importance
    print("\nLearned Feature Importance:")
    importance = model.get_feature_importance()
    for feat, imp in sorted(importance.items(), key=lambda x: -x[1]):
        print(f"  {feat}: {imp:.3f}")
    
    print(f"\nModel saved to: {save_path}")
    return model


if __name__ == "__main__":
    train_mem_snn(
        epochs=100,
        hidden_dim=32,
        n_ssm_blocks=2,
        lr=0.005,
        batch_size=8
    )
