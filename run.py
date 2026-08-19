"""
Root entrypoint for malloc-app repository.
Switches to memora/ and delegates to memora/run.py.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORA_DIR = os.path.join(BASE_DIR, "memora")

if os.path.exists(MEMORA_DIR):
    os.chdir(MEMORA_DIR)
    sys.path.insert(0, MEMORA_DIR)

import run

if __name__ == "__main__":
    run.main()
