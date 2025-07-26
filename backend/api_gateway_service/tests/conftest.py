import sys
import os

os.environ["TESTING"] = "true"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
