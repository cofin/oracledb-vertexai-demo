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

from sqlspec.adapters.oracledb import OracleAsyncConfig
from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore
from sqlspec.extensions.adk import SQLSpecSessionService

from app.lib.di import Provider, QueryContext, Scope, provide, query_id_var

from .adk import ADKRunner, AgentToolsService, IntentService


class ChatServiceProvider(Provider):
    scope = Scope.REQUEST

    @provide(scope=Scope.APP)
    def get_adk_store(self, config: OracleAsyncConfig) -> OracleAsyncADKStore:
        return OracleAsyncADKStore(config=config)

    @provide(scope=Scope.APP)
    def get_session_service(self, store: OracleAsyncADKStore) -> SQLSpecSessionService:
        return SQLSpecSessionService(store)

    @provide(scope=Scope.APP)
    def get_adk_runner(self, session_service: SQLSpecSessionService) -> ADKRunner:
        return ADKRunner(session_service=session_service)

    @provide
    def get_query_context(self) -> QueryContext | None:
        qid = query_id_var.get()
        if not qid:
            return None
        return QueryContext(query_id=qid)

    agent_tools_service = provide(AgentToolsService)
    intent_service = provide(IntentService)

__all__ = (
    "ADKRunner",
    "AgentToolsService",
    "ChatServiceProvider",
    "IntentService",
    "OracleAsyncADKStore",
    "SQLSpecSessionService",
)
