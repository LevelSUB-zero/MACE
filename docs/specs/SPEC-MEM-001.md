# SPEC: Deterministic Candidate Generation & Memory Pipeline Testing
**Backlog ID:** MEM-001
**Date:** 2026-02-21
**Status:** DRAFT → APPROVED

## 1. Goal
Implement the first component of Stage-2 Memory Governance: **Candidate Generation**. A "Candidate" is a transient, compressed hypothesis formulated from raw patterns in Episodic Memory. It is not a belief; it acts as a testable proposition sent to the Council. We also need to build an end-to-end memory pipeline test that validates episodic writes/reads and semantic retrieval without affecting other execution stages.

## 2. Anti-Drift Validation
- ✅ **Autonomy**: Candidates allow MACE to independently recognize recursive patterns in its own life without human-labeled training data.
- ✅ **Self-regeneration**: This is the necessary first step to converting raw experience (episodic) into permanent knowledge (semantic) to regenerate the brain's knowledge graph.
- ✅ **Not an LLM wrapper**: Candidate generation uses deterministic mathematical clustering and heuristic features (`frequency`, `consistency`) over a SQLite database, completely isolated from LLM prompt completion.
- ✅ **Biological alignment**: Mimics memory consolidation (the "sleep" phase) where short-term episodes are compressed into hypothetical rules for long-term storage.

## 3. Design

### 3.1 Architecture
The existing memory architecture stops at Episodic Memory.
Adding `candidate.py` serves as the bridge:
`EpisodicMemory` -> `CandidateGenerator.extract_candidates()` -> [List of Candidates] -> `Council` (Future task).

### 3.2 Components
- `src/mace/memory/candidate.py`: New module.
  - Generates transient Candidate objects.
  - Enforces the frozen feature semantic rules (no LLMs or magic embeddings allowed here; just heuristic string/context clustering).
- `tests/v02_validation/test_memory_pipeline.py`: New integration test.
  - Ensures saving/retrieving API calls for the entire memory stack (WM, Episodic, Semantic) work holistically without locking or schema issues on Windows.

### 3.3 Data Flow
1. Fetch latest blocks of `EpisodicMemory` logs.
2. Cluster similar logs using a deterministic grouping key (e.g., matching `context_tags` and `percept_text` noun structures).
3. Compute the **6 Frozen Features** for each cluster:
   - `frequency` (int count)
   - `consistency` (float ratio of non-contradicting elements)
   - `recency` (float, based on time since oldest trace)
   - `source_diversity` (int, count of unique agents/tools)
   - `semantic_novelty` (bool/float, check if similar key exists in Semantic Memory and contradicts)
   - `governance_conflict_flag` (bool, does this trip a basic regex filter or policy block?)
4. Output a list of candidate dictionaries.

### 3.4 Interfaces

```python
# src/mace/memory/candidate.py

from typing import List, Dict, Any
from mace.memory.episodic import EpisodicMemory

class CandidateGenerator:
    def __init__(self, episodic_memory: EpisodicMemory):
        self.episodic = episodic_memory
        
    def generate_candidates(self, max_episodes: int = 100) -> List[Dict[str, Any]]:
        """
        Extracts candidate hypotheses from the N most recent episodic traces.
        Returns a list of candidate dictionaries with the 6 strictly prescribed features.
        """
        pass
        
    def _cluster_episodes(self, episodes: List[Dict]) -> Dict[str, List[Dict]]:
        """Group episodes by overlapping semantic/context tags."""
        pass
        
    def _calculate_features(self, cluster_key: str, cluster_eps: List[Dict]) -> Dict[str, Any]:
        """Calculates frequency, consistency, recency, etc. for a given cluster."""
        pass
```

## 4. Task Breakdown

| # | Task | Files | Dependencies |
|---|------|-------|-------------|
| 1 | Create basic `candidate.py` structure and clustering logic | `src/mace/memory/candidate.py` | None |
| 2 | Implement the 6 frozen feature mathematical extractions | `src/mace/memory/candidate.py` | Task 1 |
| 3 | Write Candidate generator unit tests | `tests/v02_validation/test_candidate.py` | Task 2 |
| 4 | Write holistic E2E Memory Pipeline test (saving/retrieving API) | `tests/v02_validation/test_memory_pipeline.py` | None |
| 5 | Resolve any SQLite file-locking issues encountered in test suite | Multiple if applicable | Task 4 |

## 5. Acceptance Criteria
- [ ] `candidate.py` successfully groups similar episodic records (e.g. 5 requests to "store name as Bob") into a single Candidate.
- [ ] No LLMs or stochastic networks are used in candidate generation (Strictly deterministic).
- [ ] E2E memory pipeline test successfully creates Episodic traces and extracts Candidates.
- [ ] Candidate outputs contain exact keys: `frequency`, `consistency`, `recency`, `source_diversity`, `semantic_novelty`, `governance_conflict_flag`.

## 6. Risks & Edge Cases
- **Database Locks**: Reading from episodic memory while writes might be happening in another test thread. Python's SQLite wrapper on Windows is notoriously finicky with locking. Ensure `tearDown` cleans up DBs properly like in the executor tests to prevent cross-test contamination.
- **Clustering Naivety**: Initially, clustering by text/tags might be too rigorous (grouping only perfect string matches) or too loose. Start strict to prevent hallucinatory merges.

## 7. Decisions Made
- Candidates will be simple Python dictionaries during generation, not persisted to a database table yet, adhering to the "Transient/Ephemeral" requirement in the rulebook.
