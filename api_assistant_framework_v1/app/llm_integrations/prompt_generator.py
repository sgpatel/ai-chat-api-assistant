# app/llm_integrations/prompt_generator.py
# Uses an LLM to generate natural language prompts for API parameters.

import openai
from openai import OpenAI, AsyncOpenAI # Import AsyncOpenAI for async usage
from typing import Optional

# Use absolute imports within the 'app' package
from app.models.api_spec import ParameterInfo
from app.config import settings, logger

# --- Initialize OpenAI Client ---
# Use AsyncOpenAI for compatibility with FastAPI's async nature
aclient: Optional[AsyncOpenAI] = None
if settings.OPENAI_API_KEY:
    try:
        aclient = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("Async OpenAI client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Async OpenAI client: {e}", exc_info=True)
else:
    logger.warning("OPENAI_API_KEY not found in settings. LLM prompt generation will be disabled.")
# --- End Initialization ---


async def generate_natural_language_prompt(param_info: ParameterInfo) -> str:
    """
    Uses an LLM (if available) to generate a user-friendly prompt for a given API parameter.

    Args:
        param_info: A Pydantic model containing details about the parameter.

    Returns:
        A natural language question string, or a default template if LLM fails/unavailable.
    """
    # --- Fallback Prompt Generation ---
    # Generate a default prompt based on available info, used if LLM fails or is disabled
    default_prompt = f"Please provide the {param_info.name.replace('_', ' ')}"
    details = []
    if param_info.description:
        # Clean up description slightly for prompt
        desc_clean = param_info.description.replace('\n', ' ').strip()
        details.append(f"{desc_clean}")
    if param_info.schema_details.type:
        details.append(f"Type: {param_info.schema_details.type}")
    if param_info.schema_details.format:
        details.append(f"Format: {param_info.schema_details.format}")
    if param_info.schema_details.enum:
        details.append(f"Options: {', '.join(map(str, param_info.schema_details.enum))}")

    if details:
        default_prompt += f" ({'; '.join(details)})"
    default_prompt += ":"
    # --- End Fallback Prompt Generation ---


    # --- LLM Prompt Generation ---
    if not aclient:
        logger.debug("OpenAI client not available, returning default prompt.")
        return default_prompt

    try:
        # Construct the prompt for the LLM
        system_message = """You are an assistant that rephrases technical API parameter requests into simple, friendly, natural language questions for a user in a chat interface. Ask only one clear question per parameter."""

        # Describe the parameter to the LLM
        user_message_content = f"Parameter Name: {param_info.name}\n"
        user_message_content += f"Required: {'Yes' if param_info.required else 'No'}\n"
        user_message_content += f"Type: {param_info.schema_details.type}\n"
        if param_info.schema_details.format:
            user_message_content += f"Format: {param_info.schema_details.format}\n"
        if param_info.schema_details.enum:
            user_message_content += f"Allowed Values: {', '.join(map(str, param_info.schema_details.enum))}\n"
        if param_info.description:
            user_message_content += f"Description: {param_info.description}\n"

        user_message_content += "\nPlease formulate a short, clear, and friendly question to ask the user for this parameter's value."

        logger.debug(f"Sending request to OpenAI for prompt generation. Parameter: {param_info.name}")
        response = await aclient.chat.completions.create(
            model=settings.DEFAULT_LLM_MODEL if hasattr(settings, 'DEFAULT_LLM_MODEL') else "gpt-4o-mini", # Use model from settings or default
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message_content}
            ],
            temperature=0.5, # Lower temperature for more focused prompts
            max_tokens=100, # Limit response length
            n=1,
            stop=None,
        )

        generated_prompt = response.choices[0].message.content.strip()

        # Basic cleanup - remove quotes if LLM wraps response in them
        if generated_prompt.startswith('"') and generated_prompt.endswith('"'):
            generated_prompt = generated_prompt[1:-1]
        # Ensure it ends with a question mark or colon if appropriate
        if not generated_prompt.endswith(('?', ':', '.')):
             generated_prompt += "?" # Default to question mark

        logger.info(f"LLM generated prompt for '{param_info.name}': {generated_prompt}")
        return generated_prompt

    except openai.APIConnectionError as e:
        logger.error(f"OpenAI API request failed to connect: {e}")
    except openai.RateLimitError as e:
        logger.error(f"OpenAI API request exceeded rate limit: {e}")
    except openai.APIStatusError as e:
        logger.error(f"OpenAI API returned non-200 status code: {e.status_code} {e.response}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during OpenAI call: {e}", exc_info=True)

    # Fallback to default prompt if LLM call fails
    logger.warning(f"LLM prompt generation failed for '{param_info.name}', returning default prompt.")
    return default_prompt


# --- Example Usage (for testing this module directly) ---
if __name__ == "__main__":
    import asyncio
    from app.models.api_spec import ParameterSchema # Need this for example

    async def test_prompt_gen():
        # Make sure OPENAI_API_KEY is set in your environment/.env
        if not settings.OPENAI_API_KEY:
             print("Skipping test: OPENAI_API_KEY not set.")
             return

        print("Testing Prompt Generation...")

        # Example 1: Simple string
        param1 = ParameterInfo(name="task_name", required=True, location="body_property",
                               schema_details=ParameterSchema(type="string", description="The primary name or title of the task."))
        prompt1 = await generate_natural_language_prompt(param1)
        print(f"\nParameter: {param1.name}")
        print(f"Generated Prompt: {prompt1}")

        # Example 2: Enum
        param2 = ParameterInfo(name="status", required=True, location="body_property",
                               schema_details=ParameterSchema(type="string", enum=["Pending", "In Progress", "Blocked", "Completed"], description="The current status"))
        prompt2 = await generate_natural_language_prompt(param2)
        print(f"\nParameter: {param2.name}")
        print(f"Generated Prompt: {prompt2}")

        # Example 3: Date
        param3 = ParameterInfo(name="due_date", required=True, location="body_property",
                               schema_details=ParameterSchema(type="string", format="date", description="Task due date (YYYY-MM-DD)"))
        prompt3 = await generate_natural_language_prompt(param3)
        print(f"\nParameter: {param3.name}")
        print(f"Generated Prompt: {prompt3}")

        # Example 4: Boolean
        param4 = ParameterInfo(name="send_notification", required=True, location="body_property",
                               schema_details=ParameterSchema(type="boolean", default=True, description="Send notification?"))
        prompt4 = await generate_natural_language_prompt(param4)
        print(f"\nParameter: {param4.name}")
        print(f"Generated Prompt: {prompt4}")

    # Run the async test function
    asyncio.run(test_prompt_gen())

