"""
AtomAgent Manager implementation.

This agent is responsible for processing high-level descriptions and
managing the coordination between other specialized agents.
"""
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
import tempfile
import subprocess
import sys
import langchain_core.tools as tools
save_msg = None

class Response(BaseModel):
    content: str = Field(..., description="The content of the response")
    END: bool = False

@tools.tool
def code_runner(code: str) -> Dict[str, Any]:
    """
    Execute the generated Python code in a safe, isolated environment.

    Args:
        code: The Python code to execute as a string.

    Returns:
        Dictionary with execution results including stdout, stderr, and exit code.
    """
    print('** Running code **')
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=True) as tmp_file:
        # Write code to temporary file
        tmp_file.write(code)
        tmp_file.flush()

        # Run the code using subprocess in a separate process
        try:
            result = subprocess.run(
                [sys.executable, tmp_file.name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,  # Prevent infinite loops, adjust timeout as needed
                text=True
            )

            return {
                "code": code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "code": code,
                "stdout": "",
                "stderr": "Execution timed out after 30 seconds.",
                "returncode": -1
            }

        except Exception as e:
            return {
                "code": code,
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "returncode": -1
            }

class Manager(BaseModel):
    """
    Manager should be used to act as manager, its role is to transform the more1 
    """
    
    __name__: str = "Manager"
    llm: ChatOpenAI = None
    prompt :str = None
    n_jobs: int = 0
    

    class Config:
        arbitrary_types_allowed = True
        
        
    def __init__(self,domain='Mechanics',**kwargs):

        super().__init__(**kwargs)
        self.prompt = f'''You are act as a manager agent for solving promblem of in the domain of {domain}, When reeive the question, you will analyze all the content including the question and image content.\n When first receive the question with various format. You will express the question in plain text with all information first, for the solver agent; make sure the question is clear and understandable, good enough for solving the problem, if necessary, you can add some equations or formulas to help the solver agent to understand the question.
    When receive the answer from the solver agent, you will put the question and answer and intermediate procedure include the code together as the final answer in the markdown format, and mark as END.\n\n''' \
             

    
    def invoke(self, state:State):
        
        
        
        msgs = state.get('messages', [])
        message_template = ChatPromptTemplate.from_messages([
            ("system", self.prompt),
            MessagesPlaceholder("messages")
        ])
        prompt = message_template.format_prompt(messages=msgs)
        
        llm = self.llm.with_structured_output(Response)
        
        response = llm.invoke(prompt.to_messages())
        content = response.content

                # Update the state with the new message
        msgs.append(AIMessage(content=content, name= self.__name__))
        end = response.END
        return {
            'messages': msgs,
            'send_to': "NEXT" if not end else "END",
            'ground_truth': state.get('ground_truth', ''),
        }
    
    
    def __call__(self, *args, **kwds):
        return self.invoke(*args, **kwds)
    
    
    


class Solver(BaseModel):
    
    __name__: str = "Solver"
    llm: ChatOpenAI = None
    tools: List[BaseTool] = None
    tool_node: ToolNode = None
    prompt :str = None
    n_jobs: int = 0
    

    class Config:
        arbitrary_types_allowed = True
        
    def __init__(self,domain='Mechanics',**kwargs):
        super().__init__(**kwargs)
        self.prompt = f'You are act as a solver agent for solving promblem of in the domain of {domain}, When receive the question, you will think about the question first, then write the plan step by step, in each step, you will do the calculation or using code to solve the problem. If the problem is solved, you will write the final answer in the markdown format, and mark as END.\n\n' 
        self.tools = [code_runner]
        self.tool_node = ToolNode(self.tools)

    def plan(self, state:State):
        """
        Plan the steps to solve the problem based on the current state.
        """
        # Implement the planning logic here
        plan_prompt = 'If the plan is not prepared yet, you should write the step to step plan first, then working on the first step; else, you should work on the next step of the plan. If there is no more step, mark as END\n\n' 
        
        msgs = state.get('messages', [])
        
        message_template = ChatPromptTemplate.from_messages([
            ("system", self.prompt),
            ("system", plan_prompt),    
            MessagesPlaceholder("messages")
        ])
        
        llm = self.llm.with_structured_output(Response)
        
        messages = message_template.format_messages(messages=msgs)
        response = llm.invoke(messages)
        content = response.content
        end = response.END
        
        return {
            'messages': msgs + [AIMessage(content=content, name= self.__name__)],
            'send_to': "NEXT" if not end else "END",
            'ground_truth': state.get('ground_truth', ''),
        }
        
        
        
    
    def act(self, state:State) -> Union[AgentAction, AgentFinish]:
        """
        Act based on the current state and return an action or finish.
        """
        act_prompt = "Based on current state, you should act on the problem.\n\n"
        
        llm_with_tools = self.llm.bind_tools(self.tools)
        
        msg = state.get('messages', [])
        
        message_template = ChatPromptTemplate.from_messages([
            ("system", self.prompt),
            ("system", act_prompt),
            MessagesPlaceholder("messages")
        ])
        
        message = message_template.format_messages(messages=msg)
        response = llm_with_tools.invoke(message)
        response.name = self.__name__
        # print(response)
        return response
        
        
        
    def invoke(self, state:State):
        """
        Invoke the solver with the current state.
        """
        # plan first
        state = self.plan(state)
        
        end = state.get('send_to', '') == "END"
        
        while not end:
            msg = self.act(state)
            state['messages'].append(msg)
            if msg.tool_calls:
                res = self.tool_node.invoke({
                    'messages':[msg],
                })
                print(res)
                res = res['messages'][-1]
                res.name = self.__name__
                
                state['messages'].append(res)
                
            else:
                state['messages'].append(AIMessage(content=msg.content, name= self.__name__))
                
            state = self.plan(state)
            end = state.get('send_to', '') == "END"
        else:
            
            return state
                
    
    def __call__(self, *args, **kwargs):
        """
        Call the solver with the provided arguments.
        """
        return self.invoke(*args, **kwargs)
    
    
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