class ConsolidatedWorkingMemory:
    def __init__(self):
        self.items = []
        
    def add_item(self, item):
        """
        Add item to CWM.
        """
        # In a real implementation, this might persist to a specific store.
        # For Stage-1, it's an in-memory buffer for the session/job.
        self.items.append(item)
        
    def get_items(self):
        return self.items
        
    def clear(self):
        self.items = []
