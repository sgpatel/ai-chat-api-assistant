// src/App.jsx (Implementing Operation Selector, DateTimePicker, TagsInput)

import React, { useState, useEffect, useCallback, useRef } from 'react';
// --- Import react-datepicker and its CSS ---
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
// --- Import date-fns for date formatting ---
import { format as formatDate, parseISO } from 'date-fns'; // Use date-fns

// Import icons
import { Send, Bot, User, Loader2, CheckSquare, Calendar, Code, Tags, Clock, List } from 'lucide-react'; // Added List icon

// --- Configuration ---
const API_BASE_URL = 'http://localhost:8000/api/v1'; // Your FastAPI backend URL
const CHAT_ENDPOINT = `${API_BASE_URL}/chat/message`;
const OPERATIONS_ENDPOINT = `${API_BASE_URL}/operations`; // Endpoint to fetch operations
const USER_ID = "ui_user_enh"; // Example User ID

// --- Logger Stub (for frontend debugging) ---
const logger = {
    debug: console.debug,
    info: console.info,
    warn: console.warn,
    error: console.error,
};

// --- Helper Function for API Calls ---
async function fetchApi(url, options = {}) {
    logger.debug(`Fetching API: ${options.method || 'GET'} ${url}`);
    const response = await fetch(url, options);
    if (!response.ok) {
        let errorDetail = `API Error: ${response.status}`;
        try {
            const errorData = await response.json();
            errorDetail = errorData.detail || errorDetail;
            if (Array.isArray(errorData.detail)) {
                errorDetail = errorData.detail.map(err => `${err.loc?.join('.')}: ${err.msg}`).join('; ');
            }
             logger.error(`API Fetch Error (${response.status}): ${errorDetail}`, errorData);
        } catch (e) {
             logger.error(`API Fetch Error (${response.status}), could not parse error body.`);
        }
        throw new Error(errorDetail);
    }
    // Handle 204 No Content
    if (response.status === 204) {
        logger.debug(`API Response: ${response.status} No Content`);
        return null;
    }
    // Assume JSON response otherwise
    const jsonData = await response.json();
    logger.debug(`API Response: ${response.status}`, jsonData);
    return jsonData;
}


// --- Individual UI Component Renderers ---

// Renders a text input within the chat
function ChatTextInput({ componentDetails, onSubmit, disabled }) {
  const [value, setValue] = useState(componentDetails.default || '');
  const { parameter_name, placeholder, description } = componentDetails;
  const handleSubmit = (e) => { e.preventDefault(); onSubmit(parameter_name, value); };
  // Effect to handle external default value changes
  useEffect(() => { setValue(componentDetails.default || ''); }, [componentDetails.default]);
  return (
    <form onSubmit={handleSubmit} className="mt-2 mb-1 p-3 border rounded bg-gray-100 shadow-sm">
      <label htmlFor={parameter_name} className="block text-sm font-medium text-gray-700 mb-1">
        {description || `Enter ${parameter_name.replace('_', ' ')}`}
      </label>
      <div className="flex items-center space-x-2">
        <input type="text" id={parameter_name} value={value} onChange={(e) => setValue(e.target.value)}
          className="flex-grow block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm disabled:opacity-50 disabled:bg-gray-200"
          placeholder={placeholder || ''} disabled={disabled} aria-label={description || `Input for ${parameter_name}`} />
        <button type="submit" disabled={disabled}
            className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-300 disabled:cursor-not-allowed"
            aria-label="Send text input">
          <Send size={16} />
        </button>
      </div>
    </form>
  );
}

// Renders a dropdown/select input within the chat
function ChatDropdown({ componentDetails, onSubmit, disabled }) {
  const { parameter_name, options, description } = componentDetails;
  const [selectedValue, setSelectedValue] = useState(componentDetails.default || options?.[0] || '');
  const handleChange = (e) => { const value = e.target.value; setSelectedValue(value); if (value) { onSubmit(parameter_name, value); } };
  useEffect(() => { setSelectedValue(componentDetails.default || options?.[0] || ''); }, [componentDetails.default, options]);
  return (
    <div className="mt-2 mb-1 p-3 border rounded bg-gray-100 shadow-sm">
       <label htmlFor={parameter_name} className="block text-sm font-medium text-gray-700 mb-1">
         {description || `Select ${parameter_name.replace('_', ' ')}`}
       </label>
      <select id={parameter_name} value={selectedValue} onChange={handleChange} disabled={disabled}
        className="block w-full pl-3 pr-10 py-1.5 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md disabled:opacity-50 disabled:bg-gray-200"
        aria-label={description || `Select ${parameter_name}`}>
        {(options || []).map((option, index) => ( <option key={index} value={option}> {option} </option> ))}
      </select>
       <p className="text-xs text-gray-500 mt-1 italic">Selecting an option submits the value.</p>
    </div>
  );
}

// Number Input Component
function ChatNumberInput({ componentDetails, onSubmit, disabled }) {
  const [value, setValue] = useState(componentDetails.default !== undefined ? String(componentDetails.default) : '');
  const { parameter_name, placeholder, description } = componentDetails;
  const handleSubmit = (e) => { e.preventDefault(); const numValue = parseFloat(value); onSubmit(parameter_name, isNaN(numValue) ? value : numValue); };
  useEffect(() => { setValue(componentDetails.default !== undefined ? String(componentDetails.default) : ''); }, [componentDetails.default]);
  return (
    <form onSubmit={handleSubmit} className="mt-2 mb-1 p-3 border rounded bg-gray-100 shadow-sm">
      <label htmlFor={parameter_name} className="block text-sm font-medium text-gray-700 mb-1">
        {description || `Enter ${parameter_name.replace('_', ' ')} (Number)`}
      </label>
      <div className="flex items-center space-x-2">
        <input type="number" id={parameter_name} value={value} onChange={(e) => setValue(e.target.value)}
          className="flex-grow block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm disabled:opacity-50 disabled:bg-gray-200"
          placeholder={placeholder || 'Enter a number'} step="any" disabled={disabled} aria-label={description || `Input for ${parameter_name}`} />
        <button type="submit" disabled={disabled}
            className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-300 disabled:cursor-not-allowed"
            aria-label="Send number input">
          <Send size={16} />
        </button>
      </div>
    </form>
  );
}

// Checkbox Input Component
function ChatCheckbox({ componentDetails, onSubmit, disabled }) {
  const { parameter_name, description, default: defaultValue } = componentDetails;
  const [isChecked, setIsChecked] = useState(defaultValue !== undefined ? !!defaultValue : false);
  const handleChange = (e) => { const newValue = e.target.checked; setIsChecked(newValue); onSubmit(parameter_name, newValue); };
  useEffect(() => { setIsChecked(defaultValue !== undefined ? !!defaultValue : false); }, [defaultValue]);
  return (
    <div className="mt-2 mb-1 p-3 border rounded bg-gray-100 shadow-sm">
      <div className="flex items-center">
        <input id={parameter_name} name={parameter_name} type="checkbox" checked={isChecked} onChange={handleChange} disabled={disabled}
          className="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 disabled:opacity-50" />
        <label htmlFor={parameter_name} className="ml-2 block text-sm font-medium text-gray-700">
          {description || parameter_name.replace('_', ' ')}
        </label>
      </div>
      <p className="text-xs text-gray-500 mt-1 italic">Checking/unchecking submits the value.</p>
    </div>
  );
}

// Date Picker Component (Native HTML5)
function ChatDatePickerNative({ componentDetails, onSubmit, disabled }) {
  const [value, setValue] = useState(componentDetails.default || '');
  const { parameter_name, description } = componentDetails;
  const handleSubmit = (e) => { e.preventDefault(); onSubmit(parameter_name, value); };
  useEffect(() => { setValue(componentDetails.default || ''); }, [componentDetails.default]);
  return (
    <form onSubmit={handleSubmit} className="mt-2 mb-1 p-3 border rounded bg-gray-100 shadow-sm">
      <label htmlFor={parameter_name} className="block text-sm font-medium text-gray-700 mb-1">
        {description || `Select ${parameter_name.replace('_', ' ')}`}
      </label>
      <div className="flex items-center space-x-2">
        <input type="date" id={parameter_name} value={value} onChange={(e) => setValue(e.target.value)}
          className="flex-grow block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm disabled:opacity-50 disabled:bg-gray-200"
          disabled={disabled} aria-label={description || `Input for ${parameter_name}`} />
        <button type="submit" disabled={disabled || !value}
            className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-300 disabled:cursor-not-allowed"
            aria-label="Send date input">
          <Send size={16} />
        </button>
      </div>
       <p className="text-xs text-gray-500 mt-1 italic">Select a date and click send.</p>
    </form>
  );
}

// JSON Input Component
function ChatJsonInput({ componentDetails, onSubmit, disabled }) {
  const generatePlaceholder = (paramName) => { if (paramName === 'messages') { return `[\n  {\n    "role": "user",\n    "content": "Your message here..."\n  }\n]`; } return `{\n  "key": "value"\n}`; }
  const [value, setValue] = useState( componentDetails.default !== undefined ? JSON.stringify(componentDetails.default, null, 2) : '' );
  const [isValidJson, setIsValidJson] = useState(true);
  const { parameter_name, description } = componentDetails;
  useEffect(() => { const defaultVal = componentDetails.default !== undefined ? JSON.stringify(componentDetails.default, null, 2) : ''; setValue(defaultVal); setIsValidJson(true); }, [componentDetails.default]);
  const handleChange = (e) => { const textValue = e.target.value; setValue(textValue); try { JSON.parse(textValue); setIsValidJson(true); } catch (error) { if (textValue.trim() !== '') { setIsValidJson(false); } else { setIsValidJson(true); } } };
  const handleSubmit = (e) => { e.preventDefault(); let submittedValue = null; let parseError = false; if (value.trim() === '') { submittedValue = null; setIsValidJson(true); } else { try { submittedValue = JSON.parse(value); setIsValidJson(true); } catch (error) { console.error("Invalid JSON submitted:", error); setIsValidJson(false); parseError = true; submittedValue = value; alert("Warning: Submitting potentially invalid JSON string."); } } if (!parseError || submittedValue === null || typeof submittedValue === 'string') { onSubmit(parameter_name, submittedValue); } else { alert("Please fix invalid JSON."); } };
  return (
    <form onSubmit={handleSubmit} className="mt-2 mb-1 p-3 border rounded bg-gray-100 shadow-sm">
      <label htmlFor={parameter_name} className="block text-sm font-medium text-gray-700 mb-1"> {description || `Enter ${parameter_name.replace('_', ' ')} (JSON format)`} </label>
      <textarea id={parameter_name} value={value} onChange={handleChange} rows="6"
        className={`block w-full px-3 py-1.5 border rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono disabled:opacity-50 disabled:bg-gray-200 ${isValidJson ? 'border-gray-300' : 'border-red-500 focus:ring-red-500 focus:border-red-500'}`}
        placeholder={generatePlaceholder(parameter_name)} disabled={disabled} aria-label={description || `Input for ${parameter_name} in JSON format`} />
      {!isValidJson && <p className="text-xs text-red-600 mt-1">Invalid JSON format.</p>}
      <div className="flex justify-end mt-2"> <button type="submit" disabled={disabled} className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-300 disabled:cursor-not-allowed" aria-label="Send JSON input"> <Send size={16} /> <span className="ml-1">Send JSON</span> </button> </div>
    </form>
  );
}

// --- ADDED: DateTime Picker Component (Using react-datepicker) ---
function ChatDateTimePicker({ componentDetails, onSubmit, disabled }) {
  const { parameter_name, description, default: defaultValue } = componentDetails;
  // Initialize state, try parsing default value if it exists and is valid ISO string
  const parseDefault = (val) => { try { return val ? parseISO(val) : null; } catch { return null; }};
  const [selectedDate, setSelectedDate] = useState(parseDefault(defaultValue));

  // Update state if default value changes externally
  useEffect(() => { setSelectedDate(parseDefault(defaultValue)); }, [defaultValue]);

  // Submit the selected date in ISO format when changed
  const handleChange = (date) => {
    setSelectedDate(date);
    if (date instanceof Date && !isNaN(date)) {
        try {
             const isoString = date.toISOString(); // Standard ISO format (UTC)
             onSubmit(parameter_name, isoString);
        } catch (e) {
             logger.error("Error formatting date:", e);
             onSubmit(parameter_name, null); // Submit null on error
        }
    } else {
        onSubmit(parameter_name, null); // Submit null if cleared or invalid
    }
  };

  return (
    <div className="mt-2 mb-1 p-3 border rounded bg-gray-100 shadow-sm">
      <label htmlFor={parameter_name} className="block text-sm font-medium text-gray-700 mb-1">
        {description || `Select ${parameter_name.replace('_', ' ')}`}
      </label>
      {/* Use react-datepicker component */}
      <DatePicker
        id={parameter_name}
        selected={selectedDate}
        onChange={handleChange}
        showTimeSelect // Enable time selection
        dateFormat="Pp" // Format like "MM/dd/yyyy, h:mm aa"
        className="block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm disabled:opacity-50 disabled:bg-gray-200"
        placeholderText="Select date and time"
        disabled={disabled}
        aria-label={description || `Select date and time for ${parameter_name}`}
        popperPlacement="top-start" // Adjust placement if needed
      />
      <p className="text-xs text-gray-500 mt-1 italic">Selecting a date/time submits the value.</p>
    </div>
  );
}

// --- ADDED: Basic Tags Input Component ---
function ChatTagsInput({ componentDetails, onSubmit, disabled }) {
  const { parameter_name, description, item_type = 'string' } = componentDetails;
  const [inputValue, setInputValue] = useState('');
  const [tags, setTags] = useState(Array.isArray(componentDetails.default) ? componentDetails.default : []);

  // Update state if default value changes externally
  useEffect(() => { setTags(Array.isArray(componentDetails.default) ? componentDetails.default : []); }, [componentDetails.default]);

  const handleInputChange = (e) => { setInputValue(e.target.value); };

  // Add tag on comma, space, or Enter
  const handleKeyDown = (e) => {
    if (['Enter', ',', ' '].includes(e.key) && inputValue.trim()) {
      e.preventDefault();
      const newTagValue = inputValue.trim();
      let processedTag = newTagValue;
      if (item_type === 'integer' || item_type === 'number') {
           const num = parseFloat(newTagValue);
           if (!isNaN(num)) processedTag = num;
           else { alert(`Tag "${newTagValue}" is not a valid ${item_type}.`); return; }
      }
      if (!tags.includes(processedTag)) {
        const newTags = [...tags, processedTag];
        setTags(newTags);
        onSubmit(parameter_name, newTags); // Submit updated array
      }
      setInputValue('');
    } else if (e.key === 'Backspace' && !inputValue && tags.length > 0) {
       e.preventDefault();
       const newTags = tags.slice(0, -1);
       setTags(newTags);
       onSubmit(parameter_name, newTags);
    }
  };

  const removeTag = (indexToRemove) => {
    const newTags = tags.filter((_, index) => index !== indexToRemove);
    setTags(newTags);
    onSubmit(parameter_name, newTags);
  };

  return (
    <div className="mt-2 mb-1 p-3 border rounded bg-gray-100 shadow-sm">
      <label htmlFor={`${parameter_name}-input`} className="block text-sm font-medium text-gray-700 mb-1">
        {description || `Enter ${parameter_name.replace('_', ' ')} (comma/space/Enter to add)`}
      </label>
      <div className={`flex flex-wrap items-center gap-1 p-1.5 border rounded-md bg-white min-h-[38px] ${disabled ? 'bg-gray-200' : 'border-gray-300'}`}>
        {tags.map((tag, index) => (
          <span key={index} className="flex items-center bg-indigo-100 text-indigo-700 text-xs font-medium px-2 py-0.5 rounded-full">
            {String(tag)} {/* Ensure tag is string for display */}
            <button type="button" onClick={() => removeTag(index)} disabled={disabled}
              className="ml-1.5 flex-shrink-0 text-indigo-400 hover:text-indigo-600 focus:outline-none disabled:opacity-50"
              aria-label={`Remove ${tag}`}>
              &times;
            </button>
          </span>
        ))}
        <input id={`${parameter_name}-input`} type="text" value={inputValue}
          onChange={handleInputChange} onKeyDown={handleKeyDown} disabled={disabled}
          className="flex-grow p-0.5 border-none focus:ring-0 text-sm disabled:bg-gray-200 bg-transparent"
          placeholder={tags.length === 0 ? 'Add items...' : ''} aria-label={`Input for ${parameter_name}`} />
      </div>
       <p className="text-xs text-gray-500 mt-1 italic">Changes submit automatically. Backspace removes last tag.</p>
    </div>
  );
}


// --- Operation Selector Component ---
function OperationSelector({ operations, onSelectOperation, disabled, currentSelection }) {
    // Controlled component: value reflects external state if provided
    const selectedOpId = currentSelection ? operations.find(op => op.path === currentSelection.path && op.method === currentSelection.method)?.id || '' : '';

    const handleChange = (e) => {
        const opId = e.target.value;
        const selectedOp = operations.find(op => op.id === opId);
        if (selectedOp) {
            onSelectOperation({
                type: 'intent', value: selectedOp.summary,
                apiDetails: { path: selectedOp.path, method: selectedOp.method }
            });
        }
    };

    return (
        <div className="mb-4 p-3 border-b">
             <label htmlFor="operationSelect" className="block text-sm font-medium text-gray-700 mb-1 flex items-center">
                <List size={16} className="mr-1"/> Select API Operation:
             </label>
             <select id="operationSelect" value={selectedOpId} onChange={handleChange}
                disabled={disabled || operations.length === 0}
                className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md disabled:opacity-50 disabled:bg-gray-100">
                 <option value="" disabled>-- Select an Operation --</option>
                 {operations.map((op) => ( <option key={op.id} value={op.id}> {op.summary} ({op.method.toUpperCase()} {op.path}) </option> ))}
             </select>
             {operations.length === 0 && !disabled && <p className="text-xs text-gray-500 mt-1">Loading operations...</p>}
        </div>
    );
}


// --- Main Chat Interface Component ---
function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [isAssistantTyping, setIsAssistantTyping] = useState(false);
  const [currentInteractionDisabled, setCurrentInteractionDisabled] = useState(false);
  const [availableOperations, setAvailableOperations] = useState([]);
  const [fetchError, setFetchError] = useState(null);
  const [currentApiOperation, setCurrentApiOperation] = useState(null); // Track selected operation
  const chatEndRef = useRef(null);

  const scrollToBottom = () => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); };
  useEffect(scrollToBottom, [messages]);

  // Fetch available operations on initial load
  useEffect(() => {
      const fetchOps = async () => {
          setFetchError(null);
          try {
              logger.debug("Fetching available operations...");
              const ops = await fetchApi(OPERATIONS_ENDPOINT);
              setAvailableOperations(ops || []);
              logger.debug(`Fetched ${ops?.length || 0} operations.`);
          } catch (error) {
               console.error("Failed to fetch API operations:", error);
               const errorMsg = `Failed to load available API operations: ${error.message}`;
               setFetchError(errorMsg);
               addMessage('assistant', { prompt: errorMsg, ui_component: null });
          }
      };
      fetchOps();
  }, []); // Run only once on mount


  const addMessage = useCallback((sender, content) => {
    const messageId = Date.now() + Math.random();
    setMessages(prev => [...prev, { id: messageId, sender, content }]);
  }, []);

  // Handles sending user input (intent or parameter value) to backend
  const handleUserInput = useCallback(async (input) => {
    // Add user message only for initial intent
    if (input.type === 'intent') {
        addMessage('user', input.value);
        // Set the current operation when intent is selected
        setCurrentApiOperation(input.apiDetails);
    }
    setIsAssistantTyping(true);
    setCurrentInteractionDisabled(true);
    setFetchError(null);

    let requestBody;
    if (input.type === 'intent') {
        if (!input.apiDetails || !input.apiDetails.path || !input.apiDetails.method) {
             addMessage('assistant', { prompt: `Sorry, I couldn't map '${input.value}' to a known API action. Please select from the list.`, ui_component: null });
             setIsAssistantTyping(false); setCurrentInteractionDisabled(false); setCurrentApiOperation(null); return;
        }
        requestBody = { user_id: USER_ID, type: 'intent', intent_string: input.value, target_api_path: input.apiDetails.path, target_api_method: input.apiDetails.method };
    } else if (input.type === 'parameter') {
        requestBody = { user_id: USER_ID, type: 'parameter_response', parameter_name: input.parameterName, parameter_value: input.value };
    } else { /* ... */ }

    try {
        const backendResponse = await fetchApi(CHAT_ENDPOINT, {
            method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }, body: JSON.stringify(requestBody),
        });

        if (backendResponse.type === 'ui_instruction') {
            addMessage('assistant', backendResponse.data);
            setCurrentInteractionDisabled(false); // Re-enable for next input
        } else if (backendResponse.type === 'final_message' || backendResponse.type === 'error_message') {
            addMessage('assistant', { prompt: backendResponse.text, ui_component: null });
            setCurrentInteractionDisabled(false); // Interaction finished or failed
            setCurrentApiOperation(null); // Reset current operation after completion/error
        } else { /* ... handle unknown response ... */ }

    } catch (error) {
        console.error('Failed to send message or process response:', error);
        addMessage('assistant', { prompt: `Error: ${error.message}`, ui_component: null });
        setCurrentInteractionDisabled(false); // Re-enable input after error
        setCurrentApiOperation(null); // Reset current operation after error
    } finally {
        setIsAssistantTyping(false);
    }
  }, [addMessage]); // Include addMessage

  // Callback passed to dynamic input components
  const handleDynamicInputSubmit = useCallback((parameterName, value) => {
    handleUserInput({ type: 'parameter', parameterName, value });
  }, [handleUserInput]); // Include handleUserInput

  // Renders the correct dynamic UI component based on instructions
  const renderDynamicComponent = (instructionContent) => {
     if (typeof instructionContent === 'string') return <p>{instructionContent}</p>;
     if (!instructionContent || (!instructionContent.prompt && !instructionContent.ui_component)) return <p className="text-red-500 italic">[Invalid Message Format]</p>;

     const { prompt, ui_component } = instructionContent;
     const promptElement = prompt ? <p className="mb-1">{prompt}</p> : null;
     if (!ui_component) return promptElement;

     const componentType = ui_component.type;
     let inputElement = null;
     const props = { componentDetails: ui_component, onSubmit: handleDynamicInputSubmit, disabled: currentInteractionDisabled };

     // --- UPDATED Switch ---
     switch (componentType) {
       case 'text_input': inputElement = <ChatTextInput {...props} />; break;
       case 'dropdown': inputElement = <ChatDropdown {...props} />; break;
       case 'number_input': inputElement = <ChatNumberInput {...props} />; break;
       case 'checkbox': inputElement = <ChatCheckbox {...props} />; break;
       case 'date_picker': inputElement = <ChatDatePickerNative {...props} />; break; // Using native for now
       case 'json_input': inputElement = <ChatJsonInput {...props} />; break;
       case 'datetime_picker': inputElement = <ChatDateTimePicker {...props} />; break; // Use new component
       case 'tags_input': inputElement = <ChatTagsInput {...props} />; break; // Use new component
       default: inputElement = <p className='text-sm text-red-500 italic'>(Unsupported UI type: {componentType})</p>;
     }
     return <div>{promptElement}{inputElement}</div>;
  };

  // --- Initial Message ---
  useEffect(() => {
    addMessage('assistant', { prompt: "Hello! Please select an API operation above to begin.", ui_component: null });
  }, [addMessage]); // Depend on addMessage

  return (
    <div className="flex flex-col h-[calc(100vh-40px)] max-w-4xl mx-auto border rounded shadow-lg bg-white">
      {/* Header */}
      <div className="p-3 border-b bg-gray-100 text-center font-semibold text-gray-700">API Assistant</div>

      {/* Operation Selector */}
      <OperationSelector
          operations={availableOperations}
          onSelectOperation={handleUserInput}
          disabled={isAssistantTyping || currentInteractionDisabled || !!currentApiOperation} // Disable if flow in progress
          currentSelection={currentApiOperation} // Pass current selection
      />

      {/* Message List */}
      <div className="flex-grow p-4 overflow-y-auto space-y-4 bg-gray-50">
        {/* Display fetch error if any */}
        {fetchError && !isLoading && <p className="error">{fetchError}</p>} {/* Show fetch error if not loading */}

        {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                {/* ... Message bubble structure ... */}
                <div className={`flex items-end max-w-[80%] ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                   <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-white ${msg.sender === 'user' ? 'bg-blue-500 ml-2' : 'bg-gray-400 mr-2'}`}> {msg.sender === 'user' ? <User size={14}/> : <Bot size={14}/>} </div>
                   <div className={`px-4 py-2 rounded-lg shadow-sm ${ msg.sender === 'user' ? 'bg-blue-500 text-white rounded-br-none' : 'bg-white text-gray-800 border border-gray-200 rounded-bl-none' }`}>
                    {msg.sender === 'assistant' && typeof msg.content === 'object'
                        ? renderDynamicComponent(msg.content)
                        : <p className="text-sm" style={{whiteSpace: 'pre-wrap'}}>{typeof msg.content === 'object' ? JSON.stringify(msg.content) : msg.content}</p>
                    }
                  </div>
                </div>
            </div>
         ))}
         {/* Typing Indicator */}
         {isAssistantTyping && ( <div className="flex justify-start"> {/* ... Typing indicator bubble ... */} <div className={`flex items-end max-w-[80%]`}> <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-white bg-gray-400 mr-2`}> <Bot size={14}/> </div> <div className="px-4 py-2 rounded-lg bg-white text-gray-500 italic border border-gray-200 rounded-bl-none shadow-sm"> <Loader2 className="animate-spin inline h-4 w-4 mr-1" /> Typing... </div> </div> </div> )}
        <div ref={chatEndRef} /> {/* Element to scroll to */}
      </div>

      {/* Input Bar (Removed/Replaced by Operation Selector for starting flows) */}
       <div className="p-3 border-t bg-gray-50 text-center text-xs text-gray-400">
            Select an operation above to start a new API interaction.
       </div>
    </div>
  );
}

// Export the main component
export default ChatInterface;

