from dishka import Provider, Scope, provide
from sqlspec.adapters.oracledb import OracleAsyncConfig
from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore
from sqlspec.extensions.adk import SQLSpecSessionService

from app.lib.di import QueryContext, query_id_var

from ._adk.runner import ADKRunner
from ._adk.tool_service import AgentToolsService
from ._intent import IntentService


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
