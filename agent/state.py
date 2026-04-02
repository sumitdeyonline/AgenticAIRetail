from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # The 'add_messages' ensures all messages are merged in a correct sequence
    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: str
    metadata: dict
