import streamlit as st
import requests
import toml
from utils.api import BACKEND_URL
from utils.helpers import get_client_name

client_name = get_client_name()

def apply_custom_theme():
    """
    Apply a custom theme to the Streamlit app based on the organization's configuration.
    """
    try:
        
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/public-config/{client_name}")
        response.raise_for_status()
        config_content = response.text
        theme_config = toml.loads(config_content)

        theme_css = f"""
        <style>
            /* Global styles */
            .stApp, .stApp p, .stApp label, .stApp .stMarkdown, .stApp .stText {{
                color: {theme_config['theme']['textColor']};
            }}
            .stApp {{
                background-color: {theme_config['theme']['backgroundColor']};
            }}
            * {{
                font-family: {theme_config['theme']['font']};
            }}

            /* Input fields */
            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea,
            .stSelectbox > div > div > div,
            .stMultiSelect > div > div > div {{
                color: {theme_config['theme']['textColor']};                
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                border: 1px solid {theme_config['theme']['primaryColor']};
                border-radius: 4px;
            }}

            /* Select box */
            .stSelectbox > div > div::before {{
                background-color: {theme_config['theme']['primaryColor']};
            }}
            .stSelectbox > div > div > div:hover {{
                border-color: {theme_config['theme']['primaryColor']};
            }}
            .stSelectbox > div > div > div[aria-selected="true"] {{
                background-color: {theme_config['theme']['primaryColor']};
                color: {theme_config['theme']['backgroundColor']};
            }}

            /* Buttons */
            .stButton > button {{
                color: {theme_config['theme']['backgroundColor']};                
                background-color: #25cf47;
                border: none;
                border-radius: 4px;
                padding: 0.5rem 1rem;
                font-weight: bold;
            }}
            .stButton > button:hover {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['primaryColor']};
            }}

            /* Tabs */
            .stTabs {{
                background-color: {theme_config['theme']['backgroundColor']};
            }}
            .stTabs [data-baseweb="tab-list"] {{
                gap: 25px;
                background-color: {theme_config['theme']['backgroundColor']};
                border-radius: 4px;
                padding: 0.5rem;
            }}
            .stTabs [data-baseweb="tab"] {{
                height: 50px;
                background-color: {theme_config['theme']['backgroundColor']};
                border-radius: 4px;
                color: {theme_config['theme']['textColor']};
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            .stTabs [aria-selected="true"] {{                
                color: {theme_config['theme']['secondaryBackgroundColor']};
            }}
            .stTabs [data-baseweb="tab"]:hover {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['backgroundColor']};
                font-weight: 800;
                opacity: 0.8;
            }}

             /* Expander */
            .streamlit-expanderHeader {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['textColor']};
                border-radius: 4px;
                border: 1px solid {theme_config['theme']['primaryColor']};
                padding: 0.5rem;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            .streamlit-expanderHeader:hover {{
                background-color: {theme_config['theme']['primaryColor']};
                color: {theme_config['theme']['backgroundColor']};
            }}
            .streamlit-expanderContent {{
                background-color: {theme_config['theme']['backgroundColor']};
                color: {theme_config['theme']['textColor']};
                border: 1px solid {theme_config['theme']['primaryColor']};
                border-top: none;
                border-radius: 0 0 4px 4px;
                padding: 0.5rem;
            }}

            /* Checkbox */
            .stCheckbox > label > span {{
                color: {theme_config['theme']['textColor']};
            }}
            .stCheckbox > label > div[data-baseweb="checkbox"] {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
            }}
            .stCheckbox > label > div[data-baseweb="checkbox"] > div {{
                background-color: {theme_config['theme']['primaryColor']};
            }}

            /* Slider */
            .stSlider > div > div > div > div {{
                background-color: {theme_config['theme']['primaryColor']};
            }}
            .stSlider > div > div > div > div > div {{
                color: {theme_config['theme']['backgroundColor']};
            }}

            /* Table */
            .dataframe {{
                color: {theme_config['theme']['textColor']} !important;
            }}
            .dataframe th {{
                color: {theme_config['theme']['textColor']} !important;
            }}
            .dataframe td {{
                color: {theme_config['theme']['textColor']} !important;
            }}

            /* File uploader */
            .stFileUploader > div > div {{
                color: {theme_config['theme']['textColor']} !important;
            }}

            /* Info, warning, and error messages */
            .stAlert > div {{
                color: {theme_config['theme']['textColor']} !important;
            }}

            /* Sidebar styling */
            [data-testid="stSidebar"] {{
                background-color: #292727;
            }}
            [data-testid="stSidebar"] .stButton > button {{
                background-color: #25cf47;
                color: white;
            }}
            [data-testid="stSidebar"] .stTextInput > div > div > input {{
                background-color: #3E3E3E;
                color: white;
            }}
            [data-testid="stSidebar"] .stSelectbox > div > div > div {{
                background-color: #3E3E3E;
                color: white;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
                color: white;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {{
                color: white;
            }}
            [data-testid="stSidebar"] .stCheckbox > label > span {{
                color: white;
            }}

            /* Hide Streamlit Hamburger Menu and "Deploy" Button */
            .stApp > header {{
                display: none !important;
            }}

            /* Adjust the main content area to take up the space of the removed header */
            .stApp > .main {{
                margin-top: -4rem;
            }}

            /* Chat message styling */
            .chat-message, .chat-message p, .chat-message li, .chat-message h1, .chat-message h2, .chat-message h3, .chat-message h4, .chat-message h5, .chat-message h6 {{
                color: white !important;
            }}
            .assistant-response, .assistant-response p, .assistant-response li, .assistant-response h1, .assistant-response h2, .assistant-response h3, .assistant-response h4, .assistant-response h5, .assistant-response h6 {{
                color: white !important;
            }}
            .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {{
                color: white !important;
            }}
            
              /* Pulsating spike animation */
            @keyframes pulse-spike {{
                0% {{ transform: scaleY(0.4); opacity: 0.3; }}
                50% {{ transform: scaleY(1); opacity: 1; }}
                100% {{ transform: scaleY(0.4); opacity: 0.3; }}
            }}
            .pulsating-spike-container {{
                display: flex;
                align-items: center;
                margin-bottom: 10px;
            }}
            .pulsating-spike {{
                width: 4px;
                height: 20px;
                background-color: #ff0000;
                display: inline-block;
                margin-right: 3px;
                animation: pulse-spike 0.8s ease-in-out infinite;
            }}
            .pulsating-spike:nth-child(2) {{
                animation-delay: 0.1s;
            }}
            .pulsating-spike:nth-child(3) {{
                animation-delay: 0.2s;
            }}
            .amusing-remark {{
                margin-left: 10px;
                font-style: italic;
                color: #888;
            }}
          
            /* Separator for tabs */
            .separator {{
                width: 100%;
                height: 2px;
                background-color: red;
                margin: 1rem 0;
            }}
            
              /* Comprehensive Slider Styling */
            .stSlider label,
            .stSlider text,
            .stSlider .st-bb,
            .stSlider .st-bv,
            .stSlider .st-cj,
            .stSlider .st-cl,
            .stSlider [data-baseweb="slider"] {{
                color: white !important;
            }}
            
            /* Ensure all text within the slider container is white */
            [data-testid="stSlider"] {{
                color: white !important;
            }}
            
            /* Target specific parts of the slider */
            [data-testid="stSlider"] > div > div > div {{
                color: white !important;
            }}
            
            /* Slider thumb label */
            [data-testid="stSlider"] [data-testid="stThumbValue"] {{
                color: white !important;
            }}
            
             /* Enhanced Expander Styling */
            .streamlit-expanderHeader {{
                background-color: {theme_config['theme']['primaryColor']};
                color: {theme_config['theme']['backgroundColor']};
                border-radius: 8px 8px 0 0;
                border: 2px solid {theme_config['theme']['primaryColor']};
                padding: 0.75rem 1rem;
                font-weight: 600;
                font-size: 1.1em;
                transition: all 0.3s ease;
                margin-top: 1rem;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .streamlit-expanderHeader:hover {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['primaryColor']};
            }}
            .streamlit-expanderContent {{
                background-color: {theme_config['theme']['secondaryBackgroundColor']};
                color: {theme_config['theme']['textColor']};
                border: 2px solid {theme_config['theme']['primaryColor']};
                border-top: none;
                border-radius: 0 0 8px 8px;
                padding: 1rem;
                margin-bottom: 1rem;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            
            /* Expander icon styling */
            .streamlit-expanderHeader svg {{
                transform: scale(1.5);
                fill: {theme_config['theme']['backgroundColor']};
                transition: all 0.3s ease;
            }}
            .streamlit-expanderHeader:hover svg {{
                fill: {theme_config['theme']['primaryColor']};
            }}
        </style>
        """
        st.markdown(theme_css, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"An error occurred while applying the theme: {str(e)}")

def maximize_content_area():
    """
    Maximize the content area by hiding default Streamlit elements and adjusting layout.
    """
    hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stApp {
            max-width: 100%;
            padding-top: 0rem;
        }
        .main .block-container {
            max-width: 100%;
            padding-top: 1rem;
            padding-right: 1rem;
            padding-left: 1rem;
            padding-bottom: 1rem;
        }
        .sidebar .sidebar-content {
            width: 300px;
        }
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

def apply_expander_style():
    """
    Apply custom styling to Streamlit expander components.
    """
    expander_style = """
        <style>
        .streamlit-expanderHeader {
            background-color: #4CAF50;
            color: white;
            border-radius: 8px 8px 0 0;
            border: 2px solid #4CAF50;
            padding: 0.75rem 1rem;
            font-weight: 600;
            font-size: 1.1em;
            transition: all 0.3s ease;
            margin-top: 1rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .streamlit-expanderHeader:hover {
            background-color: #45a049;
        }
        .streamlit-expanderContent {
            background-color: #1E1E1E;
            color: white;
            border: 2px solid #4CAF50;
            border-top: none;
            border-radius: 0 0 8px 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .streamlit-expanderHeader svg {
            transform: scale(1.5);
            fill: white;
            transition: all 0.3s ease;
        }
        .streamlit-expanderHeader:hover svg {
            fill: #E0E0E0;
        }
        </style>
    """
    st.markdown(expander_style, unsafe_allow_html=True)