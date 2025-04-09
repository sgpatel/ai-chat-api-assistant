# API Chat Assistant Framework

## Overview

This project provides a framework for building AI-powered conversational assistants that act as a user-friendly frontend for interacting with existing APIs. Instead of users needing to understand complex API requests, they can interact with the assistant via chat. The assistant, guided by an API's OpenAPI specification, dynamically asks the user for necessary parameters using appropriate UI elements within the chat and then executes the API call.

**Core Idea:** Translate natural conversation into structured API calls.

## Key Features (Implemented/Conceptual)

* **OpenAPI-Driven:** Uses OpenAPI v3 (and basic v2) specifications (YAML/JSON) as the source of truth for API endpoints, parameters, and schemas.
* **Conversational Flow:** A `DialogFlowEngine` manages the conversation, determining which parameter to ask for next based on the API spec and collected user input.
* **Dynamic UI Generation (Concept):** The backend generates instructions for the frontend to render appropriate UI elements (text input, dropdown, date picker, checkbox, JSON input, etc.) within the chat, based on parameter types defined in the spec.
* **State Management:** Conversation state (target API, collected parameters) is persisted using a local SQLite database (`chat_state.db`).
* **API Client:** Includes an `httpx`-based asynchronous client (`APIClient`) to make calls to the target API, configured via environment variables. Handles basic parameter placement (query/body) and authentication headers (e.g., Bearer token for OpenAI, custom keys). Includes path parameter substitution.
* **Response Handling:** A `ResponseHandler` formats success and error responses from the target API into user-friendly Markdown messages for the chat. Includes JSON pretty-printing and `<details>` tags for large payloads.
* **Basic LLM Integration:** Includes a component (`PromptGenerator`) to use an LLM (e.g., OpenAI) for generating more natural language prompts when asking for parameters (requires API key).
* **FastAPI Backend:** Built using FastAPI, providing an async API endpoint (`/api/v1/chat/message`) for the frontend to interact with. Includes CORS configuration.
* **React Frontend (Separate Project):** A separate React UI (`api_chat_assistant_ui`) demonstrates how to:
    * Connect to the backend chat endpoint.
    * Render chat messages (using `react-markdown` for formatting).
    * Dynamically render interactive input components based on backend instructions.
    * Allow users to select the target API operation from a list fetched from the backend.

## Architecture

* **Backend (`api_assistant_framework`):**
    * **`app/`**: Root application package.
        * **`main.py`**: FastAPI app setup, lifespan management (DB init, engine creation), middleware (CORS), router inclusion.
        * **`config.py`**: Pydantic settings management (loads `.env`), basic logging config.
        * **`core/`**: Contains the main logic components:
            * `api_parser.py`: Loads and parses OpenAPI specs.
            * `state_manager.py`: Loads/saves conversation state to the database.
            * `flow_engine.py`: Orchestrates the conversation steps.
            * `api_client.py`: Executes calls to the target external API.
            * `response_handler.py`: Formats API responses for chat display.
        * **`db/`**: SQLAlchemy setup for async SQLite, DB models (`ConversationStateDB`), CRUD operations.
        * **`models/`**: Pydantic models for API specs (`api_spec.py`) and conversation state (`conversation_state.py`).
        * **`ui_generators/`**: Defines the structure for UI instructions (`chat_elements.py`).
        * **`llm_integrations/`**: Contains LLM-related logic (`prompt_generator.py`).
        * **`api/`**: FastAPI routers and endpoints (`chat.py`, `operations.py`).
* **Frontend (`api_chat_assistant_ui`):**
    * A separate React project (built with Vite).
    * Uses `fetch` to communicate with the backend chat API.
    * Includes components to render the chat interface and dynamic input elements.
    * Uses `react-markdown` to render formatted assistant messages.
    * Uses `react-datepicker` for date/time input.

## Setup

**Prerequisites:**

* Python 3.8+
* Node.js and npm (or yarn) for the React frontend.
* An OpenAI API Key (if using LLM prompt generation).

**Backend Setup (`api_assistant_framework`):**

1.  **Clone/Download:** Get the backend project code.
2.  **Navigate:** `cd api_assistant_framework`
3.  **Create Virtual Environment:**
    ```bash
    python -m venv venv
    # Activate:
    # Windows: venv\Scripts\activate
    # macOS/Linux: source venv/bin/activate
    ```
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Prepare API Specification:**
    * Download or create an OpenAPI v3 (or v2) specification file (e.g., `openapi.yaml`, `petstore_v2.json`) for the API you want the assistant to interact with.
    * Place it in the project root directory.
6.  **Configure `.env` File:**
    * Create a `.env` file in the project root.
    * Set the required variables (see Configuration section below).
7.  **(Optional) Database:** The first run will create the `chat_state.db` SQLite file automatically.

**Frontend Setup (`api_chat_assistant_ui`):**

1.  **Clone/Download:** Get the frontend project code (or use the files provided in the conversation).
2.  **Navigate:** `cd api_chat_assistant_ui`
3.  **Install Dependencies:**
    ```bash
    npm install
    # or: yarn install
    ```
4.  **Install Peer Dependencies (if needed):** Ensure necessary libraries like `react-datepicker`, `date-fns`, `react-markdown` etc. are installed based on the final `App.jsx` code.
    ```bash
    npm install react-markdown remark-gfm rehype-raw react-datepicker date-fns lucide-react
    ```

## Configuration (`.env` file)

Create a `.env` file in the `api_assistant_framework` backend project root with the following variables:

```ini
# .env Example

# Path to the API specification file (relative to project root)
API_SPEC_FILE="openapi.yaml"
# API_SPEC_FILE="petstore_v2.json"

# Base URL of the target API the assistant will call
TARGET_API_BASE_URL="[https://api.openai.com/v1](https://api.openai.com/v1)"
# TARGET_API_BASE_URL="[https://petstore.swagger.io/v2](https://petstore.swagger.io/v2)"

# Database URL (default is SQLite in project root)
# DATABASE_URL="sqlite+aiosqlite:///./chat_state.db"

# API Keys (add keys required by your TARGET_API_BASE_URL)
OPENAI_API_KEY="sk-..." # Needed for LLM prompt generation AND if targeting OpenAI API
# MY_API_KEY="your_custom_api_key_here" # Example for another API
Running the ApplicationRun the Backend:Navigate to the api_assistant_framework directory.Activate the virtual environment (source venv/bin/activate or venv\Scripts\activate).Start the Uvicorn server (use --log-level debug for more details):uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
The backend API will be available at http://localhost:8000. Docs at http://localhost:8000/docs.Run the Frontend:Navigate to the api_chat_assistant_ui directory in a separate terminal.Start the Vite development server:npm run dev
# or: yarn dev
The UI will be available, typically at http://localhost:5173.Usage / TestingVia UI:Open the React UI in your browser (e.g., http://localhost:5173).Select an available API operation from the dropdown.Follow the assistant's prompts, providing values using the dynamic input fields that appear in the chat.The final result from the API call will be displayed.Via curl:You can test the backend directly using curl commands targeting http://localhost:8000/api/v1/chat/message.Start a flow (Intent):curl -X POST http://localhost:8000/api/v1/chat/message \
-H "Content-Type: application/json" \
-d '{
  "user_id": "curl_tester",
  "type": "intent",
  "intent_string": "Your goal here",
  "target_api_path": "/path/in/your/spec",
  "target_api_method": "post"
}'
Respond to Parameter Request:curl -X POST http://localhost:8000/api/v1/chat/message \
-H "Content-Type: application/json" \
-d '{
  "user_id": "curl_tester",
  "type": "parameter_response",
  "parameter_name": "param_name_asked_by_assistant",
  "parameter_value": "value_you_provide"
}'
Backend Tests (pytest):Navigate to the api_assistant_framework directory.Activate the virtual environment.Run tests (if tests/ directory and test files exist):python -m pytest tests/ -v -s
Future Enhancements / TODOsRobust Parameter Handling: Improve APIClient to use parsed spec details (location) to correctly place parameters in path, query, headers, or body.Advanced NLU/Intent Mapping: Replace basic UI mapping with a more flexible NLU approach (LLM or simpler model) to understand diverse user requests.Complex Input Components: Implement more sophisticated UI components for arrays of objects or deeply nested objects (e.g., dynamic form builders).LLM Response Summarization: Integrate llm_integrations/summarizer.py into ResponseHandler.LLM Parameter Parsing: Integrate llm_integrations/response_parser.py into DialogFlowEngine to handle natural language parameter values.Workflow/Chaining: Add logic to DialogFlowEngine to handle multi-step API call sequences.WebSocket Support: Replace frontend polling with WebSockets for real-time updates.Authentication Management: Add secure storage and handling for multiple target API credentials.


![image](https://github.com/user-attachments/assets/3b460c12-a93f-4eab-93ce-79206d6b18b6)

![image](https://github.com/user-attachments/assets/c432bb94-5323-47e8-979e-4132927438bd)

![image](https://github.com/user-attachments/assets/4daa8249-461d-4402-b22d-9c1e6aa9abc9)


