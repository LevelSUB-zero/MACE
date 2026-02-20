"""
MEM-SNN Demo Model

A tiny State Space Model (SSM) inspired architecture for memory value prediction.
Designed for the LR-01 training data validation.

Architecture:
- Input: 6 features (freq, recency, consistency, novelty, diversity, conflict_flag)
- SSM Block: Simple selective state space layer
- Multi-head output: governance, truth, utility, safety

This is a demonstration model to validate training data quality.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional


class SelectiveSSMBlock(nn.Module):
    """
    Simplified Selective State Space Model block.
    Inspired by Mamba but much smaller for our demo.
    """
    def __init__(self, d_model: int = 32, d_state: int = 16):
        super().__init__()
        self.d_model = d_model
        self.d_state = d_state
        
        # Input projection
        self.in_proj = nn.Linear(d_model, d_model * 2)
        
        # SSM parameters (learned)
        self.A = nn.Parameter(torch.randn(d_state, d_state) * 0.1)
        self.B = nn.Linear(d_model, d_state)
        self.C = nn.Linear(d_state, d_model)
        self.D = nn.Parameter(torch.ones(d_model))
        
        # Selection mechanism (what makes it selective)
        self.delta_proj = nn.Linear(d_model, d_model)
        
        # Output projection
        self.out_proj = nn.Linear(d_model, d_model)
        
        # Layer norm
        self.norm = nn.LayerNorm(d_model)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, d_model)
        Returns:
            (batch, d_model)
        """
        residual = x
        x = self.norm(x)
        
        # Gate and value split
        xz = self.in_proj(x)
        x_gate, x_val = xz.chunk(2, dim=-1)
        x_gate = F.silu(x_gate)
        
        # Compute selection (delta)
        delta = F.softplus(self.delta_proj(x_val))
        
        # SSM step (simplified - single step, not sequence)
        # In full Mamba, this would be a scan over sequence
        B_x = self.B(x_val)  # (batch, d_state)
        
        # Discretized state transition: A_bar = exp(delta * A)
        # Simplified: just use delta-scaled A
        h = torch.tanh(B_x @ self.A.T)  # (batch, d_state)
        
        # Output
        y = self.C(h) + self.D * x_val
        
        # Gate and project
        y = x_gate * y
        y = self.out_proj(y)
        
        return y + residual


class MEMSNN(nn.Module):
    """
    Memory Spiking Neural Network (MEM-SNN) Demo.
    
    Predicts memory candidate value across multiple dimensions:
    - governance_decision: approve/reject (binary)
    - truth_status: correct/incorrect/uncertain (3-class)
    - utility_status: useful/redundant/premature (3-class)
    - safety_status: safe/unsafe (binary)
    """
    
    def __init__(
        self,
        input_dim: int = 6,
        hidden_dim: int = 32,
        n_ssm_blocks: int = 2,
        dropout: float = 0.1
    ):
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        # Feature names for interpretability
        self.feature_names = [
            "frequency", "recency", "consistency", 
            "semantic_novelty", "source_diversity", "governance_conflict_flag"
        ]
        
        # Input embedding
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout)
        )
        
        # SSM blocks
        self.ssm_blocks = nn.ModuleList([
            SelectiveSSMBlock(d_model=hidden_dim, d_state=hidden_dim // 2)
            for _ in range(n_ssm_blocks)
        ])
        
        # Multi-task heads
        self.governance_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.SiLU(),
            nn.Linear(hidden_dim // 2, 2)  # approve/reject
        )
        
        self.truth_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.SiLU(),
            nn.Linear(hidden_dim // 2, 3)  # correct/incorrect/uncertain
        )
        
        self.utility_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.SiLU(),
            nn.Linear(hidden_dim // 2, 3)  # useful/redundant/premature
        )
        
        self.safety_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.SiLU(),
            nn.Linear(hidden_dim // 2, 2)  # safe/unsafe
        )
        
        # Initialize weights
        self.apply(self._init_weights)
    
    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
    
    def forward(self, features: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            features: (batch, 6) - the 6 MEM features
        
        Returns:
            Dict with logits for each prediction head
        """
        # Project input
        x = self.input_proj(features)
        
        # Pass through SSM blocks
        for block in self.ssm_blocks:
            x = block(x)
        
        # Multi-task predictions
        return {
            "governance": self.governance_head(x),
            "truth": self.truth_head(x),
            "utility": self.utility_head(x),
            "safety": self.safety_head(x),
        }
    
    def predict(self, features: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Get class predictions (not logits)."""
        logits = self.forward(features)
        return {
            "governance": logits["governance"].argmax(dim=-1),
            "truth": logits["truth"].argmax(dim=-1),
            "utility": logits["utility"].argmax(dim=-1),
            "safety": logits["safety"].argmax(dim=-1),
        }
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Compute feature importance from input projection weights.
        """
        weights = self.input_proj[0].weight.data.abs().mean(dim=0)
        importance = weights / weights.sum()
        return {
            name: float(importance[i]) 
            for i, name in enumerate(self.feature_names)
        }


class MEMSNNLoss(nn.Module):
    """
    Multi-task loss for MEM-SNN training.
    Combines governance, truth, utility, and safety losses.
    """
    def __init__(
        self,
        governance_weight: float = 1.0,
        truth_weight: float = 1.0,
        utility_weight: float = 1.0,
        safety_weight: float = 1.0
    ):
        super().__init__()
        self.weights = {
            "governance": governance_weight,
            "truth": truth_weight,
            "utility": utility_weight,
            "safety": safety_weight,
        }
        self.ce = nn.CrossEntropyLoss()
    
    def forward(
        self, 
        logits: Dict[str, torch.Tensor],
        targets: Dict[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Compute weighted multi-task loss.
        
        Returns:
            total_loss, per_task_losses
        """
        losses = {}
        for task in ["governance", "truth", "utility", "safety"]:
            losses[task] = self.ce(logits[task], targets[task])
        
        total = sum(self.weights[t] * losses[t] for t in losses)
        
        return total, {k: v.item() for k, v in losses.items()}


def count_parameters(model: nn.Module) -> int:
    """Count trainable parameters."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":
    # Quick test
    model = MEMSNN(input_dim=6, hidden_dim=32, n_ssm_blocks=2)
    print(f"MEM-SNN Demo Model")
    print(f"  Parameters: {count_parameters(model):,}")
    
    # Test forward pass
    batch = torch.randn(4, 6)
    output = model(batch)
    print(f"  Output shapes:")
    for k, v in output.items():
        print(f"    {k}: {v.shape}")
    
    # Feature importance
    importance = model.get_feature_importance()
    print(f"  Initial feature importance:")
    for k, v in importance.items():
        print(f"    {k}: {v:.3f}")
