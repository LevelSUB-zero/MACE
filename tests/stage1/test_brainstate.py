import unittest
import copy
from mace.brainstate import brainstate
from mace.core import deterministic

class TestBrainState(unittest.TestCase):
    
    def test_create_snapshot_determinism(self):
        s1 = brainstate.create_snapshot("seed1")
        
        # Reset seed to ensure independence or re-init
        deterministic.init_seed("seed1") # create_snapshot calls init_seed, but let's be sure
        s2 = brainstate.create_snapshot("seed1")
        
        self.assertEqual(s1["snapshot_id"], s2["snapshot_id"])
        
        s3 = brainstate.create_snapshot("seed2")
        self.assertNotEqual(s1["snapshot_id"], s3["snapshot_id"])
        
    def test_tick_logic(self):
        bs = brainstate.create_snapshot("seed_tick")
        initial_id = bs["snapshot_id"]
        
        # Add WM item
        item = {"memory_id": "m1", "content": "foo"}
        brainstate.add_wm_item(bs, item)
        
        self.assertEqual(len(bs["working_memory"]), 1)
        self.assertEqual(bs["working_memory"][0]["ttl"], 10)
        
        # Tick
        brainstate.tick(bs)
        
        self.assertNotEqual(bs["snapshot_id"], initial_id)
        self.assertEqual(bs["working_memory"][0]["ttl"], 9)
        self.assertLess(bs["attention_gain"], 1.0)
        
    def test_wm_expiry(self):
        bs = brainstate.create_snapshot("seed_expiry")
        item = {"memory_id": "m1", "content": "foo"}
        brainstate.add_wm_item(bs, item)
        
        # Tick 10 times
        for _ in range(10):
            brainstate.tick(bs)
            
        # Should be gone (TTL was 10, now 0 -> removed)
        self.assertEqual(len(bs["working_memory"]), 0)

if __name__ == "__main__":
    unittest.main()
