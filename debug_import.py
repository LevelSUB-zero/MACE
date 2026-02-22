
import sys
import os

# Ensure src is in path
sys.path.insert(0, r"f:\MAIN PROJECTS\Mace\src")

try:
    print("Attempting import...")
    from mace.core.cognitive.cortex import ShadowCortex
    print("Import success!")
except Exception as e:
    print("Import failed!")
    import traceback
    traceback.print_exc()

print("Checking directory structure:")
try:
    import mace.core.cognitive
    print("mace.core.cognitive file:", mace.core.cognitive.__file__)
except:
    print("Could not import mace.core.cognitive")
