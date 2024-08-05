import json
import os
from pathlib import Path
from typing import List, Optional

import httpx
import psutil
from dotenv import load_dotenv

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
from team.react_assistant import ReactAssistant
from team.research_assistant import EnhancedResearchAssistant
from team.maintenance_engineer import EnhancedMaintenanceEngineer
from team.investment_assistant import EnhancedInvestmentAssistant
from team.company_analyst import EnhancedCompanyAnalyst
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
    if llm_id in ["tinyllama", "llama3"]:
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        try:
            return Ollama(
                model=llm_id,
                base_url=ollama_base_url,
                options={"num_ctx": 2048, "temperature": 0.7, "top_p": 0.9}
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

def get_llm_os(
    llm_id: str = "gpt-4o",
    fallback_model: str = "tinyllama",    
    user_id: Optional[int] = None,
    user_role: Optional[str] = None,
    user_nickname: Optional[str] = "friend",
    run_id: Optional[str] = None,
    debug_mode: bool = True,
    web_search: bool = True,
) -> Assistant:
    
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
        "QA": ["Web Search", "Enhanced Quality Analyst", "Business Analyst"],
        "Product": ["Web Search", "Product Owner", "Business Analyst", "Enhanced Data Analyst"],
        "Delivery": ["Web Search", "Business Analyst", "Enhanced Data Analyst"],
        "Manager": ["Web Search", "Enhanced Financial Analyst", "Business Analyst", "Enhanced Data Analyst"]
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
    }

    for assistant in available_assistants:
        if assistant in assistant_mapping:
            if assistant == "Web Search":
                tools.append(assistant_mapping[assistant](num_results=5, text_length_limit=2000))
            else:
                team.append(assistant_mapping[assistant](
                    llm=llm, 
                    tools=[pandas_tools, ExaTools()] if assistant in ["Business Analyst", "Product Owner"] else [pandas_tools], 
                    knowledge_base=knowledge_base, 
                    debug_mode=debug_mode
                ))

    log_system_resources()        

    client_name = get_client_name()
    assistant_instructions = load_assistant_instructions(client_name, user_nickname)    
    
    if 'introduction' in assistant_instructions:
        assistant_instructions['introduction'] = assistant_instructions['introduction'].replace('{user_nickname}', user_nickname)

    # Add team description to instructions
    assistant_instructions['instructions'].append(f"\nYour current team:\n{team_description}")

    llm_os = Assistant(
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