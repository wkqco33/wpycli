from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from pathlib import Path


def atomic_write_files(files: Mapping[Path, str]) -> None:
    """Write multiple text files together and restore originals on failure."""
    if not files:
        return

    originals = {path: path.read_bytes() if path.exists() else None for path in files}
    temporary_paths: dict[Path, Path] = {}
    try:
        for path, content in files.items():
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                delete=False,
            ) as temporary:
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
            os.chmod(temporary_path, mode)
            temporary_paths[path] = temporary_path

        for path, temporary_path in temporary_paths.items():
            os.replace(temporary_path, path)
    except OSError:
        for path, original in originals.items():
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original)
        raise
    finally:
        for temporary_path in temporary_paths.values():
            temporary_path.unlink(missing_ok=True)
