"""A failed native process must stop the documented dependent-step recipe."""
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


SHELL = shutil.which('pwsh') or shutil.which('powershell')
SOURCE = Path(__file__).resolve().parents[1] / 'skills/code-craft/references/powershell.md'


@unittest.skipUnless(SHELL, 'PowerShell is unavailable on this test host')
class NativeFailureExampleTest(unittest.TestCase):
    def test_native_failure_prevents_dependent_step(self):
        """Exercise the actual Markdown example with a harmless failing native executable."""
        blocks = re.findall(r'```powershell\n(.*?)\n\s*```',
                            SOURCE.read_text(encoding='utf-8'), re.DOTALL)
        examples = [block for block in blocks if '$commandExit = $LASTEXITCODE' in block]
        self.assertEqual(len(examples), 1)
        python = sys.executable.replace("'", "''")
        command = f"& '{python}' -c 'import sys; sys.exit(7)'"
        self.assertIn('& docker version', examples[0])
        recipe = examples[0].replace('& docker version', command)
        marker = "Write-Output 'DEPENDENT_RAN'"
        # Stop alone does not catch a native failure; the explicit exit check must make the
        # difference. Disable the newer optional behavior so this also exercises the 5.1 path.
        setup = "$ErrorActionPreference = 'Stop'\n$PSNativeCommandUseErrorActionPreference = $false\n"
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / 'native-failure.ps1'
            for body, guarded in ((command, False), (recipe, True)):
                with self.subTest(guarded=guarded):
                    script.write_text(setup + body + '\n' + marker, encoding='utf-8-sig')
                    result = subprocess.run(
                        [SHELL, '-NoProfile', '-NonInteractive', '-File', str(script)],
                        capture_output=True, text=True, timeout=30,
                    )
                    if guarded:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertNotIn('DEPENDENT_RAN', result.stdout)
                        self.assertIn('exit code 7', result.stderr)
                    else:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn('DEPENDENT_RAN', result.stdout)


if __name__ == '__main__':
    unittest.main()
