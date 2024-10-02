import streamlit as st
import pandas as pd
from src.backend.utils.confluence_bulk_loader import ConfluenceBulkUploader

def render_bulk_uploader():
    st.title("Enhanced Confluence Bulk Page Uploader")

    # Confluence credentials
    url = st.text_input("Confluence URL", "https://your-domain.atlassian.net")
    username = st.text_input("Username (email)")
    api_token = st.text_input("API Token", type="password")
    space_key = st.text_input("Space Key")
    root_folder = st.text_input("Root Folder (optional)")

    # File uploader for CSV
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write(df)

        if st.button("Upload Pages"):
            uploader = ConfluenceBulkUploader(url, username, api_token)
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Save DataFrame to a temporary CSV file
            temp_csv = "temp_upload.csv"
            df.to_csv(temp_csv, index=False)

            # Perform the bulk upload
            uploader.bulk_upload_from_csv(space_key, temp_csv, root_folder if root_folder else None)

            # Update progress
            for i in range(100):
                progress_bar.progress(i + 1)
                status_text.text(f"Uploading: {i + 1}%")

            status_text.text("Upload completed!")
            st.success("All pages have been uploaded successfully!")

if __name__ == "__main__":
    render_bulk_uploader()