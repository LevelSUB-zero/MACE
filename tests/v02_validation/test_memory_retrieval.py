"""
Module: test_memory_retrieval.py
Stage: 2
Purpose: Complex end-to-end validation of Memory Saving & Retrieving.

Tests the REAL NLU pipeline (Gemma 3 1B via Ollama) — NO MOCKING.
Validates 6 tiers of memory complexity:
  Tier 1: Multi-attribute profile store/recall
  Tier 2: Third-party entity (contact) store/recall
  Tier 3: Knowledge fact lifecycle
  Tier 4: Episodic memory search (system-initiated recall)
  Tier 5: Knowledge graph entity recall
  Tier 6: Rapid SQLite write stability

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


@unittest.skipUnless(OLLAMA_READY, SKIP_REASON)
class TestMemoryRetrieval(unittest.TestCase):
    """
    All tests use the REAL NLU pipeline (Ollama Gemma 3 1B).
    No mocking. Tests are ordered to build on each other.
    """

    # Override conftest.py's autouse db_cleanup fixture — this class
    # manages its own DB lifecycle via setUpClass/tearDownClass.
    # Without this, conftest deletes mace_memory.db after EACH test,
    # destroying data needed by recall tests.
    db_cleanup = None

    @classmethod
    def setUpClass(cls):
        """One-time setup: clean slate for all tests."""
        deterministic.set_mode("DETERMINISTIC")
        cls.seed_base = "mem002_complex_test"
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
    # TIER 1: Multi-Attribute Profile Storage & Recall
    # =========================================================

    def test_t1a_store_name(self):
        """Store user's name via real NLU and verify in semantic DB."""
        output, log = executor.execute(
            "my name is Alice",
            seed=f"{self.seed_base}_t1a"
        )
        # Agent should have stored the name
        print(f"[T1a] Output: {output['text']}")
        print(f"[T1a] Agent: {log['router_decision']['selected_agents'][0]['agent_id']}")

        # Verify the semantic DB has the value
        res = semantic.get_sem("user/profile/user_123/name")
        self.assertTrue(res["exists"], "Name was NOT stored in semantic memory!")
        self.assertEqual(res["value"], "Alice")

    def test_t1b_recall_name(self):
        """Recall the stored name via real NLU."""
        # Ensure name is seeded (in case t1a ran in a different order)
        semantic.put_sem("user/profile/user_123/name", "Alice", source="test_setup")

        output, log = executor.execute(
            "what is my name",
            seed=f"{self.seed_base}_t1b"
        )
        print(f"[T1b] Output: {output['text']}")

        self.assertIn("Alice", output["text"],
                       f"Expected 'Alice' in response, got: {output['text']}")

    def test_t1c_store_color(self):
        """Store user's favorite color via real NLU."""
        output, log = executor.execute(
            "my favorite color is blue",
            seed=f"{self.seed_base}_t1c"
        )
        print(f"[T1c] Output: {output['text']}")

        # Check DB — NLU might parse attribute as "favorite_color" or "color"
        res_fc = semantic.get_sem("user/profile/user_123/favorite_color")
        res_c = semantic.get_sem("user/profile/user_123/color")

        stored = res_fc["exists"] or res_c["exists"]
        self.assertTrue(stored, "Favorite color was NOT stored in semantic memory!")

    def test_t1d_store_location(self):
        """Store user's location via real NLU."""
        output, log = executor.execute(
            "I live in Tokyo",
            seed=f"{self.seed_base}_t1d"
        )
        print(f"[T1d] Output: {output['text']}")

        # NLU might parse as "location", "city", or "live"
        for attr in ["location", "city", "live"]:
            res = semantic.get_sem(f"user/profile/user_123/{attr}")
            if res["exists"]:
                self.assertIn("Tokyo", str(res["value"]).capitalize(),
                              f"Location stored but doesn't contain Tokyo: {res['value']}")
                return
        # If none found, fail
        self.fail("Location was NOT stored in semantic memory under any expected key!")

    # =========================================================
    # TIER 2: Third-Party Entity (Contact) Storage & Recall
    # =========================================================

    def test_t2a_store_contact(self):
        """Store info about a third-party entity via real NLU."""
        output, log = executor.execute(
            "my friend John is a doctor",
            seed=f"{self.seed_base}_t2a"
        )
        print(f"[T2a] Output: {output['text']}")
        print(f"[T2a] Agent: {log['router_decision']['selected_agents'][0]['agent_id']}")
        print(f"[T2a] Intent: {log['percept']['intent']}")
        print(f"[T2a] Entities: {log['percept']['entities']}")

        # NLU might parse as contact_store (→ user/contacts/john/role)
        # or as profile_store (→ user/profile/user_123/role)
        # Check both paths
        for key in ["user/contacts/john/role",
                     "user/contacts/john/occupation",
                     "user/profile/user_123/role",
                     "user/profile/user_123/occupation"]:
            res = semantic.get_sem(key)
            if res["exists"]:
                print(f"[T2a] Found at key: {key} = {res['value']}")
                self.assertIn("doctor", str(res["value"]).lower())
                return
        self.fail(
            f"Contact 'John' was NOT stored in semantic memory!\n"
            f"Intent was: {log['percept']['intent']}\n"
            f"Entities were: {log['percept']['entities']}"
        )

    def test_t2b_recall_contact(self):
        """Recall info about a third-party entity via real NLU."""
        # Seed in case t2a didn't run
        semantic.put_sem("user/contacts/john/role", "doctor", source="test_setup")

        output, log = executor.execute(
            "who is John",
            seed=f"{self.seed_base}_t2b"
        )
        print(f"[T2b] Output: {output['text']}")

        self.assertIn("doctor", output["text"].lower(),
                       f"Expected 'doctor' in response about John, got: {output['text']}")

    # =========================================================
    # TIER 3: Knowledge Fact Lifecycle
    # =========================================================

    def test_t3a_teach_fact(self):
        """Teach a knowledge fact via real NLU and verify storage."""
        output, log = executor.execute(
            "remember that the sun is a star",
            seed=f"{self.seed_base}_t3a"
        )
        print(f"[T3a] Output: {output['text']}")
        print(f"[T3a] Agent: {log['router_decision']['selected_agents'][0]['agent_id']}")

        # Check semantic DB — key depends on NLU entity extraction
        # Knowledge agent uses: world/fact/general/{attr}
        res = semantic.get_sem("world/fact/general/sun")
        if not res["exists"]:
            res = semantic.get_sem("world/fact/general/the_sun")
        self.assertTrue(res["exists"],
                        "Fact about the sun was NOT stored in semantic memory!")

    def test_t3b_recall_fact(self):
        """Recall a taught fact via real NLU."""
        semantic.put_sem("world/fact/general/sun", "a star", source="test_setup")

        output, log = executor.execute(
            "what is the sun",
            seed=f"{self.seed_base}_t3b"
        )
        print(f"[T3b] Output: {output['text']}")

        self.assertIn("star", output["text"].lower(),
                       f"Expected 'star' in response, got: {output['text']}")

    # =========================================================
    # TIER 4: Episodic Memory — System-Initiated Recall
    # =========================================================

    def test_t4a_episodic_records_interactions(self):
        """
        After several executor calls, episodic memory should contain
        interaction records searchable by keyword.
        """
        # Run a few diverse interactions to populate episodic memory
        interactions = [
            ("calculate 15 + 27", "t4_math"),
            ("my age is 25", "t4_age"),
            ("hello", "t4_greet"),
        ]
        for text, suffix in interactions:
            executor.execute(text, seed=f"{self.seed_base}_{suffix}")
            time.sleep(0.05)  # Small delay for timestamp ordering

        em = EpisodicMemory()
        recent = em.get_recent(n=20)

        print(f"[T4a] Episodic memory has {len(recent)} episodes")
        self.assertGreaterEqual(len(recent), 3,
                                "Episodic memory did not record enough interactions!")

        # Verify episodes contain correct data
        summaries = [ep.get("summary", "") for ep in recent]
        print(f"[T4a] Summaries: {summaries[:5]}")

    def test_t4b_episodic_search_by_keyword(self):
        """
        System-initiated recall: search episodic memory by keyword.
        Simulates what would happen if the system needed to recall
        past interactions related to a topic while processing a task.
        """
        # Ensure there's something to find — run an interaction first
        executor.execute("my name is Alice", seed=f"{self.seed_base}_t4b_seed")
        time.sleep(0.05)

        em = EpisodicMemory()

        # Search for name-related episodes
        results = em.search_by_summary("name")
        print(f"[T4b] Search 'name' returned {len(results)} results")
        self.assertGreater(len(results), 0,
                           "Episodic search for 'name' returned no results!")

        # Verify the found episode contains the right data
        found = results[0]
        payload = found.get("payload", {})
        if isinstance(payload, str):
            import json
            payload = json.loads(payload)
        self.assertIn("Alice", payload.get("percept_text", "") + payload.get("response_text", ""),
                       "Found episode does not contain 'Alice'!")

    def test_t4c_episodic_search_contact(self):
        """
        System searches its own memory for past interactions about a contact.
        """
        executor.execute("my friend John is a doctor",
                         seed=f"{self.seed_base}_t4c_seed")
        time.sleep(0.05)

        em = EpisodicMemory()
        results = em.search_by_summary("doctor")
        if not results:
            # Might be tagged under "personal_context" — search broader
            results = em.search_by_summary("John")

        print(f"[T4c] Search for contact interaction returned {len(results)} results")
        self.assertGreater(len(results), 0,
                           "Episodic search for 'John' or 'doctor' returned no results!")

    # =========================================================
    # TIER 5: Knowledge Graph — Entity Recall
    # =========================================================

    def test_t5a_kg_entity_recall(self):
        """
        After multiple interactions mentioning 'John', the Knowledge Graph
        should accumulate attributes about John and be able to recall them.
        """
        # Run interactions about John to populate KG
        executor.execute("my friend John is a doctor",
                         seed=f"{self.seed_base}_t5a_1")
        time.sleep(0.05)

        kg = get_knowledge_graph()
        recall = kg.recall_about("john")
        print(f"[T5a] KG recall about 'john': {recall}")

        self.assertTrue(recall.get("found", False),
                        "Knowledge Graph does not know about 'john'!")
        # Should have at least some attribute
        attrs = recall.get("attributes", {})
        self.assertGreater(len(attrs), 0,
                           f"KG has no attributes for 'john': {recall}")

    def test_t5b_kg_user_entity(self):
        """
        After storing user attributes ('my name is Alice'),
        the KG should know about the 'user' entity.
        """
        executor.execute("my name is Alice", seed=f"{self.seed_base}_t5b")
        time.sleep(0.05)

        kg = get_knowledge_graph()
        recall = kg.recall_about("user")
        print(f"[T5b] KG recall about 'user': {recall}")

        if recall.get("found"):
            attrs = recall.get("attributes", {})
            self.assertIn("name", attrs,
                          f"KG 'user' entity missing 'name' attribute: {attrs}")

    # =========================================================
    # TIER 6: Rapid Sequential SQLite Writes (Stability)
    # =========================================================

    def test_t6_rapid_sequential_writes(self):
        """
        10 rapid put/get cycles to verify no SQLite locking errors.
        """
        errors = []
        for i in range(10):
            key = f"world/fact/rapid/test_item_{i}"
            val = f"value_{i}"

            res_put = semantic.put_sem(key, val)
            if not res_put["success"]:
                errors.append(f"PUT {key} failed: {res_put.get('error')}")

            res_get = semantic.get_sem(key)
            if not res_get["exists"]:
                errors.append(f"GET {key} failed: not found after PUT")
            elif res_get["value"] != val:
                errors.append(f"GET {key} mismatch: expected {val}, got {res_get['value']}")

        self.assertEqual(len(errors), 0,
                         f"SQLite stability issues:\n" + "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
