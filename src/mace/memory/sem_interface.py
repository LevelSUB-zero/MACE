from mace.memory import semantic

class SemanticMemoryInterface:
    def __init__(self):
        # Initialize store? 
        # semantic.py uses LiveSEMStore or ReplaySEMStore.
        # For Stage-1, we assume LiveSEMStore for now or pass config.
        self.store = semantic.LiveSEMStore()
        
    def put(self, key, value, source="unknown"):
        return semantic.put_sem(key, value, source)
        
    def get(self, key):
        return semantic.get_sem(key)
        
    def search(self, query):
        # semantic.py doesn't seem to have a search function exposed in the snippets I saw.
        # But it likely has one.
        # For now, let's assume basic get/put is what we need.
        pass
