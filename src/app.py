import time
import streamlit as st
import base64
from ui.components.layout import set_page_layout
from ui.components.sidebar import render_sidebar
from ui.components.chat import render_chat
from utils.auth import login, logout, is_authenticated, login_required, register, request_password_reset, reset_password, is_valid_email

def login_form():
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
                    st.success("Logged in successfully!")
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
                time.sleep(3)  # Give user time to read the message
                st.rerun()  # Rerun the app to show the login form
            else:
                st.error(message)

def main_app():
    set_page_layout()

    st.sidebar.write(f"Welcome, {st.session_state['email']}!")
    
    # Add logout link to sidebar
    if st.sidebar.button("Logout"):
        logout()
        st.rerun()

    render_sidebar()
    render_chat()

def main():
    st.set_page_config(
        page_title="Compare the Meerkat Assistant",
        page_icon="favicon.png",
    )

    if "logout" in st.query_params:
        logout()
        st.query_params.clear()
        st.rerun()

    if "message" in st.query_params:
        st.success(st.query_params["message"])
        st.query_params.clear()

    if "token" in st.query_params:
        reset_password_form()
    elif is_authenticated():
        main_app()
    else:
        login_form()

if __name__ == "__main__":
    main()