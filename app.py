import streamlit as st
import requests
import time

def initialize_session_state():
    """Initialize session state variables."""
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ''
    if 'api_endpoint' not in st.session_state:
        st.session_state.api_endpoint = ''
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'upload_complete' not in st.session_state:
        st.session_state.upload_complete = False
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False

def auth_form():
    """Display authentication form and handle credentials."""
    with st.form("auth_form"):
        st.text_input("API Endpoint", key="input_api_endpoint", 
                     placeholder="https://your-api-id.execute-api.region.amazonaws.com/dev/generate-url")
        st.text_input("API Key", type="password", key="input_api_key",
                     placeholder="Enter your API key")
        submitted = st.form_submit_button("Authenticate")
        
        if submitted:
            if not st.session_state.input_api_endpoint or not st.session_state.input_api_key:
                st.error("Both API Endpoint and API Key are required")
                return
                
            # Save credentials to session state
            st.session_state.api_key = st.session_state.input_api_key
            st.session_state.api_endpoint = st.session_state.input_api_endpoint
            st.session_state.authenticated = True
            st.success("Authentication successful! You can now upload files.")
            st.rerun()

def get_presigned_urls(file_name):
    """Get presigned URLs for upload and download from the API."""
    try:
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': st.session_state.api_key
        }
        
        response = requests.post(
            st.session_state.api_endpoint,
            headers=headers,
            json={'file_name': file_name}
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            st.error("Authentication failed. Please check your API key.")
            st.session_state.authenticated = False
            return None
        else:
            st.error(f"Error getting presigned URL: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error calling API: {str(e)}")
        return None

def main():
    st.title("PDF Transaction Extractor")
    
    # Initialize session state
    initialize_session_state()
    
    # Display sidebar with authentication status
    with st.sidebar:
        st.title("Authentication")
        if st.session_state.authenticated:
            st.success("Authenticated ")
            st.info(f"API Endpoint: {st.session_state.api_endpoint}")
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.api_key = ''
                st.session_state.api_endpoint = ''
                st.session_state.upload_complete = False
                st.session_state.processing_complete = False
                st.rerun()
        else:
            st.warning("Not authenticated")
            auth_form()
    
    # Main content
    if st.session_state.authenticated:
        st.write("Upload your PDF bank statement and we'll extract the transactions for you.")
        
        uploaded_file = st.file_uploader("Choose a PDF file", type=['pdf'])

        if uploaded_file:
            file_name = uploaded_file.name
            
            # Get presigned URLs
            urls = get_presigned_urls(file_name)
            
            if urls:
                # Create a progress container
                progress_container = st.empty()
                status_text = st.empty()
                
                # Upload file using the presigned URL
                try:
                    with progress_container.container():
                        st.info("Uploading file...")
                        
                    headers = {'Content-Type': 'application/pdf'}
                    upload_response = requests.put(
                        urls['upload_url'],
                        data=uploaded_file.getbuffer(),
                        headers=headers
                    )
                    
                    if upload_response.status_code == 200:
                        st.session_state.upload_complete = True
                        progress_container.success("File uploaded successfully!")
                        
                        # Wait for processing
                        status_text.info("Processing your PDF... This may take a few moments.")
                        
                        # Check status for up to 2 minutes
                        for i in range(24):  # 24 * 5 seconds = 2 minutes
                            # Try to access the download URL
                            try:
                                response = requests.head(urls['download_url'])
                                if response.status_code == 200:
                                    st.session_state.processing_complete = True
                                    status_text.success("Processing complete! Your CSV file is ready.")
                                    st.markdown(f"[Download your processed CSV file]({urls['download_url']})")
                                    break
                            except:
                                pass
                                
                            time.sleep(5)
                        else:
                            status_text.warning("Processing is taking longer than expected. Please check back later using the download link.")
                            st.markdown(f"[Check your CSV file here]({urls['download_url']})")
                            
                    else:
                        progress_container.error("Failed to upload file.")
                        
                except Exception as e:
                    progress_container.error(f"Error during upload: {str(e)}")
    else:
        st.info("Please authenticate using the sidebar to upload files.")

if __name__ == "__main__":
    main()
