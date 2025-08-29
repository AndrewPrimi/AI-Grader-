import re
import json
from typing import Dict, List, Union, Tuple, Any, Optional,Sequence,Literal
from langchain.llms.base import BaseLLM
from langchain.schema import AgentAction, AgentFinish
from langchain.tools.base import BaseTool
from langchain.prompts import PromptTemplate
from langchain.prompts.base import BasePromptTemplate
from langchain.memory.buffer import ConversationBufferMemory
from pydantic import BaseModel, Field
from langchain_core.stores import BaseStore
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from uuid import uuid4
from langgraph.prebuilt import ToolNode
from .state import State

import langchain_core.tools as tools
save_msg = None




class Reviewer(BaseModel):
    
    __name__: str = "Reviewer"
    llm: ChatOpenAI = None
    prompt :str = None
    

    class Config:
        arbitrary_types_allowed = True
        
    def __init__(self,domain='Mechanics',**kwargs):
        super().__init__(**kwargs)
        self.prompt = f'You are act as a reviewer agent for solving promblem of in the domain of {domain}, When receive the question, you will review the answer from the solver agent, compared with the ground truth as reference answer, and evaluate the answer and give a score over 100 as maximum. Also give the scorring details.\n\n' 
        
        
        
    
    def invoke(self, state:State):
        """
        Invoke the reviewer with the current state.
        """
        msgs = state.get('messages', [])
        ground_truth = state.get('ground_truth', '')
        message_template = ChatPromptTemplate.from_messages([
            ("system", self.prompt),
            MessagesPlaceholder("messages"),
            ("human", "Ground Truth:\n\n{ground_truth}")
        ])
        
        prompt = message_template.format_prompt(messages=msgs, ground_truth=ground_truth)
        
        response = self.llm.invoke(prompt.to_messages())
        response.name = self.__name__
        state['messages'].append(response)
        
        return state
        
    def __call__(self, *args, **kwargs):
        """
        Call the reviewer with the provided arguments.
        """
        return self.invoke(*args, **kwargs)