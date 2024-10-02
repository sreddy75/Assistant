# src/frontend/components/confluence_loader_component.py

import streamlit as st
from utils.api_helpers import get_confluence_spaces, sync_confluence_space

def render_confluence_loader(org_id):
    st.header("Confluence Data Loader")
    
    spaces = get_confluence_spaces(org_id)
    
    if not spaces:
        st.warning("No Confluence spaces available. Please configure Confluence integration.")
        return

    space_options = {space['name']: space['key'] for space in spaces}
    selected_space_name = st.selectbox("Select Confluence Space", list(space_options.keys()))
    selected_space_key = space_options[selected_space_name]

    if st.button("Load Confluence Space"):
        with st.spinner("Loading Confluence space..."):
            result = sync_confluence_space(org_id, selected_space_key)
        if result.get("success"):
            st.success(f"Confluence space '{selected_space_name}' loaded successfully!")
            st.session_state.confluence_space_loaded = True
            st.session_state.loaded_space_key = selected_space_key
        else:
            st.error(f"Failed to load Confluence space. Error: {result.get('error', 'Unknown error')}")

    if st.session_state.get("confluence_space_loaded"):
        st.info("Confluence space loaded. You can now use the Business Analysis Chat.")