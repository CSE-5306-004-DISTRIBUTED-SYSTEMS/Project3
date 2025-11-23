"""Top-level package for the Python HTTP-based auction architecture."""

from importlib import metadata

__all__ = ["get_version"]


def get_version() -> str:
    """Return the distribution version if installed, otherwise a placeholder."""
    try:
        return metadata.version("distributed-online-auction-platform")
    except metadata.PackageNotFoundError:  # pragma: no cover - not installed as dist
        return "0.0.0-dev"
