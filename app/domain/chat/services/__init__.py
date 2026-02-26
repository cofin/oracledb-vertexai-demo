from dishka import Provider, Scope, provide

from app.lib.di import QueryContext, query_id_var

from ._adk.runner import ADKRunner
from ._adk.tool_service import AgentToolsService
from ._intent import IntentService


class ChatServiceProvider(Provider):
    scope = Scope.REQUEST

    @provide(scope=Scope.APP)
    def get_adk_runner(self) -> ADKRunner:
        return ADKRunner()

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
)
