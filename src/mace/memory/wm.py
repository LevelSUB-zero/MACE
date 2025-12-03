from mace.brainstate import brainstate

class WorkingMemory:
    def __init__(self, brainstate_snapshot):
        self.snapshot = brainstate_snapshot

    def add_item(self, content, memory_id=None):
        """
        Add item to WM.
        """
        if memory_id is None:
            # Generate ID? Or require it?
            # For now, require it or generate simple one.
            import uuid
            memory_id = str(uuid.uuid4())
            
        item = {
            "memory_id": memory_id,
            "content": content,
            "type": "wm"
        }
        brainstate.add_wm_item(self.snapshot, item)
        
    def get_items(self):
        return self.snapshot["working_memory"]
