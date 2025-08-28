from typing import TypedDict, Optional, Dict, Any, List, Sequence, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    send_to: Optional[str]
    ground_truth: str
    
__all__ = ["State"]