from asyncio.log import logger
import streamlit as st
from kr8.tools.pandas import PandasTools
from ui.utils.helper import restart_assistant


def initialize_session_state():
    if "web_search_enabled" not in st.session_state:
        st.session_state.web_search_enabled = True
    # if "research_assistant_enabled" not in st.session_state:
    #     st.session_state.research_assistant_enabled = True
    # if "company_analyst_enabled" not in st.session_state:
    #     st.session_state.company_analyst_enabled = True
    # if "investment_assistant_enabled" not in st.session_state:
    #     st.session_state.investment_assistant_enabled = True
    if "product_owner_enabled" not in st.session_state:
        st.session_state.product_owner_enabled = True
    if "business_analyst_enabled" not in st.session_state:
        st.session_state.business_analyst_enabled = True
    if "quality_analyst_enabled" not in st.session_state:
        st.session_state.quality_analyst_enabled = True
    if 'pandas_tools' not in st.session_state:
        st.session_state.pandas_tools = PandasTools()        
        

def render_sidebar():
    initialize_session_state()    
    st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)  # Add divider            
    with st.sidebar.expander("Available Assistants", expanded=False):                                                                       
            
        if "web_search_enabled" not in st.session_state:
            st.session_state["web_search_enabled"] = False
        web_search_enabled = st.session_state["web_search_enabled"]
        web_search = st.checkbox("Web Search", value=web_search_enabled, help="Enable web search using DuckDuckGo.")
        if web_search_enabled != web_search:
            st.session_state["web_search_enabled"] = web_search
            restart_assistant()
    
        # if "research_assistant_enabled" not in st.session_state:
        #     st.session_state["research_assistant_enabled"] = True
        # research_assistant_enabled = st.session_state["research_assistant_enabled"]
        # research_assistant = st.checkbox("Research Assistant", value=research_assistant_enabled, help="Enable the research assistant (uses Exa).")
        # if research_assistant_enabled != research_assistant:
        #     st.session_state["research_assistant_enabled"] = research_assistant
        #     restart_assistant()
        
        if "data_analyst_enabled" not in st.session_state:
            st.session_state["data_analyst_enabled"] = True
        data_analyst_enabled = st.session_state["data_analyst_enabled"]
        data_analyst = st.checkbox("Data Analyst", value=data_analyst_enabled, help="Enable the Data Analyst for financial data analysis.")
        if data_analyst_enabled != data_analyst:
            st.session_state["data_analyst_enabled"] = data_analyst
            restart_assistant()
        
        if "financial_analyst_enabled" not in st.session_state:
            st.session_state["financial_analyst_enabled"] = True
        financial_analyst_enabled = st.session_state["financial_analyst_enabled"]
        financial_analyst = st.checkbox("Financial Analyst", value=financial_analyst_enabled, help="Enable the Financial Analyst for financial data analysis.")
        if financial_analyst_enabled != financial_analyst:
            logger.debug(f"Financial Analyst enabled changed from {financial_analyst_enabled} to {financial_analyst}")
            st.session_state["financial_analyst_enabled"] = financial_analyst
            restart_assistant()
                                    
        # if "legal_assistant_enabled" not in st.session_state:
        #     st.session_state["legal_assistant_enabled"] = False
        # legal_assistant_enabled = st.session_state["legal_assistant_enabled"]
        # legal_assistant = st.checkbox("Legal Analyst", value=legal_assistant_enabled, help="Enable the legal analyst (uses Exa).")
        # if legal_assistant_enabled != legal_assistant:
        #     st.session_state["legal_assistant_enabled"] = legal_assistant
        #     restart_assistant()            

        # if "company_analyst_enabled" not in st.session_state:
        #     st.session_state["company_analyst_enabled"] = True
        # company_analyst_enabled = st.session_state["company_analyst_enabled"]
        # company_analyst = st.checkbox("Company Analyst", value=company_analyst_enabled, help="Enable the company analyst (uses Exa).")
        # if company_analyst_enabled != company_analyst:
        #     st.session_state["company_analyst_enabled"] = company_analyst
        #     restart_assistant()
            
        # if "investment_assistant_enabled" not in st.session_state:
        #     st.session_state["investment_assistant_enabled"] = True
        # investment_assistant_enabled = st.session_state["investment_assistant_enabled"]
        # investment_assistant = st.checkbox("Investment Assistant", value=investment_assistant_enabled, help="Enable the investment assistant. NOTE: This is not financial advice.")
        # if investment_assistant_enabled != investment_assistant:
        #     st.session_state["investment_assistant_enabled"] = investment_assistant
        #     restart_assistant()                

        if "product_owner_enabled" not in st.session_state:
            st.session_state["product_owner_enabled"] = True
        product_owner_enabled = st.session_state["product_owner_enabled"]
        product_owner = st.checkbox("PO", value=product_owner_enabled, help="Enable Ze Great Visionary of Producting.")
        if product_owner_enabled != product_owner:
            st.session_state["product_owner_enabled"] = product_owner
            restart_assistant()

        if "business_analyst_enabled" not in st.session_state:
            st.session_state["business_analyst_enabled"] = True
        business_analyst_enabled = st.session_state["business_analyst_enabled"]
        business_analyst = st.checkbox("BA", value=business_analyst_enabled, help="Enable Ze Business analysis Solver")
        if business_analyst_enabled != business_analyst:
            st.session_state["business_analyst_enabled"] = business_analyst
            restart_assistant()

        if "quality_analyst_enabled" not in st.session_state:
            st.session_state["quality_analyst_enabled"] = True
        quality_analyst_enabled = st.session_state["quality_analyst_enabled"]
        quality_analyst = st.checkbox("QA", value=quality_analyst_enabled, help="Enable Ze Finder of Glitches.")
        if quality_analyst_enabled != quality_analyst:
            st.session_state["quality_analyst_enabled"] = quality_analyst
            restart_assistant()    
                
    st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)  # Add divider            
                    
    with st.sidebar.expander("Select model:", expanded=False):
        # Model Type Selection
        model_type = st.sidebar.radio("Select Model Type", ["Closed", "Open Source"])

        # Model Selection based on type
        if model_type == "Closed": # Closed Source
            llm_options = ["gpt-4o", "gpt-3.5-turbo"]
            llm_id = st.sidebar.selectbox("Select Closed Source Model", options=llm_options)
        else: 
            llm_options = ["tinyllama"]
            llm_id = st.sidebar.selectbox("Select Open Source Model", options=llm_options)
        

        # Update session state and restart assistant if necessary
        if "llm_id" not in st.session_state:
            st.session_state["llm_id"] = llm_id
        elif st.session_state["llm_id"] != llm_id:
            st.session_state["llm_id"] = llm_id
            restart_assistant()                