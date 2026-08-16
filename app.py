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
if uploaded_file is not None:
    st.markdown(
        f"<div class='dataset-status'>Currently analyzing: <span>{uploaded_file.name}</span></div>",
        unsafe_allow_html=True
    )
else:
    st.markdown(
        "<div class='dataset-status'><span>No dataset loaded</span></div>",
        unsafe_allow_html=True
    )

# Calculate metrics from the loaded dataframe and file
num_rows = f"{agent_module.df.shape[0]:,}"
num_cols = f"{agent_module.df.shape[1]:,}"

try:
    file_size_bytes = os.path.getsize(agent_module.CURRENT_CSV_PATH)
except (FileNotFoundError, OSError):
    file_size_bytes = 0

if file_size_bytes >= 1024 * 1024:
    file_size_str = f"{file_size_bytes / (1024 * 1024):.2f} MB"
elif file_size_bytes > 0:
    file_size_str = f"{file_size_bytes / 1024:.2f} KB"
else:
    file_size_str = "0 KB (File not found)"

# Render metric cards or prompt user to upload a dataset
if agent_module.df.empty:
    st.info("👆 Upload a CSV file from the sidebar to get started. No dataset loaded yet.")
else:
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

# Define async question generator
async def generate_example_questions() -> list[str]:
    user_message = Content(
        role="user",
        parts=[Part(text="Based on the dataset schema, suggest exactly 5 short, specific questions a user could ask about this data. Return only a Python list of 5 strings, nothing else, no explanation.")]
    )
    
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
                
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    
    import ast
    parsed = ast.literal_eval(cleaned)
    if isinstance(parsed, list) and len(parsed) == 5 and all(isinstance(x, str) for x in parsed):
        return parsed
    raise ValueError("Failed to parse valid list of 5 strings")

DEFAULT_QUESTIONS = [
    "Which movie has the highest budget?",
    "What is the average rating?",
    "What is the most common genre?",
    "Show me a bar chart of movie count by genre",
    "Show me a histogram of ratings"
]

# Check if dataset path has changed to regenerate questions
if "active_path" not in st.session_state or st.session_state.active_path != agent_module.CURRENT_CSV_PATH or "example_questions" not in st.session_state:
    st.session_state.active_path = agent_module.CURRENT_CSV_PATH
    try:
        st.session_state.example_questions = asyncio.run(generate_example_questions())
        st.session_state.is_dynamic = True
    except Exception as e:
        st.session_state.example_questions = DEFAULT_QUESTIONS
        st.session_state.is_dynamic = False

# Render sidebar question buttons
clicked_question = None
if uploaded_file is None:
    st.sidebar.write("Upload a CSV file above to see suggested questions for your dataset.")
else:
    if st.session_state.get("is_dynamic", False):
        st.sidebar.caption("Suggested for this dataset")
    else:
        st.sidebar.write("Click an example question below to run it:")

    for question in st.session_state.example_questions:
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
