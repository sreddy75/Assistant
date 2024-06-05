import nest_asyncio
import streamlit as st
from kr8.utils.ut import initialize_usage_tracking
from ui.components.layout import set_page_layout
from ui.components.sidebar import render_sidebar
from ui.components.chat import render_chat

nest_asyncio.apply()

def main() -> None:
    st.set_page_config(
        page_title="Assistant",
        page_icon="favicon.png",
    )

    set_page_layout()
    initialize_usage_tracking()
    render_sidebar()
    render_chat()

if __name__ == "__main__":
    main()