"""
Module: test_memory_persistence.py
Stage: 2
Purpose: Validate memory persistence across simulated shutdowns and
         cross-layer entity search.

Tests the REAL NLU pipeline (Gemma 3 1B via Ollama) — NO MOCKING.
Validates:
  T1: Complex sentence → shutdown → semantic search by entity name
  T2: Multi-entity storage → cross-search after shutdown
  T3: Episodic memory persistence after shutdown
  T4: Knowledge Graph persistence after shutdown
  T5: Working Memory volatile behavior (store → retrieve → lost after shutdown)

Requires: Ollama running at localhost:11434 with gemma3:1b

Part of MACE (Meta Aware Cognitive Engine).
"""
import unittest
import os
import time
import requests
from mace.runtime import executor
from mace.core import deterministic
from mace.memory import semantic
from mace.memory.episodic import EpisodicMemory
from mace.memory.knowledge_graph import get_knowledge_graph
from mace.memory.wm import WorkingMemory


def _ollama_available():
    """Check if Ollama is running and gemma3:1b is available."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        models = [m["name"] for m in r.json().get("models", [])]
        return any("gemma3" in m or "gemma3:1b" in m for m in models)
    except Exception:
        return False


OLLAMA_READY = _ollama_available()
SKIP_REASON = "Ollama not running or gemma3:1b not available"


def _simulate_shutdown():
    """
    Simulate a system shutdown by resetting all in-memory state.
    SQLite DB files are preserved (like a real restart).
    """
    from mace.reflective import writer
    from mace.brainstate import persistence as bs_persistence
    import mace.memory.episodic as eps
    import mace.memory.knowledge_graph as kg_mod

    writer._table_initialized = False
    bs_persistence._table_initialized = False
    semantic._tables_initialized = False
    eps._table_initialized = False
    kg_mod._table_initialized = False
    kg_mod._kg_instance = None  # Reset KG singleton

    # Re-set the semantic store to a fresh LiveSEMStore instance
    # This simulates a cold start — new connections to the same DB
    semantic.set_store(semantic.LiveSEMStore())


@unittest.skipUnless(OLLAMA_READY, SKIP_REASON)
class TestMemoryPersistence(unittest.TestCase):
    """
    Validates that memory persists after simulated shutdown and
    can be searched by entity name across all memory layers.
    """

    # Override conftest.py's autouse db_cleanup fixture
    db_cleanup = None

    @classmethod
    def setUpClass(cls):
        """One-time setup: clean slate for all tests."""
        deterministic.set_mode("DETERMINISTIC")
        cls.seed_base = "mem003_persistence"
        deterministic.init_seed(cls.seed_base)

        # Reset module-level init flags
        from mace.reflective import writer
        from mace.brainstate import persistence as bs_persistence
        import mace.memory.episodic as eps

        writer._table_initialized = False
        bs_persistence._table_initialized = False
        semantic._tables_initialized = False
        eps._table_initialized = False

        # Clean DB files
        for f in ["mace_stage1.db", "mace_memory.db",
                   "logs/reflective_log.jsonl", "logs/sem_write_journal.jsonl"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    @classmethod
    def tearDownClass(cls):
        """Post-test cleanup."""
        for f in ["mace_stage1.db", "mace_memory.db",
                   "logs/reflective_log.jsonl", "logs/sem_write_journal.jsonl"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    # =========================================================
    # T1: Complex Sentence → Shutdown → Semantic Search
    # =========================================================

    def test_t1_semantic_persistence_after_shutdown(self):
        """
        Store a complex sentence, simulate shutdown, then search
        semantic memory by entity name.
        """
        # Phase 1: STORE
        output, log = executor.execute(
            "my friend Sarah is a chef",
            seed=f"{self.seed_base}_t1_store"
        )
        print(f"[T1] Store output: {output['text']}")
        print(f"[T1] Agent: {log['router_decision']['selected_agents'][0]['agent_id']}")

        # Verify it was stored
        results_before = semantic.search_sem("sarah")
        print(f"[T1] Before shutdown - search 'sarah': {results_before}")
        self.assertGreater(len(results_before), 0,
                           "Data was NOT stored before shutdown!")

        # Phase 2: SHUTDOWN
        _simulate_shutdown()
        print("[T1] === SYSTEM SHUTDOWN SIMULATED ===")

        # Phase 3: SEARCH AFTER RESTART
        results_after = semantic.search_sem("sarah")
        print(f"[T1] After shutdown - search 'sarah': {results_after}")

        self.assertGreater(len(results_after), 0,
                           "Semantic memory did NOT persist after shutdown!")

        # Verify correct data
        found_sarah = any("sarah" in r["key"] for r in results_after)
        self.assertTrue(found_sarah,
                        f"No key contains 'sarah': {results_after}")

    # =========================================================
    # T2: Multi-Entity Storage → Cross-Search
    # =========================================================

    def test_t2_multi_entity_cross_search(self):
        """
        Store facts about multiple entities, shutdown, then search
        for each entity independently.
        """
        # Store about Alex
        output1, _ = executor.execute(
            "my brother Alex is an engineer",
            seed=f"{self.seed_base}_t2_alex"
        )
        print(f"[T2] Alex store: {output1['text']}")
        time.sleep(0.1)

        # Store about Sarah (favorite movie)
        output2, _ = executor.execute(
            "remember that Mars is a planet",
            seed=f"{self.seed_base}_t2_mars"
        )
        print(f"[T2] Mars store: {output2['text']}")
        time.sleep(0.1)

        # Store user location
        output3, _ = executor.execute(
            "my name is Bob",
            seed=f"{self.seed_base}_t2_bob"
        )
        print(f"[T2] Bob store: {output3['text']}")

        # SHUTDOWN
        _simulate_shutdown()
        print("[T2] === SYSTEM SHUTDOWN SIMULATED ===")

        # Search for each entity
        alex_results = semantic.search_sem("alex")
        mars_results = semantic.search_sem("mars")
        bob_results = semantic.search_sem("bob")

        print(f"[T2] Search 'alex': {alex_results}")
        print(f"[T2] Search 'mars': {mars_results}")
        print(f"[T2] Search 'bob': {bob_results}")

        self.assertGreater(len(alex_results), 0,
                           "Alex was NOT found after shutdown!")
        self.assertGreater(len(mars_results), 0,
                           "Mars was NOT found after shutdown!")
        self.assertGreater(len(bob_results), 0,
                           "Bob was NOT found after shutdown!")

    # =========================================================
    # T3: Episodic Memory Persistence After Shutdown
    # =========================================================

    def test_t3_episodic_persistence(self):
        """
        After storing data and shutting down, episodic memory
        should still contain interaction records.
        """
        # Run some interactions
        executor.execute("hello", seed=f"{self.seed_base}_t3_greet")
        time.sleep(0.05)
        executor.execute("calculate 10 * 5", seed=f"{self.seed_base}_t3_math")
        time.sleep(0.05)

        # Check before shutdown
        em = EpisodicMemory()
        before_count = len(em.get_recent(n=50))
        print(f"[T3] Episodes before shutdown: {before_count}")

        # SHUTDOWN
        _simulate_shutdown()
        print("[T3] === SYSTEM SHUTDOWN SIMULATED ===")

        # Check after shutdown
        em2 = EpisodicMemory()
        after_episodes = em2.get_recent(n=50)
        print(f"[T3] Episodes after shutdown: {len(after_episodes)}")

        self.assertEqual(len(after_episodes), before_count,
                         "Episodic memory lost episodes after shutdown!")

        # Search for specific interaction
        math_results = em2.search_content("10")
        print(f"[T3] Search '10' in episodic: {len(math_results)} results")
        self.assertGreater(len(math_results), 0,
                           "Episodic search for '10' returned no results!")

    # =========================================================
    # T4: Knowledge Graph Persistence After Shutdown
    # =========================================================

    def test_t4_kg_persistence(self):
        """
        KG entities should persist after shutdown.
        """
        # Store entity via executor
        executor.execute(
            "my friend Sarah is a chef",
            seed=f"{self.seed_base}_t4_kg"
        )
        time.sleep(0.1)

        # Check KG before shutdown
        kg = get_knowledge_graph()
        before = kg.recall_about("sarah")
        print(f"[T4] KG before shutdown: {before}")

        # SHUTDOWN
        _simulate_shutdown()
        print("[T4] === SYSTEM SHUTDOWN SIMULATED ===")

        # Check KG after shutdown
        kg2 = get_knowledge_graph()
        after = kg2.recall_about("sarah")
        print(f"[T4] KG after shutdown: {after}")

        self.assertTrue(after.get("found", False),
                        "KG lost 'sarah' entity after shutdown!")

    # =========================================================
    # T5: Working Memory — Volatile by Design
    # =========================================================

    def test_t5_wm_volatile(self):
        """
        WM items should be accessible immediately but lost after
        shutdown (by design — WM is session-scoped).
        """
        # Phase 1: Store in WM
        wm = WorkingMemory(job_seed="mem003_wm_test")
        id1 = wm.add({"fact": "Python was created by Guido", "type": "knowledge"})
        id2 = wm.add({"fact": "MACE is an artificial organism", "type": "identity"})
        id3 = wm.add({"task": "Complete persistence tests", "type": "task"})

        print(f"[T5] WM items stored: {len(wm)}")

        # Phase 2: Immediate retrieval (should work)
        all_items = wm.get_all()
        self.assertEqual(len(all_items), 3, f"Expected 3 WM items, got {len(all_items)}")

        item1 = wm.get(id1)
        self.assertIsNotNone(item1, "WM item 1 not found!")
        self.assertEqual(item1["content"]["fact"], "Python was created by Guido")

        item2 = wm.get(id2)
        self.assertIsNotNone(item2, "WM item 2 not found!")
        self.assertEqual(item2["content"]["fact"], "MACE is an artificial organism")

        print(f"[T5] Immediate retrieval: PASS (all {len(all_items)} items)")

        # Phase 3: After "shutdown" — WM is gone (new instance)
        wm2 = WorkingMemory(job_seed="mem003_wm_test_after")
        self.assertEqual(len(wm2), 0,
                         "New WM instance should be empty!")
        print(f"[T5] After new session: WM empty (expected)")

        # Also verify original WM is independent
        self.assertEqual(len(wm), 3,
                         "Original WM should still have items in-process")
        print(f"[T5] Original WM still alive in-process: {len(wm)} items")


if __name__ == "__main__":
    unittest.main()
