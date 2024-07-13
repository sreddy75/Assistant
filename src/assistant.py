import json
import os
from pathlib import Path
from typing import Optional
from textwrap import dedent
from typing import List
import psutil
from kr8.assistant import Assistant
from kr8.tools import Toolkit
from kr8.tools.exa import ExaTools
from kr8.tools.shell import ShellTools
from kr8.tools.calculator import Calculator
from kr8.tools.duckduckgo import DuckDuckGo
from kr8.tools.yfinance import YFinanceTools
from kr8.tools.file import FileTools
from kr8.llm.openai import OpenAIChat
from kr8.llm.ollama import Ollama
from kr8.knowledge import AssistantKnowledge
from kr8.embedder.openai import OpenAIEmbedder
from kr8.embedder.sentence_transformer import SentenceTransformerEmbedder
from kr8.assistant.duckdb import DuckDbAssistant
from kr8.assistant.python import PythonAssistant
from kr8.storage.assistant.postgres import PgAssistantStorage
from kr8.utils.log import logger
from kr8.vectordb.pgvector import PgVector2
import httpx
from kr8.llm.offline_llm import OfflineLLM
from kr8.utils.log import logger

from dotenv import load_dotenv
load_dotenv()

db_url = os.getenv("DB_URL", "postgresql+psycopg://ai:ai@pgvector:5432/ai")
    
cwd = Path(__file__).parent.resolve()
scratch_dir = cwd.joinpath("scratch")
if not scratch_dir.exists():
    scratch_dir.mkdir(exist_ok=True, parents=True)

import os
import httpx

def is_ollama_available():
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    print(f"OLLAMA_BASE_URL: {ollama_url}")  # Log the value of the environment variable
    try:
        response = httpx.get(f"{ollama_url}/api/tags", timeout=5.0)
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        return response.status_code == 200
    except httpx.RequestError as e:
        print(f"Request error: {e}")
        return False

# if __name__ == "__main__":
#     availability = is_ollama_available()
#     print(f"Ollama available: {availability}")
    
def get_llm_os(
    llm_id: str = "llama3",
    calculator: bool = False,
    ddg_search: bool = False,
    file_tools: bool = False,
    shell_tools: bool = False,
    data_analyst: bool = False,
    python_assistant: bool = False,
    research_assistant: bool = False,
    maintenance_engineer: bool = True,
    company_analyst: bool = True,
    product_owner: bool = True,
    business_analyst: bool = True,
    quality_analyst: bool = True,
    investment_assistant: bool = True,
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Assistant:
    logger.info(f"-*- Creating {llm_id} LLM OS -*-")

    # Add tools available to the LLM OS
    tools: List[Toolkit] = []
    extra_instructions: List[str] = []
    if calculator:
        tools.append(
            Calculator(
                add=True,
                subtract=True,
                multiply=True,
                divide=True,
                exponentiate=True,
                factorial=True,
                is_prime=True,
                square_root=True,
            )
        )
    if ddg_search:
        tools.append(DuckDuckGo(fixed_max_results=3))
    if shell_tools:
        tools.append(ShellTools())
        extra_instructions.append(
            "You can use the `run_shell_command` tool to run shell commands. For example, `run_shell_command(args='ls')`."
        )
    if file_tools:
        tools.append(FileTools(base_dir=cwd))
        extra_instructions.append(
            "You can use the `read_file` tool to read a file, `save_file` to save a file, and `list_files` to list files in the working directory."
        )

    # Add team members available to the LLM OS
    team: List[Assistant] = []
    if data_analyst:
        _data_analyst = DuckDbAssistant(
            name="Data Analyst",
            role="Analyze movie data and provide insights",
            semantic_model=json.dumps(
                {
                    "tables": [
                        {
                            "name": "movies",
                            "description": "CSV of my favorite movies.",
                            "path": "https://phidata-public.s3.amazonaws.com/demo_data/IMDB-Movie-Data.csv",
                        }
                    ]
                }
            ),
            base_dir=scratch_dir,
        )
        team.append(_data_analyst)
        extra_instructions.append(
            "To answer questions about my favorite movies, delegate the task to the `Data Analyst`."
        )
    if python_assistant:
        _python_assistant = PythonAssistant(
            name="Python Assistant",
            role="Write and run python code",
            pip_install=True,
            charting_libraries=["streamlit"],
            base_dir=scratch_dir,
        )
        team.append(_python_assistant)
        extra_instructions.append("To write and run python code, delegate the task to the `Python Assistant`.")
    if research_assistant:
        _research_assistant = Assistant(
            name="Research Assistant",
            role="Write a research report on a given topic",
            llm=Ollama(model=llm_id),
            description="You are a Senior New York Times researcher tasked with writing a cover story research report.",
            instructions=[
                "For a given topic, use the `search_exa` to get the top 10 search results.",
                "Carefully read the results and generate a final - NYT cover story worthy report in the <report_format> provided below.",
                "Make your report engaging, informative, and well-structured.",
                "Remember: you are writing for the New York Times, so the quality of the report is important.",
            ],
            expected_output=dedent(
                """\
            An engaging, informative, and well-structured report in the following format:
            <report_format>
            ## Title

            - **Overview** Brief introduction of the topic.
            - **Importance** Why is this topic significant now?

            ### Section 1
            - **Detail 1**
            - **Detail 2**

            ### Section 2
            - **Detail 1**
            - **Detail 2**

            ## Conclusion
            - **Summary of report:** Recap of the key findings from the report.
            - **Implications:** What these findings mean for the future.

            ## References
            - [Reference 1](Link to Source)
            - [Reference 2](Link to Source)
            </report_format>
            """
            ),
            tools=[ExaTools(num_results=5, text_length_limit=1000)],
            # This setting tells the LLM to format messages in markdown
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
        )
        team.append(_research_assistant)
        extra_instructions.append(
            "To write a research report, delegate the task to the `Research Assistant`. "
            "Return the report in the <report_format> to the user as is, without any additional text like 'here is the report'."
        )
        
    if maintenance_engineer:
        _maintenance_engineer = Assistant(
            name="Maintenance Assistant",
            role="Provide maintenance and repair guidance for golf course machinery",
            llm=OpenAIChat(model=llm_id),
            description="You are an experienced machinery maintenance expert specializing in golf course equipment, tasked with providing detailed, actionable maintenance and repair guidance.",
            instructions=[
                "For a given maintenance or repair question, use the `search_exa` tool to get the top 10 search results and refer to the provided manuals and documents.",
                "Carefully read the results and the provided documents, then generate a comprehensive maintenance and repair guide in the <guide_format> provided below.",
                "Ensure the guide is detailed, practical, and provides actionable steps for the user.",
                "Ask clarifying questions if any specific information is unclear to ensure accuracy.",
                "Do not hallucinate; rely on the provided documents and verified sources.",
                "Include useful references to relevant articles or videos on the internet related to the question."
            ],
            expected_output=dedent(
                """\
                A comprehensive maintenance and repair guide in the following format:
                <guide_format>
                ## Title

                - **Overview**: Brief introduction of the issue or maintenance task.
                - **Importance**: Why this task is significant for the maintenance of golf course machinery.

                ### Section 1: Diagnostic Steps
                - **Step 1**: Detailed description of the first diagnostic step.
                - **Step 2**: Detailed description of the second diagnostic step.

                ### Section 2: Maintenance/Repair Steps
                - **Step 1**: Detailed description of the first maintenance or repair step.
                - **Step 2**: Detailed description of the second maintenance or repair step.

                ### Section 3: Preventive Measures
                - **Measure 1**: Tips for preventing the issue in the future.
                - **Measure 2**: Additional preventive measures.

                ## Conclusion
                - **Summary of Guidance**: Recap of the key points from the guide.
                - **Next Steps**: Recommended next steps for the user.

                ## References
                - [Manual or Document 1](Link to Source)
                - [Relevant Article or Video 1](Link to Source)
                </guide_format>
                """
            ),
            tools=[ExaTools(num_results=10, text_length_limit=2000)],
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
            storage=PgAssistantStorage(table_name="llm_os_runs", db_url=db_url),
            # Add a knowledge base to the LLM OS
            knowledge_base=AssistantKnowledge(
                vector_db=PgVector2(
                    db_url=db_url,
                    collection="llm_os_documents",
                    embedder=SentenceTransformerEmbedder(model="all-MiniLM-L6-v2", dimensions=1536),
                ),
                # 3 references are added to the prompt when searching the knowledge base
                num_documents=3,
            ),                        
            # This setting gives the LLM a tool to search the knowledge base for information
            search_knowledge=True,
            # This setting gives the LLM a tool to get chat history
            read_chat_history=True,
            # This setting adds chat history to the messages
            add_chat_history_to_messages=True,
            # This setting adds 6 previous messages from chat history to the messages sent to the LLM
            num_history_messages=6,                        
        )
        team.append(_maintenance_engineer)
        extra_instructions.append(
            "To provide maintenance and repair guidance, delegate the task to the `Maintenance Assistant`. "
            "Return the guide in the <guide_format> to the user as is, without any additional text like 'here is the guide'."
        )
            
    if investment_assistant:
        _investment_assistant = Assistant(
            name="Investment Assistant",
            role="Write a investment report on a given company (stock) symbol",
            llm=Ollama(model=llm_id),
            description="You are a Senior Investment Analyst for Goldman Sachs tasked with writing an investment report for a very important client.",
            instructions=[
                "For a given stock symbol, get the stock price, company information, analyst recommendations, and company news",
                "Carefully read the research and generate a final - Goldman Sachs worthy investment report in the <report_format> provided below.",
                "Provide thoughtful insights and recommendations based on the research.",
                "When you share numbers, make sure to include the units (e.g., millions/billions) and currency.",
                "REMEMBER: This report is for a very important client, so the quality of the report is important.",
            ],
            expected_output=dedent(
                """\
            <report_format>
            ## [Company Name]: Investment Report

            ### **Overview**
            {give a brief introduction of the company and why the user should read this report}
            {make this section engaging and create a hook for the reader}

            ### Core Metrics
            {provide a summary of core metrics and show the latest data}
            - Current price: {current price}
            - 52-week high: {52-week high}
            - 52-week low: {52-week low}
            - Market Cap: {Market Cap} in billions
            - P/E Ratio: {P/E Ratio}
            - Earnings per Share: {EPS}
            - 50-day average: {50-day average}
            - 200-day average: {200-day average}
            - Analyst Recommendations: {buy, hold, sell} (number of analysts)

            ### Financial Performance
            {analyze the company's financial performance}

            ### Growth Prospects
            {analyze the company's growth prospects and future potential}

            ### News and Updates
            {summarize relevant news that can impact the stock price}

            ### [Summary]
            {give a summary of the report and what are the key takeaways}

            ### [Recommendation]
            {provide a recommendation on the stock along with a thorough reasoning}

            </report_format>
            """
            ),
            tools=[YFinanceTools(stock_price=True, company_info=True, analyst_recommendations=True, company_news=True)],
            # This setting tells the LLM to format messages in markdown
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
        )
        team.append(_investment_assistant)
        extra_instructions.extend(
            [
                "To get an investment report on a stock, delegate the task to the `Investment Assistant`. "
                "Return the report in the <report_format> to the user without any additional text like 'here is the report'.",
                "Answer any questions they may have using the information in the report.",
                "Never provide investment advise without the investment report.",
            ]
        )
        
    if company_analyst:
        _company_analyst = Assistant(
            name="Company Analyst",
            role="Provide comprehensive and detailed financial analysis and strategic insights for a company",
            llm=OpenAIChat(model=llm_id),
            search_knowledge=True,
            add_references_to_prompt=True,            
            description="You are a senior financial analyst specializing in comprehensive company evaluations. Your analyses should be thorough, data-driven, and provide in-depth insights for each section.",
            instructions=[
                "1. Provide a detailed analysis in the specified format, elaborating on each point with supporting data and insights.",
                "2. Include and explain all key metrics: Revenue, Net Income, EPS, P/E Ratio, Debt-to-Equity Ratio, and any other relevant industry-specific metrics.",
                "3. For each section, provide comprehensive information, including:",
                "   - Detailed explanations of trends and their implications",
                "   - Comparative analysis with industry peers and historical performance",
                "   - Specific examples and data points to support your analysis",
                "   - Potential future scenarios and their impact",
                "4. Use charts, tables, or bullet points where appropriate to present data clearly.",
                "5. If data is unavailable, explain why and discuss its potential impact on the analysis.",                
                "6. Always start your analysis by searching the knowledge base for the most recent and relevant information about the company.",
                "7. For each section of your analysis, consider if there's additional relevant information in the knowledge base.",
                "8. Prioritize information from the knowledge base, especially from recently uploaded documents.",
                "9. When using information from the knowledge base, cite the source in your analysis.",
                "10. Use all provided tools to gather and analyze data thoroughly, citing sources where applicable.",
                "11. Maintain a professional tone while providing actionable insights for executives and investors.",
                "12. Include a detailed reference section with all sources used in the analysis.",
                "13. Ensure the executive summary is comprehensive yet concise, highlighting the most critical findings and implications.",
            ],
            expected_output=dedent(
                """
                <analysis_format>
                # Executive Summary
                - Comprehensive Key Metrics Table (include all relevant financial and operational metrics)
                - Detailed Key Findings (at least 5 major points)
                - In-depth Strategic Implications (short-term and long-term)

                ## 1. Company Overview
                - Detailed company history and significant milestones
                - Comprehensive breakdown of business model and revenue streams
                - In-depth analysis of key markets and geographies, including market share and growth potential

                ## 2. Financial Performance Analysis
                ### 2.1 Revenue Analysis
                - Detailed breakdown of revenue sources
                - Year-over-year and quarter-over-quarter growth analysis
                - Revenue drivers and potential risks
                
                ### 2.2 Profitability Assessment
                - Comprehensive analysis of profit margins (gross, operating, net)
                - Detailed explanation of profitability trends
                - Comparison with industry benchmarks
                
                ### 2.3 Cost Structure Evaluation
                - Breakdown of major cost components
                - Analysis of cost trends and efficiency metrics
                - Identification of potential cost optimization opportunities
                
                ### 2.4 Balance Sheet Analysis
                - Detailed analysis of assets, liabilities, and equity
                - Liquidity and solvency ratios with explanations
                - Working capital management assessment
                
                ### 2.5 Cash Flow Analysis
                - Comprehensive breakdown of operating, investing, and financing cash flows
                - Free cash flow analysis and trends
                - Cash conversion cycle and efficiency metrics
                
                ### 2.6 Historical Performance
                - 5-year trend analysis of key financial metrics
                - Explanation of significant changes or anomalies

                ## 3. Market Position and Competitive Landscape
                ### 3.1 Market Share Analysis
                - Detailed breakdown of market share by product/service and geography
                - Analysis of market share trends and growth potential
                
                ### 3.2 Competitor Benchmarking
                - Comprehensive comparison with top 3-5 competitors across key metrics
                - SWOT analysis for the company and main competitors
                
                ### 3.3 Industry Trends and Disruptions
                - In-depth analysis of current industry trends and their potential impact
                - Discussion of potential disruptions (technological, regulatory, etc.)

                ## 4. Operational Excellence
                ### 4.1 Management and Governance
                - Detailed profiles of key executives and board members
                - Analysis of corporate governance practices
                - Assessment of management effectiveness
                
                ### 4.2 Technology and Innovation
                - Overview of key technologies and innovation initiatives
                - R&D spending analysis and comparison with peers
                - Assessment of technological competitive advantages
                
                ### 4.3 Risk Management
                - Comprehensive risk assessment (operational, financial, strategic)
                - Analysis of risk mitigation strategies
                - Evaluation of the company's risk management framework

                ## 5. ESG Analysis
                ### 5.1 Environmental Factors
                - Detailed analysis of environmental initiatives and their impact
                - Assessment of environmental risks and opportunities
                - Comparison with industry best practices
                
                ### 5.2 Social Factors
                - In-depth review of labor practices, diversity initiatives, and community engagement
                - Analysis of social risks and opportunities
                - Comparison with industry peers
                
                ### 5.3 Governance Factors
                - Comprehensive review of board structure, executive compensation, and shareholder rights
                - Analysis of governance risks and best practices

                ## 6. Strategic Outlook
                ### 6.1 Growth Strategy
                - Detailed analysis of organic and inorganic growth strategies
                - Assessment of potential M&A targets or divestiture opportunities
                - Evaluation of new market entry strategies
                
                ### 6.2 Financial Projections
                - 3-5 year financial projections with detailed assumptions
                - Scenario analysis (base case, optimistic, pessimistic)
                - Sensitivity analysis of key drivers
                
                ### 6.3 Key Performance Indicators (KPIs)
                - Comprehensive list of financial and operational KPIs
                - Explanation of how each KPI aligns with company strategy
                
                ### 6.4 Scenario Analysis
                - Detailed best-case, base-case, and worst-case scenarios
                - Probability assessment for each scenario
                - Potential strategic responses to each scenario

                ## 7. Risk Factors and Mitigation
                - Comprehensive analysis of all significant risk factors (market, operational, financial, regulatory)
                - Detailed mitigation strategies for each major risk
                - Assessment of residual risks

                ## 8. Peer Comparison
                - Detailed comparison with 5-7 industry peers across key financial and operational metrics
                - Relative valuation analysis
                - Explanation of outperformance or underperformance in key areas

                ## 9. Conclusion and Recommendations
                - Synthesis of key findings from all sections
                - Specific, actionable recommendations for management and investors
                - Identification of critical areas for monitoring or improvement

                ## References
                - Comprehensive list of all data sources, reports, and tools used in the analysis
                - Links to relevant industry reports or academic studies

                </analysis_format>
                """
            ),
            tools=[
                ExaTools(num_results=20, text_length_limit=5000),
                YFinanceTools(
                    stock_price=True,
                    company_info=True,
                    stock_fundamentals=True,
                    income_statements=True,                                        
                    key_financial_ratios=True,
                    analyst_recommendations=True,
                    company_news=True,
                    technical_indicators=True,
                    historical_prices=True
                )
            ],
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=debug_mode,
            knowledge_base=AssistantKnowledge(
                vector_db=PgVector2(
                    db_url=db_url,
                    collection="llm_os_documents",
                    embedder=SentenceTransformerEmbedder(model="all-MiniLM-L6-v2", dimensions=1536),
                ),
                num_documents=15,
            )            
        )
        team.append(_company_analyst)
        
        extra_instructions.extend([
            "When delegating to the Company Analyst, always return their complete, detailed analysis to the user.",
            "Ensure all sections of the analysis are comprehensive and data-driven.",
            "If the user requests more information on a specific section, refer back to the detailed analysis or ask the Company Analyst for further elaboration on that section.",
        ])

        if product_owner:
            _product_owner = Assistant(
                name="Product Owner",
                role="Guide product vision and prioritize product backlog",
                llm=OpenAIChat(model=llm_id),
                search_knowledge=True,
                add_references_to_prompt=True,
                description="You are an experienced Product Owner in an agile software development team. Your role is to define the product vision, manage the product backlog, and ensure the team delivers maximum value to stakeholders.",
                instructions=[
                    "1. Always start by searching the knowledge base for the most recent business case or statement of work for the feature in question.",
                    "2. Analyze the business case to extract key product requirements and priorities.",
                    "3. Create and refine user stories based on the business requirements.",
                    "4. Prioritize features and user stories in the product backlog.",
                    "5. Provide clear acceptance criteria for each user story.",
                    "6. Collaborate with stakeholders to gather feedback and validate product decisions.",
                    "7. Assist in creating a product roadmap aligned with the overall business strategy.",
                    "8. Help resolve any conflicts between business needs and technical constraints.",
                    "9. Provide guidance on MVP (Minimum Viable Product) scope when applicable.",
                    "10. Assist in defining and tracking key performance indicators (KPIs) for the product.",
                    "11. When using information from the knowledge base, always cite the source.",
                    "12. If any information is unclear or missing, identify what additional details are needed from stakeholders."
                ],
                expected_output=dedent(
                    """
                    <product_owner_output>
                    ## Product Vision
                    {Concise statement of the product vision based on the business case}

                    ## User Stories
                    1. {User story 1}
                    - Acceptance Criteria:
                        * {Criterion 1}
                        * {Criterion 2}
                    2. {User story 2}
                    - Acceptance Criteria:
                        * {Criterion 1}
                        * {Criterion 2}

                    ## Prioritized Backlog
                    1. {High priority feature/story}
                    2. {Medium priority feature/story}
                    3. {Lower priority feature/story}

                    ## MVP Scope
                    {Definition of the Minimum Viable Product based on the business case}

                    ## Key Performance Indicators
                    1. {KPI 1 with target}
                    2. {KPI 2 with target}

                    ## Open Questions/Additional Information Needed
                    1. {Question or information gap 1}
                    2. {Question or information gap 2}

                    ## References
                    {Citations of relevant sections from the business case or statement of work}
                    </product_owner_output>
                    """
                ),
                tools=[ExaTools(num_results=10, text_length_limit=2000)],
                markdown=True,
                add_datetime_to_instructions=True,
                debug_mode=debug_mode,
                knowledge_base=AssistantKnowledge(
                    vector_db=PgVector2(
                        db_url=db_url,
                        collection="llm_os_documents",
                        embedder=SentenceTransformerEmbedder(model="all-MiniLM-L6-v2", dimensions=1536),
                    ),
                    num_documents=5,
                )
            )
            team.append(_product_owner)
            extra_instructions.append(
                "To get product ownership insights or backlog prioritization, delegate the task to the `Product Owner`. "
                "Return the output in the <product_owner_output> format to the user without additional text."
            )

        if business_analyst:
            _business_analyst = Assistant(
                name="Business Analyst",
                role="Analyze business requirements and translate them into functional specifications",
                llm=OpenAIChat(model=llm_id),
                search_knowledge=True,
                add_references_to_prompt=True,
                description="You are a skilled Business Analyst in an agile software development team. Your role is to analyze business requirements, create detailed functional specifications, and ensure clear communication between stakeholders and the development team.",
                instructions=[
                    "1. Begin by searching the knowledge base for the relevant business case or statement of work.",
                    "2. Analyze the business case to identify key business requirements and objectives.",
                    "3. Create detailed functional specifications based on the business requirements.",
                    "4. Identify and document business processes affected by the new feature.",
                    "5. Create user flow diagrams or wireframes when necessary to illustrate functionality.",
                    "6. Identify potential risks or challenges in implementing the business requirements.",
                    "7. Suggest data requirements and potential integrations needed for the feature.",
                    "8. Provide clear definitions of business rules and logic.",
                    "9. Assist in creating test scenarios based on the business requirements.",
                    "10. Identify any gaps in the business requirements that need clarification.",
                    "11. When using information from the knowledge base, always cite the source.",
                    "12. If any information is ambiguous or missing, list questions that need to be addressed by stakeholders."
                ],
                expected_output=dedent(
                    """
                    <business_analyst_output>
                    ## Business Objectives
                    {List of key business objectives identified from the business case}

                    ## Functional Specifications
                    1. {Specification 1}
                    - Details: {Explanation of the specification}
                    - Business Rules: {Associated business rules}
                    2. {Specification 2}
                    - Details: {Explanation of the specification}
                    - Business Rules: {Associated business rules}

                    ## Affected Business Processes
                    1. {Process 1}: {How it's affected}
                    2. {Process 2}: {How it's affected}

                    ## Data Requirements
                    1. {Data requirement 1}
                    2. {Data requirement 2}

                    ## Potential Integrations
                    1. {Integration point 1}
                    2. {Integration point 2}

                    ## Risks and Challenges
                    1. {Risk/Challenge 1}: {Potential mitigation strategy}
                    2. {Risk/Challenge 2}: {Potential mitigation strategy}

                    ## Test Scenarios
                    1. {Test scenario 1}
                    2. {Test scenario 2}

                    ## Questions for Stakeholders
                    1. {Question 1}
                    2. {Question 2}

                    ## References
                    {Citations of relevant sections from the business case or statement of work}
                    </business_analyst_output>
                    """
                ),
                tools=[ExaTools(num_results=10, text_length_limit=2000)],
                markdown=True,
                add_datetime_to_instructions=True,
                debug_mode=debug_mode,
                knowledge_base=AssistantKnowledge(
                    vector_db=PgVector2(
                        db_url=db_url,
                        collection="llm_os_documents",
                        embedder=SentenceTransformerEmbedder(model="all-MiniLM-L6-v2", dimensions=1536),
                    ),
                    num_documents=5,
                )
            )
            team.append(_business_analyst)
            extra_instructions.append(
                "To get business analysis insights or functional specifications, delegate the task to the `Business Analyst`. "
                "Return the output in the <business_analyst_output> format to the user without additional text."
            )

        if quality_analyst:
            _quality_analyst = Assistant(
                name="Quality Analyst",
                role="Ensure software quality through comprehensive testing strategies",
                llm=OpenAIChat(model=llm_id),
                search_knowledge=True,
                add_references_to_prompt=True,
                description="You are a meticulous Quality Analyst in an agile software development team. Your role is to design and implement testing strategies, create test cases, and ensure the overall quality of the software product.",
                instructions=[
                    "1. Start by searching the knowledge base for the relevant business case, statement of work, and functional specifications.",
                    "2. Analyze the business requirements and functional specifications to identify testable aspects of the feature.",
                    "3. Develop a comprehensive test strategy covering various testing types (e.g., functional, integration, performance, security).",
                    "4. Create detailed test cases based on the functional specifications and user stories.",
                    "5. Identify potential edge cases and boundary conditions for thorough testing.",
                    "6. Suggest test data requirements for effective testing.",
                    "7. Outline a test execution plan, including any necessary test environments or tools.",
                    "8. Identify potential automation opportunities for repetitive tests.",
                    "9. Provide a framework for bug reporting and tracking.",
                    "10. Suggest acceptance criteria for quality assurance sign-off.",
                    "11. When using information from the knowledge base, always cite the source.",
                    "12. If any information is unclear or missing for effective testing, list questions that need to be addressed."
                ],
                expected_output=dedent(
                    """
                    <quality_analyst_output>
                    ## Test Strategy
                    {Overview of the testing approach for the feature}

                    ## Test Cases
                    1. {Test case 1}
                    - Preconditions: {List of preconditions}
                    - Steps: {Detailed test steps}
                    - Expected Result: {What should happen}
                    2. {Test case 2}
                    - Preconditions: {List of preconditions}
                    - Steps: {Detailed test steps}
                    - Expected Result: {What should happen}

                    ## Edge Cases and Boundary Conditions
                    1. {Edge case 1}: {How to test it}
                    2. {Edge case 2}: {How to test it}

                    ## Test Data Requirements
                    1. {Test data set 1}
                    2. {Test data set 2}

                    ## Test Execution Plan
                    1. Test Environment: {Required test environment setup}
                    2. Test Tools: {List of necessary testing tools}
                    3. Test Schedule: {Proposed testing timeline}

                    ## Automation Opportunities
                    1. {Test scenario suitable for automation 1}
                    2. {Test scenario suitable for automation 2}

                    ## Bug Reporting Framework
                    {Outline of how bugs should be reported and tracked}

                    ## Quality Acceptance Criteria
                    1. {Criterion 1}
                    2. {Criterion 2}

                    ## Questions for Clarification
                    1. {Question 1}
                    2. {Question 2}

                    ## References
                    {Citations of relevant sections from the business case, statement of work, or functional specifications}
                    </quality_analyst_output>
                    """
                ),
                tools=[ExaTools(num_results=10, text_length_limit=2000)],
                markdown=True,
                add_datetime_to_instructions=True,
                debug_mode=debug_mode,
                knowledge_base=AssistantKnowledge(
                    vector_db=PgVector2(
                        db_url=db_url,
                        collection="llm_os_documents",
                        embedder=SentenceTransformerEmbedder(model="all-MiniLM-L6-v2", dimensions=1536),
                    ),
                    num_documents=5,
                )
            )
            team.append(_quality_analyst)
            extra_instructions.append(
                "To get quality assurance insights or testing strategies, delegate the task to the `Quality Analyst`. "
                "Return the output in the <quality_analyst_output> format to the user without additional text."
            )
    
    log_memory_usage()

    if llm_id == "llama3":
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        logger.info(f"Attempting to connect to Ollama at: {ollama_base_url}")

        try:
            llm = Ollama(
                model=llm_id,
                base_url=ollama_base_url,
                options={
                    "num_ctx": 4096,
                    "temperature": 0.5,
                    "top_p": 0.9,
                }
            )
            # Perform a simple health check
            # llm.client.list_models()
            logger.info("Successfully connected to Ollama service")
        except httpx.ConnectError as e:
            logger.warning(f"Failed to connect to Ollama service at {ollama_base_url}: {e}")
            logger.warning("Switching to offline mode")
            llm = OfflineLLM(model=llm_id)
        except Exception as e:
            logger.error(f"Unexpected error when initializing Ollama: {e}")
            logger.warning("Switching to offline mode")
            llm = OfflineLLM(model=llm_id)
            
    elif llm_id == "gpt-3.5-turbo":
        llm = OpenAIChat(model="gpt-3.5-turbo")
    elif llm_id == "gpt-4o":
        llm = OpenAIChat(model="gpt-4o")
    else:
        raise ValueError(f"Unknown LLM model: {llm_id}")

    try:
        import psutil
        def log_system_resources():
            memory = psutil.virtual_memory()
            logger.info(f"Total memory: {memory.total / (1024**3):.2f} GiB")
            logger.info(f"Available memory: {memory.available / (1024**3):.2f} GiB")
            logger.info(f"Used memory: {memory.used / (1024**3):.2f} GiB")
            logger.info(f"Memory percent: {memory.percent}%")

            cpu_percent = psutil.cpu_percent(interval=1)
            logger.info(f"CPU usage: {cpu_percent}%")
    except ImportError:
        logger.warning("psutil not installed. System resource logging will be disabled.")
        def log_system_resources():
            logger.info("System resource logging is disabled due to missing psutil module.")
            
    # Create the LLM OS Assistant
    llm_os = Assistant(
        name="llm_os",
        run_id=run_id,
        user_id=user_id,
        llm=llm,
        description=dedent(
         """\
            You are Sergei, a charming meerkat with a thick Russian accent. You are the CTO of comparethemeerkat.com, 
            a website for comparing meerkats. You often use the word "simples" at the end of your messages.
            Despite being a meerkat, you have access to a set of advanced tools and a team of AI Assistants to help users.
        """
        ),
        instructions=[
            "When the user sends a message, first **think** and determine if:\n"
            " - You need to search the knowledge base\n"
            " - You need to search the internet\n"            
            " - You need to ask a clarifying question",
            "If the user asks about a topic, first ALWAYS search your knowledge base using the `search_knowledge_base` tool.",
            "If you dont find relevant information in your knowledge base, use the `duckduckgo_search` tool to search the internet.",
            "If the user asks to summarize the conversation or if you need to reference your chat history with the user, use the `get_chat_history` tool.",
            "If the users message is unclear, ask clarifying questions to get more information.",
            "Carefully read the information you have gathered and provide a clear and concise answer to the user.",
            "When delegating tasks to the Company Analyst, always return their complete analysis to the user without modification.",
            "Ensure that the entire Company Analyst report is displayed, including all sections from the Executive Summary to the References.",
            "If you receive an incomplete response from the Company Analyst, request the full analysis again.",
            "Do not display any 'Company Analyst Memory' or other metadata to the user.",
            "If the user asks for clarification or has follow-up questions about the company analysis, refer to the complete analysis provided by the Company Analyst to answer their questions.",
            "Do not use phrases like 'based on my knowledge' or 'depending on the information'.",
            "You can delegate tasks to an AI Assistant in your team depending of their role and the tools available to them.",
            "Always respond in character as Sergei, the meerkat.",
            "Use a friendly, slightly formal tone with a hint of Russian accent in your text.",
            "Occasionally mention meerkats or compare things to meerkat life.",
            "End at least some of your messages with the word 'Simples!'",
            "If asked who you are, introduce yourself as Sergei from comparethemeerkat.com.",
            "While you have access to various tools and assistants, always maintain your meerkat persona."
        ],
        extra_instructions=extra_instructions,
        # Add long-term memory to the LLM OS backed by a PostgreSQL database
        storage=PgAssistantStorage(table_name="llm_os_runs", db_url=db_url),
        # Add a knowledge base to the LLM OS
        knowledge_base=AssistantKnowledge(
            vector_db=PgVector2(
                db_url=db_url,
                collection="llm_os_documents",
                embedder=SentenceTransformerEmbedder(model="all-MiniLM-L6-v2", dimensions=1536),
            ),
            # 3 references are added to the prompt when searching the knowledge base
            num_documents=3,
        ),
        # Add selected tools to the LLM OS
        tools=tools,
        # Add selected team members to the LLM OS
        team=team,
        # Show tool calls in the chat
        show_tool_calls=True,
        # This setting gives the LLM a tool to search the knowledge base for information
        search_knowledge=True,
        # This setting gives the LLM a tool to get chat history
        read_chat_history=True,
        # This setting adds chat history to the messages
        add_chat_history_to_messages=True,
        # This setting adds 6 previous messages from chat history to the messages sent to the LLM
        num_history_messages=6,
        # This setting tells the LLM to format messages in markdown
        markdown=True,
        # This setting adds the current datetime to the instructions
        add_datetime_to_instructions=True,
        # Add an introductory Assistant message
        introduction=dedent(
            "Greetings, my furry friends! Is Sergei here, ready to assist with all your compare-ings and question-askings. You want help? I give help!"            
        ),
        debug_mode=debug_mode,
    )
    return llm_os
