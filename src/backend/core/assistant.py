import json
import os
from pathlib import Path
from typing import List, Optional, Union

from fastapi import Depends
import httpx
import psutil
from dotenv import load_dotenv
from typing import Union, Any
from pydantic import Field
from sqlalchemy.orm import Session

from src.backend.kr8.tools.toolkit import Toolkit
from src.backend.kr8.tools.code_tools import CodeTools
from src.backend.kr8.assistant import Assistant
from src.backend.kr8.embedder.sentence_transformer import SentenceTransformerEmbedder
from src.backend.kr8.knowledge import AssistantKnowledge
from src.backend.kr8.llm.offline_llm import OfflineLLM
from src.backend.kr8.llm.ollama import Ollama
from src.backend.kr8.llm.openai import OpenAIChat
from src.backend.kr8.llm.anthropic import Claude
from src.backend.kr8.storage.assistant.postgres import PgAssistantStorage
from src.backend.kr8.tools.exa import ExaTools
from src.backend.kr8.tools.pandas import PandasTools
from src.backend.kr8.utils.log import logger
from src.backend.kr8.vectordb.pgvector import PgVector2

from src.backend.kr8.tools.yfinance import YFinanceTools
from src.backend.db.session import get_db 
from src.backend.utils.org_utils import load_org_config
from src.backend.kr8.assistant.team.data_analyst import EnhancedDataAnalyst
from src.backend.kr8.assistant.team.financial_analyst import EnhancedFinancialAnalyst
from src.backend.kr8.assistant.team.quality_analyst import EnhancedQualityAnalyst
from src.backend.kr8.assistant.team.research_assistant import EnhancedResearchAssistant
from src.backend.kr8.assistant.team.maintenance_engineer import EnhancedMaintenanceEngineer
from src.backend.kr8.assistant.team.investment_assistant import EnhancedInvestmentAssistant
from src.backend.kr8.assistant.team.company_analyst import EnhancedCompanyAnalyst
from src.backend.kr8.assistant.team.code_assistant import CodeAssistant
from src.backend.kr8.assistant.team.product_owner import EnhancedProductOwner
from src.backend.kr8.assistant.team.business_analyst import EnhancedBusinessAnalyst
from src.backend.kr8.assistant.team.call_center_assistant import CallCenterAssistant
from src.backend.kr8.assistant.team.project_management_assistant import ProjectManagementAssistant
from src.backend.models.models import Organization


from src.backend.core.client_config import get_client_name

load_dotenv()
client_name = get_client_name()         

db_url = os.getenv("DB_URL", "postgresql+psycopg://ai:ai@pgvector:5432/ai")
    
cwd = Path(__file__).parent.resolve()
scratch_dir = cwd.joinpath("scratch")
if not scratch_dir.exists():
    scratch_dir.mkdir(exist_ok=True, parents=True)

def load_assistant_instructions(client_name: str, user_nickname: str) -> dict:
    instructions_path = Path(f"src/backend/config/themes/{client_name}/instructions.json")
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
    if llm_id in ["llama3.1"]:
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
    org_id: Optional[int] = None,
    user_role: Optional[str] = None,
    user_nickname: Optional[str] = "friend",
    run_id: Optional[str] = None,
    debug_mode: bool = True,
    web_search: bool = True,    
    org_config: Optional[dict] = None
) -> Union[Assistant, 'ContextAwareAssistant']: # type: ignore
    
    logger.info(f"-*- Creating {llm_id} LLM OS -*-")    
    
    # Fetch the organization name from the database
    if org_id is not None:
        db = next(get_db())
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if org is None:
            raise ValueError(f"Organization with id {org_id} not found")
        client_name = org.name
    else:
        raise ValueError("org_id must be provided")
    
    # Use org_config to determine available assistants and feature flags
    available_assistants = org_config['assistants'].get(user_role, [])
    feature_flags = org_config['feature_flags']

    knowledge_base = AssistantKnowledge(
        vector_db=PgVector2(
            db_url=db_url,
            collection=f"org_{org_id}_user_{user_id}_documents" if user_id is not None else "llm_os_documents",
            embedder=SentenceTransformerEmbedder(model="all-MiniLM-L6-v2"),
        ),
        num_documents=100,
        user_id=user_id,
    )

    try:
        pandas_tools = create_pandas_tools(user_id)
        code_tools = CodeTools(knowledge_base=knowledge_base)
        exa_tools = ExaTools(num_results=5, text_length_limit=2000)
        
        tools = [
            pandas_tools,
            exa_tools,
            code_tools
        ]    

        if web_search:
            tools.append(ExaTools(num_results=5, text_length_limit=2000))
    except Exception as e:
        logger.error(f"Failed to initialize tools: {str(e)}")
        raise
    
    team: List[Assistant] = []
    
    team_description = "Your team consists of:\n"
    for assistant in available_assistants:
        team_description += f"- {assistant}\n"
        
    llm = get_llm(llm_id, fallback_model)

    assistant_mapping = {
        "Enhanced Quality Analyst": EnhancedQualityAnalyst,
        "Business Analyst": EnhancedBusinessAnalyst,
        "Enhanced Data Analyst": EnhancedDataAnalyst,
        "Call Center Assistant": CallCenterAssistant,
        "Enhanced Financial Analyst": EnhancedFinancialAnalyst,
        "Product Owner": EnhancedProductOwner,
        "Web Search": ExaTools,
        "Code Assistant": CodeAssistant,
        "PM Assistant": ProjectManagementAssistant
    }

    for assistant in available_assistants:
        if assistant in assistant_mapping:
            if assistant == "Web Search":
                tools.append(assistant_mapping[assistant](num_results=5, text_length_limit=2000))
            else:
                assistant_kwargs = {
                    "llm": llm,
                    "tools": [pandas_tools, ExaTools()] if assistant in ["Business Analyst", "Call Center Assistant", "Product Owner"] else [pandas_tools],
                    "debug_mode": debug_mode
                }
                if assistant == "Code Assistant":
                    assistant_kwargs["code_tools"] = CodeTools(knowledge_base=knowledge_base)
                else:
                    assistant_kwargs["knowledge_base"] = knowledge_base
                team.append(assistant_mapping[assistant](**assistant_kwargs))    
    
    assistant_instructions = load_assistant_instructions(client_name, user_nickname)    
    
    if 'introduction' in assistant_instructions:
        assistant_instructions['introduction'] = assistant_instructions['introduction'].replace('{user_nickname}', user_nickname)

    # Add team description to instructions
    assistant_instructions['instructions'].append(f"\nYour current team:\n{team_description}")

    class ContextAwareAssistant(Assistant):
        current_project: Optional[str] = Field(default=None, description="Current project name")
        current_project_type: Optional[str] = Field(default=None, description="Current project type (react or java)")
        last_search_results: Optional[List[Any]] = Field(default=None, description="Last search results")
        tools: List[Union[Toolkit, CodeTools, PandasTools, ExaTools]] = Field(default_factory=list)


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