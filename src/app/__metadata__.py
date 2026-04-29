# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Metadata for the Project."""

import importlib.metadata
import tomllib
from pathlib import Path

__all__ = ("__project__", "__version__")


def _load_metadata() -> tuple[str, str]:
    try:
        project = importlib.metadata.metadata("app")
    except importlib.metadata.PackageNotFoundError:
        pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        with pyproject_path.open("rb") as pyproject_file:
            project = tomllib.load(pyproject_file)["project"]
        return project["name"], project["version"]
    return project["Name"], importlib.metadata.version("app")


__project__, __version__ = _load_metadata()
"""Version of the project."""
"""Name of the project."""
