from mace.core import structures

def run(percept):
    return structures.create_agent_output(
        agent_id="generic_agent",
        text="I don’t have enough stored info to answer that yet.",
        confidence=1.0
    )
