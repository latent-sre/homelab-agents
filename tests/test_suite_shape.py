"""Every test module must load at least one test.

Risk hypothesis: `python -m unittest discover` reports only the aggregate count, so a module that
loses every test — a rename that breaks the `test_` prefix, an import guard that skips the class,
a file emptied by a bad merge — exits green while its coverage silently vanishes. The retired
parallel runner failed any module that ran zero tests; this keeps that tripwire without a runner.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent


class SuiteShapeTests(unittest.TestCase):
    def test_every_test_module_loads_at_least_one_test(self) -> None:
        modules = sorted(p for p in TESTS.glob("test_*.py") if p.name != Path(__file__).name)
        self.assertGreater(len(modules), 0, "no test modules found beside this file")
        loader = unittest.TestLoader()
        empty: list[str] = []
        for path in modules:
            suite = loader.loadTestsFromName(f"tests.{path.stem}")
            if suite.countTestCases() == 0:
                empty.append(path.name)
        self.assertEqual(
            [],
            empty,
            "test modules that load zero tests — a lost or misnamed test class passes the whole "
            f"suite silently: {empty}",
        )


class BareInterpreterTests(unittest.TestCase):
    """Every test module must still IMPORT without the optional dev group.

    `AGENTS.md` promises T0 and the full unittest suite run on a bare interpreter, with the dev
    group's tools skipping loudly. The suite-shape tripwire above cannot see a violation of that:
    it imports modules on a machine where the dev group IS installed. The phase-3 property tests
    broke the promise immediately -- `@given(st.text())` evaluates its argument while the class
    body runs, so the `st = None` fallback raised AttributeError at import and took the whole
    suite down before any skip could act (Codex, PR #190). A module-level import is the only
    thing that catches it, so this runs one.
    """

    OPTIONAL = ("hypothesis", "yaml")

    def test_every_test_module_imports_without_the_dev_group(self) -> None:
        import builtins
        import importlib

        modules = sorted(
            f"tests.{path.stem}"
            for path in (Path(__file__).parent).glob("test_*.py")
        )
        self.assertGreater(len(modules), 1, "discovery found no test modules to check")

        real_import = builtins.__import__

        def refuse_optional(name, *args, **kwargs):
            if name.split(".")[0] in self.OPTIONAL:
                raise ImportError(f"No module named {name!r}")
            return real_import(name, *args, **kwargs)

        for name in modules:
            with self.subTest(module=name):
                # Purge the module under test, the shim module it imports, and the optional
                # packages themselves. Blocking `__import__` while leaving an already-imported
                # hypothesis in sys.modules does not simulate absence -- it half-breaks a live
                # package, and `tests.support` keeps the real strategies it bound at first
                # import. Both make this test lie, in opposite directions.
                purge = [name, "tests.support", *self.OPTIONAL]
                saved = {
                    key: value
                    for key, value in sys.modules.items()
                    if key in purge or key.split(".")[0] in self.OPTIONAL
                }
                for key in list(saved):
                    sys.modules.pop(key, None)
                builtins.__import__ = refuse_optional
                try:
                    importlib.import_module(name)
                except ImportError as exc:  # pragma: no cover - the failure this test reports
                    self.fail(
                        f"{name} cannot be imported without the dev group ({exc}). A property "
                        f"test's decorators are constructed at class-definition time; use the "
                        f"stubs in tests.support rather than a None placeholder."
                    )
                finally:
                    builtins.__import__ = real_import
                    for key in [k for k in sys.modules if k in purge]:
                        sys.modules.pop(key, None)
                    sys.modules.update(saved)


if __name__ == "__main__":
    unittest.main()
