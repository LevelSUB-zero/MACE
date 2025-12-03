#!/usr/bin/env python3
"""
Cleanup Preview Tool

Safely preview files that would be deleted/archived without making changes.

Usage:
    python tools/preview_cleanup.py --days 90
"""
import os
import time
import argparse
from pathlib import Path

def preview_cleanup(days_old=90, directories=None):
    """
    Preview files older than specified days.
    
    Args:
        days_old: Age threshold in days
        directories: List of directories to scan (default: logs, samples, archived)
    """
    if directories is None:
        directories = ["logs", "samples", "."]
    
    cutoff_time = time.time() - (days_old * 24 * 3600)
    candidates = []
    
    print(f"=== Cleanup Preview (files older than {days_old} days) ===\n")
    
    for directory in directories:
        if not os.path.exists(directory):
            continue
        
        for root, dirs, files in os.walk(directory):
            # Skip archived and .git
            if "archived" in root or ".git" in root:
                continue
            
            for filename in files:
                filepath = os.path.join(root, filename)
                
                try:
                    mtime = os.path.getmtime(filepath)
                    size = os.path.getsize(filepath)
                    
                    if mtime < cutoff_time:
                        age_days = (time.time() - mtime) / (24 * 3600)
                        candidates.append({
                            "path": filepath,
                            "size_kb": size / 1024,
                            "age_days": age_days
                        })
                except (OSError, IOError):
                    continue
    
   # Sort by age
    candidates.sort(key=lambda x: x["age_days"], reverse=True)
    
    # Report
    if not candidates:
        print("✅ No files older than {days_old} days found")
        return
    
    print(f"Found {len(candidates)} candidate files:\n")
    
    total_size = 0
    for i, item in enumerate(candidates[:20], 1):  # Show top 20
        print(f"{i}. {item['path']}")
        print(f"   Age: {item['age_days']:.0f} days, Size: {item['size_kb']:.1f} KB")
        total_size += item['size_kb']
    
    if len(candidates) > 20:
        print(f"\n... and {len(candidates) - 20} more files")
    
    print(f"\nTotal size: {total_size / 1024:.2f} MB")
    print(f"\n⚠️  This is a PREVIEW ONLY - no files deleted")
    print(f"To archive these files, run: ./tools/archive_old_files.sh")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preview cleanup candidates")
    parser.add_argument("--days", type=int, default=90, help="Age threshold in days")
    args = parser.parse_args()
    
    preview_cleanup(args.days)
