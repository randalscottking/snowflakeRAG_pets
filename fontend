import streamlit as st
import snowflake.connector
from snowflake.cortex import Complete
import pandas as pd
from datetime import datetime
import json
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="🐾 Pet Health Assistant",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        color: #2E86AB;
        border-bottom: 2px solid #A23B72;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #2E86AB;
        background-color: #F8F9FA;
    }
    .user-message {
        background-color: #E3F2FD;
        border-left-color: #2196F3;
    }
    .assistant-message {
        background-color: #E8F5E8;
        border-left-color: #4CAF50;
    }
    .warning-box {
        background-color: #FFF3E0;
        border: 1px solid #FF9800;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .sidebar-content {
        background-color: #F5F5F5;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

class SnowflakeRAGConnector:
    """Handles connection and queries to Snowflake Cortex Search"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    def connect(self, account: str, user: str, password: str, warehouse: str, 
                database: str, schema: str) -> bool:
        """Establish connection to Snowflake"""
        try:
            self.connection = snowflake.connector.connect(
                account=account,
                user=user,
                password=password,
                warehouse=warehouse,
                database=database,
                schema=schema
            )
            self.cursor = self.connection.cursor()
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def search_documents(self, query: str, search_service: str, limit: int = 5) -> List[Dict]:
        """Search for relevant documents using Cortex Search"""
        try:
            search_query = f"""
            SELECT SNOWFLAKE.CORTEX.SEARCH(
                '{search_service}',
                '{query}',
                {{'limit': {limit}}}
            ) as search_results
            """
            
            self.cursor.execute(search_query)
            results = self.cursor.fetchone()
            
            if results and results[0]:
                return json.loads(results[0])
            return []
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def generate_response(self, query: str, context: str, model: str = "llama2-70b-chat") -> str:
        """Generate response using Cortex Complete"""
        try:
            prompt = f"""
            You are a helpful veterinary assistant AI designed to provide general information about pet health. 
            
            IMPORTANT DISCLAIMERS:
            - Always remind users that this information is for general guidance only
            - Emphasize that they should consult with a licensed veterinarian for proper diagnosis and treatment
            - Never provide specific medical diagnoses or treatment recommendations
            - If the question involves emergency symptoms, advise immediate veterinary care
            
            Context from veterinary knowledge base:
            {context}
            
            User Question: {query}
            
            Please provide a helpful, informative response while maintaining appropriate medical disclaimers.
            """
            
            complete_query = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                '{model}',
                '{prompt.replace("'", "''")}'
            ) as response
            """
            
            self.cursor.execute(complete_query)
            result = self.cursor.fetchone()
            
            if result and result[0]:
                return result[0]
            return "I'm sorry, I couldn't generate a response at this time."
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return "I encountered an error while processing your question. Please try again."
    
    def close(self):
        """Close database connections"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

def initialize_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'rag_connector' not in st.session_state:
        st.session_state.rag_connector = SnowflakeRAGConnector()
    if 'connected' not in st.session_state:
        st.session_state.connected = False

def display_connection_sidebar():
    """Display connection settings in sidebar"""
    st.sidebar.markdown("### 🔧 Snowflake Connection")
    
    with st.sidebar.expander("Database Configuration", expanded=not st.session_state.connected):
        account = st.text_input("Account", placeholder="your-account.snowflakecomputing.com")
        user = st.text_input("Username")
        password = st.text_input("Password", type="password")
        warehouse = st.text_input("Warehouse", value="COMPUTE_WH")
        database = st.text_input("Database")
        schema = st.text_input("Schema", value="PUBLIC")
        search_service = st.text_input("Cortex Search Service Name", placeholder="PET_HEALTH_SEARCH")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Connect", type="primary"):
                if all([account, user, password, warehouse, database, schema]):
                    with st.spinner("Connecting to Snowflake..."):
                        success = st.session_state.rag_connector.connect(
                            account, user, password, warehouse, database, schema
                        )
                    if success:
                        st.session_state.connected = True
                        st.session_state.search_service = search_service
                        st.success("Connected successfully!")
                        st.rerun()
                    else:
                        st.error("Connection failed. Please check your credentials.")
                else:
                    st.error("Please fill in all required fields.")
        
        with col2:
            if st.button("Disconnect"):
                st.session_state.rag_connector.close()
                st.session_state.connected = False
                st.session_state.messages = []
                st.success("Disconnected successfully!")
                st.rerun()
    
    # Connection status
    if st.session_state.connected:
        st.sidebar.success("✅ Connected to Snowflake")
    else:
        st.sidebar.error("❌ Not connected")

def display_pet_info_sidebar():
    """Display pet information input in sidebar"""
    st.sidebar.markdown("### 🐕 Pet Information (Optional)")
    
    with st.sidebar.expander("Pet Details"):
        pet_name = st.text_input("Pet Name", placeholder="Buddy")
        pet_type = st.selectbox("Pet Type", ["Dog", "Cat", "Bird", "Rabbit", "Other"])
        pet_breed = st.text_input("Breed", placeholder="Golden Retriever")
        pet_age = st.number_input("Age (years)", min_value=0.0, max_value=30.0, step=0.5)
        pet_weight = st.number_input("Weight (lbs)", min_value=0.0, step=0.1)
        
        # Store pet info in session state
        st.session_state.pet_info = {
            "name": pet_name,
            "type": pet_type,
            "breed": pet_breed,
            "age": pet_age,
            "weight": pet_weight
        }

def display_conversation_controls():
    """Display conversation control buttons"""
    st.sidebar.markdown("### 💬 Conversation")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.sidebar.button("Clear Chat", type="secondary"):
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        if st.sidebar.button("Export Chat"):
            if st.session_state.messages:
                chat_export = {
                    "timestamp": datetime.now().isoformat(),
                    "messages": st.session_state.messages
                }
                st.sidebar.download_button(
                    "Download Chat",
                    data=json.dumps(chat_export, indent=2),
                    file_name=f"pet_health_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

def display_sample_questions():
    """Display sample questions for users"""
    st.sidebar.markdown("### 💡 Sample Questions")
    
    sample_questions = [
        "What are the signs of dehydration in dogs?",
        "How often should I feed my kitten?",
        "What vaccinations does my puppy need?",
        "Is chocolate really dangerous for dogs?",
        "How can I tell if my cat is stressed?",
        "What are common symptoms of allergies in pets?",
        "When should I be concerned about my pet's behavior?",
        "How do I introduce a new pet to my household?"
    ]
    
    for question in sample_questions:
        if st.sidebar.button(f"📝 {question}", key=f"sample_{hash(question)}"):
            st.session_state.current_question = question
            st.rerun()

def format_context_from_search(search_results: List[Dict]) -> str:
    """Format search results into context for the LLM"""
    if not search_results:
        return "No relevant information found in the knowledge base."
    
    context_parts = []
    for i, result in enumerate(search_results, 1):
        # Extract relevant fields from search result
        content = result.get('content', result.get('text', str(result)))
        score = result.get('score', 'N/A')
        context_parts.append(f"[Source {i} (Relevance: {score})]: {content}")
    
    return "\n\n".join(context_parts)

def display_chat_interface():
    """Display the main chat interface"""
    st.markdown('<h1 class="main-header">🐾 Pet Health Assistant</h1>', unsafe_allow_html=True)
    
    # Medical disclaimer
    st.markdown("""
    <div class="warning-box">
        <strong>⚠️ Important Medical Disclaimer:</strong><br>
        This AI assistant provides general information about pet health for educational purposes only. 
        It is not a substitute for professional veterinary advice, diagnosis, or treatment. 
        Always consult with a qualified veterinarian for your pet's specific health concerns.
        <strong>In case of emergency, contact your veterinarian or emergency animal hospital immediately.</strong>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.connected:
        st.warning("Please connect to Snowflake using the sidebar to start asking questions.")
        return
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            message_class = "user-message" if message["role"] == "user" else "assistant-message"
            icon = "🧑" if message["role"] == "user" else "🤖"
            
            st.markdown(f"""
            <div class="chat-message {message_class}">
                <strong>{icon} {message["role"].title()}:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
    
    # Chat input
    question = st.chat_input("Ask me about your pet's health...")
    
    # Handle sample question selection
    if 'current_question' in st.session_state:
        question = st.session_state.current_question
        del st.session_state.current_question
    
    if question:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": question, "timestamp": datetime.now()})
        
        with st.spinner("Searching knowledge base and generating response..."):
            # Search for relevant documents
            search_results = st.session_state.rag_connector.search_documents(
                query=question,
                search_service=st.session_state.get('search_service', 'PET_HEALTH_SEARCH'),
                limit=3
            )
            
            # Format context from search results
            context = format_context_from_search(search_results)
            
            # Add pet information to context if available
            if hasattr(st.session_state, 'pet_info') and st.session_state.pet_info['name']:
                pet_context = f"\nPet Information: {st.session_state.pet_info['name']} is a {st.session_state.pet_info['age']} year old {st.session_state.pet_info['breed']} {st.session_state.pet_info['type']}"
                if st.session_state.pet_info['weight']:
                    pet_context += f" weighing {st.session_state.pet_info['weight']} lbs"
                context += pet_context
            
            # Generate response
            response = st.session_state.rag_connector.generate_response(question, context)
            
            # Add assistant message to chat
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response, 
                "timestamp": datetime.now(),
                "sources": len(search_results)
            })
        
        st.rerun()

def display_analytics():
    """Display simple analytics about the conversation"""
    if st.session_state.messages:
        st.sidebar.markdown("### 📊 Session Stats")
        
        user_messages = [msg for msg in st.session_state.messages if msg["role"] == "user"]
        assistant_messages = [msg for msg in st.session_state.messages if msg["role"] == "assistant"]
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("Questions Asked", len(user_messages))
        with col2:
            st.metric("Responses Given", len(assistant_messages))
        
        # Average sources per response
        avg_sources = sum(msg.get("sources", 0) for msg in assistant_messages) / len(assistant_messages) if assistant_messages else 0
        st.sidebar.metric("Avg. Sources Used", f"{avg_sources:.1f}")

def main():
    """Main application function"""
    initialize_session_state()
    
    # Sidebar
    with st.sidebar:
        display_connection_sidebar()
        
        if st.session_state.connected:
            display_pet_info_sidebar()
            display_sample_questions()
            display_conversation_controls()
            display_analytics()
    
    # Main content
    display_chat_interface()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "💡 **Tips:** Be specific about your pet's symptoms or concerns. "
        "Include your pet's species, breed, age, and any relevant medical history for better assistance."
    )

if __name__ == "__main__":
    main()
