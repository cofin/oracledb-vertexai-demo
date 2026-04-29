# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

import msgspec
from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict


class BaseStruct(msgspec.Struct):
    def to_dict(self) -> dict[str, Any]:
        from typing import cast
        return cast("dict[str, Any]", msgspec.to_builtins(self))


class CamelizedBaseStruct(BaseStruct, rename="camel"):
    """Camelized Base Struct"""


class Message(CamelizedBaseStruct):
    message: str


def camel_case(string: str) -> str:
    """Convert a string to camel case.

    Args:
        string (str): The string to convert

    Returns:
        str: The string converted to camel case
    """
    return "".join(word if index == 0 else word.capitalize() for index, word in enumerate(string.split("_")))


class BaseSchema(_BaseModel):
    """Base Settings."""

    model_config = ConfigDict(
        validate_assignment=True,
        from_attributes=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )


class CamelizedBaseSchema(BaseSchema):
    """Camelized Base pydantic schema."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=camel_case)
