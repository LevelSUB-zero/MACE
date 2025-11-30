import re
from mace.core import structures
from mace.memory import semantic

# Regex for write command: "remember my <attr> is <value>" or "my <attr> is <value>"
REGEX_WRITE = re.compile(r"^(remember my|my) (?P<attribute>[a-z0-9_]+) is (?P<value>.+)$", re.IGNORECASE)
# Regex for read command: "what is my <attr>" or "my <attr>"
REGEX_READ = re.compile(r"(what is my|my) (?P<attribute>[a-z0-9_]+)", re.IGNORECASE)

def run(percept):
    text = percept["text"].strip()
    
    # Check for write
    write_match = REGEX_WRITE.match(text)
    if write_match:
        attr = write_match.group("attribute").lower()
        val = write_match.group("value").lower()
        
        # Construct canonical key
        # Assuming user_id is fixed for Stage-0 single user
        key = f"user/profile/user_123/{attr}"
        
        result = semantic.put_sem(key, val, source="agent:profile_agent")
        
        if result["success"]:
            return structures.create_agent_output(
                agent_id="profile_agent",
                text=f"Stored {attr} = {val}",
                confidence=1.0,
                reasoning_trace=f"Parsed write intent for '{attr}'. Stored value '{val}' in SEM."
            )
        else:
            return structures.create_agent_output(
                agent_id="profile_agent",
                text="I tried to store this, but my memory backend failed. I may not remember this next time.",
                confidence=0.0,
                reasoning_trace=f"Failed to write to SEM: {result.get('error', 'unknown error')}"
            )

    # Check for read
    read_match = REGEX_READ.search(text)
    if read_match:
        attr = read_match.group("attribute").lower()
        key = f"user/profile/user_123/{attr}"
        
        result = semantic.get_sem(key)
        
        if result["exists"]:
            val = result["value"]
            return structures.create_agent_output(
                agent_id="profile_agent",
                text=str(val),
                confidence=1.0,
                reasoning_trace=f"Parsed read intent for '{attr}'. Found value in SEM."
            )
        else:
            return structures.create_agent_output(
                agent_id="profile_agent",
                text="I don’t have this information stored yet.",
                confidence=1.0,
                reasoning_trace=f"Parsed read intent for '{attr}'. SEM miss."
            )
            
    # Fallback if regex matched in router but not here (shouldn't happen if regexes align)
    return structures.create_agent_output(
        agent_id="profile_agent",
        text="I don't understand that profile request.",
        confidence=0.0,
        reasoning_trace="No regex match in agent."
    )
