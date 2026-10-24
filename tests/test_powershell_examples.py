"""Execute PowerShell safety examples against harmless, isolated effects."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SHELL = shutil.which('pwsh') or shutil.which('powershell')
SOURCE = Path(__file__).resolve().parents[1] / 'skills/code-craft/references/powershell.md'


def powershell_blocks():
    return re.findall(r'```powershell\n(.*?)\n\s*```',
                      SOURCE.read_text(encoding='utf-8'), re.DOTALL)


@unittest.skipUnless(SHELL, 'PowerShell is unavailable on this test host')
class NativeFailureExampleTest(unittest.TestCase):
    def test_whatif_suppresses_the_documented_effect_and_guard_mutation_does_not(self):
        examples = [block for block in powershell_blocks() if 'function Set-FileText' in block]
        self.assertEqual(len(examples), 1)
        guard = "$PSCmdlet.ShouldProcess($LiteralPath, 'Write file text')"
        self.assertIn(guard, examples[0])
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / 'should-process.ps1'
            for mode, whatif, remove_guard in (
                ('apply', False, False), ('preview', True, False), ('mutated', True, True)
            ):
                with self.subTest(mode=mode):
                    target = Path(temporary) / f'{mode}.txt'
                    literal = str(target).replace("'", "''")
                    body = examples[0].replace(guard, '$true') if remove_guard else examples[0]
                    invoke = f"Set-FileText -LiteralPath '{literal}' -Value 'changed'"
                    invoke += ' -WhatIf' if whatif else ' -Confirm:$false'
                    script.write_text(body + '\n' + invoke, encoding='utf-8-sig')
                    result = subprocess.run(
                        [SHELL, '-NoProfile', '-NonInteractive', '-File', str(script)],
                        capture_output=True, text=True, timeout=30,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(target.exists(), not whatif or remove_guard)
                    if target.exists():
                        self.assertEqual(target.read_text(encoding='utf-8-sig'), 'changed')

    def test_native_failure_prevents_dependent_step(self):
        """Exercise the actual Markdown example with a harmless failing native executable."""
        examples = [
            block for block in powershell_blocks() if '$commandExit = $LASTEXITCODE' in block
        ]
        self.assertEqual(len(examples), 1)
        python = sys.executable.replace("'", "''")
        command = f"& '{python}' -c 'import sys; sys.exit(7)'"
        self.assertIn('& docker version', examples[0])
        recipe = examples[0].replace('& docker version', command)
        marker = "Write-Output 'DEPENDENT_RAN'"
        # Stop alone does not catch a native failure; the explicit exit check must make the
        # difference. Disable the newer optional behavior so this also exercises the 5.1 path.
        setup = (
            "$ErrorActionPreference = 'Stop'\n"
            "$PSNativeCommandUseErrorActionPreference = $false\n"
        )
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
