import streamlit as st
import asyncio
import os
import re
from dotenv import load_dotenv

# Load environment variables from the project root's .env file
load_dotenv(dotenv_path=os.path.abspath(os.path.join(os.path.dirname(__file__), ".env")))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from greeting_agent.agent import root_agent
import greeting_agent.agent as agent_module
from google.genai.types import Content, Part

# Configure the Streamlit page
st.set_page_config(page_title="AskMyData", page_icon="📊", layout="wide")

# Inject custom CSS for subtle background tint and purple/violet accent styling
st.markdown(
    """
    <style>
    /* Base background tint */
    .stApp {
        background-color: #f3f4f6 !important;
    }
    @media (prefers-color-scheme: dark) {
        .stApp {
            background-color: #13111f !important;
        }
    }

    /* Accent color override for primary theme color */
    :root {
        --primary-color: #7C3AED;
    }

    /* Currently analyzing status badge */
    .dataset-status {
        font-size: 1rem;
        font-weight: 500;
        margin-bottom: 1rem;
    }
    .dataset-status span {
        color: #7C3AED;
        background-color: #F5F3FF;
        padding: 4px 12px;
        border-radius: 20px;
        font-family: monospace;
        font-size: 0.9rem;
        border: 1px solid #E9D5FF;
    }
    @media (prefers-color-scheme: dark) {
        .dataset-status span {
            color: #C084FC;
            background-color: #2E1065;
            border-color: #5B21B6;
        }
    }

    /* Sidebar example buttons hover border and pill shape */
    [data-testid="stSidebar"] button {
        border-radius: 20px !important;
        transition: all 0.2s ease-in-out !important;
    }
    [data-testid="stSidebar"] button:hover {
        border-color: #7C3AED !important;
        color: #7C3AED !important;
        background-color: rgba(124, 58, 237, 0.05) !important;
    }

    /* File uploader button styling */
    [data-testid="stFileUploader"] button {
        border-radius: 20px !important;
        border-color: #7C3AED !important;
        color: #7C3AED !important;
        transition: all 0.2s ease-in-out !important;
    }
    [data-testid="stFileUploader"] button:hover {
        background-color: rgba(124, 58, 237, 0.08) !important;
        color: #6D28D9 !important;
        border-color: #6D28D9 !important;
    }

    /* Sidebar success notification color override to purple */
    [data-testid="stSidebar"] [data-testid="stNotification"] {
        background-color: #F5F3FF !important;
        border-color: #C084FC !important;
        color: #5B21B6 !important;
    }
    @media (prefers-color-scheme: dark) {
        [data-testid="stSidebar"] [data-testid="stNotification"] {
            background-color: #2E1065 !important;
            border-color: #7C3AED !important;
            color: #DDD6FE !important;
        }
    }

    /* Chat input submit button color */
    button[data-testid="stChatInputSubmitButton"] {
        color: #7C3AED !important;
    }
    button[data-testid="stChatInputSubmitButton"]:hover {
        color: #6D28D9 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📊 AskMyData")
st.markdown("##### Ask any question about your dataset in plain English. Works with any CSV - upload your own CSV in the sidebar to try a different dataset.")

# Sidebar for file uploader and example questions
st.sidebar.title("AskMyData")

# File uploader for custom CSV files
uploaded_file = st.sidebar.file_uploader("Upload your own CSV file", type=["csv"])

if uploaded_file is not None:
    # Save the uploaded file to a temp directory inside the workspace
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_uploads"))
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, uploaded_file.name)
    
    # Write the uploaded file
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Update the dataset path in the agent module
    agent_module.set_dataset_path(temp_path)
    st.sidebar.success(f"Now using: {uploaded_file.name}")
    active_dataset_name = uploaded_file.name
else:
    # Reset to default movie dataset
    default_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "tmdb_5000_movies.csv"))
    agent_module.set_dataset_path(default_path)
    active_dataset_name = "tmdb_5000_movies.csv (default)"

# Display currently active dataset status line using styled HTML
st.markdown(
    f"<div class='dataset-status'>Currently analyzing: <span>{active_dataset_name}</span></div>",
    unsafe_allow_html=True
)

# Calculate metrics from the loaded dataframe and file
num_rows = f"{agent_module.df.shape[0]:,}"
num_cols = f"{agent_module.df.shape[1]:,}"

file_size_bytes = os.path.getsize(agent_module.CURRENT_CSV_PATH)
if file_size_bytes >= 1024 * 1024:
    file_size_str = f"{file_size_bytes / (1024 * 1024):.2f} MB"
else:
    file_size_str = f"{file_size_bytes / 1024:.2f} KB"

# Render metric cards
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Rows", value=num_rows)
with col2:
    st.metric(label="Columns", value=num_cols)
with col3:
    st.metric(label="File Size", value=file_size_str)

st.markdown("---")

# Cache the initialization of the ADK runner and session service
@st.cache_resource
def init_adk():
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="AskMyData",
        session_service=session_service
    )
    return runner, session_service

runner, session_service = init_adk()

# Initialize session state for the ADK session ID
if "session_id" not in st.session_state:
    async def create_session():
        session = await session_service.create_session(app_name="AskMyData", user_id="streamlit_user")
        return session.id
    st.session_state.session_id = asyncio.run(create_session())

# Initialize session state for chat messages history
if "messages" not in st.session_state:
    st.session_state.messages = []

st.sidebar.write("Click an example question below to run it:")

example_questions = [
    "Which movie has the highest budget?",
    "What is the average rating?",
    "What is the most common genre?",
    "Show me a bar chart of movie count by genre",
    "Show me a histogram of ratings"
]

clicked_question = None
for question in example_questions:
    if st.sidebar.button(question):
        clicked_question = question

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["text"])
        if "chart" in msg and os.path.exists(msg["chart"]):
            st.image(msg["chart"])

# Helper function to run the agent synchronously
def run_agent(query: str) -> str:
    user_message = Content(role="user", parts=[Part(text=query)])
    
    async def get_response():
        response_text = ""
        async for event in runner.run_async(
            user_id="streamlit_user",
            session_id=st.session_state.session_id,
            new_message=user_message
        ):
            if event.message and event.message.parts:
                text_parts = [p.text for p in event.message.parts if p.text]
                if text_parts:
                    response_text = "".join(text_parts)
        return response_text

    return asyncio.run(get_response())

# Retrieve user input from the chat input or the clicked example question
user_query = st.chat_input("Ask something about the dataset...")
if clicked_question:
    user_query = clicked_question

# Execute query and process response
if user_query:
    # Display and append user message
    st.session_state.messages.append({"role": "user", "text": user_query})
    with st.chat_message("user"):
        st.write(user_query)
    
    # Process assistant response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing data..."):
            try:
                response_text = run_agent(user_query)
                
                chart_file = None
                display_text = response_text
                
                # Match CHART_GENERATED: followed by a filename ending with .png
                match = re.search(r"CHART_GENERATED:([^\s]+\.png)", response_text)
                if match:
                    filename = match.group(1)
                    chart_file = os.path.abspath(os.path.join(os.path.dirname(__file__), filename))
                    
                    # Split using the matched string to clean and isolate the descriptive message
                    marker_str = match.group(0)
                    parts = response_text.split(marker_str, 1)
                    desc_part = parts[1].strip()
                    if desc_part.startswith("-"):
                        desc_part = desc_part[1:].strip()
                    
                    prefix = parts[0].strip()
                    if prefix:
                        display_text = f"{prefix} {desc_part}"
                    else:
                        display_text = desc_part
                
                # Display text response
                st.write(display_text)
                
                # Display chart if generated
                if chart_file and os.path.exists(chart_file):
                    st.image(chart_file)
                    
                # Append assistant response to history
                history_entry = {"role": "assistant", "text": display_text}
                if chart_file:
                    history_entry["chart"] = chart_file
                st.session_state.messages.append(history_entry)
            except Exception as e:
                error_msg = "I'm currently experiencing high demand on the free tier and need a moment to recover. Please wait about a minute and try again."
                st.write(error_msg)
                st.session_state.messages.append({"role": "assistant", "text": error_msg})
            
            # Rerun to refresh state and prevent double submission
            st.rerun()
