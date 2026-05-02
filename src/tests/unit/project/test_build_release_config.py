# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin build and release packaging configuration."""

from __future__ import annotations

import tomllib
from json import loads

from tests.support.paths import PROJECT_ROOT

PYPROJECT = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
PACKAGE_JSON = loads((PROJECT_ROOT / "package.json").read_text())
RELEASE_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
CI_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
ONEFILE_SCRIPT = PROJECT_ROOT / "tools" / "scripts" / "build-onefile-package.sh"
BUNDLER = PROJECT_ROOT / "tools" / "bundler.py"
MAKEFILE = PROJECT_ROOT / "Makefile"
RELEASE_DOCKERFILE = PROJECT_ROOT / "tools" / "deploy" / "docker" / "Dockerfile"
LEGACY_DOCKER_RUN_DIR = PROJECT_ROOT / "tools" / "deploy" / "docker" / "run"
DOCKERIGNORE = PROJECT_ROOT / ".dockerignore"


def test_project_metadata_declares_python_314_support() -> None:
    project = PYPROJECT["project"]

    assert project["requires-python"] == ">=3.11,<3.15"
    assert "Programming Language :: Python :: 3.14" in project["classifiers"]


def test_pyapp_uses_custom_dma_style_builder() -> None:
    assert "pyapp" not in PYPROJECT["tool"]

    script = ONEFILE_SCRIPT.read_text()
    assert 'PYAPP_VERSION="v0.29.0"' in script
    assert 'PYAPP_BUILD_PYTHON="cpython-3.13.12-linux-x86_64-gnu"' in script
    assert 'PYAPP_BUILD_PYTHON="cpython-3.13.12-linux-aarch64-gnu"' in script
    assert 'PYAPP_BUILD_TARGET="x86_64-unknown-linux-gnu"' in script
    assert 'PYAPP_BUILD_TARGET="aarch64-unknown-linux-gnu"' in script
    assert 'PYAPP_PYTHON_VERSION="3.13"' in script
    assert 'PYAPP_EXEC_SPEC="app.__main__:run_cli"' in script
    assert 'PYAPP_SKIP_INSTALL="true"' in script
    assert '--target "${PYAPP_BUILD_TARGET}"' in script
    assert '--install-root "~/.config"' in script
    assert '--project-name "cymbal-coffee"' in script
    assert '--python-version "3.13"' in script
    assert "dist/python-dist-${PYAPP_BUILD_TARGET}.tar.gz" in script
    assert "tools/bundler.py build" in script
    assert 'cargo zigbuild --release --target "${PYAPP_BUILD_TARGET}.2.17"' in script
    assert "cargo-zigbuild is required for Linux onefile builds" in script
    assert "uvx pyapp build" not in script

    makefile = MAKEFILE.read_text()
    assert "PYAPP_BUILD_PYTHON ?= cpython-3.13.12-linux-x86_64-gnu" in makefile
    assert "PYAPP_BUILD_TARGET ?=" in makefile
    assert 'UV_PYTHON="$(PYAPP_BUILD_PYTHON)" $(MAKE) build-wheel' in makefile
    assert 'PYAPP_BUILD_TARGET="$(PYAPP_BUILD_TARGET)"' in makefile


def test_pyapp_bundler_patches_install_dir_to_xdg_config() -> None:
    source = BUNDLER.read_text()

    assert "Bundle Python dependencies into a standalone distribution for PyApp." in source
    assert 'DEFAULT_PYTHON_VERSION = "3.13"' in source
    assert "cpython-3.13.13%2B20260414-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz" in source
    assert ".config" in source
    assert ".config_dir()" in source
    assert "patch_pyapp_install_dir" in source


def test_release_dockerfile_wraps_onefile_distribution() -> None:
    dockerfile = RELEASE_DOCKERFILE.read_text()

    assert "ARG PYTHON_VERSION=3.13" in dockerfile
    assert "ARG RUN_IMAGE=gcr.io/distroless/cc-debian12:nonroot" in dockerfile
    assert "FROM ${BUILDER_IMAGE} AS prep" in dockerfile
    assert "COPY tools/scripts/install_oracle_client.sh /tmp/" in dockerfile
    assert "COPY dist/coffee-${TARGETARCH}-linux-gnu /app/bin/coffee" in dockerfile
    assert "TNS_ADMIN=/app/wallet" in dockerfile
    assert "WALLET_LOCATION=/app/wallet" in dockerfile
    assert "RUN /app/bin/coffee upgrade --help" in dockerfile
    assert "COPY --from=prep --chown=65532:65532 /app/.config/cymbal-coffee /app/.config/cymbal-coffee" in dockerfile
    assert "COPY --from=prep --chown=65532:65532 /app/wallet /app/wallet" in dockerfile
    assert 'VOLUME ["/app/wallet"]' in dockerfile
    assert 'ENTRYPOINT ["/usr/local/bin/tini", "--", "coffee"]' in dockerfile
    assert not LEGACY_DOCKER_RUN_DIR.exists()


def test_makefile_can_build_distroless_onefile_container() -> None:
    makefile = MAKEFILE.read_text()

    assert ".PHONY: build-onefile-container" in makefile
    assert "build-onefile-container: build-onefile" in makefile
    assert "tools/deploy/docker/Dockerfile" in makefile
    assert "tools/deploy/docker/run" not in makefile
    assert "dist/coffee-$(ARCH)-linux-gnu" in makefile
    assert "--build-arg TARGETARCH=$(ARCH)" in makefile
    assert "-t cymbal-coffee:latest" in makefile

    dockerignore = DOCKERIGNORE.read_text()
    assert "dist/*" in dockerignore
    assert "!dist/coffee-amd64-linux-gnu" in dockerignore
    assert "!dist/coffee-arm64-linux-gnu" in dockerignore


def test_build_dependency_group_is_release_tooling_only() -> None:
    build_group = PYPROJECT["dependency-groups"]["build"]

    assert set(build_group) == {"bump-my-version"}


def test_package_json_version_mirrors_python_project_version() -> None:
    assert PACKAGE_JSON["version"] == PYPROJECT["project"]["version"] == "0.2.0"


def test_bumpversion_updates_only_package_metadata() -> None:
    bumpversion = PYPROJECT["tool"]["bumpversion"]

    assert bumpversion["current_version"] == "0.2.0"
    assert bumpversion["tag"] is True
    assert bumpversion["tag_name"] == "v{new_version}"
    assert bumpversion["commit"] is True

    files = {file_config["filename"]: file_config for file_config in bumpversion["files"]}
    assert set(files) == {"pyproject.toml", "package.json"}
    assert files["pyproject.toml"]["search"] == 'version = "{current_version}"'
    assert files["package.json"]["search"] == '"version": "{current_version}"'


def test_release_workflow_builds_assets_for_release_matrix() -> None:
    workflow = RELEASE_WORKFLOW.read_text()

    assert "tags:" in workflow
    assert "- 'v*'" in workflow
    assert "contents: write" in workflow
    assert "astral-sh/setup-uv" in workflow
    assert "uv python install cpython-3.13.12-linux-x86_64-gnu" in workflow
    assert "uv sync --python cpython-3.13.12-linux-x86_64-gnu --group build" in workflow
    assert "mlugg/setup-zig@v2" in workflow
    assert "cargo install cargo-zigbuild --locked" in workflow
    assert "uv run python manage.py assets install" in workflow
    assert "uv run python manage.py assets build" in workflow
    assert "uv build" in workflow
    assert "make build-onefile" in workflow
    assert "build-python-package:" in workflow
    assert "build-release-artifacts:" in workflow
    assert "create-release:" in workflow
    assert "runner: ubuntu-24.04" in workflow
    assert "runner: ubuntu-24.04-arm" in workflow
    assert "python-version: cpython-3.13.12-linux-aarch64-gnu" in workflow
    assert "rust-target: x86_64-unknown-linux-gnu" in workflow
    assert "rust-target: aarch64-unknown-linux-gnu" in workflow
    assert "docker-arch: amd64" in workflow
    assert "docker-arch: arm64" in workflow
    assert "onefile-asset: dist/coffee-linux-x86_64" in workflow
    assert "onefile-asset: dist/coffee-linux-aarch64" in workflow
    assert "container-asset: dist/coffee-image-amd64.tar" in workflow
    assert "container-asset: dist/coffee-image-arm64.tar" in workflow
    assert "container-image: cymbal-coffee:release-amd64" in workflow
    assert "container-image: cymbal-coffee:release-arm64" in workflow
    assert "PYAPP_BUILD_TARGET: ${{ matrix.rust-target }}" in workflow
    assert 'install -m 755 dist/coffee "${{ matrix.onefile-asset }}"' in workflow
    assert "dist/coffee-${{ matrix.docker-arch }}-linux-gnu" in workflow
    assert 'test -s "${{ matrix.onefile-asset }}"' in workflow
    assert 'sha256sum "${{ matrix.onefile-asset }}" > "${{ matrix.onefile-asset }}.sha256"' in workflow
    assert "docker/setup-buildx-action@v4" in workflow
    assert 'docker buildx build --load --platform "linux/${{ matrix.docker-arch }}"' in workflow
    assert "tools/deploy/docker/Dockerfile" in workflow
    assert "tools/deploy/docker/run" not in workflow
    assert "Dockerfile.canonical" not in workflow
    assert "Dockerfile.distroless" not in workflow
    assert 'docker run --rm "${{ matrix.container-image }}" upgrade --help' in workflow
    assert 'docker save "${{ matrix.container-image }}" -o "${{ matrix.container-asset }}"' in workflow
    assert 'test -s "${{ matrix.container-asset }}"' in workflow
    assert 'sha256sum "${{ matrix.container-asset }}" > "${{ matrix.container-asset }}.sha256"' in workflow


def test_release_workflow_publishes_release_artifacts() -> None:
    workflow = RELEASE_WORKFLOW.read_text()

    assert "actions/upload-artifact@v4" in workflow
    assert "actions/download-artifact@v4" in workflow
    assert "merge-multiple: true" in workflow
    assert "dist/app-*.whl" in workflow
    assert "dist/app-*.tar.gz" in workflow
    assert "dist/coffee-linux-x86_64" in workflow
    assert "dist/coffee-linux-x86_64.sha256" in workflow
    assert "dist/coffee-linux-aarch64" in workflow
    assert "dist/coffee-linux-aarch64.sha256" in workflow
    assert "dist/coffee-image-amd64.tar" in workflow
    assert "dist/coffee-image-amd64.tar.sha256" in workflow
    assert "dist/coffee-image-arm64.tar" in workflow
    assert "dist/coffee-image-arm64.tar.sha256" in workflow
    assert "softprops/action-gh-release@v2" in workflow
    assert "fail_on_unmatched_files: true" in workflow


def test_ci_runs_python_314_matrix() -> None:
    workflow = CI_WORKFLOW.read_text()

    assert "python-version:" in workflow
    assert "runs-on: ${{ matrix.runner }}" in workflow
    assert 'python-label: "3.13 x86_64"' in workflow
    assert '"cpython-3.13.12-linux-x86_64-gnu"' in workflow
    assert 'python-label: "3.14 x86_64"' in workflow
    assert '"cpython-3.14.3-linux-x86_64-gnu"' in workflow
    assert 'python-label: "3.13 arm64"' in workflow
    assert 'python-label: "3.14 arm64"' in workflow
    assert '"cpython-3.13.12-linux-aarch64-gnu"' in workflow
    assert '"cpython-3.14.3-linux-aarch64-gnu"' in workflow
    assert "runner: ubuntu-24.04" in workflow
    assert "runner: ubuntu-24.04-arm" in workflow
    assert "uv python install" in workflow
    assert "uv run pytest src/tests/unit" in workflow
    assert "uv build" in workflow
