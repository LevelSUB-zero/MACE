#!/usr/bin/env python3
"""
LR-01 Training Data Generator

Integrated runner that executes:
1. Multi-dimensional label computation
2. Parameter sweeps (3 world variants)
3. Governance policy sweeps (5 policies)
4. Time-shifted replay (3 SEM snapshots)

Produces complete training dataset with diversity.
"""
import os
import sys
import json
import sqlite3
import shutil
from datetime import datetime

# Ensure imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))
os.environ.setdefault("MACE_DB_URL", "sqlite:///lr01_training.db")

from mace.core import deterministic, persistence
from mace.memory import consolidator, rewards

# Import sweep runners
from sweep_worlds import run_all_sweeps, WORLD_VARIANTS
from sweep_policies import run_all_policy_sweeps, GOVERNANCE_POLICIES
from sweep_time_shift import run_all_time_shifts, SEM_SNAPSHOTS


OUTPUT_DIR = "training_artifacts"


def setup_database():
    """Create training database with all tables."""
    db_path = "lr01_training.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    
    # Create LR-01 tables
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS mem_candidates (
            candidate_id TEXT PRIMARY KEY,
            features_json TEXT NOT NULL,
            proposed_key TEXT NOT NULL,
            value TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            consolidator_score REAL NOT NULL,
            mem_snn_score REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS episodic_memory (
            episode_id TEXT PRIMARY KEY,
            scope TEXT NOT NULL,
            hypothesis TEXT NOT NULL,
            confidence REAL,
            evidence_json TEXT,
            source TEXT,
            created_at TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS amendments (
            amendment_id TEXT PRIMARY KEY,
            canonical_key TEXT NOT NULL,
            old_value TEXT NOT NULL,
            new_value TEXT NOT NULL,
            reason TEXT NOT NULL,
            trigger TEXT NOT NULL,
            source_evidence_json TEXT,
            linked_action_request TEXT,
            timestamp_seeded TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS enhanced_labels (
            label_id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            truth_status TEXT NOT NULL,
            utility_status TEXT NOT NULL,
            safety_status TEXT NOT NULL,
            governance_decision TEXT NOT NULL,
            delayed_reward REAL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    
    print(f"[OK] Database created: {db_path}")
    return db_path


def generate_test_episodes():
    """Generate diverse episodic data for training with balanced labels."""
    deterministic.init_seed("lr01_training_episodes_v2")
    
    episodes = []
    
    # === GROUP 1: STABLE PERSONAL FACTS (APPROVED) ===
    for i, summary in enumerate([
        "user/preferences/favorite_color: User's favorite color is blue",
        "user/preferences/favorite_color: User prefers blue color",
        "user/preferences/favorite_color: Blue is the preferred color",
    ]):
        episodes.append({
            "episode_id": deterministic.deterministic_id("epi", f"g1_{i}"),
            "summary": summary, "confidence": 0.9, "evidence": ["multiple mentions"],
            "source": f"chat_{len(episodes)}", "expected_decision": "approve",
            "truth_status": "correct", "safety_status": "safe", "utility_status": "useful",
        })
    
    # === GROUP 2: VERIFIED WORLD FACTS (APPROVED) ===
    for i, summary in enumerate([
        "world/fact/geography/capital_france: The capital of France is Paris",
        "world/fact/geography/capital_france: Paris is the capital of France",
        "world/fact/geography/capital_france: France's capital city is Paris",
    ]):
        episodes.append({
            "episode_id": deterministic.deterministic_id("epi", f"g2_{i}"),
            "summary": summary, "confidence": 0.98, "evidence": ["verified fact"],
            "source": f"factcheck_{len(episodes)}", "expected_decision": "approve",
            "truth_status": "correct", "safety_status": "safe", "utility_status": "useful",
        })
    
    # === GROUP 3: STABLE PREFERENCES (APPROVED) ===
    for i, summary in enumerate([
        "user/preferences/programming_language: User prefers Python",
        "user/preferences/programming_language: Python is the go-to language",
        "user/preferences/programming_language: Always uses Python",
    ]):
        episodes.append({
            "episode_id": deterministic.deterministic_id("epi", f"g3_{i}"),
            "summary": summary, "confidence": 0.85, "evidence": ["code analysis"],
            "source": f"analysis_{len(episodes)}", "expected_decision": "approve",
            "truth_status": "correct", "safety_status": "safe", "utility_status": "useful",
        })
    
    # === GROUP 4: CONTEXT FACTS (APPROVED) ===
    for i, summary in enumerate([
        "context/project/framework: This project uses PyTorch",
        "context/project/framework: PyTorch is the framework here",
        "context/project/framework: Using PyTorch for the model",
    ]):
        episodes.append({
            "episode_id": deterministic.deterministic_id("epi", f"g4_{i}"),
            "summary": summary, "confidence": 0.92, "evidence": ["import statements"],
            "source": f"analysis_{len(episodes)}", "expected_decision": "approve",
            "truth_status": "correct", "safety_status": "safe", "utility_status": "useful",
        })
    
    # === GROUP 5: AMBIGUOUS PREFERENCES (REJECTED) ===
    for i, summary in enumerate([
        "user/preferences/beverage: User likes coffee",
        "user/preferences/beverage: Coffee is great",
        "user/preferences/beverage: Might like coffee more than tea",
    ]):
        episodes.append({
            "episode_id": deterministic.deterministic_id("epi", f"g5_{i}"),
            "summary": summary, "confidence": 0.5, "evidence": ["ambiguous statement"],
            "source": f"chat_{len(episodes)}", "expected_decision": "reject",
            "truth_status": "uncertain", "safety_status": "safe", "utility_status": "premature",
        })
    
    # === GROUP 6: INCORRECT FACTS (REJECTED) ===
    for i, summary in enumerate([
        "world/fact/geography/capital_australia: Sydney is the capital of Australia",
        "world/fact/geography/capital_australia: Australia's capital is Sydney",
        "world/fact/geography/capital_australia: The capital of Australia is Sydney",
    ]):
        episodes.append({
            "episode_id": deterministic.deterministic_id("epi", f"g6_{i}"),
            "summary": summary, "confidence": 0.6, "evidence": ["common misconception"],
            "source": f"chat_{len(episodes)}", "expected_decision": "reject",
            "truth_status": "incorrect", "safety_status": "safe", "utility_status": "redundant",
        })
    
    # === GROUP 7: EPHEMERAL STATES (REJECTED) ===
    for i, summary in enumerate([
        "user/state/temporary: User is tired today",
        "user/state/temporary: Feeling sleepy right now",
        "user/state/temporary: Exhausted at the moment",
    ]):
        episodes.append({
            "episode_id": deterministic.deterministic_id("epi", f"g7_{i}"),
            "summary": summary, "confidence": 0.7, "evidence": ["temporal statement"],
            "source": f"chat_{len(episodes)}", "expected_decision": "reject",
            "truth_status": "uncertain", "safety_status": "safe", "utility_status": "premature",
        })
    
    # === GROUP 8: UNSAFE PRIVATE DATA (REJECTED - UNSAFE) ===
    for i, summary in enumerate([
        "user/private/password: User's password is secret123",
        "user/private/password: Remember password secret123",
        "user/private/password: Store password secret123",
    ]):
        episodes.append({
            "episode_id": deterministic.deterministic_id("epi", f"g8_{i}"),
            "summary": summary, "confidence": 0.9, "evidence": ["security risk"],
            "source": f"chat_{len(episodes)}", "expected_decision": "reject",
            "truth_status": "uncertain", "safety_status": "unsafe", "utility_status": "premature",
        })
    
    # === GROUP 9: UNSAFE PII (REJECTED - UNSAFE) ===
    for i, summary in enumerate([
        "user/private/ssn: User's SSN is 123-45-6789",
        "user/private/ssn: Social security 123-45-6789",
        "user/private/ssn: Remember SSN number",
    ]):
        episodes.append({
            "episode_id": deterministic.deterministic_id("epi", f"g9_{i}"),
            "summary": summary, "confidence": 0.9, "evidence": ["security risk"],
            "source": f"chat_{len(episodes)}", "expected_decision": "reject",
            "truth_status": "uncertain", "safety_status": "unsafe", "utility_status": "premature",
        })
    
    # === GROUP 10: CONTRADICTORY (REJECTED - CONFLICT) ===
    for i, summary in enumerate([
        "user/preferences/color_conflict: Favorite color is blue",
        "user/preferences/color_conflict: Actually favorite color is red",
        "user/preferences/color_conflict: Now prefers green",
    ]):
        episodes.append({
            "episode_id": deterministic.deterministic_id("epi", f"g10_{i}"),
            "summary": summary, "confidence": 0.7, "evidence": ["contradictory"],
            "source": f"chat_{len(episodes)}", "expected_decision": "reject",
            "truth_status": "uncertain", "safety_status": "safe", "utility_status": "premature",
            "governance_conflict_flag": True,
        })
    
    # === GROUP 11: CONFLICTING SOURCES (REJECTED - CONFLICT) ===
    for i, summary in enumerate([
        "context/meeting/time: Meeting is at 2pm according to User A",
        "context/meeting/time: Meeting is at 3pm according to User B",
        "context/meeting/time: Calendar shows 2:30pm",
    ]):
        episodes.append({
            "episode_id": deterministic.deterministic_id("epi", f"g11_{i}"),
            "summary": summary, "confidence": 0.6, "evidence": ["conflicting sources"],
            "source": f"chat_{len(episodes)}", "expected_decision": "reject",
            "truth_status": "uncertain", "safety_status": "safe", "utility_status": "premature",
            "governance_conflict_flag": True,
        })
    
    # === GROUP 12: USER IDENTITY (APPROVED) ===
    for i, summary in enumerate([
        "user/identity/name: User's name is Alex",
        "user/identity/name: I am Alex",
        "user/identity/name: Call me Alex",
    ]):
        episodes.append({
            "episode_id": deterministic.deterministic_id("epi", f"g12_{i}"),
            "summary": summary, "confidence": 0.95, "evidence": ["self identification"],
            "source": f"chat_{len(episodes)}", "expected_decision": "approve",
            "truth_status": "correct", "safety_status": "safe", "utility_status": "useful",
        })
    
    return episodes


def insert_episodes(episodes: list, db_path: str):
    """Insert episodes into database."""
    conn = sqlite3.connect(db_path)
    
    for ep in episodes:
        # Extract scope and hypothesis from summary (format: "key: hypothesis")
        summary = ep.get("summary", "")
        parts = summary.split(": ", 1)
        scope = parts[0] if len(parts) > 0 else ""
        hypothesis = parts[1] if len(parts) > 1 else summary
        
        conn.execute(
            """INSERT OR REPLACE INTO episodic_memory 
               (episode_id, scope, hypothesis, confidence, evidence_json, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                ep["episode_id"],
                scope,
                hypothesis,
                ep["confidence"],
                json.dumps(ep.get("evidence", [])),
                ep.get("source", "unknown"),
                datetime.now().isoformat(),
            )
        )
    
    conn.commit()
    conn.close()
    print(f"[OK] Inserted {len(episodes)} episodes")


def generate_base_candidates(episodes: list, db_path: str) -> list:
    """Generate candidates using consolidator."""
    clusters = consolidator.cluster_episodes(episodes, user_id="lr01_training")
    
    candidates = []
    for cluster in clusters:
        features = consolidator.compute_features(cluster, episodes, [])
        provenance = cluster.get_member_ids()
        
        candidate_payload = f"{cluster.canonical_key}:{cluster.normalized_value}:{','.join(sorted(provenance))}"
        candidate_id = deterministic.deterministic_id("cand", candidate_payload)
        
        candidate = {
            "candidate_id": candidate_id,
            "features": features,
            "proposed_key": cluster.canonical_key,
            "value": cluster.normalized_value or "",
            "provenance": provenance,
            "consolidator_score": consolidator.compute_consolidator_score(features),
            "mem_snn_score": consolidator.compute_mem_snn_shadow_score(features),
            "created_at": datetime.now().isoformat(),
        }
        candidates.append(candidate)
        
        # Insert into DB
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT OR REPLACE INTO mem_candidates
               (candidate_id, features_json, proposed_key, value, 
                provenance_json, consolidator_score, mem_snn_score, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_id,
                json.dumps(features),
                cluster.canonical_key,
                cluster.normalized_value or "",
                json.dumps(provenance),
                candidate["consolidator_score"],
                candidate["mem_snn_score"],
                candidate["created_at"],
            )
        )
        conn.commit()
        conn.close()
    
    print(f"[OK] Generated {len(candidates)} base candidates")
    return candidates


def run_full_training_pipeline():
    """Execute full training data generation pipeline."""
    print("=" * 60)
    print("LR-01 Training Data Generator")
    print("=" * 60)
    
    # Setup
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(f"{OUTPUT_DIR}/sweeps", exist_ok=True)
    os.makedirs(f"{OUTPUT_DIR}/policy_sweeps", exist_ok=True)
    os.makedirs(f"{OUTPUT_DIR}/time_shifts", exist_ok=True)
    
    db_path = setup_database()
    deterministic.init_seed("lr01_training_main")
    
    # Phase 1: Generate episodes
    print("\n--- Phase 1: Generate Episodes ---")
    episodes = generate_test_episodes()
    insert_episodes(episodes, db_path)
    
    # Phase 2: Generate base candidates
    print("\n--- Phase 2: Generate Candidates ---")
    candidates = generate_base_candidates(episodes, db_path)
    
    # Save base candidates
    with open(f"{OUTPUT_DIR}/base_candidates.jsonl", "w") as f:
        for c in candidates:
            f.write(json.dumps(c) + "\n")
    
    # Phase 3: Run parameter sweeps
    print("\n--- Phase 3: Parameter Sweeps ---")
    sweep_results = run_all_sweeps(
        episodes,
        current_tick=12,
        sem_state={},
        output_dir=f"{OUTPUT_DIR}/sweeps"
    )
    
    # Phase 4: Run policy sweeps
    print("\n--- Phase 4: Policy Sweeps ---")
    policy_results = run_all_policy_sweeps(
        candidates,
        current_tick=12,
        sem_state={},
        output_dir=f"{OUTPUT_DIR}/policy_sweeps"
    )
    
    # Phase 5: Run time-shifted replay
    print("\n--- Phase 5: Time-Shifted Replay ---")
    time_results = run_all_time_shifts(
        candidates,
        output_dir=f"{OUTPUT_DIR}/time_shifts"
    )
    
    # Phase 6: Compute multi-dimensional labels for base candidates
    print("\n--- Phase 6: Multi-Dimensional Labels ---")
    labels = []
    for candidate in candidates:
        label = rewards.compute_full_label(
            candidate,
            current_tick=12,
            sem_state={},
            governance_decision="approved"  # Baseline
        )
        labels.append(label)
    
    with open(f"{OUTPUT_DIR}/base_labels.jsonl", "w") as f:
        for l in labels:
            f.write(json.dumps(l) + "\n")
    
    print(f"[OK] Generated {len(labels)} multi-dimensional labels")
    
    # Generate summary
    summary = {
        "generated_at": datetime.now().isoformat(),
        "base_episodes": len(episodes),
        "base_candidates": len(candidates),
        "sweep_variants": len(WORLD_VARIANTS),
        "policy_variants": len(GOVERNANCE_POLICIES),
        "time_snapshots": len(SEM_SNAPSHOTS),
        "total_labeled_examples": (
            len(candidates) +  # Base
            sum(len(r["candidates"]) for r in sweep_results) +  # Sweeps
            sum(len(r["labels"]) for r in policy_results) +  # Policies
            sum(len(r["labels"]) for r in time_results)  # Time
        ),
        "label_distribution": {
            "truth": {"correct": 0, "incorrect": 0, "uncertain": 0},
            "utility": {"useful": 0, "redundant": 0, "premature": 0},
            "safety": {"safe": 0, "unsafe": 0},
        }
    }
    
    # Count label distributions
    for label in labels:
        summary["label_distribution"]["truth"][label["truth_status"]] += 1
        summary["label_distribution"]["utility"][label["utility_status"]] += 1
        summary["label_distribution"]["safety"][label["safety_status"]] += 1
    
    with open(f"{OUTPUT_DIR}/training_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "=" * 60)
    print("TRAINING DATA GENERATION COMPLETE")
    print("=" * 60)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"Total labeled examples: {summary['total_labeled_examples']}")
    print(f"\nLabel distributions:")
    print(f"  Truth:   {summary['label_distribution']['truth']}")
    print(f"  Utility: {summary['label_distribution']['utility']}")
    print(f"  Safety:  {summary['label_distribution']['safety']}")
    
    return summary


if __name__ == "__main__":
    run_full_training_pipeline()
