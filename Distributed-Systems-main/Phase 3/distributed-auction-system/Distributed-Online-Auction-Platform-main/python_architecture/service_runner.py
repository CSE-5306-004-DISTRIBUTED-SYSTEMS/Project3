"""Container entrypoint for running individual Python services.

This helper reads the ``SERVICE`` environment variable that docker-compose
provides for each container, imports the corresponding service module, and
invokes its ``run`` or ``main`` callable.  Centralising the logic in this
module avoids relying on shell-style environment variable expansion inside the
Dockerfile command while keeping service modules focused on business logic.
"""

from __future__ import annotations

import importlib
import os
import sys
from types import ModuleType
from typing import Callable


def _resolve_entrypoint(module: ModuleType) -> Callable[[], None]:
    """Return an executable callable from *module*.

    Service modules expose either a ``run`` or ``main`` function.  We probe for
    both in a predictable order so existing modules continue to work without
    modification.
    """

    for attribute in ("run", "main"):
        candidate = getattr(module, attribute, None)
        if callable(candidate):
            return candidate  # type: ignore[return-value]
    raise AttributeError(
        f"Module {module.__name__} does not define a callable 'run' or 'main'"
    )


def main() -> None:
    """Module entrypoint executed by ``python -m``."""

    service = os.environ.get("SERVICE")
    if not service:
        print("SERVICE environment variable is required", file=sys.stderr)
        raise SystemExit(2)

    module_name = f"python_architecture.services.{service}.server"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        print(f"Unable to import {module_name}: {exc}", file=sys.stderr)
        raise SystemExit(3) from exc

    entrypoint = _resolve_entrypoint(module)
    entrypoint()


if __name__ == "__main__":
    main()

