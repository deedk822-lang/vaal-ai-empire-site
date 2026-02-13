"""Pytest configuration for agents tests."""

from importlib.util import find_spec
from pathlib import Path
import sys
import types

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


if find_spec("dotenv") is None:
    dotenv_stub = types.ModuleType("dotenv")

    def load_dotenv(*_args, **_kwargs):
        return False

    dotenv_stub.load_dotenv = load_dotenv
    sys.modules["dotenv"] = dotenv_stub


if find_spec("openai") is None:
    openai_stub = types.ModuleType("openai")

    class OpenAI:  # pragma: no cover - import fallback for test envs
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    openai_stub.OpenAI = OpenAI
    sys.modules["openai"] = openai_stub
