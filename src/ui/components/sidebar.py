from asyncio.log import logger
import streamlit as st
from kr8.tools.pandas import PandasTools
from kr8.tools.code_tools import CodeTools
from ui.utils.helper import restart_assistant
from utils.npm_utils import run_npm_command


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
        if "react_assistant_enabled" not in st.session_state:
            st.session_state["react_assistant_enabled"] = False
        react_assistant_enabled = st.session_state["react_assistant_enabled"]
        react_assistant = st.checkbox("React Assistant", value=react_assistant_enabled, help="Enable the React Assistant for React project development.")
        if react_assistant_enabled != react_assistant:
            st.session_state["react_assistant_enabled"] = react_assistant
            restart_assistant()
            
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
    
        if st.session_state.get("react_assistant_enabled", False):
            st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)
            st.sidebar.subheader("React Project Upload")
        
        # Check if npm is installed
        if run_npm_command("--version") is None:
            st.sidebar.warning("npm is not installed or not in PATH. Some features may not work correctly.")
            
      # File uploader
        react_files = st.sidebar.file_uploader(
            "Upload React Project Files", 
            type=["js", "jsx", "ts", "tsx", "css", "json", "html", "md", "yml", "yaml", "txt"],
            key="react_file_uploader",
            accept_multiple_files=True
        )
        
        # Project name input
        project_name = st.sidebar.text_input("Enter React Project Name", "my_react_project")
        
         # Process files when they are uploaded
        if react_files:
            if 'react_files_processed' not in st.session_state:
                st.session_state.react_files_processed = False
            
            if not st.session_state.react_files_processed:
                st.sidebar.info("React files uploaded. Click 'Process React Project' to analyze them.")
            
            if st.sidebar.button("Process React Project"):
                # Create placeholders in the main area for progress bar and status
                progress_bar = st.empty()
                status_text = st.empty()
                
                with st.spinner("Processing React project files..."):
                    try:
                        directory_content = {}
                        total_files = len(react_files)
                        
                        for i, file in enumerate(react_files):
                            file_content = file.read().decode('utf-8', errors='ignore')
                            directory_content[file.name] = file_content
                            
                            # Update progress
                            progress = (i + 1) / total_files
                            progress_bar.progress(progress)
                            status_text.text(f"Processing file {i+1} of {total_files}: {file.name}")

                        # Use the LLM OS from the session state
                        llm_os = st.session_state.get("llm_os")
                        if llm_os and llm_os.knowledge_base:
                            code_tools = CodeTools(knowledge_base=llm_os.knowledge_base)
                            result = code_tools.load_react_project(project_name, directory_content)
                            st.success(result)
                            st.session_state['current_project'] = project_name
                            st.session_state.react_files_processed = True
                        else:
                            st.error("LLM OS or knowledge base not initialized. Please try restarting the application.")
                    except Exception as e:
                        st.error(f"Error processing React project files: {str(e)}")
                        logger.error(f"Error processing React project files: {str(e)}")
                    finally:
                        # Clear the progress bar and status text
                        progress_bar.empty()
                        status_text.empty()
        else:
            st.session_state.react_files_processed = False
        
        # React Assistant Tools
        if st.session_state.get('current_project') and st.session_state.get('react_files_processed', False):
            st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)
            st.sidebar.subheader("React Assistant Tools")
            project_name = st.session_state['current_project']
            
            if st.sidebar.button("Analyze Project Structure"):
                llm_os = st.session_state.get("llm_os")
                if llm_os:
                    result = llm_os.run(f"Analyze the structure of the React project named {project_name}")
                    st.write(result)
                else:
                    st.sidebar.error("LLM OS not initialized. Please try restarting the application.")
                            
    st.sidebar.markdown('<hr class="dark-divider">', unsafe_allow_html=True)  # Add divider            
                    
    with st.sidebar.expander("Select model:", expanded=False):
        # Model Type Selection
        model_type = st.sidebar.radio("Select Model Type", ["Closed", "Open Source"])

        # Model Selection based on type
        if model_type == "Closed": # Closed Source
            llm_options = ["gpt-4o", "gpt-3.5-turbo"]
            llm_id = st.sidebar.selectbox("Select Closed Source Model", options=llm_options)
        else: 
            llm_options = ["llama3", "tinyllama"]
            llm_id = st.sidebar.selectbox("Select Open Source Model", options=llm_options)
        

        # Update session state and restart assistant if necessary
        if "llm_id" not in st.session_state:
            st.session_state["llm_id"] = llm_id
        elif st.session_state["llm_id"] != llm_id:
            st.session_state["llm_id"] = llm_id
            restart_assistant()                