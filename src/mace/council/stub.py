import datetime
from mace.core import deterministic

def evaluate(agent_output):
    """
    Stub evaluation that always approves.
    """
    # Use deterministic ID
    # We need a unique seed for this vote.
    # We can use the agent output as part of the seed or just a counter.
    vote_id = deterministic.deterministic_id("council_vote", agent_output["text"])
    
    return {
        "vote_id": vote_id,
        "agent_id": "council_stub",
        "correctness": 1.0,
        "relevance": 1.0,
        "safety": 1.0,
        "coherence": 1.0,
        "approve": True,
        "suggested_changes": None,
        "explain": "Stage-1 Stub Approval"
    }
