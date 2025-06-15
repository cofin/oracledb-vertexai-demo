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

from litestar.plugins.htmx import HTMXPlugin
from litestar.plugins.structlog import StructlogPlugin
from litestar_granian import GranianPlugin
from litestar_oracledb import OracleDatabasePlugin

from app import config
from app.lib.settings import get_settings
from app.server.core import ApplicationCore

settings = get_settings()
app_config = ApplicationCore()
oracle = OracleDatabasePlugin(config=config.oracle_async)
granian = GranianPlugin()
structlog = StructlogPlugin(config=config.log)
htmx = HTMXPlugin()
