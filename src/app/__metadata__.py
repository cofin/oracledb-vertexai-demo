# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
