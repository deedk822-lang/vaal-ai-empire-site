"""Pytest configuration for agents tests."""

 codex/remove-git-merge-artifacts-and-fix-echo-logic-1c2gbt

 codex/remove-git-merge-artifacts-and-fix-echo-logic-3nm2nb

 codex/remove-git-merge-artifacts-and-fix-echo-logic-blkxko
 merge/develop-to-main
 merge/develop-to-main
from importlib.util import find_spec
from pathlib import Path
import sys
import types

 codex/remove-git-merge-artifacts-and-fix-echo-logic-1c2gbt
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

 codex/remove-git-merge-artifacts-and-fix-echo-logic-3nm2nb
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pathlib import Path
import sys
 merge/develop-to-main

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
 codex/remove-git-merge-artifacts-and-fix-echo-logic-blkxko
 merge/develop-to-main
 merge/develop-to-main


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
 codex/remove-git-merge-artifacts-and-fix-echo-logic-1c2gbt

 codex/remove-git-merge-artifacts-and-fix-echo-logic-3nm2nb


 merge/develop-to-main
 merge/develop-to-main
 merge/develop-to-main
