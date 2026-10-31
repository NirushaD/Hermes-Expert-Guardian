import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import fastapi
        except ImportError:
            raise unittest.SkipTest("FastAPI unavailable outside Hermes; run using Hermes Python")
        path = Path(__file__).resolve().parents[1] / "dashboard" / "plugin_api.py"
        spec = importlib.util.spec_from_file_location("guardian_backend_test", path)
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    def test_empty_session_rejected(self):
        from fastapi import HTTPException
        with patch.object(self.module.integration, "create"), self.assertRaises(HTTPException):
            self.module.action({"action": "send", "session": ""})

    def test_model_controls_not_registered(self):
        # Only browser/backend routes expose egress and recovery authorization.
        from guardian.integration import register
        class Context:
            def __init__(self): self.hooks = []
            def register_hook(self, name, callback): self.hooks.append(name)
            def register_auxiliary_task(self, *args, **kwargs): pass
        ctx = Context()
        register(ctx)
        self.assertEqual(set(ctx.hooks), {"pre_tool_call", "post_tool_call", "pre_llm_call", "transform_tool_result"})

    def test_evidence_confirmation_required(self):
        from fastapi import HTTPException
        with patch.object(self.module.integration, "create") as create, self.assertRaises(HTTPException):
            self.module.action({"session": "s", "incident": "i", "action": "authorize"})
        create.return_value.authorize.assert_not_called()

