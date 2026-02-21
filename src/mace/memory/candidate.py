"""
Module: candidate.py
Stage: 2
Purpose: Generates deterministic Candidate hypotheses from Episodic Memory.

Part of MACE (Meta Aware Cognitive Engine).
"""
import re
from datetime import datetime
from typing import List, Dict, Any
from mace.memory.episodic import EpisodicMemory
from mace.memory import semantic

# Simple heuristic for governance conflict
# In a real system, this would call out to a more robust policy engine
DANGEROUS_KEYWORDS = re.compile(r"\b(kill|destroy|hack|steal|password|ssn|credit\s*card)\b", re.IGNORECASE)

class CandidateGenerator:
    """
    Candidate Generator for Stage-2 Memory Governance.
    
    Extracts transient Candidate hypotheses from raw 
    episodic memory traces using strictly deterministic logic.
    """
    
    def __init__(self, episodic_memory: EpisodicMemory):
        self.episodic = episodic_memory
        
    def generate_candidates(self, max_episodes: int = 100) -> List[Dict[str, Any]]:
        """
        Extracts candidate hypotheses from the N most recent episodic traces.
        Returns a list of candidate dictionaries with the 6 strictly prescribed features.
        """
        episodes = self.episodic.get_recent(n=max_episodes)
        if not episodes:
            return []
            
        clusters = self._cluster_episodes(episodes)
        candidates = []
        for key, cluster in clusters.items():
            if len(cluster) > 0:
                features = self._calculate_features(key, cluster)
                # The candidate is transient
                candidate = {
                    "cluster_key": key,
                    "episodes_count": len(cluster),
                    "features": features
                }
                candidates.append(candidate)
                
        # Sort by cluster key to ensure deterministic output order
        return sorted(candidates, key=lambda c: c["cluster_key"])
        
    def _cluster_episodes(self, episodes: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group episodes by overlapping semantic/context tags.
        A highly deterministic mathematical clustering based on tags.
        """
        clusters = {}
        for ep in episodes:
            payload = ep.get("payload", {})
            tags = payload.get("context_tags", ["general_context"])
            
            # Use the primary tag as the clustering key
            primary_tag = tags[0] if tags else "general_context"
            
            # Avoid clustering completely generic things unless they are really similar
            if primary_tag in ["general_context", "untagged"]:
                # Try to cluster by agent
                agent_id = payload.get("agent_id", "unknown_agent")
                primary_tag = f"generic_{agent_id}"
                
            if primary_tag not in clusters:
                clusters[primary_tag] = []
            clusters[primary_tag].append(ep)
            
        return clusters

    def _calculate_features(self, cluster_key: str, cluster_eps: List[Dict]) -> Dict[str, Any]:
        """Calculates frequency, consistency, recency, source_diversity, semantic_novelty, and governance_conflict_flag for a given cluster."""
        
        # 1. Frequency
        frequency = len(cluster_eps)
        
        # 2. Consistency
        # To calculate consistency deterministically without an LLM:
        # We track how many unique responses (or percepts) exist. 
        # A perfectly consistent interaction has few unique branches.
        responses = [ep.get("payload", {}).get("response_text", "") for ep in cluster_eps]
        unique_responses = len(set(responses))
        consistency = 1.0 if frequency == 0 else (1.0 / unique_responses) if unique_responses > 0 else 1.0
        
        # 3. Recency
        # Time span of the cluster to remain deterministic without `datetime.now()`
        # We find the newest and oldest in the cluster.
        timestamps = []
        for ep in cluster_eps:
            dt_str = ep.get("created_at")
            if dt_str:
                try:
                    dt_str = dt_str.replace("Z", "+00:00")
                    timestamps.append(datetime.fromisoformat(dt_str))
                except ValueError:
                    pass
        
        if timestamps:
            oldest_time = min(timestamps)
            newest_time = max(timestamps)
            recency = (newest_time - oldest_time).total_seconds()
        else:
            recency = 0.0
            
        # 4. Source Diversity
        agents = set(ep.get("payload", {}).get("agent_id", "") for ep in cluster_eps)
        source_diversity = len(agents)
        
        # 5. Semantic Novelty
        # Check if the cluster key (or something derived) already exists in semantic memory
        # Here we use a heuristic key
        sem_key = f"concept/{cluster_key}"
        val, _ = semantic._active_store.get(sem_key)
        semantic_novelty = 1.0 if val is None else 0.0 # 1.0 = completely novel
        
        # 6. Governance Conflict Flag
        conflict = False
        for ep in cluster_eps:
            text = ep.get("payload", {}).get("percept_text", "") + " " + ep.get("payload", {}).get("response_text", "")
            if DANGEROUS_KEYWORDS.search(text):
                conflict = True
                break
                
        return {
            "frequency": frequency,
            "consistency": float(consistency),
            "recency": float(recency),
            "source_diversity": source_diversity,
            "semantic_novelty": float(semantic_novelty),
            "governance_conflict_flag": conflict
        }
