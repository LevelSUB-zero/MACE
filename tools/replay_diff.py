import sys
import json
import argparse
from mace.core import replay

def main():
    parser = argparse.ArgumentParser(description="Replay a log and show diffs.")
    parser.add_argument("logfile", help="Path to log file")
    args = parser.parse_args()
    
    try:
        with open(args.logfile, "r") as f:
            log_entry = json.load(f)
            
        print(f"Replaying log {log_entry['log_id']}...")
        replay.replay_log(log_entry)
        print("Replay successful. No mismatches.")
        
    except Exception as e:
        print(f"Replay failed: {e}")
        # If replay_debug.txt exists, print it
        if os.path.exists("replay_debug.txt"):
            print("\n--- DIFF DETAILS ---")
            with open("replay_debug.txt", "r") as f:
                print(f.read())
        sys.exit(1)

if __name__ == "__main__":
    import os
    main()
