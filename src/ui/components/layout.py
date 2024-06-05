import streamlit as st
from PIL import Image
import base64
import io

def set_page_layout():
    # Inject custom CSS to use Comic Sans
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Comic+Sans+MS:wght@400;700&display=swap');

        html, body, [class*="css"]  {
            font-family: 'Helvetica', cursive, sans-serif;
            background-color: #F0F0F0;
            color: #333333;
        }

        .stButton>button {
            background-color: #4CAF50;
            color: #FFFFFF;
            border: none;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 4px;
        }
        .dark-divider {
            border-top: 2px solid #2b2924;
            margin: 10px 0;
        }    
        /* Target the div that contains the select box */
        .stSelectbox div[data-baseweb="select"] > div {
            color: black;
            background-color: white; 
        }

        /* Ensure the dropdown items are also styled */
        .stSelectbox div[data-baseweb="select"] .css-1nq2h4b {
            color: black;
            background-color: white; 
        }
        /* Target the text input box */
        input[type="text"] {
            color: white;
            background-color: white; 
        }
  
        </style>
        """,
        unsafe_allow_html=True
    )

    image_path = "rozy.png"
    icon_image = Image.open(image_path)
    # Convert the image to base64
    buffered = io.BytesIO()
    icon_image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # Create a custom title with an icon using markdown and HTML
    st.markdown(
        f"""
        <style>
        .title-with-icon {{
            display: flex;
            align-items: center;
        }}
        .title-with-icon img {{
            margin-right: 10px;
        }}
        
        </style>
        <div class="title-with-icon">
            <img src="data:image/png;base64,{img_str}" width="75" height="75">        
            <H3> Assistant</H3>
        </div>    
        """,
        unsafe_allow_html=True
    )