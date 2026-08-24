# SPDX-License-Identifier: Apache-2.0

import re
import tomllib
from pathlib import Path


API_PROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _project_metadata() -> dict:
    return tomllib.loads(API_PROJECT.read_text(encoding="utf-8"))


def _dependency_name(requirement: str) -> str:
    return re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0].strip().lower()


def test_api_declares_core_runtime_dependency() -> None:
    dependencies = _project_metadata()["project"]["dependencies"]
    dependency_names = {_dependency_name(dependency) for dependency in dependencies}

    assert "maskingtape" in dependency_names


def test_api_dev_dependencies_are_unique() -> None:
    dev_dependencies = _project_metadata()["project"]["optional-dependencies"]["dev"]

    assert len(dev_dependencies) == len(set(dev_dependencies))
