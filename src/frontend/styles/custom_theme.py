import streamlit as st
import requests
import toml
from utils.api import BACKEND_URL
from utils.helpers import get_client_name

def load_theme_config():
    """
    Load the theme configuration from the server.
    Returns the theme config if successful, None otherwise.
    """
    client_name = get_client_name()
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/organizations/public-config/{client_name}")
        response.raise_for_status()
        config_content = response.text
        theme_config = toml.loads(config_content)
        return theme_config.get('theme', {})
    except requests.RequestException as e:
        st.warning(f"Failed to load theme configuration: {str(e)}")
        return None
    except toml.TomlDecodeError:
        st.warning("Invalid theme configuration format")
        return None

def apply_custom_theme(theme_config=None):
    """
    Apply a custom theme to the Streamlit app based on the provided configuration.
    If no configuration is provided, uses default values.
    """
    if theme_config is None:
        theme_config = {
            'textColor': '#000000',
            'backgroundColor': '#FFFFFF',
            'secondaryBackgroundColor': '#F0F2F6',
            'primaryColor': '#4CAF50',
            'font': 'sans-serif'
        }

    theme_css = f"""
    <style>
        /* Global styles */
        .stApp, .stApp p, .stApp label, .stApp .stMarkdown, .stApp .stText {{
            color: {theme_config.get('textColor', '#000000')};
        }}
        .stApp {{
            background-color: {theme_config.get('backgroundColor', '#FFFFFF')};
        }}
        * {{
            font-family: {theme_config.get('font', 'sans-serif')};
        }}

        /* Input fields */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div > div,
        .stMultiSelect > div > div > div {{
            color: {theme_config.get('textColor', '#000000')};                
            background-color: {theme_config.get('secondaryBackgroundColor', '#F0F2F6')};
            border: 1px solid {theme_config.get('primaryColor', '#4CAF50')};
            border-radius: 4px;
        }}

        /* Login page*/
            .login-form {{
                max-width: 400px;
                margin: 0 auto;
                padding: 20px;
                background-color: {theme_config.get('primaryColor', '#4CAF50')};
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            .login-form input {{
                width: 100%;
                margin-bottom: 10px;
            }}
            .login-form .stButton > button {{
                width: 100%;
            }}
            .separator {{
                width: 100%;
                height: 2px;
                background-color: #4CAF50;
                margin: 1rem 0;
            }}
            .centered-image {{
                display: flex;
                justify-content: center;
                margin-bottom: 20px;
            }}
            /* Select box */
            .stSelectbox > div > div::before {{
                background-color: {theme_config.get('primaryColor', '#4CAF50')};
            }}
            .stSelectbox > div > div > div:hover {{
                border-color: {theme_config.get('primaryColor', '#4CAF50')};
            }}
            .stSelectbox > div > div > div[aria-selected="true"] {{
                background-color: {theme_config.get('primaryColor', '#4CAF50')};
                color: {theme_config.get('backgroundColor', '#FFFFFF')};
            }}

            /* Buttons */
            .stButton > button {{
                color: {theme_config.get('backgroundColor', '#FFFFFF')};                
                background-color: {theme_config.get('primaryColor', '#4CAF50')};
                border: none;
                border-radius: 4px;
                padding: 0.5rem 1rem;
                font-weight: bold;
            }}
            .stButton > button:hover {{
                background-color: {theme_config.get('secondaryBackgroundColor', '#F0F2F6')};
                color: {theme_config.get('primaryColor', '#4CAF50')};
            }}

            /* Tabs */
            .stTabs {{
                background-color: {theme_config.get('backgroundColor', '#FFFFFF')};
            }}
            .stTabs [data-baseweb="tab-list"] {{
                gap: 25px;
                background-color: {theme_config.get('backgroundColor', '#FFFFFF')};
                border-radius: 4px;
                padding: 0.5rem;
            }}
            .stTabs [data-baseweb="tab"] {{
                height: 50px;
                background-color: {theme_config.get('backgroundColor', '#FFFFFF')};
                border-radius: 4px;
                color: {theme_config.get('textColor', '#000000')} !important;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            .stTabs [aria-selected="true"] {{                
                color: {theme_config.get('secondaryBackgroundColor', '#F0F2F6')};
            }}
            .stTabs [data-baseweb="tab"]:hover {{
                background-color: {theme_config.get('secondaryBackgroundColor', '#F0F2F6')};
                color: {theme_config.get('backgroundColor', '#FFFFFF')};
                font-weight: 800;
                opacity: 0.8;
            }}

            /* Expander */
            .streamlit-expanderHeader {{
                background-color: {theme_config.get('secondaryBackgroundColor', '#F0F2F6')};
                color: {theme_config.get('textColor', '#000000')} !important;
                border-radius: 4px;
                border: 1px solid {theme_config.get('primaryColor', '#4CAF50')};
                padding: 0.5rem;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            .streamlit-expanderHeader:hover {{
                background-color: {theme_config.get('primaryColor', '#4CAF50')};
                color: {theme_config.get('backgroundColor', '#FFFFFF')};
            }}
            .streamlit-expanderContent {{
                background-color: {theme_config.get('backgroundColor', '#FFFFFF')};
                color: {theme_config.get('textColor', '#000000')} !important;
                border: 1px solid {theme_config.get('primaryColor', '#4CAF50')};
                border-top: none;
                border-radius: 0 0 4px 4px;
                padding: 0.5rem;
            }}

            /* Checkbox */
            .stCheckbox > label > span {{
                color: {theme_config.get('textColor', '#000000')} !important;
            }}
            .stCheckbox > label > div[data-baseweb="checkbox"] {{
                background-color: {theme_config.get('secondaryBackgroundColor', '#F0F2F6')};
            }}
            .stCheckbox > label > div[data-baseweb="checkbox"] > div {{
                background-color: {theme_config.get('primaryColor', '#4CAF50')};
            }}

            /* Slider */
            .stSlider > div > div > div > div {{
                background-color: {theme_config.get('primaryColor', '#4CAF50')};
            }}
            .stSlider > div > div > div > div > div {{
                color: {theme_config.get('backgroundColor', '#FFFFFF')};
            }}

            /* Table */
            .dataframe {{
                color: {theme_config.get('textColor', '#000000')} !important;
            }}
            .dataframe th {{
                color: {theme_config.get('textColor', '#000000')} !important;
            }}
            .dataframe td {{
                color: {theme_config.get('textColor', '#000000')} !important;
            }}

            /* File uploader */
            .stFileUploader > div > div {{
                color: {theme_config.get('textColor', '#000000')} !important;
            }}

            /* Info, warning, and error messages */
            .stAlert > div {{
                color: {theme_config.get('textColor', '#000000')} !important;
            }}

            /* Sidebar styling */
            [data-testid="stSidebar"] {{
                background-color: {theme_config.get('secondaryBackgroundColor', '#F0F2F6')};
            }}
            [data-testid="stSidebar"] .stButton > button {{
                background-color: {theme_config.get('primaryColor', '#4CAF50')};
                color: {theme_config.get('backgroundColor', '#FFFFFF')};
            }}
            [data-testid="stSidebar"] .stTextInput > div > div > input {{
                background-color: {theme_config.get('backgroundColor', '#FFFFFF')};
                color: {theme_config.get('textColor', '#000000')} !important;
            }}
            [data-testid="stSidebar"] .stSelectbox > div > div > div {{
                background-color: {theme_config.get('backgroundColor', '#FFFFFF')};
                color: {theme_config.get('textColor', '#000000')} !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
                color: {theme_config.get('textColor', '#000000')} !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {{
                color: {theme_config.get('textColor', '#000000')} !important;
            }}
            [data-testid="stSidebar"] .stCheckbox > label > span {{
                color: {theme_config.get('textColor', '#000000')} !important;
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
            color: {theme_config.get('textColor', '#000000')} !important;
        }}
        .assistant-response, .assistant-response p, .assistant-response li, .assistant-response h1, .assistant-response h2, .assistant-response h3, .assistant-response h4, .assistant-response h5, .assistant-response h6 {{
            color: {theme_config.get('textColor', '#000000')} !important;
        }}
        .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {{
            color: {theme_config.get('textColor', '#000000')} !important;
        }}
    </style>
    """
    st.markdown(theme_css, unsafe_allow_html=True)

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
            max-width: 80%;
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