import os
import re
import ast

def find_python_files(root_dir):
    py_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if f.endswith(".py"):
                py_files.append(os.path.join(dirpath, f))
    return py_files

def extract_module_name(file_path, src_root):
    # e.g., file_path="src/mace/apt/engine.py" -> "mace.apt.engine"
    rel_path = os.path.relpath(file_path, src_root)
    if rel_path.endswith(".py"):
        rel_path = rel_path[:-3]
    if rel_path.endswith("__init__"):
        rel_path = rel_path[:-9]
    return rel_path.replace(os.sep, ".")

def analyze():
    src_dir = os.path.join("src", "mace")
    test_dir = "tests"
    
    all_src_files = find_python_files(src_dir)
    all_test_files = find_python_files(test_dir) if os.path.exists(test_dir) else []
    
    # Map file -> module_name
    module_to_file = {}
    for f in all_src_files:
        mod = extract_module_name(f, "src")
        # ignore empty or top-level mace
        if mod and mod != "mace":
            module_to_file[mod] = f

    # We want to find which modules are NEVER imported in src/ OR tests/
    # An import could look like:
    # `from mace.apt import engine`
    # `import mace.apt.engine`
    # `from mace.apt.engine import ...`
    
    # Read all content
    content_cache = {}
    for f in all_src_files + all_test_files:
        with open(f, "r", encoding="utf-8") as file_obj:
            content_cache[f] = file_obj.read()
            
    orphans = []
    test_only = []

    for mod, file_path in module_to_file.items():
        base_mod = mod.split(".")[-1]
        parent_mod = ".".join(mod.split(".")[:-1])
        
        # Build regex patterns to catch standard imports
        # pattern 1: mace.apt.engine
        p1 = mod
        # pattern 2: from mace.apt import engine
        p2 = f"from {parent_mod} import.*\\b{base_mod}\\b"
        # pattern 3: from mace.apt.engine import ...
        p3 = f"from {mod} import"
        
        found_in_src = False
        found_in_tests = False
        
        for f, content in content_cache.items():
            if f == file_path:
                continue # ignore self
                
            # If it's an __init__.py of the same package, it might just expose it
            # but that's technically a usage. Let's count it.
            
            if re.search(p1, content) or re.search(p2, content) or re.search(p3, content):
                if f.startswith("src"):
                    found_in_src = True
                elif f.startswith("tests"):
                    found_in_tests = True
                    
        if not found_in_src and not found_in_tests:
            # exclude __init__ and constants if we want, but let's list all
            orphans.append(mod)
        elif not found_in_src and found_in_tests:
            test_only.append(mod)
            
    print("=== ORPHANED MODULES (No imports anywhere) ===")
    for o in sorted(orphans):
        print(" -", o)
        
    print("\n=== TEST-ONLY MODULES (Imported in tests, but not in src/) ===")
    for t in sorted(test_only):
        print(" -", t)

if __name__ == "__main__":
    analyze()
