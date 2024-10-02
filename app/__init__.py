# Copyright 2024 Google LLC
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

from __future__ import annotations

import multiprocessing
import platform


def run_cli() -> None:
    """Application Entrypoint."""

    if platform.system() == "Darwin":
        multiprocessing.set_start_method("fork", force=True)
    import os
    import sys
    from pathlib import Path

    current_path = Path(__file__).parent.parent.resolve()
    sys.path.append(str(current_path))
    os.environ.setdefault("LITESTAR_APP", "app.asgi:create_app")
    os.environ.setdefault("LITESTAR_APP_NAME", "Oracle23AI & Google VertexAI")
    try:
        from litestar.__main__ import run_cli as run_litestar_cli

    except ImportError as exc:
        print(  # noqa: T201
            "Could not load required libraries.  ",
            "Please check your installation and make sure you activated any necessary virtual environment",
        )
        print(exc)  # noqa: T201
        sys.exit(1)
    run_litestar_cli()


if __name__ == "__main__":
    run_cli()
