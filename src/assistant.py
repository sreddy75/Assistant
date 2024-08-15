import json
import os
from pathlib import Path
from typing import List, Optional, Union

import httpx
import psutil
from dotenv import load_dotenv
from typing import Union, Any
from pydantic import Field

from kr8.tools.code_tools import CodeTools
from kr8.assistant import Assistant
from kr8.embedder.sentence_transformer import SentenceTransformerEmbedder
from kr8.knowledge import AssistantKnowledge
from kr8.llm.offline_llm import OfflineLLM
from kr8.llm.ollama import Ollama
from kr8.llm.openai import OpenAIChat
from kr8.llm.anthropic import Claude
from kr8.storage.assistant.postgres import PgAssistantStorage
from kr8.tools.exa import ExaTools
from kr8.tools.pandas import PandasTools
from kr8.utils.log import logger
from kr8.vectordb.pgvector import PgVector2

from kr8.tools.yfinance import YFinanceTools
from team.data_analyst import EnhancedDataAnalyst
from team.financial_analyst import EnhancedFinancialAnalyst
from team.quality_analyst import EnhancedQualityAnalyst
from team.research_assistant import EnhancedResearchAssistant
from team.maintenance_engineer import EnhancedMaintenanceEngineer
from team.investment_assistant import EnhancedInvestmentAssistant
from team.company_analyst import EnhancedCompanyAnalyst
from team.code_assistant import CodeAssistant
from team.product_owner import EnhancedProductOwner
from team.business_analyst import EnhancedBusinessAnalyst
from config.client_config import get_client_name

load_dotenv()
client_name = get_client_name()         

db_url = os.getenv("DB_URL", "postgresql+psycopg://ai:ai@pgvector:5432/ai")
    
cwd = Path(__file__).parent.resolve()
scratch_dir = cwd.joinpath("scratch")
if not scratch_dir.exists():
    scratch_dir.mkdir(exist_ok=True, parents=True)

def load_assistant_instructions(client_name: str, user_nickname: str) -> dict:
    instructions_path = Path(f"src/config/themes/{client_name}/assistant_instructions.json")
    if not instructions_path.exists():
        raise FileNotFoundError(f"Instructions file not found at {instructions_path}")
    
    with open(instructions_path, 'r') as f:
        instructions_data = json.load(f)
    
    instructions_data['introduction'] = instructions_data['introduction'].replace('{user_nickname}', user_nickname)
    instructions_data['description'] = "\n".join(instructions_data['description']).replace('{client_name}', client_name)
    instructions_data['instructions'] = [instr.replace('{client_name}', client_name) for instr in instructions_data['instructions']]
    instructions_data['introduction'] = instructions_data['introduction'].replace('{client_name}', client_name)
    
    return instructions_data

def is_ollama_available() -> bool:
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    try:
        response = httpx.get(f"{ollama_url}/api/tags", timeout=5.0)
        return response.status_code == 200
    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        return False

def create_pandas_tools(user_id: Optional[int]) -> PandasTools:
    return PandasTools(user_id=user_id)

def get_llm(llm_id: str, fallback_model: str):
    if llm_id in ["llama3"]:
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        try:
            return Ollama(
                model=llm_id,
                base_url=ollama_base_url,
                options={
                    "num_ctx": 4096, 
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            )
        except Exception as e:
            logger.warning(f"Failed to initialize {llm_id}: {e}")
            logger.info(f"Attempting to fall back to {fallback_model}")
            try:
                return Ollama(
                    model=fallback_model,
                    base_url=ollama_base_url,
                    options={"num_ctx": 1024, "temperature": 0.7, "top_p": 0.9}
                )
            except Exception as fallback_error:
                logger.error(f"Failed to initialize Ollama with fallback model: {fallback_error}")
                logger.warning("Switching to offline mode")
                return OfflineLLM(model=fallback_model)
    elif llm_id == "claude-3.5":
        return Claude(model="claude-3-sonnet-20240229")
    elif llm_id == "gpt-4o":
        return OpenAIChat(model="gpt-4o")
    else:
        raise ValueError(f"Unknown LLM model: {llm_id}")

def log_system_resources():
    try:
        memory = psutil.virtual_memory()
        logger.info(f"Total memory: {memory.total / (1024**3):.2f} GiB")
        logger.info(f"Available memory: {memory.available / (1024**3):.2f} GiB")
        logger.info(f"Used memory: {memory.used / (1024**3):.2f} GiB")
        logger.info(f"Memory percent: {memory.percent}%")
        cpu_percent = psutil.cpu_percent(interval=1)
        logger.info(f"CPU usage: {cpu_percent}%")
    except ImportError:
        logger.warning("psutil not installed. System resource logging is disabled.")

def preprocess_query(query, current_project, current_project_type):
    if current_project and current_project_type:
        return f"In the context of the {current_project_type} project '{current_project}': {query}"
    return query

def add_context_reminder(messages, current_project, current_project_type):
    if current_project and current_project_type:
        reminder = f"Remember, we are discussing the {current_project_type} project named '{current_project}'. Only use information relevant to this project."
        messages.append({"role": "system", "content": reminder})
    return messages

def filter_results(results, current_project, current_project_type):
    if current_project and current_project_type:
        return [r for r in results if r.meta_data.get('project') == current_project and r.meta_data.get('type').startswith(current_project_type)]
    return results

def get_llm_os(
    llm_id: str = "gpt-4o",
    fallback_model: str = "tinyllama",    
    user_id: Optional[int] = None,
    user_role: Optional[str] = None,
    user_nickname: Optional[str] = "friend",
    run_id: Optional[str] = None,
    debug_mode: bool = True,
    web_search: bool = True,
) -> Union[Assistant, 'ContextAwareAssistant']:
    
    logger.info(f"-*- Creating {llm_id} LLM OS -*-")

    knowledge_base = AssistantKnowledge(
        vector_db=PgVector2(
            db_url=db_url,
            collection=f"user_{user_id}_documents" if user_id is not None else "llm_os_documents",
            embedder=SentenceTransformerEmbedder(model="all-MiniLM-L6-v2"),
        ),
        num_documents=50,
        user_id=user_id,
    )

    pandas_tools = create_pandas_tools(user_id)
    tools = [
        pandas_tools,    
        ExaTools(num_results=5, text_length_limit=2000),        
    ]    

    if web_search:
        tools.append(ExaTools(num_results=5, text_length_limit=2000))
            
    role_assistants = {
        "Dev": ["Web Search", "Code Assistant"],
        "QA": ["Web Search", "Enhanced Quality Analyst", "Business Analyst"],
        "Product": ["Web Search", "Product Owner", "Business Analyst", "Enhanced Data Analyst"],
        "Delivery": ["Web Search", "Business Analyst", "Enhanced Data Analyst"],
        "Manager": ["Web Search", "Code Assistant", "Product Owner", "Enhanced Financial Analyst", "Business Analyst", "Enhanced Data Analyst"]
    }

    available_assistants = role_assistants.get(user_role, [])
    
    team: List[Assistant] = []
    
    team_description = "Your team consists of:\n"
    for assistant in available_assistants:
        team_description += f"- {assistant}\n"
        
    llm = get_llm(llm_id, fallback_model)

    assistant_mapping = {
        "Enhanced Quality Analyst": EnhancedQualityAnalyst,
        "Business Analyst": EnhancedBusinessAnalyst,
        "Enhanced Data Analyst": EnhancedDataAnalyst,
        "Enhanced Financial Analyst": EnhancedFinancialAnalyst,
        "Product Owner": EnhancedProductOwner,
        "Web Search": ExaTools,
        "Code Assistant": CodeAssistant,
    }

    for assistant in available_assistants:
        if assistant in assistant_mapping:
            if assistant == "Web Search":
                tools.append(assistant_mapping[assistant](num_results=5, text_length_limit=2000))
            else:
                assistant_kwargs = {
                    "llm": llm,
                    "tools": [pandas_tools, ExaTools()] if assistant in ["Business Analyst", "Product Owner"] else [pandas_tools],
                    "debug_mode": debug_mode
                }
                if assistant == "Code Assistant":
                    assistant_kwargs["code_tools"] = CodeTools(knowledge_base=knowledge_base)
                else:
                    assistant_kwargs["knowledge_base"] = knowledge_base
                team.append(assistant_mapping[assistant](**assistant_kwargs))

    log_system_resources()        

    client_name = get_client_name()
    assistant_instructions = load_assistant_instructions(client_name, user_nickname)    
    
    if 'introduction' in assistant_instructions:
        assistant_instructions['introduction'] = assistant_instructions['introduction'].replace('{user_nickname}', user_nickname)

    # Add team description to instructions
    assistant_instructions['instructions'].append(f"\nYour current team:\n{team_description}")

    class ContextAwareAssistant(Assistant):
        current_project: Optional[str] = Field(default=None, description="Current project name")
        current_project_type: Optional[str] = Field(default=None, description="Current project type (react or java)")
        last_search_results: Optional[List[Any]] = Field(default=None, description="Last search results")

        def set_project_context(self, project_name: str, project_type: str):
            self.current_project = project_name
            self.current_project_type = project_type

        def run(self, query: str, stream: bool = False, **kwargs) -> Union[str, Any]:
            if self.current_project and self.current_project_type:
                preprocessed_query = preprocess_query(query, self.current_project, self.current_project_type)
                context_messages = add_context_reminder(kwargs.get('messages', []), self.current_project, self.current_project_type)
                kwargs['messages'] = context_messages
            else:
                preprocessed_query = query

            # Clear previous conversation history only for Claude
            if isinstance(self.llm, Claude):
                self.memory.clear()
                
            results = super().run(preprocessed_query, stream=stream, **kwargs)
            
            if self.knowledge_base and self.current_project and self.current_project_type:
                filtered_results = filter_results(self.knowledge_base.search(preprocessed_query), self.current_project, self.current_project_type)
                self.last_search_results = filtered_results

            return results

        def get_last_search_results(self) -> Optional[List[Any]]:
            return self.last_search_results

    # Determine whether to use ContextAwareAssistant or regular Assistant
    AssistantClass = ContextAwareAssistant if "Code Assistant" in available_assistants else Assistant

    llm_os = AssistantClass(
        name="llm_os",
        run_id=run_id,
        user_id=user_id,
        knowledge_base=knowledge_base,
        llm=llm,
        description=assistant_instructions['description'],
        instructions=assistant_instructions['instructions'],
        storage=PgAssistantStorage(table_name="llm_os_runs", db_url=db_url),        
        tools=tools,
        team=team,
        show_tool_calls=True,
        search_knowledge=True,
        read_chat_history=True,
        add_chat_history_to_messages=True,
        num_history_messages=6,
        markdown=True,
        add_datetime_to_instructions=True,
        introduction=assistant_instructions['introduction'],
        debug_mode=debug_mode,
    )
    return llm_os