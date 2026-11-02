import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ARCHITECT_DATA_DIR", tempfile.mkdtemp(prefix="architect-test-"))
os.environ["ARCHITECT_LLM"] = "none"
