
import sys
import unittest
import os
import shutil

sys.path.insert(0, r"f:\MAIN PROJECTS\Mace\src")

from mace.stage5.stage5_router import route_regenerative

class TestEvolution(unittest.TestCase):
    def test_evolution_trigger(self):
        """
        The Golden Test:
        Verify that the system can realize a need, synthesize a tool, and ready it for deployment.
        """
        # Clean up previous run
        tool_path = r"f:\MAIN PROJECTS\Mace\src\mace\tools\dynamic\dynamic_calc.py"
        if os.path.exists(tool_path):
            os.remove(tool_path)
            
        print("\n[TEST] Sending inputs to trigger Evolution...")
        
        input_data = {
            "text": "I need you to calculate something.",
            "content": "perform math calculation", # Keyword 'math' triggers safe stub
            "need_tool": "dynamic_calc" # Trigger for Reptile -> SYNTHESIZE_TOOL
        }
        
        # Tick 1: Goal Formation
        print("\n[TEST] Tick 1...")
        result1 = route_regenerative(input_data, {})
        op1 = result1["stage4_trace"]["op"]
        print(f"[TEST] Tick 1 Op: {op1}")
        self.assertEqual(op1, "PLAN_GOAL", "Expected PLAN_GOAL on first tick")
        
        # Tick 2: Tool Synthesis
        # Input is empty to simulate internal thought progression
        print("\n[TEST] Tick 2...")
        result2 = route_regenerative({}, {}) 
        trace = result2.get("stage4_trace", {})
        op2 = trace.get("op")
        print(f"[TEST] Tick 2 Op: {op2}")
        
        self.assertEqual(op2, "SYNTHESIZE_TOOL", "Reptile failed to propose SYNTHESIZE_TOOL on tick 2")
        
        # 2. Check Logic State (Debug)
        frame_data = trace.get("frame", {})
        logic = frame_data.get("logic", {}).get("predicates", {})
        print(f"[TEST] Logic Keys: {list(logic.keys())}")
        
        # 3. Check Physical File Creation
        # This is the real proof of evolution
        if os.path.exists(tool_path):
            print("[TEST] SUCCESS: Dynamic Tool file created.")
        else:
            self.fail("Dynamic Tool file was NOT created.")
            
        # Optional: Check logic if present
        if "tool_deployment_result" in logic:
             self.assertIn("DEPLOYED", logic["tool_deployment_result"])

if __name__ == "__main__":
    unittest.main()
