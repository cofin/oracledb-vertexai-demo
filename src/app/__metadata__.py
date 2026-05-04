# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Metadata for the Project."""

from importlib.metadata import PackageNotFoundError, metadata, version

__all__ = ("__package_date__", "__project__", "__version__")

try:
    __version__ = version("app")
    __project__ = metadata("app")["Name"]
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.2.2"
    __project__ = "Cymbal Coffee"
finally:
    del version, PackageNotFoundError, metadata

__package_date__ = "2026-05-04T16:54:36Z"
