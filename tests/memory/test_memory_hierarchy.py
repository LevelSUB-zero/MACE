"""
Memory Hierarchy Tests

Tests for WM, CWM, and Episodic Memory integration.
"""
import unittest
import os

from mace.core import deterministic
from mace.memory.wm import WorkingMemory
from mace.memory.cwm import ContextualWorkingMemory
from mace.memory.episodic import EpisodicMemory


def reset_db_state():
    """Reset DB state for test isolation."""
    for db in ["mace_stage1.db", "mace_memory.db"]:
        if os.path.exists(db):
            os.remove(db)
    
    from mace.memory import cwm, episodic
    from mace.brainstate import persistence as bs_persistence
    from mace.reflective import writer as reflective_writer
    
    cwm._table_initialized = False
    episodic._table_initialized = False
    bs_persistence._table_initialized = False
    reflective_writer._table_initialized = False


class TestWorkingMemory(unittest.TestCase):
    """Test Working Memory."""
    
    @classmethod
    def setUpClass(cls):
        reset_db_state()
        deterministic.init_seed("wm_test_seed")
    
    def test_wm_add_and_get(self):
        """Add items to WM and retrieve them."""
        wm = WorkingMemory(job_seed="test_job")
        
        mem_id = wm.add({"text": "hello"})
        self.assertIsNotNone(mem_id)
        
        item = wm.get(mem_id)
        self.assertEqual(item["content"]["text"], "hello")
    
    def test_wm_capacity_enforcement(self):
        """WM should evict oldest when at capacity (7)."""
        evicted = []
        wm = WorkingMemory(job_seed="test_job", on_expire_callback=lambda x: evicted.append(x))
        
        # Add 8 items (capacity is 7)
        for i in range(8):
            wm.add({"num": i})
        
        # Should have exactly 7 items
        self.assertEqual(len(wm), 7)
        # First item should have been evicted
        self.assertEqual(len(evicted), 1)
        self.assertEqual(evicted[0]["content"]["num"], 0)
    
    def test_wm_ttl_expiry(self):
        """Items should expire after TTL ticks."""
        expired = []
        wm = WorkingMemory(job_seed="test_job", on_expire_callback=lambda x: expired.append(x))
        
        # Add with TTL of 2
        wm.add({"temp": "data"}, ttl=2)
        
        # Tick once
        wm.tick()
        self.assertEqual(len(wm), 1)
        self.assertEqual(len(expired), 0)
        
        # Tick again - should expire
        wm.tick()
        self.assertEqual(len(wm), 0)
        self.assertEqual(len(expired), 1)


class TestContextualWorkingMemory(unittest.TestCase):
    """Test Contextual Working Memory."""
    
    @classmethod
    def setUpClass(cls):
        reset_db_state()
        deterministic.init_seed("cwm_test_seed")
    
    def test_cwm_add_and_persist(self):
        """CWM items should persist to DB."""
        cwm1 = ContextualWorkingMemory(job_seed="session_1")
        
        item_id = cwm1.add({"context": "first"})
        self.assertIsNotNone(item_id)
        
        # Create new CWM instance - should load from DB
        cwm2 = ContextualWorkingMemory(job_seed="session_1")
        items = cwm2.get_all()
        
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["content"]["context"], "first")
    
    def test_cwm_capacity_enforcement(self):
        """CWM should enforce 20 item limit."""
        cwm = ContextualWorkingMemory(job_seed="capacity_test")
        
        # Add 21 items
        for i in range(21):
            cwm.add({"num": i})
        
        # Should have exactly 20
        self.assertEqual(len(cwm), 20)
        # First item should have been evicted
        items = cwm.get_all()
        self.assertEqual(items[0]["content"]["num"], 1)
    
    def test_cwm_wm_promotion(self):
        """WM items should promote to CWM on expiry."""
        cwm = ContextualWorkingMemory(job_seed="promotion_test")
        wm = WorkingMemory(job_seed="promotion_test", on_expire_callback=cwm.add_from_wm)
        
        # Add to WM with short TTL
        wm.add({"promoted": "data"}, ttl=1)
        
        # Tick to expire
        wm.tick()
        
        # Should be in CWM now
        items = cwm.get_all()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["content"]["promoted"], "data")


class TestEpisodicMemory(unittest.TestCase):
    """Test Episodic Memory."""
    
    @classmethod
    def setUpClass(cls):
        reset_db_state()
        deterministic.init_seed("episodic_test_seed")
    
    def test_record_interaction(self):
        """Record and retrieve an interaction."""
        ep = EpisodicMemory(job_seed="interaction_test")
        
        ep_id = ep.record_interaction(
            percept_text="what is my name",
            response_text="Your name is John",
            agent_id="profile_agent",
            job_seed="interaction_test"
        )
        
        self.assertIsNotNone(ep_id)
        
        # Retrieve
        episode = ep.get(ep_id)
        self.assertEqual(episode["payload"]["percept_text"], "what is my name")
        self.assertEqual(episode["payload"]["agent_id"], "profile_agent")
    
    def test_get_recent(self):
        """Get recent episodes."""
        ep = EpisodicMemory()
        
        for i in range(5):
            ep.record_interaction(
                percept_text=f"query {i}",
                response_text=f"response {i}",
                agent_id="test_agent",
                job_seed="recent_test"
            )
        
        recent = ep.get_recent(n=3, job_seed="recent_test")
        self.assertEqual(len(recent), 3)
    
    def test_search_by_summary(self):
        """Search episodes by summary."""
        ep = EpisodicMemory()
        
        ep.record_interaction(
            percept_text="tell me about cats",
            response_text="cats are cute",
            agent_id="knowledge_agent",
            job_seed="search_test"
        )
        
        results = ep.search_by_summary("cats")
        self.assertGreater(len(results), 0)


class TestFullIntegration(unittest.TestCase):
    """Test full memory hierarchy integration."""
    
    @classmethod
    def setUpClass(cls):
        reset_db_state()
        deterministic.init_seed("integration_test_seed")
    
    def test_executor_records_episodic(self):
        """Executor should record interactions to Episodic."""
        from mace.runtime import executor
        
        res, _ = executor.execute("remember my name is Alice")
        
        # Check episodic was recorded
        ep = EpisodicMemory()
        recent = ep.get_recent(n=1)
        
        self.assertGreater(len(recent), 0)
        self.assertIn("Alice", recent[0]["payload"]["percept_text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
