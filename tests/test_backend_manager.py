"""Protocol/isolation tests. These mocks do not stand in for live NLP validation."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from deterministic_formaliser.adapters import BackendError
from deterministic_formaliser.backend_manager import parse_text, JSON_MARKER


class BackendManagerTests(unittest.TestCase):
    def test_symlink_interpreter_still_runs_backend_process(self):
        with tempfile.TemporaryDirectory() as directory:
            interpreter = Path(directory) / "python"
            interpreter.symlink_to(sys.executable)
            output = JSON_MARKER + '{"parser":"udpipe","text":"","sentences":[]}'
            with patch("deterministic_formaliser.backend_manager.subprocess.run",
                       return_value=subprocess.CompletedProcess([], 0, output, "")) as run:
                parse_text("udpipe", "", backend_python=str(interpreter))
            self.assertEqual(run.call_args.args[0][0], str(interpreter))

    def test_missing_override_is_not_silently_ignored(self):
        with self.assertRaises(BackendError):
            parse_text("udpipe", "text", backend_python="/nonexistent/dform/python")
        with patch.dict(os.environ, {"DFORM_UDPIPE_PYTHON": "/nonexistent/dform/python"}):
            with self.assertRaises(BackendError):
                parse_text("udpipe", "text")

    def test_nonzero_exit_with_payload_is_failure(self):
        output = JSON_MARKER + '{"parser":"udpipe","sentences":[]}'
        with patch("deterministic_formaliser.backend_manager.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 1, output, "backend crashed")):
            with self.assertRaisesRegex(BackendError, "backend crashed"):
                parse_text("udpipe", "text", backend_python=sys.executable)
