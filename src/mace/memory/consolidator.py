"""
Consolidator Module - LR-01

Implements deterministic symbolic clustering for memory promotion candidates.

Two-stage clustering:
- Stage A: Key-candidate bucketing (hard gate)
- Stage B: Token overlap sanity check (soft gate, Jaccard >= 0.6)

No embeddings. No LLM similarity. Fully deterministic and replayable.
"""
import re
import json
import datetime
from typing import List, Dict, Any, Optional, Tuple

from mace.core import persistence, deterministic, canonical
from mace.memory import semantic


# Known canonical key patterns
KEY_PATTERNS = [
    # user/profile/*/favorite_X
    (r"(?:my |i |remember that my )?favorite (\w+) is (\w+)", "user/profile/{user_id}/favorite_{0}"),
    (r"(?:i )?really like (\w+) best", "user/profile/{user_id}/favorite_color"),
    
    # world/fact/*/capital
    (r"(?:the )?capital of (\w+) is (\w+)", "world/fact/geography/capital_{0}"),
    (r"(\w+)'s capital is (\w+)", "world/fact/geography/capital_{0}"),
    (r"(\w+) is the capital of (\w+)", "world/fact/geography/capital_{1}"),
    
    # mood/state/*/temporary
    (r"i(?:'m| am) (\w+) (?:today|right now|at the moment)", "mood/state/{user_id}/temporary"),
    (r"i feel (\w+) (?:today|right now|at the moment)?", "mood/state/{user_id}/temporary"),
    
    # preferences
    (r"i (?:like|love|prefer) (\w+)", "user/preference/{user_id}/likes_{0}"),
    (r"(\w+) is (?:great|good|nice)", "user/preference/{user_id}/likes_{0}"),
    (r"i might like (\w+)", "user/preference/{user_id}/maybe_likes_{0}"),
]


def infer_canonical_key(text: str, user_id: str = "default_user") -> Optional[str]:
    """
    Infer a canonical key from natural language text using pattern matching.
    Returns None if no pattern matches.
    
    Handles two formats:
    1. Direct key format: "key/path: hypothesis text"
    2. Natural language patterns
    """
    text_lower = text.lower().strip()
    
    # Check for direct key format first: "key/path: value"
    if ": " in text:
        potential_key = text.split(": ", 1)[0].strip().lower()
        # Validate it looks like a canonical key (has / and valid chars)
        if "/" in potential_key and re.match(r'^[a-z0-9/_]+$', potential_key):
            return potential_key
    
    # Fall back to pattern matching
    for pattern, key_template in KEY_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            groups = match.groups()
            key = key_template.format(*groups, user_id=user_id)
            # Normalize key
            key = re.sub(r'[^a-z0-9/_]', '', key.lower())
            return key
    
    return None


def extract_value(text: str) -> str:
    """
    Extract the core value from text.
    
    Handles two formats:
    1. Direct key format: "key/path: hypothesis text" -> extract from hypothesis
    2. Natural language patterns
    """
    text_lower = text.lower().strip()
    
    # Handle direct key format: extract the hypothesis part
    if ": " in text:
        hypothesis_part = text.split(": ", 1)[1].strip().lower()
    else:
        hypothesis_part = text_lower
    
    # Favorite color patterns
    match = re.search(r"favorite (?:color|colour) is (\\w+)", hypothesis_part)
    if match:
        return match.group(1)
    
    match = re.search(r"(?:color is|prefers?) (\\w+)(?: color)?", hypothesis_part)
    if match:
        return match.group(1)
    
    match = re.search(r"really like (\\w+) best", hypothesis_part)
    if match:
        return match.group(1)
    
    # Capital patterns
    match = re.search(r"capital (?:of \\w+ )?is (\\w+)", hypothesis_part)
    if match:
        return match.group(1)
    
    match = re.search(r"(\\w+) is the capital", hypothesis_part)
    if match:
        return match.group(1)
    
    # Mood patterns
    match = re.search(r"i(?:'m| am| feel) (\\w+)", hypothesis_part)
    if match:
        return match.group(1)
    
    # Preference patterns
    match = re.search(r"i (?:like|love|prefer) (\\w+)", hypothesis_part)
    if match:
        return match.group(1)
    
    match = re.search(r"user (?:is|enjoys|likes) (\\w+)", hypothesis_part)
    if match:
        return match.group(1)
    
    match = re.search(r"(?:is|uses|language is) (\\w+)", hypothesis_part)
    if match:
        return match.group(1)
    
    # Fallback: return last significant word or cleaned text
    words = hypothesis_part.split()
    if words:
        return words[-1][:50]
    return hypothesis_part[:50]


def tokenize(text: str) -> set:
    """
    Tokenize text for Jaccard similarity.
    """
    text_lower = text.lower()
    # Remove punctuation, split on whitespace
    tokens = re.findall(r'\b\w+\b', text_lower)
    return set(tokens)


def jaccard_similarity(set1: set, set2: set) -> float:
    """
    Compute Jaccard similarity between two token sets.
    """
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


class Cluster:
    """
    Represents a cluster of related episodic entries.
    """
    def __init__(self, canonical_key: str):
        self.canonical_key = canonical_key
        self.members: List[Dict] = []
        self.normalized_value: Optional[str] = None
    
    def add_member(self, episode: Dict):
        self.members.append(episode)
        if self.normalized_value is None:
            self.normalized_value = extract_value(episode.get("summary", ""))
    
    def get_member_ids(self) -> List[str]:
        # Try both 'episode_id' and 'episodic_id' for compatibility
        return [m.get("episode_id", m.get("episodic_id", "")) for m in self.members]


def cluster_episodes(episodes: List[Dict], user_id: str = "default_user", jaccard_threshold: float = 0.6) -> List[Cluster]:
    """
    Two-stage deterministic clustering:
    - Stage A: Key-candidate bucketing
    - Stage B: Token overlap within buckets
    """
    # Stage A: Group by canonical key
    key_buckets: Dict[str, List[Dict]] = {}
    
    for episode in episodes:
        text = episode.get("summary", "")
        key = infer_canonical_key(text, user_id)
        
        if key is None:
            # Cannot bucket, skip
            continue
        
        if key not in key_buckets:
            key_buckets[key] = []
        key_buckets[key].append(episode)
    
    # Stage B: Within each bucket, cluster by token overlap or identical value
    clusters: List[Cluster] = []
    
    for key, bucket_episodes in key_buckets.items():
        if len(bucket_episodes) == 1:
            # Single episode = single cluster
            cluster = Cluster(key)
            cluster.add_member(bucket_episodes[0])
            clusters.append(cluster)
            continue
        
        # Group by similar text within bucket
        used = set()
        for i, ep1 in enumerate(bucket_episodes):
            if i in used:
                continue
            
            cluster = Cluster(key)
            cluster.add_member(ep1)
            used.add(i)
            
            tokens1 = tokenize(ep1.get("summary", ""))
            val1 = extract_value(ep1.get("summary", ""))
            
            for j, ep2 in enumerate(bucket_episodes):
                if j in used:
                    continue
                
                tokens2 = tokenize(ep2.get("summary", ""))
                val2 = extract_value(ep2.get("summary", ""))
                
                # Check: identical value OR Jaccard >= threshold
                if val1 == val2 or jaccard_similarity(tokens1, tokens2) >= jaccard_threshold:
                    cluster.add_member(ep2)
                    used.add(j)
            
            clusters.append(cluster)
    
    return clusters


def compute_features(cluster: Cluster, all_episodes: List[Dict], existing_sem_keys: List[str]) -> Dict[str, Any]:
    """
    Compute the 5 core features + governance_conflict_flag for a cluster.
    """
    members = cluster.members
    n = len(members)
    
    # 1. Frequency: count of members (normalized)
    frequency = min(n / 5.0, 1.0)  # Cap at 5 mentions
    
    # 2. Recency: based on timestamps (most recent member)
    recency = 0.5  # Default if no timestamps
    if members:
        # Use order in list as proxy for recency (later = more recent)
        try:
            indices = [all_episodes.index(m) for m in members if m in all_episodes]
            if indices:
                max_idx = max(indices)
                recency = (max_idx + 1) / len(all_episodes) if all_episodes else 0.5
        except (ValueError, IndexError):
            recency = 0.5
    
    # 3. Consistency: do all members agree on value?
    values = [extract_value(m.get("summary", "")) for m in members]
    unique_values = set(values)
    consistency = 1.0 if len(unique_values) == 1 else 1.0 / len(unique_values)
    
    # 4. Semantic novelty: is this key already in SEM?
    semantic_novelty = 1.0 if cluster.canonical_key not in existing_sem_keys else 0.0
    
    # 5. Source diversity: unique job_seeds / sources
    sources = set()
    for m in members:
        payload = m.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except:
                payload = {}
        sources.add(payload.get("job_seed", m.get("episodic_id", "")))
    source_diversity = min(len(sources) / 3.0, 1.0)  # Normalize to 3 sources
    
    # 6. Governance conflict flag
    governance_conflict_flag = False
    
    # Check for known false facts
    false_facts = [
        ("capital", "sydney", "australia"),
    ]
    value_lower = (cluster.normalized_value or "").lower()
    key_lower = cluster.canonical_key.lower()
    
    for fact_type, wrong_val, context in false_facts:
        if fact_type in key_lower and wrong_val == value_lower:
            governance_conflict_flag = True
            break
    
    # Check for temporary/ephemeral content
    if "temporary" in key_lower or "mood/state" in key_lower:
        governance_conflict_flag = True
    
    # Check for ambiguous preference patterns
    if "maybe_likes" in key_lower or "might" in key_lower:
        governance_conflict_flag = True
    
    return {
        "frequency": round(frequency, 3),
        "recency": round(recency, 3),
        "consistency": round(consistency, 3),
        "semantic_novelty": round(semantic_novelty, 3),
        "source_diversity": round(source_diversity, 3),
        "governance_conflict_flag": governance_conflict_flag
    }


def compute_consolidator_score(features: Dict) -> float:
    """
    Heuristic consolidator score based on features.
    Higher = more promotable.
    """
    # Conflict flag is a hard penalty
    if features.get("governance_conflict_flag", False):
        return 0.1
    
    # Weighted sum
    score = (
        features["frequency"] * 0.2 +
        features["recency"] * 0.1 +
        features["consistency"] * 0.3 +
        features["semantic_novelty"] * 0.2 +
        features["source_diversity"] * 0.2
    )
    return round(score, 3)


def compute_mem_snn_shadow_score(features: Dict) -> float:
    """
    Shadow MEM-SNN score (placeholder for future ML model).
    For LR-01, returns a heuristic approximation.
    """
    # Simple heuristic that mimics what an SNN might learn
    if features.get("governance_conflict_flag", False):
        return 0.15
    
    # Slightly different weights than consolidator
    score = (
        features["frequency"] * 0.25 +
        features["recency"] * 0.15 +
        features["consistency"] * 0.25 +
        features["semantic_novelty"] * 0.15 +
        features["source_diversity"] * 0.20
    )
    return round(score, 3)


def generate_candidates(clusters: List[Cluster], all_episodes: List[Dict], existing_sem_keys: List[str]) -> List[Dict]:
    """
    Generate MEMCandidate objects from clusters.
    """
    candidates = []
    
    for cluster in clusters:
        features = compute_features(cluster, all_episodes, existing_sem_keys)
        consolidator_score = compute_consolidator_score(features)
        mem_snn_score = compute_mem_snn_shadow_score(features)
        
        # Generate deterministic candidate ID
        provenance = cluster.get_member_ids()
        candidate_payload = f"{cluster.canonical_key}:{cluster.normalized_value}:{','.join(sorted(provenance))}"
        candidate_id = deterministic.deterministic_id("mem_candidate", candidate_payload)
        
        candidate = {
            "candidate_id": candidate_id,
            "features": features,
            "proposed_key": cluster.canonical_key,
            "value": cluster.normalized_value or "",
            "provenance": provenance,
            "consolidator_score": consolidator_score,
            "mem_snn_score": mem_snn_score,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        candidates.append(candidate)
    
    return candidates


def persist_candidate(candidate: Dict) -> str:
    """
    Persist a MEMCandidate to the database.
    """
    conn = persistence.get_connection()
    try:
        persistence.execute_query(conn,
            """INSERT OR REPLACE INTO mem_candidates 
               (candidate_id, features_json, proposed_key, value, provenance_json, 
                consolidator_score, mem_snn_score, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate["candidate_id"],
                json.dumps(candidate["features"]),
                candidate["proposed_key"],
                candidate["value"],
                json.dumps(candidate["provenance"]),
                candidate["consolidator_score"],
                candidate["mem_snn_score"],
                candidate["created_at"]
            )
        )
        conn.commit()
        return candidate["candidate_id"]
    finally:
        conn.close()


def get_all_candidates() -> List[Dict]:
    """
    Retrieve all MEMCandidates from database.
    """
    conn = persistence.get_connection()
    try:
        cur = persistence.execute_query(conn, "SELECT * FROM mem_candidates ORDER BY created_at")
        rows = persistence.fetch_all(cur)
        
        candidates = []
        for row in rows:
            candidates.append({
                "candidate_id": row["candidate_id"],
                "features": json.loads(row["features_json"]),
                "proposed_key": row["proposed_key"],
                "value": row["value"],
                "provenance": json.loads(row["provenance_json"]),
                "consolidator_score": row["consolidator_score"],
                "mem_snn_score": row["mem_snn_score"],
                "created_at": row["created_at"]
            })
        
        return candidates
    finally:
        conn.close()
