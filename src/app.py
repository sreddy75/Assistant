import time
import requests
import streamlit as st
import base64
from ui.components.layout import set_page_layout
from ui.components.sidebar import render_sidebar
from ui.components.chat import render_chat, debug_knowledge_base
from utils.auth import BACKEND_URL, login, logout, is_authenticated, login_required, register, request_password_reset, reset_password, is_valid_email, verify_email


def login_form():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("Welcome to Compare the Meerkat!")

        # Display the animated meerkat logo
        file_ = open("images/meerkat_logo.gif", "rb")
        contents = file_.read()
        data_url = base64.b64encode(contents).decode("utf-8")
        file_.close()

        st.markdown(
            f'<div style="display: flex; justify-content: center; margin-bottom: 20px;">'
            f'<img src="data:image/gif;base64,{data_url}" alt="meerkat logo" width="200">'
            f'</div>',
            unsafe_allow_html=True,
        )

        tab1, tab2, tab3 = st.tabs(["Login", "Register", "Reset Password"])
        
        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Log In"):
                if is_valid_email(email):
                    if login(email, password):
                        st.session_state.authenticated = True
                        st.session_state.initialization_complete = False
                        st.rerun()
                    else:
                        st.error("Invalid email or password")
                else:
                    st.error("Please enter a valid email address")

    with tab2:
        new_email = st.text_input("Email", key="register_email")
        new_password = st.text_input("Password", type="password", key="register_password")
        if st.button("Register"):
            if is_valid_email(new_email):
                success, message = register(new_email, new_password)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.error("Please enter a valid email address")

    with tab3:
        reset_email = st.text_input("Email", key="reset_email")
        if st.button("Reset Password"):
            if is_valid_email(reset_email):
                success, message = request_password_reset(reset_email)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.error("Please enter a valid email address")

def initialize_app():
    # Simulate initialization process
    time.sleep(5)  # Adjust this value based on your actual initialization time
    set_page_layout()
    render_sidebar()
    st.session_state.initialization_complete = True

def reset_password_form():
    st.title("Reset Your Password")

    token = st.query_params.get("token", "")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")

    if st.button("Reset Password"):
        if new_password != confirm_password:
            st.error("Passwords do not match")
        elif len(new_password) < 8:
            st.error("Password must be at least 8 characters long")
        else:
            success, message = reset_password(token, new_password)
            if success:
                st.success(message)
                st.info("You can now log in with your new password")
                # Clear the token from query params
                st.query_params.clear()
                # Add a button to go to login page
                if st.button("Go to Login"):
                    st.rerun()
            else:
                st.error(message)
                
def verify_email_form():
    st.title("Email Verification")

    token = st.query_params.get("token", "")
    
    if token:
        success, message = verify_email(token)
        if success:
            st.success(message)
            st.info("Your email has been verified. You can now log in to your account.")
            # Clear the token from query params
            st.query_params.clear()
            # Add a button to go to login page
            if st.button("Go to Login"):
                st.rerun()
        else:
            st.error(message)
    else:
        st.error("Invalid verification link. Please check your email and try again.")                            

def check_token_validity():
    if 'token' in st.session_state:
        try:
            response = requests.get(f"{BACKEND_URL}/users/me", headers={"Authorization": f"Bearer {st.session_state['token']}"})
            if response.status_code != 200:
                logout()
                st.rerun()
            else:
                # Update email in session state
                st.session_state['email'] = response.json().get('email')
        except requests.exceptions.RequestException:
            logout()
            st.rerun()
            
def main_app():
    st.sidebar.title("Compare the Meerkat")
    if 'email' in st.session_state:
        st.sidebar.write(f"Welcome, {st.session_state['email']}!")
    else:   
        st.sidebar.write("Welcome!")

    # Add logout link to sidebar
    if st.sidebar.button("Logout"):
        logout()
        st.rerun()

    render_chat()

def main():
    st.set_page_config(
        page_title="Compare the Meerkat Assistant",
        page_icon="favicon.png",
    )

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "initialization_complete" not in st.session_state:
        st.session_state.initialization_complete = False

    if "logout" in st.query_params:
        logout()
        st.query_params.clear()
        st.rerun()

    if "message" in st.query_params:
        st.success(st.query_params["message"])
        st.query_params.clear()

    if "token" in st.query_params:
        if "verify" in st.query_params:
            verify_email_form()
        elif "reset" in st.query_params:
            reset_password_form()
        else:
            st.error("Invalid link. Please check your email and try again.")
    elif st.session_state.authenticated:
        if not st.session_state.initialization_complete:
            with st.spinner("Loading the Meerkats...!!!"):
                initialize_app()
                st.rerun()
        else:
            main_app()
    else:
        login_form()

if __name__ == "__main__":
    main()