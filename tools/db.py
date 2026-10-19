"""Shared WRDS connection helper: reads the username from ~/.pgpass (never the password)."""
import os, wrds

KEEPALIVE = {"sslmode": "require", "keepalives": 1, "keepalives_idle": 60, "keepalives_interval": 30, "keepalives_count": 10}

def connect(keepalive=False):
    user = None
    with open(os.path.expanduser("~/.pgpass")) as f:
        for line in f:
            parts = line.strip().split(":")
            if len(parts) >= 5 and "wrds" in parts[0]:
                user = parts[3]; break
    if keepalive:  # TCP keepalives so long server-side queries do not drop the idle SSL connection
        return wrds.Connection(wrds_username=user, wrds_connect_args=dict(KEEPALIVE, application_name="software-job-postings"))
    return wrds.Connection(wrds_username=user)
