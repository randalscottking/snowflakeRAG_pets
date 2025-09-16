import streamlit as st
import pandas as pd
from datetime import datetime
import json
from snowflake.snowpark.context import get_active_session
from typing import List, Dict, Any

# Get the current Snowflake session
session = get_active_session()

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
    .metric-card {
        background-color: #F8F9FA;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    .source-info {
        background-color: #E8F4F8;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin: 0.5rem 0;
        font-size: 0.9em;
        border-left: 3px solid #2E86AB;
    }
</style>
""", unsafe_allow_html=True)

class SnowflakeRAGService:
    """Handles RAG operations using Snowflake Cortex SQL functions"""
    
    def __init__(self, session):
        self.session = session
    
    def search_documents(self, query: str, search_service: str, limit: int = 5) -> List[Dict]:
        """Search for relevant documents using SNOWFLAKE.CORTEX.SEARCH SQL function"""
        try:
            # Escape single quotes in query
            escaped_query = query.replace("'", "''")
            
            # Build the search SQL query
            search_sql = f"""
            SELECT SNOWFLAKE.CORTEX.SEARCH(
                '{search_service}',
                '{escaped_query}',
                {{'limit': {limit}}}
            ) as search_results
            """
            
            # Execute the search
            result_df = self.session.sql(search_sql).collect()
            
            if result_df and len(result_df) > 0:
                search_result = result_df[0]['SEARCH_RESULTS']
                if isinstance(search_result, str):
                    # Parse JSON string if needed
                    import json
                    search_data = json.loads(search_result)
                else:
                    search_data = search_result
                
                # Extract results array
                if isinstance(search_data, dict) and 'results' in search_data:
                    return search_data['results']
                elif isinstance(search_data, list):
                    return search_data
                else:
                    return [search_data] if search_data else []
            
            return []
            
        except Exception as e:
            st.error(f"Search failed: {str(e)}")
            return []
    
    def generate_response(self, query: str, context: str, pet_info: Dict = None, 
                         model: str = "llama3-8b") -> str:
        """Generate response using SNOWFLAKE.CORTEX.COMPLETE SQL function"""
        try:
            # Build pet context if available
            pet_context = ""
            if pet_info and any(pet_info.values()):
                pet_details = []
                if pet_info.get('name'):
                    pet_details.append(f"Pet name: {pet_info['name']}")
                if pet_info.get('type'):
                    pet_details.append(f"Type: {pet_info['type']}")
                if pet_info.get('breed'):
                    pet_details.append(f"Breed: {pet_info['breed']}")
                if pet_info.get('age'):
                    pet_details.append(f"Age: {pet_info['age']} years")
                if pet_info.get('weight'):
                    pet_details.append(f"Weight: {pet_info['weight']} lbs")
                if pet_info.get('spayed_neutered'):
                    pet_details.append(f"Spayed/Neutered: {pet_info['spayed_neutered']}")
                if pet_info.get('medical_conditions'):
                    pet_details.append(f"Medical conditions: {pet_info['medical_conditions']}")
                
                if pet_details:
                    pet_context = f"\n\nPet Information:\n{', '.join(pet_details)}"
            
            prompt = f"""You are a helpful veterinary assistant AI designed to provide general information about pet health. 

IMPORTANT GUIDELINES:
- Provide helpful, accurate information based on the knowledge base context
- Always include appropriate medical disclaimers
- Remind users to consult with a licensed veterinarian for proper diagnosis and treatment
- Never provide specific medical diagnoses or treatment recommendations
- If the question involves emergency symptoms, advise immediate veterinary care
- Be empathetic and understanding of pet owners' concerns
- Keep responses concise but informative

Context from veterinary knowledge base:
{context}
{pet_context}

User Question: {query}

Please provide a helpful, informative response while maintaining appropriate medical disclaimers."""

            # Escape single quotes in the prompt
            escaped_prompt = prompt.replace("'", "''")
            
            # Build the completion SQL query
            completion_sql = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                '{model}',
                '{escaped_prompt}'
            ) as response
            """
            
            # Execute the completion
            result_df = self.session.sql(completion_sql).collect()
            
            if result_df and len(result_df) > 0:
                response = result_df[0]['RESPONSE']
                return response if response else "I'm sorry, I couldn't generate a response at this time."
            
            return "I'm sorry, I couldn't generate a response at this time."
            
        except Exception as e:
            st.error(f"Response generation failed: {str(e)}")
            return "I encountered an error while processing your question. Please try again."

def initialize_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'rag_service' not in st.session_state:
        st.session_state.rag_service = SnowflakeRAGService(session)
    if 'search_service' not in st.session_state:
        st.session_state.search_service = ""
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = "llama3-8b"

def display_configuration_sidebar():
    """Display RAG configuration in sidebar"""
    st.sidebar.markdown("### ⚙️ Configuration")
    
    # Search service configuration
    search_service = st.sidebar.text_input(
        "Cortex Search Service Name",
        value=st.session_state.search_service,
        placeholder="e.g., PET_HEALTH_SEARCH",
        help="Enter the name of your Cortex Search service containing pet health documents"
    )
    
    if search_service:
        st.session_state.search_service = search_service
    
    # Model selection - Available models in Snowflake Cortex
    available_models = [
        "llama3-8b",
        "llama3-70b", 
        "llama3.1-8b",
        "llama3.1-70b",
        "llama3.1-405b",
        "mixtral-8x7b",
        "mistral-large",
        "mistral-7b",
        "reka-flash",
        "reka-core",
        "gemma-7b"
    ]
    
    selected_model = st.sidebar.selectbox(
        "LLM Model",
        options=available_models,
        index=available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0,
        help="Choose the language model for generating responses"
    )
    st.session_state.selected_model = selected_model
    
    # Search parameters
    st.sidebar.markdown("#### Search Parameters")
    search_limit = st.sidebar.slider("Max Search Results", min_value=1, max_value=10, value=5)
    st.session_state.search_limit = search_limit
    
    # Test configuration
    if st.sidebar.button("Test Configuration"):
        if not st.session_state.search_service:
            st.sidebar.error("Please enter a search service name")
        else:
            try:
                with st.spinner("Testing..."):
                    test_results = st.session_state.rag_service.search_documents(
                        "test query", 
                        st.session_state.search_service, 
                        limit=1
                    )
                    st.sidebar.success("✅ Configuration valid!")
            except Exception as e:
                st.sidebar.error(f"❌ Configuration error: {str(e)}")

def display_pet_info_sidebar():
    """Display pet information input in sidebar"""
    st.sidebar.markdown("### 🐕 Pet Information")
    
    with st.sidebar.expander("Pet Details (Optional)", expanded=False):
        pet_name = st.text_input("Pet Name", placeholder="e.g., Buddy")
        
        pet_type = st.selectbox(
            "Pet Type", 
            ["", "Dog", "Cat", "Bird", "Rabbit", "Guinea Pig", "Hamster", "Fish", "Reptile", "Other"],
            index=0
        )
        
        pet_breed = st.text_input("Breed", placeholder="e.g., Golden Retriever")
        
        col1, col2 = st.columns(2)
        with col1:
            pet_age = st.number_input("Age (years)", min_value=0.0, max_value=30.0, step=0.5, value=0.0)
        with col2:
            pet_weight = st.number_input("Weight (lbs)", min_value=0.0, step=0.1, value=0.0)
        
        # Additional pet info
        spayed_neutered = st.selectbox("Spayed/Neutered", ["Unknown", "Yes", "No"])
        medical_conditions = st.text_area("Known Medical Conditions", placeholder="Any existing conditions...")
        
        # Store pet info in session state
        st.session_state.pet_info = {
            "name": pet_name if pet_name else None,
            "type": pet_type if pet_type else None,
            "breed": pet_breed if pet_breed else None,
            "age": pet_age if pet_age > 0 else None,
            "weight": pet_weight if pet_weight > 0 else None,
            "spayed_neutered": spayed_neutered if spayed_neutered != "Unknown" else None,
            "medical_conditions": medical_conditions if medical_conditions else None
        }

def display_conversation_controls():
    """Display conversation control buttons"""
    st.sidebar.markdown("### 💬 Conversation")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        if st.button("📥 Export", use_container_width=True) and st.session_state.messages:
            chat_export = {
                "timestamp": datetime.now().isoformat(),
                "pet_info": st.session_state.get('pet_info', {}),
                "search_service": st.session_state.get('search_service', ''),
                "model": st.session_state.get('selected_model', ''),
                "messages": st.session_state.messages
            }
            
            st.download_button(
                "Download Chat History",
                data=json.dumps(chat_export, indent=2, default=str),
                file_name=f"pet_health_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )

def display_sample_questions():
    """Display sample questions for users"""
    st.sidebar.markdown("### 💡 Quick Questions")
    
    sample_questions = [
        "What are signs of dehydration in dogs?",
        "How often should I feed my kitten?",
        "What vaccinations does my puppy need?",
        "Is chocolate dangerous for dogs?",
        "How can I tell if my cat is stressed?",
        "Common symptoms of pet allergies?",
        "When should I worry about my pet's behavior?",
        "How to introduce pets to each other?"
    ]
    
    # Create a more compact display
    st.sidebar.markdown("Click a question to ask it:")
    for i, question in enumerate(sample_questions):
        if st.sidebar.button(f"❓ {question}", key=f"sample_{i}", use_container_width=True):
            st.session_state.current_question = question
            st.rerun()

def format_context_from_search(search_results: List[Dict]) -> tuple[str, List[Dict]]:
    """Format search results into context for the LLM and return source info"""
    if not search_results:
        return "No relevant information found in the knowledge base.", []
    
    context_parts = []
    sources = []
    
    for i, result in enumerate(search_results, 1):
        # Handle different possible result structures from Cortex Search
        if isinstance(result, dict):
            # Try different possible field names for content
            content = (result.get('chunk') or 
                      result.get('content') or 
                      result.get('text') or 
                      result.get('document') or 
                      str(result))
            
            # Try different possible field names for score/distance
            score = (result.get('distance') or 
                    result.get('score') or 
                    result.get('similarity') or 
                    'N/A')
            
            # Try different possible field names for source
            source = (result.get('file_name') or 
                     result.get('source') or 
                     result.get('document_name') or 
                     f'Document {i}')
        else:
            content = str(result)
            score = 'N/A'
            source = f'Document {i}'
        
        context_parts.append(f"[Source {i}]: {content}")
        sources.append({
            'index': i,
            'content': content[:200] + "..." if len(str(content)) > 200 else content,
            'score': score,
            'source': source
        })
    
    return "\n\n".join(context_parts), sources

def display_sources_info(sources: List[Dict]):
    """Display information about sources used"""
    if sources:
        with st.expander(f"📚 Sources Used ({len(sources)})", expanded=False):
            for source in sources:
                st.markdown(f"""
                <div class="source-info">
                    <strong>Source {source['index']}</strong> - Distance: {source['score']}<br>
                    <em>{source['source']}</em><br>
                    {source['content']}
                </div>
                """, unsafe_allow_html=True)

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
    
    # Check if search service is configured
    if not st.session_state.search_service:
        st.warning("⚙️ Please configure your Cortex Search service name in the sidebar to get started.")
        return
    
    # Display current pet info if available
    if st.session_state.get('pet_info') and any(st.session_state.pet_info.values()):
        pet_info = st.session_state.pet_info
        pet_summary = []
        if pet_info.get('name'):
            pet_summary.append(f"**{pet_info['name']}**")
        if pet_info.get('type'):
            pet_summary.append(pet_info['type'])
        if pet_info.get('breed'):
            pet_summary.append(pet_info['breed'])
        if pet_info.get('age'):
            pet_summary.append(f"{pet_info['age']} years old")
        
        if pet_summary:
            st.info(f"🐾 Current pet: {' • '.join(pet_summary)}")
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for i, message in enumerate(st.session_state.messages):
            message_class = "user-message" if message["role"] == "user" else "assistant-message"
            icon = "🧑" if message["role"] == "user" else "🤖"
            
            st.markdown(f"""
            <div class="chat-message {message_class}">
                <strong>{icon} {message["role"].title()}:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
            
            # Display sources for assistant messages
            if message["role"] == "assistant" and "sources" in message:
                display_sources_info(message["sources"])
    
    # Chat input
    question = st.chat_input("Ask me about your pet's health...")
    
    # Handle sample question selection
    if 'current_question' in st.session_state:
        question = st.session_state.current_question
        del st.session_state.current_question
    
    if question:
        # Add user message to chat
        st.session_state.messages.append({
            "role": "user", 
            "content": question, 
            "timestamp": datetime.now()
        })
        
        with st.spinner("🔍 Searching knowledge base and generating response..."):
            try:
                # Search for relevant documents
                search_results = st.session_state.rag_service.search_documents(
                    query=question,
                    search_service=st.session_state.search_service,
                    limit=st.session_state.get('search_limit', 5)
                )
                
                # Format context from search results
                context, sources = format_context_from_search(search_results)
                
                # Generate response
                response = st.session_state.rag_service.generate_response(
                    query=question,
                    context=context,
                    pet_info=st.session_state.get('pet_info'),
                    model=st.session_state.selected_model
                )
                
                # Add assistant message to chat
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response, 
                    "timestamp": datetime.now(),
                    "sources": sources,
                    "model": st.session_state.selected_model
                })
                
            except Exception as e:
                st.error(f"Error processing your question: {str(e)}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "I apologize, but I encountered an error processing your question. Please try again or contact support if the issue persists.",
                    "timestamp": datetime.now(),
                    "sources": [],
                    "error": str(e)
                })
        
        st.rerun()

def display_analytics():
    """Display simple analytics about the conversation"""
    if st.session_state.messages:
        st.sidebar.markdown("### 📊 Session Stats")
        
        user_messages = [msg for msg in st.session_state.messages if msg["role"] == "user"]
        assistant_messages = [msg for msg in st.session_state.messages if msg["role"] == "assistant"]
        
        # Metrics in a more compact format
        st.sidebar.markdown(f"""
        <div class="metric-card">
            <strong>{len(user_messages)}</strong><br>
            Questions Asked
        </div>
        """, unsafe_allow_html=True)
        
        st.sidebar.markdown(f"""
        <div class="metric-card">
            <strong>{len(assistant_messages)}</strong><br>
            Responses Given
        </div>
        """, unsafe_allow_html=True)
        
        # Average sources per response
        total_sources = sum(len(msg.get("sources", [])) for msg in assistant_messages)
        avg_sources = total_sources / len(assistant_messages) if assistant_messages else 0
        
        st.sidebar.markdown(f"""
        <div class="metric-card">
            <strong>{avg_sources:.1f}</strong><br>
            Avg. Sources Used
        </div>
        """, unsafe_allow_html=True)

def main():
    """Main application function"""
    initialize_session_state()
    
    # Sidebar
    with st.sidebar:
        display_configuration_sidebar()
        
        if st.session_state.search_service:
            display_pet_info_sidebar()
            display_sample_questions()
            display_conversation_controls()
            display_analytics()
    
    # Main content
    display_chat_interface()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9em;">
        💡 <strong>Tips:</strong> Be specific about your pet's symptoms or concerns. 
        Include your pet's species, breed, age, and any relevant medical history for better assistance.
        <br><br>
        🔧 <strong>Powered by:</strong> Snowflake Cortex AI • Built with Streamlit in Snowflake
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
