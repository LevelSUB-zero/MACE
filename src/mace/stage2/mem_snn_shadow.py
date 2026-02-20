"""
Stage-2 MEM-SNN Shadow Mode (AUTHORITATIVE)

Purpose: Validate whether learning is even possible from data.
Spec: docs/stage2_mem_snn_rules.md

Core Doctrine:
- MEM-SNN is a mirror, not a decision-maker
- It approximates "Would governance approve this?"
- Outputs are OBSERVED ONLY, NEVER CONSUMED
- Removing MEM-SNN changes NOTHING about system behavior

FORBIDDEN:
- Promotion based on MEM-SNN score
- Routing influenced by MEM-SNN
- Memory writes triggered by MEM-SNN
- Threshold enforcement using MEM-SNN
"""

import json
import datetime
from typing import Dict, Any, List, Optional

from mace.core import deterministic, canonical, persistence
from mace.stage2 import shadow_guard


# =============================================================================
# SHADOW MODE CONSTANTS
# =============================================================================

# Shadow table name (never read by live code)
SHADOW_TABLE = "mem_snn_shadow_predictions"
DIVERGENCE_TABLE = "mem_snn_divergence_log"

# Schema version
SHADOW_SCHEMA_VERSION = "2.0"

# Feature names (must match candidate.CANDIDATE_FEATURES)
FEATURE_NAMES = [
    "frequency",
    "consistency", 
    "recency",
    "source_diversity",
    "semantic_novelty",
    "governance_conflict_flag"
]


# =============================================================================
# MODEL LOADING (LAZY, SHADOW-ONLY)
# =============================================================================

_model_instance = None
_model_loaded = False


def _load_model():
    """
    Lazy-load the MEMSNN model.
    Only called when shadow scoring is requested.
    """
    global _model_instance, _model_loaded
    
    if _model_loaded:
        return _model_instance
    
    try:
        import torch
        from mace.models.mem_snn import MEMSNN
        
        # Create model with default architecture
        _model_instance = MEMSNN(
            input_dim=6,
            hidden_dim=32,
            n_ssm_blocks=2,
            dropout=0.1
        )
        _model_instance.eval()  # Always in eval mode for shadow predictions
        _model_loaded = True
        
    except ImportError:
        # PyTorch not available - use stub
        _model_instance = None
        _model_loaded = True
    
    return _model_instance


def _model_score(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score using the real MEMSNN model.
    Falls back to stub if PyTorch unavailable.
    """
    model = _load_model()
    
    if model is None:
        return _stub_score_candidate(candidate)
    
    try:
        import torch
        import torch.nn.functional as F
        
        # Extract features in correct order
        features = candidate.get("features", {})
        feature_vector = [
            float(features.get("frequency", 0)),
            float(features.get("consistency", 0)),
            float(features.get("recency", 0)),
            float(features.get("source_diversity", 0)),
            float(features.get("semantic_novelty", 1.0)),
            1.0 if features.get("governance_conflict_flag", False) else 0.0
        ]
        
        # Convert to tensor
        x = torch.tensor([feature_vector], dtype=torch.float32)
        
        # Forward pass (no grad - shadow mode)
        with torch.no_grad():
            logits = model(x)
            
            # Get probabilities
            gov_probs = F.softmax(logits["governance"], dim=-1)
            truth_probs = F.softmax(logits["truth"], dim=-1)
            utility_probs = F.softmax(logits["utility"], dim=-1)
            safety_probs = F.softmax(logits["safety"], dim=-1)
            
            # governance: [reject=0, approve=1]
            # truth: [correct=0, incorrect=1, uncertain=2]
            # utility: [useful=0, redundant=1, premature=2]
            # safety: [safe=0, unsafe=1]
            
            return {
                "truth": float(truth_probs[0, 0]),  # P(correct)
                "utility": float(utility_probs[0, 0]),  # P(useful)
                "safety": float(safety_probs[0, 0]),  # P(safe)
                "governance_approve": float(gov_probs[0, 1]),  # P(approve)
                "rank": 0,
                "confidence": float(gov_probs.max())
            }
            
    except Exception as e:
        # Fallback to stub on any error
        return _stub_score_candidate(candidate)


# =============================================================================
# SHADOW PREDICTION (OBSERVED ONLY, NEVER CONSUMED)
# =============================================================================

def score_candidate(
    candidate: Dict[str, Any],
    model_fn: callable = None
) -> Dict[str, Any]:
    """
    Score a candidate (SHADOW MODE ONLY).
    
    Output is logged to shadow table, never consumed by live code.
    
    Args:
        candidate: The candidate to score
        model_fn: Optional custom scoring function (for testing)
    
    Returns:
        Shadow prediction dict (for logging only)
    """
    # Ensure shadow mode is active
    shadow_guard.assert_shadow_mode("mem_snn_shadow.score_candidate")
    
    # Generate deterministic prediction ID
    seed = deterministic.get_seed() or "shadow_fallback"
    if deterministic.get_seed() is None:
        deterministic.init_seed(seed)
    
    prediction_id = deterministic.deterministic_id(
        "shadow_prediction",
        candidate["candidate_id"]
    )
    
    # Use provided function, real model, or stub
    if model_fn is not None:
        scores = model_fn(candidate)
    else:
        scores = _model_score(candidate)
    
    prediction = {
        "prediction_id": prediction_id,
        "candidate_id": candidate["candidate_id"],
        "predicted_truth_score": scores.get("truth", 0.5),
        "predicted_utility_score": scores.get("utility", 0.5),
        "predicted_safety_score": scores.get("safety", 0.5),
        "ranking_position": scores.get("rank", 0),
        "confidence_interval": scores.get("confidence", 0.5),
        "schema_version": SHADOW_SCHEMA_VERSION
    }
    
    return prediction


def _stub_score_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stub scoring function (fallback when PyTorch unavailable).
    
    Uses deterministic rule-based scoring (no ML).
    """
    features = candidate.get("features", {})
    
    # Simple heuristic scores (NOT learned)
    truth_score = 0.5
    if features.get("consistency", 0) > 0.8:
        truth_score += 0.3
    if features.get("frequency", 0) >= 3:
        truth_score += 0.2
    
    utility_score = 0.5
    if features.get("semantic_novelty", 0) > 0.5:
        utility_score += 0.3
    if features.get("source_diversity", 0) >= 2:
        utility_score += 0.2
    
    safety_score = 0.9  # Default safe
    if features.get("governance_conflict_flag", False):
        safety_score = 0.1  # Unsafe if conflict
    
    return {
        "truth": min(1.0, truth_score),
        "utility": min(1.0, utility_score),
        "safety": safety_score,
        "rank": 0,
        "confidence": 0.5
    }


def persist_shadow_prediction(prediction: Dict[str, Any]) -> str:
    """
    Persist a shadow prediction (NEVER READ BY LIVE CODE).
    
    Returns prediction_id.
    """
    conn = persistence.get_connection()
    try:
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        persistence.execute_query(conn,
            """INSERT INTO mem_snn_shadow_predictions 
               (prediction_id, candidate_id, predicted_truth_score, predicted_utility_score,
                predicted_safety_score, ranking_position, confidence_interval, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                prediction["prediction_id"],
                prediction["candidate_id"],
                prediction["predicted_truth_score"],
                prediction["predicted_utility_score"],
                prediction["predicted_safety_score"],
                prediction["ranking_position"],
                prediction["confidence_interval"],
                created_at
            )
        )
        conn.commit()
        return prediction["prediction_id"]
    finally:
        conn.close()


# =============================================================================
# DIVERGENCE LOGGING (FOR TRAINING ANALYSIS)
# =============================================================================

def log_divergence(
    candidate_id: str,
    mem_snn_prediction: Dict[str, Any],
    council_decision: Dict[str, Any]
) -> str:
    """
    Log divergence between MEM-SNN prediction and Council decision.
    
    High divergence is valuable data:
    - Model untrustworthy, OR
    - Council is evolving
    
    Returns divergence_id.
    """
    # Ensure shadow mode
    shadow_guard.assert_shadow_mode("mem_snn_shadow.log_divergence")
    
    # Compute divergence
    divergences = []
    
    # Truth divergence
    pred_truth = mem_snn_prediction.get("predicted_truth_score", 0.5)
    actual_truth = 1.0 if council_decision.get("truth_label") else 0.0
    truth_div = abs(pred_truth - actual_truth)
    if truth_div > 0.3:
        divergences.append(f"truth_divergence={truth_div:.2f}")
    
    # Safety divergence
    pred_safety = mem_snn_prediction.get("predicted_safety_score", 0.5)
    actual_safety = 1.0 if council_decision.get("safety_label") else 0.0
    safety_div = abs(pred_safety - actual_safety)
    if safety_div > 0.3:
        divergences.append(f"safety_divergence={safety_div:.2f}")
    
    # Generate ID
    seed = deterministic.get_seed() or "divergence_fallback"
    if deterministic.get_seed() is None:
        deterministic.init_seed(seed)
    
    divergence_id = deterministic.deterministic_id(
        "divergence_log",
        f"{candidate_id}:{json.dumps(divergences)}"
    )
    
    # Persist
    conn = persistence.get_connection()
    try:
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        persistence.execute_query(conn,
            """INSERT INTO mem_snn_divergence_log 
               (divergence_id, candidate_id, mem_snn_prediction, council_decision, 
                divergence_reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                divergence_id,
                candidate_id,
                canonical.canonical_json_serialize(mem_snn_prediction),
                canonical.canonical_json_serialize(council_decision),
                "; ".join(divergences) if divergences else "no_divergence",
                created_at
            )
        )
        conn.commit()
        return divergence_id
    finally:
        conn.close()


def get_divergence_stats() -> Dict[str, Any]:
    """
    Get divergence statistics for MEM-SNN evaluation.
    
    Only for offline metrics - NO LIVE KPIs.
    """
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn,
            "SELECT divergence_reason FROM mem_snn_divergence_log"
        )
        rows = persistence.fetch_all(cur)
        
        total = len(rows)
        divergent = sum(1 for r in rows if r["divergence_reason"] != "no_divergence")
        
        return {
            "total_comparisons": total,
            "divergent_count": divergent,
            "divergence_rate": divergent / total if total > 0 else 0.0,
            "agreement_rate": 1.0 - (divergent / total) if total > 0 else 1.0
        }
    finally:
        conn.close()


# =============================================================================
# SHADOW MODE VERIFICATION
# =============================================================================

def verify_shadow_mode_integrity():
    """
    Verify that shadow mode is properly enforced.
    
    This can be called as a health check.
    """
    checks = []
    
    # Check 1: Learning mode is shadow
    try:
        mode = shadow_guard.get_learning_mode()
        checks.append({
            "check": "learning_mode_is_shadow",
            "passed": mode == "shadow",
            "value": mode
        })
    except Exception as e:
        checks.append({
            "check": "learning_mode_is_shadow",
            "passed": False,
            "error": str(e)
        })
    
    # Check 2: Stage-2 not halted
    checks.append({
        "check": "stage2_not_halted",
        "passed": not shadow_guard.is_stage2_halted(),
        "value": shadow_guard.is_stage2_halted()
    })
    
    all_passed = all(c["passed"] for c in checks)
    
    return {
        "all_passed": all_passed,
        "checks": checks
    }
