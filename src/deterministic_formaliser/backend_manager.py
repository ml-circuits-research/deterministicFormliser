from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from .schema import Document
from .adapters import get_adapter, BackendError

JSON_MARKER = "@@DFORM_JSON@@"
ERROR_MARKER = "@@DFORM_ERROR@@"


def project_root() -> Path:
    env = os.environ.get("DFORM_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    # src/deterministic_formaliser/backend_manager.py -> project root
    return Path(__file__).resolve().parents[2]


def _venv_python(parser: str, root: Path) -> Path | None:
    env_name = f"DFORM_{parser.upper()}_PYTHON"
    if os.environ.get(env_name):
        p = Path(os.environ[env_name]).expanduser()
        if not p.is_file():
            raise BackendError(f"Backend interpreter does not exist: {p}")
        return p
    unix = root / ".venvs" / parser / "bin" / "python"
    win = root / ".venvs" / parser / "Scripts" / "python.exe"
    if unix.exists():
        return unix
    if win.exists():
        return win
    return None


def parse_text(parser: str, text: str, lang: str = "en", *, backend_python: str | None = None, **kwargs: Any) -> Document:
    root = project_root()
    kwargs = dict(kwargs)
    kwargs["project_root"] = str(root)

    py = Path(backend_python).expanduser() if backend_python else _venv_python(parser, root)
    if py is not None:
        if not py.is_file():
            raise BackendError(f"Backend interpreter does not exist: {py}")
        runner = root / "scripts" / "backend_runner.py"
        if not runner.exists():
            raise BackendError(f"Backend runner missing: {runner}")
        cmd = [str(py), str(runner), "--parser", parser, "--lang", lang]
        if kwargs.get("spacy_model"):
            cmd += ["--spacy-model", str(kwargs["spacy_model"])]
        if kwargs.get("udpipe_model"):
            cmd += ["--udpipe-model", str(kwargs["udpipe_model"])]
        if kwargs.get("trankit_cache"):
            cmd += ["--trankit-cache", str(kwargs["trankit_cache"])]
        if kwargs.get("gpu"):
            cmd += ["--gpu"]
        p = subprocess.run(cmd, input=text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        payload = None
        error = None
        for line in p.stdout.splitlines():
            if line.startswith(JSON_MARKER):
                payload = line[len(JSON_MARKER):]
            elif line.startswith(ERROR_MARKER):
                error = line[len(ERROR_MARKER):]
        if payload and p.returncode == 0 and not error:
            return Document.from_dict(json.loads(payload))
        detail = error or p.stderr.strip() or p.stdout.strip() or f"backend exited with status {p.returncode}"
        raise BackendError(f"{parser} backend failed: {detail}")

    adapter = get_adapter(parser)
    return adapter.parse(text, lang=lang, **kwargs)
