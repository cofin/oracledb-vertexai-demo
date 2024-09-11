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

from litestar.plugins.flash import FlashConfig, FlashPlugin
from litestar.plugins.sqlalchemy import SQLAlchemyPlugin
from litestar.plugins.structlog import StructlogPlugin
from litestar_granian import GranianPlugin
from litestar_oracledb import OracleDatabasePlugin
from litestar_vite import VitePlugin
from litestar_vite.inertia import InertiaPlugin

from app.config import app as config
from app.config import get_settings
from app.server.builder import ApplicationConfigurator

settings = get_settings()
app_config = ApplicationConfigurator()
vite = VitePlugin(config=config.vite)
oracle = OracleDatabasePlugin(config=config.oracle)
granian = GranianPlugin()
flasher = FlashPlugin(config=FlashConfig(template_config=vite.template_config))
inertia = InertiaPlugin(config=config.inertia)
alchemy = SQLAlchemyPlugin(config=config.alchemy)
structlog = StructlogPlugin(config=config.log)
