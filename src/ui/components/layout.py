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

    image_path = "rozy_transparent.png"
    icon_image = Image.open(image_path)
    # Convert the image to base64
    buffered = io.BytesIO()
    icon_image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    st.markdown(
        f"""
        <style>
        .centered-image {{
            display: flex;
            justify-content: left;
            align-items: center;
            width: 100%;
        }}
        .centered-image img {{
            max-width: 100px;
            height: auto;
        }}
        </style>
        <div class="centered-image">
            <img src="data:image/png;base64,{img_str}" alt="Centered Icon">
        </div>
        """,
        unsafe_allow_html=True
    )