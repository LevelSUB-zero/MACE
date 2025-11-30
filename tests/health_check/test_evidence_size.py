import unittest
import os
import json
import shutil
from mace.core import deterministic, artifact_store
from mace.runtime import executor
from mace.memory import semantic

class TestEvidenceSize(unittest.TestCase):
    
    def setUp(self):
        deterministic.init_seed("evidence_test")
        if os.path.exists("mace_memory.db"):
            os.remove("mace_memory.db")
        # Clean artifacts dir
        if os.path.exists("artifacts"):
            shutil.rmtree("artifacts")

    def test_evidence_size_boundary(self):
        """
        Verify that evidence larger than 16KB is redacted and stored as an artifact.
        """
        # 1. Create 16KB + 1 byte string
        # MAX_EVIDENCE_SIZE is 16384 bytes.
        # We need the JSON representation to exceed this.
        # "x" * N -> JSON is "x...x" (N+2 bytes)
        # So N=16383 -> JSON=16385 bytes.
        
        N = 16 * 1024 - 1 # 16383
        huge_str = "x" * N
        expected_json = json.dumps(huge_str)
        self.assertTrue(len(expected_json.encode('utf-8')) > 16 * 1024)
        
        key = "user/profile/user_123/huge_data"
        
        # 2. Put into SEM
        semantic.put_sem(key, huge_str)
        
        # 3. Read via Executor
        # We need an agent that reads this. Profile agent reads "what is my X".
        res, log_entry = executor.execute("what is my huge_data", seed="read_huge")
        
        # 4. Find evidence
        found = False
        for ev in log_entry["evidence_items"]:
            if ev["type"] == "sem_read_snapshot" and ev["source"]["reference"] == key:
                found = True
                
                # 5. Verify redaction
                self.assertIsNone(ev["raw_payload"], "raw_payload should be None")
                self.assertIsNone(ev["content"]["structured"], "structured content should be None")
                self.assertTrue(ev["content"]["text"].startswith("<Redacted"), "text should be redacted")
                
                # 6. Verify artifact
                self.assertTrue(len(ev["provenance"]) > 0)
                prov = ev["provenance"][0]
                self.assertEqual(prov["step"], "size_check")
                self.assertIn("artifact_url", prov)
                artifact_url = prov["artifact_url"]
                self.assertTrue(artifact_url.startswith("artifacts://"))
                
                # 7. Verify content
                content_bytes = artifact_store.get_artifact(artifact_url)
                self.assertIsNotNone(content_bytes, "Artifact file not found")
                self.assertEqual(content_bytes.decode('utf-8'), expected_json)
                break
                
        self.assertTrue(found, "Evidence item not found")

if __name__ == "__main__":
    unittest.main()
