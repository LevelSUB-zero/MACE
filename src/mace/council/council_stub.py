from mace.core import structures

def evaluate(agent_output):
    """
    Council Stub: Always approves with perfect scores.
    """
    return structures.create_council_vote(
        agent_id=agent_output["agent_id"],
        approve=True,
        explain="stage0_stub"
    )
