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

from litestar import Controller, get
from litestar.response import File

from app.lib.settings import BASE_DIR


class SystemController(Controller):
    """System controller for root-level and un-grouped system routes."""

    @get(path="/favicon.ico", name="favicon", exclude_from_auth=True, include_in_schema=False)
    async def favicon(self) -> File:
        """Serve favicon with security headers."""
        return File(
            path=BASE_DIR.parents[2] / "src" / "js" / "public" / "favicon.ico",
            headers={"Cache-Control": "public, max-age=31536000", "X-Content-Type-Options": "nosniff"},
        )
