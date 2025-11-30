import unittest
from mace.core import deterministic, idgen

class TestDeterminismV2(unittest.TestCase):
    def setUp(self):
        deterministic.set_mode("DETERMINISTIC")

    def test_counter_reset(self):
        """Verify init_seed resets all counters."""
        deterministic.init_seed(123)
        deterministic.increment_counter("id")
        deterministic.increment_counter("sem_write")
        deterministic.increment_counter("evidence")
        deterministic.increment_counter("log")
        
        # Re-init
        deterministic.init_seed(123)
        
        # Counters should be 0 (or start at 0, increment returns 1)
        # Let's check internal state if possible, or verify behavior
        # increment_counter returns the NEW value. So first call should be 1.
        self.assertEqual(deterministic.increment_counter("id"), 1)
        self.assertEqual(deterministic.increment_counter("sem_write"), 1)
        self.assertEqual(deterministic.increment_counter("evidence"), 1)
        self.assertEqual(deterministic.increment_counter("log"), 1)

    def test_deterministic_id(self):
        """Verify deterministic_id is consistent."""
        deterministic.init_seed("test_seed")
        
        id1 = deterministic.deterministic_id("test", "payload", counter=1)
        id2 = deterministic.deterministic_id("test", "payload", counter=1)
        
        self.assertEqual(id1, id2)
        
        # Different counter
        id3 = deterministic.deterministic_id("test", "payload", counter=2)
        self.assertNotEqual(id1, id3)
        
        # Different payload
        id4 = deterministic.deterministic_id("test", "payload2", counter=1)
        self.assertNotEqual(id1, id4)

    def test_deterministic_timestamp(self):
        """Verify deterministic_timestamp is consistent."""
        deterministic.init_seed("time_seed")
        
        ts1 = deterministic.deterministic_timestamp(counter=100)
        ts2 = deterministic.deterministic_timestamp(counter=100)
        
        self.assertEqual(ts1, ts2)
        
        ts3 = deterministic.deterministic_timestamp(counter=101)
        self.assertNotEqual(ts1, ts3)

    def test_seed_sensitivity(self):
        """Verify different seeds produce different outputs."""
        deterministic.init_seed("seedA")
        id_a = deterministic.deterministic_id("ns", "pl", 1)
        ts_a = deterministic.deterministic_timestamp(1)
        
        deterministic.init_seed("seedB")
        id_b = deterministic.deterministic_id("ns", "pl", 1)
        ts_b = deterministic.deterministic_timestamp(1)
        
        self.assertNotEqual(id_a, id_b)
        self.assertNotEqual(ts_a, ts_b)

    def test_idgen_wrapper(self):
        """Verify idgen wrapper works."""
        deterministic.init_seed("wrapper_seed")
        id_direct = deterministic.deterministic_id("ns", "pl", 5)
        
        # Re-init to get same state
        deterministic.init_seed("wrapper_seed")
        id_wrapper = idgen.deterministic_id("ns", "pl", 5)
        
        self.assertEqual(id_direct, id_wrapper)

if __name__ == '__main__':
    unittest.main()
