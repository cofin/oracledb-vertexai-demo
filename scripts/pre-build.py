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

import argparse
import logging
import os
import platform
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Any

NODEENV_INSTALLED = find_spec("nodeenv") is not None

logger = logging.getLogger("pre-build")

PROJECT_ROOT = Path(__file__).parent.parent
NODEENV = "nodeenv"
DEFAULT_VENV_PATH = Path(PROJECT_ROOT / ".venv")


def manage_resources(setup_kwargs: Any) -> Any:
    # look for this in the environment and skip this function if it exists, sometimes building here is not needed, eg. when using nixpacks
    no_nodeenv = os.environ.get("LITESTAR_SKIP_NODEENV_INSTALL") is not None or NODEENV_INSTALLED is False
    build_assets = setup_kwargs.pop("build_assets", None)
    install_packages = setup_kwargs.pop("install_packages", None)
    kwargs: dict[str, Any] = {}
    if no_nodeenv:
        logger.info("skipping nodeenv configuration")
    else:
        found_in_local_venv = Path(DEFAULT_VENV_PATH / "bin" / NODEENV).exists()
        nodeenv_command = f"{DEFAULT_VENV_PATH}/bin/{NODEENV}" if found_in_local_venv else NODEENV
        install_dir = DEFAULT_VENV_PATH if found_in_local_venv else os.environ.get("VIRTUAL_ENV", sys.prefix)
        logger.info("Installing Node environment to %s:", install_dir)
        subprocess.run([nodeenv_command, install_dir, "--force", "--quiet"], **kwargs)  # noqa: PLW1510

    if platform.system() == "Windows":
        kwargs["shell"] = True
    if install_packages is not None:
        logger.info("Installing NPM packages.")
        subprocess.run(["npm", "install"], **kwargs)  # noqa: S607, PLW1510
    if build_assets is not None:
        logger.info("Building NPM static assets.")
        subprocess.run(["npm", "run", "build"], **kwargs)  # noqa: S607, PLW1510
    return setup_kwargs


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Manage Package Resources")
    parser.add_argument("--build-assets", action="store_true", help="Build assets for static hosting.", default=None)
    parser.add_argument("--install-packages", action="store_true", help="Install NPM packages.", default=None)
    args = parser.parse_args()
    setup_kwargs = {"build_assets": args.build_assets, "install_packages": args.install_packages}
    manage_resources(setup_kwargs)
