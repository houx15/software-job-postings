"""Shared WRDS connection helper: reads the username from ~/.pgpass (never the password)."""
import os, wrds

def connect():
    user = None
    with open(os.path.expanduser("~/.pgpass")) as f:
        for line in f:
            parts = line.strip().split(":")
            if len(parts) >= 5 and "wrds" in parts[0]:
                user = parts[3]; break
    return wrds.Connection(wrds_username=user)
