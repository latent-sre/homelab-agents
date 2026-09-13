"""Import a script by path, keyed on the exact bytes of it and its siblings.

Validation imports the tree-under-validation's own scripts (the adapter generator, the
conformance schema), and the mutation suite validates about a hundred copies of this repository
in one process -- nearly all byte-identical, each previously paying compile+exec again. Keying
the cache on content keeps the reuse honest: mutated code hashes differently and gets a fresh
import, so the cache can never certify code it did not load.

The key covers every sibling `*.py` next to the script, not just the script itself: these
scripts import each other by paths derived from their own `__file__`, so a module cached on its
own bytes alone could be served for a tree whose DEPENDENCIES were mutated -- a false pass caught
in review. The cache is ONLY for scripts whose import binds no repository content beyond
`scripts/`; a script that globs fleet content into a module-level constant at import captures
state the byte key cannot see and must be imported fresh per tree.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from fleet import digest

_MODULES_BY_SOURCE: dict[tuple[str, str], ModuleType] = {}


def execute_source(source: Path, name: str, data: bytes | None = None) -> ModuleType | None:
    """Build a module by compiling the given bytes, bypassing bytecode caches.

    `SourceFileLoader.exec_module` trusts a `__pycache__` entry validated only by (mtime, size),
    so a same-size rewrite inside one timestamp tick would execute the PREVIOUS contents while a
    content digest describes the new ones (caught in review on #91). Compiling the buffer directly
    means what was hashed is exactly what runs -- which is why callers that hashed pass the SAME
    bytes rather than letting this function re-read a file that may have changed in between.
    """
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    code = compile(data if data is not None else source.read_bytes(), str(source), "exec")
    exec(code, module.__dict__)
    return module


def load_module_by_content(source: Path, name: str) -> ModuleType | None:
    """Import `source` as module `name`, reusing the module when the exact bytes were seen.

    Returns None when no import spec can be built (the caller owns that message); a module whose
    exec raises is never cached, so a broken script fails on every call, not just the first.
    """
    source = Path(source)
    parts: list[tuple[str, bytes]] = []
    source_bytes: bytes | None = None
    for sibling in sorted(source.parent.glob("*.py")):
        data = sibling.read_bytes()
        parts.append((sibling.name, data))
        if sibling == source:
            source_bytes = data
    if source_bytes is None:
        return None
    # Length-framed: bare concatenation lets bytes move across a file boundary and still hash
    # alike (caught in review on #91).
    key = (source.name, digest.framed_sha256(parts, domain=b"fleet-modules-v1"))
    module = _MODULES_BY_SOURCE.get(key)
    if module is None:
        module = execute_source(source, name, source_bytes)
        if module is None:
            return None
        _MODULES_BY_SOURCE[key] = module
    return module
