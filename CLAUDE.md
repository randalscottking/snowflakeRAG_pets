# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a pet health assistant application that uses Snowflake Cortex Search for RAG (Retrieval-Augmented Generation) with the Merck Manual for veterinarians as the knowledge base. The frontend is built with Streamlit.

## Architecture

### Core Components

- **frontend_int.py**: Main internal Streamlit application that connects directly to Snowflake using `get_active_session()` - this is the primary application file
- **frontend_ext.py**: External Streamlit application for external connections using `snowflake.connector`
- **frontend_int_old.py**: Legacy version of the internal frontend (for reference)

### Key Architecture Patterns

The application follows this flow:
1. **Session Management**: Uses Snowflake session (`get_active_session()` for internal, `snowflake.connector` for external)
2. **Cortex Search Integration**: Queries Snowflake Cortex Search services to find relevant veterinary documents
3. **LLM Processing**: Uses Snowflake Cortex Complete with various models (mistral-large2, llama3.1-70b, etc.) to generate responses
4. **RAG Pattern**: Combines search results with user queries to provide contextual pet health advice

### Snowflake Integration

- Uses Snowflake's Cortex Search services for document retrieval
- Leverages multiple LLM models through Snowflake Cortex Complete
- Default search service: `PETAPP.DATA.CC_SEARCH_SERVICE_CS`
- Supports dynamic service discovery and selection

## Development Commands

### Environment Setup
```bash
# Create and activate conda environment
conda env create -f environment.yml
conda activate app_environment
```

### Running the Application
```bash
# Run internal version (primary)
streamlit run frontend_int.py

# Run external version (for external connections)
streamlit run frontend_ext.py
```

### Key Dependencies
- Python 3.9
- Streamlit 1.47.0
- Snowflake connector and ML packages
- Pandas 2.3.1

## Important Implementation Details

### Cortex Search Service Management
- The app auto-discovers available Cortex Search services
- Falls back to manual entry if auto-discovery fails
- Service names can be fully qualified (e.g., `PETAPP.DATA.CC_SEARCH_SERVICE_CS`) or simple names

### Session State Management
- Uses Streamlit session state to maintain search service selection
- Stores conversation history and user preferences
- Key session state variables: `selected_cortex_search_service`, chat history

### Error Handling
- Graceful fallbacks for Cortex Search service discovery
- Connection error handling for both internal and external modes
- User-friendly error messages with troubleshooting guidance

## File Structure Context

This is a focused application with minimal file structure:
- Main application files are at root level
- Uses conda for dependency management (environment.yml)
- VS Code configuration emphasizes conda environment management
- No complex build process or testing framework present