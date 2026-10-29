"""Deprecated entry point: the dashboard is now built by wealth_tracker.py.

Kept so `python build_dashboard.py` still works; it runs the full Trading Desk build.
"""
from wealth_tracker import main

if __name__ == "__main__":
    main()
