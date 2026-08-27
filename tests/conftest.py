import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_service(name: str, filename: str = "main.py"):
    path = ROOT / "services" / name / filename
    mod_name = f"reviva_{name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod
