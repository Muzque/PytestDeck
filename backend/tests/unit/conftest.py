import os
import sys

# Ensure src/ is at sys.path[0] and src/test_deck/ is at sys.path[1]
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
test_deck_src = os.path.join(src_path, "test_deck")

for p in (test_deck_src, src_path):
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

for pkg in ("api_deck", "test_deck", "app"):
    mod = sys.modules.get(pkg)
    mod_file = getattr(mod, "__file__", None) or ""
    if mod is not None and not mod_file.startswith(src_path):
        sys.modules.pop(pkg, None)
