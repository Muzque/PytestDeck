import os
import sys

# Ensure src/ and backend/ are in sys.path for integration tests
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
src_path = os.path.join(backend_path, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
