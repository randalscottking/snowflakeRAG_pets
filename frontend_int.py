import streamlit as st
from snowflake.core import Root
from snowflake.cortex import Complete
from snowflake.snowpark.context import get_active_session
import json
from datetime import datetime

# --- Move session and root initialization to module-level to avoid NameError ---
session = get_active_session()
root = Root(session)

# Available models for Snowflake Cortex
MODELS = [
    "mistral-large2",
    "llama3.1-70b",
    "llama3.1-8b",
    "llama3-70b",
    "llama3-8b",
    "mixtral-8x7b",
    "reka-flash",
    "reka-core",
]

# Page configuration
st.set_page_config(
    page_title="🐾 Pet Health Assistant",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for pet health theme
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        color: #2E86AB;
        border-bottom: 3px solid #A23B72;
        margin-bottom: 2rem;
    }
    .warning-box {
        background-color: #FFF3E0;
        border: 2px solid #FF9800;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .pet-info-card {
        background-color: #E8F5E8;
        border: 1px solid #4CAF50;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #F0F8FF;
        border: 1px solid #2196F3;
        border-radius: 0.5rem;
        padding: 0.8rem;
        text-align: center;
        margin: 0.3rem 0;
    }
    .stChatMessage {
        border-radius: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def init_messages():
    """Initialize chat messages in session state"""
    if st.session_state.get("clear_conversation", False) or "messages" not in st.session_state:
        st.session_state.messages = []

def init_service_metadata():
    """Initialize cortex search service metadata"""
    if "service_metadata" not in st.session_state:
        service_metadata = []
        try:
            # Try to show services in current context first
            services = session.sql("SHOW CORTEX SEARCH SERVICES;").collect()
            if services:
                for s in services:
                    try:
                        svc_name = s["name"]
                        svc_search_col = session.sql(
                            f"DESC CORTEX SEARCH SERVICE {svc_name};"
                        ).collect()[0]["search_column"]
                        service_metadata.append(
                            {"name": svc_name, "search_column": svc_search_col}
                        )
                    except Exception as e:
                        st.sidebar.error(f"Error describing service {svc_name}: {e}")
            
            # Also try to specifically check for our known service in PETAPP.DATA
            try:
                # Try to describe the specific service we know about
                test_service = session.sql("DESC CORTEX SEARCH SERVICE PETAPP.DATA.CC_SEARCH_SERVICE_CS;").collect()
                if test_service:
                    # Check if it's already in our list
                    existing_names = [s["name"] for s in service_metadata]
                    if "PETAPP.DATA.CC_SEARCH_SERVICE_CS" not in existing_names:
                        service_metadata.append({
                            "name": "PETAPP.DATA.CC_SEARCH_SERVICE_CS",
                            "search_column": test_service[0]["search_column"]
                        })
            except Exception as e:
                st.sidebar.warning(f"Could not access PETAPP.DATA.CC_SEARCH_SERVICE_CS: {e}")
            
            # If still no services found, create fallback
            if not service_metadata:
                service_metadata = [{
                    "name": "PETAPP.DATA.CC_SEARCH_SERVICE_CS",
                    "search_column": "chunk"  # Common default
                }]
                st.sidebar.warning("Using fallback configuration for PETAPP.DATA.CC_SEARCH_SERVICE_CS")
        
        except Exception as e:
            st.sidebar.error(f"Error querying Cortex Search Services: {e}")
            # Fallback - assume the service exists with default search column
            service_metadata = [{
                "name": "PETAPP.DATA.CC_SEARCH_SERVICE_CS",
                "search_column": "chunk"  # Common default
            }]
            st.sidebar.warning("Using fallback configuration. Please verify the service exists.")
        
        st.session_state.service_metadata = service_metadata

def init_pet_info():
    """Initialize pet information in session state"""
    if "pet_info" not in st.session_state:
        st.session_state.pet_info = {}

def init_config_options():
    """Initialize configuration options in the sidebar"""
    st.sidebar.markdown("### ⚙️ Configuration")
    
    # Show current database context
    try:
        current_db = session.get_current_database()
        current_schema = session.get_current_schema()
        st.sidebar.info(f"📍 Current Context: {current_db}.{current_schema}")
        st.sidebar.info(f"🎯 Target Service: PETAPP.DATA.CC_SEARCH_SERVICE_CS")
    except Exception:
        st.sidebar.warning("Could not determine current database context")
    
    # Cortex Search Service Selection
    if st.session_state.service_metadata:
        service_names = [s["name"] for s in st.session_state.service_metadata]
        
        # Set default index to PETAPP.DATA.CC_SEARCH_SERVICE_CS if it exists
        default_index = 0
        target_service = "PETAPP.DATA.CC_SEARCH_SERVICE_CS"
        if target_service in service_names:
            default_index = service_names.index(target_service)
        
        st.sidebar.selectbox(
            "Pet Health Search Service:",
            service_names,
            index=default_index,
            key="selected_cortex_search_service",
            help="Choose the search service containing pet health documents"
        )
        
        # Display current service info
        if st.session_state.get('selected_cortex_search_service'):
            selected_service = next((s for s in st.session_state.service_metadata 
                                  if s["name"] == st.session_state.selected_cortex_search_service), None)
            if selected_service:
                st.sidebar.success(f"✅ Service: {st.session_state.selected_cortex_search_service}")
                st.sidebar.info(f"🔍 Search Column: {selected_service['search_column']}")
    else:
        st.sidebar.error("❌ No Cortex Search Services found")
        st.sidebar.markdown("**Troubleshooting:**")
        st.sidebar.markdown("- Ensure you're in the correct database/schema")
        st.sidebar.markdown("- Verify the service PETAPP.DATA.CC_SEARCH_SERVICE_CS exists")
        st.sidebar.markdown("- Check permissions to access Cortex Search services")
        
        # Manual configuration option
        with st.sidebar.expander("🔧 Manual Configuration"):
            manual_service = st.text_input(
                "Service Name:", 
                value="PETAPP.DATA.CC_SEARCH_SERVICE_CS",
                key="manual_service_name"
            )
            manual_search_col = st.text_input(
                "Search Column:", 
                value="chunk",
                key="manual_search_column"
            )
            if st.button("Use Manual Config"):
                st.session_state.service_metadata = [{
                    "name": manual_service,
                    "search_column": manual_search_col
                }]
                st.session_state.selected_cortex_search_service = manual_service
                st.rerun()
    
    # Control buttons
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.button("🗑️ Clear Chat", key="clear_conversation")
    with col2:
        if st.session_state.get("messages"):
            export_chat()
    
    # Toggles
    st.sidebar.toggle("Debug Mode", key="debug", value=False, help="Show search context and prompts")
    st.sidebar.toggle("Use Chat History", key="use_chat_history", value=True, help="Include previous messages for context")
    
    # Advanced options
    with st.sidebar.expander("🔧 Advanced Options"):
        st.selectbox("Language Model:", MODELS, key="model_name", index=0)
        st.number_input(
            "Max Search Results",
            value=5,
            key="num_retrieved_chunks",
            min_value=1,
            max_value=10,
            help="Number of document chunks to retrieve"
        )
        st.number_input(
            "Chat History Length",
            value=5,
            key="num_chat_messages",
            min_value=1,
            max_value=10,
            help="Number of previous messages to include"
        )
    
    # Debug session state
    if st.sidebar.toggle("Show Session State", value=False):
        st.sidebar.expander("Session State").write(st.session_state)

def display_pet_info_sidebar():
    """Display pet information input in sidebar"""
    st.sidebar.markdown("### 🐕 Pet Information")
    
    with st.sidebar.expander("Pet Details (Helps improve responses)", expanded=False):
        pet_types = ["", "Dog", "Cat", "Bird", "Rabbit", "Guinea Pig", "Hamster", "Fish", "Reptile", "Other"]
        pet_type_value = st.session_state.pet_info.get('type', '')
        try:
            pet_type_index = pet_types.index(pet_type_value)
        except ValueError:
            pet_type_index = 0

        pet_name = st.text_input("Pet Name", value=st.session_state.pet_info.get('name', ''), placeholder="e.g., Buddy")
        pet_type = st.selectbox(
            "Pet Type", 
            pet_types,
            index=pet_type_index
        )
        pet_breed = st.text_input("Breed", value=st.session_state.pet_info.get('breed', ''), placeholder="e.g., Golden Retriever")
        
        col1, col2 = st.columns(2)
        with col1:
            pet_age = st.number_input("Age (years)", min_value=0.0, max_value=30.0, step=0.5, 
                                     value=st.session_state.pet_info.get('age', 0.0) or 0.0)
        with col2:
            pet_weight = st.number_input("Weight (lbs)", min_value=0.0, step=0.1, 
                                        value=st.session_state.pet_info.get('weight', 0.0) or 0.0)
        
        # Additional details
        spayed_neutered_options = ["Unknown", "Yes", "No"]
        spayed_neutered_value = st.session_state.pet_info.get('spayed_neutered', 'Unknown')
        try:
            spayed_neutered_index = spayed_neutered_options.index(spayed_neutered_value)
        except ValueError:
            spayed_neutered_index = 0
        spayed_neutered = st.selectbox("Spayed/Neutered", spayed_neutered_options,
                                      index=spayed_neutered_index)
        
        medical_conditions = st.text_area("Known Medical Conditions", 
                                         value=st.session_state.pet_info.get('medical_conditions', ''),
                                         placeholder="Any existing conditions or medications...")
        
        # Store updated pet info
        st.session_state.pet_info = {
            'name': pet_name if pet_name else None,
            'type': pet_type if pet_type else None,
            'breed': pet_breed if pet_breed else None,
            'age': pet_age if pet_age > 0 else None,
            'weight': pet_weight if pet_weight > 0 else None,
            'spayed_neutered': spayed_neutered if spayed_neutered != "Unknown" else None,
            'medical_conditions': medical_conditions if medical_conditions else None
        }

def display_sample_questions():
    """Display sample questions for common pet health topics"""
    st.sidebar.markdown("### 💡 Common Questions")
    
    sample_questions = [
        "What are the signs of dehydration in dogs?",
        "How often should I feed my kitten?",
        "What vaccinations does my puppy need?",
        "Is chocolate dangerous for pets?",
        "How can I tell if my cat is stressed?",
        "What are symptoms of pet allergies?",
        "When should I be concerned about my pet's behavior?",
        "How do I introduce a new pet to my household?"
    ]
    
    st.sidebar.markdown("Click to ask:")
    for i, question in enumerate(sample_questions):
        if st.sidebar.button(f"❓ {question}", key=f"sample_{i}", use_container_width=True):
            st.session_state.sample_question = question
            st.rerun()

def display_analytics():
    """Display conversation analytics"""
    if st.session_state.get("messages"):
        st.sidebar.markdown("### 📊 Session Stats")
        
        user_messages = [msg for msg in st.session_state.messages if msg["role"] == "user"]
        assistant_messages = [msg for msg in st.session_state.messages if msg["role"] == "assistant"]
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <strong>{len(user_messages)}</strong><br>
                Questions
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <strong>{len(assistant_messages)}</strong><br>
                Responses
            </div>
            """, unsafe_allow_html=True)

def export_chat():
    """Export chat history as JSON"""
    chat_export = {
        "timestamp": datetime.now().isoformat(),
        "pet_info": st.session_state.pet_info,
        "search_service": st.session_state.get('selected_cortex_search_service', ''),
        "model": st.session_state.get('model_name', ''),
        "messages": st.session_state.messages
    }
    st.download_button(
        "Download Chat History",
        data=json.dumps(chat_export, indent=2, default=str),
        file_name=f"pet_health_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

def query_cortex_search_service(query, columns=[], filter={}):
    """Query the cortex search service for relevant pet health documents"""
    try:
        # For the specific service PETAPP.DATA.CC_SEARCH_SERVICE_CS
        service_name = st.session_state.selected_cortex_search_service
        
        # Since we know the service is in PETAPP.DATA, use those explicitly
        if service_name == "PETAPP.DATA.CC_SEARCH_SERVICE_CS":
            cortex_search_service = (
                root.databases["PETAPP"]
                .schemas["DATA"]
                .cortex_search_services["CC_SEARCH_SERVICE_CS"]
            )
        else:
            # Handle other cases - parse the service name
            if "." in service_name:
                parts = service_name.split(".")
                if len(parts) == 3:
                    service_db, service_schema, service_name_only = parts
                    cortex_search_service = (
                        root.databases[service_db]
                        .schemas[service_schema]
                        .cortex_search_services[service_name_only]
                    )
                else:
                    # Fallback to current context
                    db, schema = session.get_current_database(), session.get_current_schema()
                    cortex_search_service = (
                        root.databases[db]
                        .schemas[schema]
                        .cortex_search_services[service_name]
                    )
            else:
                # Use current database/schema context
                db, schema = session.get_current_database(), session.get_current_schema()
                cortex_search_service = (
                    root.databases[db]
                    .schemas[schema]
                    .cortex_search_services[service_name]
                )
        
        context_documents = cortex_search_service.search(
            query, columns=columns, filter=filter, limit=st.session_state.num_retrieved_chunks
        )
        results = context_documents.results
        
        service_metadata = st.session_state.service_metadata
        try:
            search_col = next(
                s["search_column"] for s in service_metadata
                if s["name"] == st.session_state.selected_cortex_search_service
            )
        except StopIteration:
            search_col = "chunk"
        search_col = search_col.lower()
        
        context_str = ""
        for i, r in enumerate(results):
            if search_col in r:
                context_str += f"Context document {i+1}: {r[search_col]} \n\n"
        
        if st.session_state.get("debug"):
            st.sidebar.text_area("Retrieved Context", context_str, height=400)
            st.sidebar.json({"search_results": results})
        
        return context_str, results
    
    except Exception as e:
        st.error(f"Error querying search service: {e}")
        if st.session_state.get("debug"):
            st.sidebar.error(f"Search error details: {str(e)}")
            # Show more debugging info
            st.sidebar.write("Debug info:")
            st.sidebar.write(f"Current Database: {session.get_current_database()}")
            st.sidebar.write(f"Current Schema: {session.get_current_schema()}")
            st.sidebar.write(f"Target Service: {st.session_state.selected_cortex_search_service}")
            st.sidebar.write("Trying to access: PETAPP.DATA.CC_SEARCH_SERVICE_CS")
        return "No context retrieved due to search error.", []

def get_chat_history():
    """Get recent chat history for context"""
    n = st.session_state.num_chat_messages
    # Only get up to but not including the latest user message
    msgs = st.session_state.messages
    if len(msgs) < 2:
        return []
    # Exclude the latest user message
    relevant = msgs[max(0, len(msgs)-n-1):len(msgs)-1]
    return relevant

def complete(model, prompt):
    """Generate completion using Snowflake Cortex"""
    return Complete(model, prompt).replace("$", "\$")

def make_chat_history_summary(chat_history, question):
    """Create a summary of chat history with current question for better context"""
    prompt = f"""
        [INST]
        Based on the chat history below and the current question about pet health, 
        generate a comprehensive query that combines the question with relevant chat context.
        The query should be in natural language and focused on pet health topics.
        Answer with only the enhanced query. Do not add any explanation.

        <chat_history>
        {chat_history}
        </chat_history>
        <question>
        {question}
        </question>
        [/INST]
    """
    
    summary = complete(st.session_state.model_name, prompt)
    
    if st.session_state.get("debug"):
        st.sidebar.text_area("Enhanced Query", summary.replace("$", "\$"), height=150)
    
    return summary

def get_pet_context():
    """Build pet-specific context string"""
    pet_info = st.session_state.pet_info
    if not pet_info or not any(pet_info.values()):
        return ""
    
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
    
    return f"\n\nPet Information: {', '.join(pet_details)}"

def create_prompt(user_question):
    """Create a comprehensive prompt for the pet health assistant"""
    # Handle chat history
    if st.session_state.use_chat_history:
        chat_history = get_chat_history()
        if chat_history:
            question_summary = make_chat_history_summary(chat_history, user_question)
            prompt_context, results = query_cortex_search_service(
                question_summary,
                columns=["chunk", "file_url", "relative_path", "title"]
            )
        else:
            prompt_context, results = query_cortex_search_service(
                user_question,
                columns=["chunk", "file_url", "relative_path", "title"]
            )
    else:
        prompt_context, results = query_cortex_search_service(
            user_question,
            columns=["chunk", "file_url", "relative_path", "title"]
        )
        chat_history = ""
    
    # Get pet-specific context
    pet_context = get_pet_context()
    
    prompt = f"""
        [INST]
        You are a knowledgeable veterinary assistant AI designed to help pet owners with health-related questions.
        
        IMPORTANT GUIDELINES:
        - Provide helpful, accurate information based on the veterinary knowledge provided
        - Always include appropriate medical disclaimers
        - Remind users to consult with a licensed veterinarian for proper diagnosis and treatment
        - Never provide specific medical diagnoses or treatment recommendations
        - If the question involves emergency symptoms, advise immediate veterinary care
        - Be empathetic and understanding of pet owners' concerns
        - Use the pet information provided to give more personalized advice when relevant
        
        If you cannot answer the question based on the provided context, say "I don't have enough information in my knowledge base to answer that question. Please consult with a qualified veterinarian for advice."
        
        Don't say phrases like "according to the provided context" - speak naturally.

        <chat_history>
        {chat_history}
        </chat_history>
        
        <veterinary_knowledge>
        {prompt_context}
        </veterinary_knowledge>
        
        <pet_information>
        {pet_context}
        </pet_information>
        
        <question>
        {user_question}
        </question>
        [/INST]
        
        Response:
    """
    
    return prompt, results

def display_main_interface():
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
    
    # Display current pet info if available
    if st.session_state.pet_info and any(st.session_state.pet_info.values()):
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
            st.markdown(f"""
            <div class="pet-info-card">
                🐾 <strong>Current Pet:</strong> {' • '.join(pet_summary)}
            </div>
            """, unsafe_allow_html=True)

def main():
    """Main application function"""
    # Initialize session state
    init_service_metadata()
    init_pet_info()
    init_config_options()
    init_messages()
    
    # Sidebar components
    with st.sidebar:
        if st.session_state.service_metadata:
            display_pet_info_sidebar()
            display_sample_questions()
            display_analytics()
    
    # Main interface
    display_main_interface()
    
    # Chat interface
    icons = {"assistant": "🤖", "user": "👤"}
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=icons[message["role"]]):
            st.markdown(message["content"])
    
    # Check if we can chat
    disable_chat = (
        "service_metadata" not in st.session_state
        or len(st.session_state.service_metadata) == 0
        or "selected_cortex_search_service" not in st.session_state
    )
    
    if disable_chat:
        st.warning("⚠️ Please ensure the PETAPP.DATA.CC_SEARCH_SERVICE_CS service is available and selected in the sidebar.")
    
    # Handle sample question
    if 'sample_question' in st.session_state:
        question = st.session_state.sample_question
        del st.session_state.sample_question
    else:
        question = st.chat_input(
            "Ask me about your pet's health..." if not disable_chat else "Please ensure PETAPP.DATA.CC_SEARCH_SERVICE_CS is configured",
            disabled=disable_chat
        )
    
    if question:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": question})
        
        with st.chat_message("user", avatar=icons["user"]):
            st.markdown(question.replace("$", "\$"))
        
        # Generate assistant response
        with st.chat_message("assistant", avatar=icons["assistant"]):
            message_placeholder = st.empty()
            
            with st.spinner("🔍 Searching veterinary knowledge base..."):
                # Clean question and create prompt
                cleaned_question = question.replace("'", "")
                prompt, results = create_prompt(cleaned_question)
                
                # Generate response
                generated_response = complete(st.session_state.model_name, prompt)
                
                # Build references if available
                references = ""
                if results:
                    references = "\n\n###### 📚 References \n\n| Document | Source |\n|----------|--------|\n"
                    for ref in results:
                        title = ref.get('title', ref.get('relative_path', 'Unknown'))
                        url = ref.get('file_url', '#')
                        references += f"| {title} | [View Source]({url}) |\n"
                
                # Display response with references
                full_response = generated_response + references
                message_placeholder.markdown(full_response)
        
        # Save assistant message
        st.session_state.messages.append(
            {"role": "assistant", "content": generated_response}
        )
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9em; padding: 1rem;">
        💡 <strong>Tips:</strong> Be specific about your pet's symptoms, include breed/age info, and describe any changes in behavior.
        <br>
        🔧 <strong>Powered by:</strong> Snowflake Cortex AI • Built with Streamlit in Snowflake
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
