import streamlit as st
from kr8.utils.log import logger
from assistant import get_llm_os
from src.backend.utils.org_utils import load_org_config
from src.team.data_analyst import EnhancedDataAnalyst

def initialize_assistant(llm_id, user_id=None):
    if "llm_os" not in st.session_state or st.session_state["llm_os"] is None:
        logger.info(f"---*--- Creating {llm_id} LLM OS ---*---")
        
        user_nickname = st.session_state.get("nickname", "friend")
        user_role = st.session_state.get("role", "default")
        org_id = st.session_state.get("org_id")


        try:
            
            org_config = load_org_config(org_id)

            llm_os = get_llm_os(
                llm_id=llm_id,
                user_id=user_id,
                org_id=org_id,
                user_role=user_role,
                user_nickname=user_nickname,
                run_id=st.session_state.get("run_id"),
                debug_mode=st.session_state.get("debug_mode", False),
                web_search=st.session_state.get("web_search_enabled", True),
                org_config=org_config

            )
            st.session_state["llm_os"] = llm_os
            logger.info(f"Initialized LLM OS with team: {[assistant.name for assistant in llm_os.team]}")
            
            data_analyst = next((a for a in llm_os.team if isinstance(a, EnhancedDataAnalyst)), None)
            if data_analyst:
                logger.info(f"EnhancedDataAnalyst initialized with pandas_tools: {data_analyst.pandas_tools is not None}")
            else:
                logger.warning("EnhancedDataAnalyst not found in the team")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM OS: {str(e)}", exc_info=True)
            st.error(f"An error occurred while initializing the assistant: {str(e)}")
            return None        
    else:
        llm_os = st.session_state["llm_os"]
        logger.info(f"Using existing LLM OS with team: {[assistant.name for assistant in llm_os.team]}")

    return llm_os