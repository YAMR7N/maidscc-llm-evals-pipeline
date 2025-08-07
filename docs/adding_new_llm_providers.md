# Adding New LLM Providers

This guide explains how to add support for new LLM providers to the pipeline.

## Overview

The pipeline currently supports three LLM providers:
- OpenAI (GPT models)
- Google Gemini
- Anthropic (Claude models)

## Steps to Add a New Provider

### 1. Update Dependencies

Add the provider's Python SDK to `requirements.txt`:
```
provider-sdk>=version
```

### 2. Update Configuration

Add model configurations to `config/settings.py`:
```python
MODELS = {
    # ... existing models ...
    "new-model-name": {
        "provider": "new_provider",
        "temperature": 0.0,
        # Optional retry configuration
        "max_retries": 3,
        "base_delay": 1.0,
        "max_delay": 30.0,
        "timeout_seconds": 60.0
    }
}
```

### 3. Update LLMProcessor

In `scripts/run_pipeline.py`, make the following changes:

#### Import the SDK
```python
import new_provider_sdk
```

#### Initialize Client in __init__
```python
elif self.provider == "new_provider":
    self.new_provider_client = new_provider_sdk.Client(
        api_key=os.getenv('NEW_PROVIDER_API_KEY')
    )
```

#### Add Token Limits in get_max_tokens
```python
elif self.provider == "new_provider":
    base_tokens = 8192  # Or whatever the limit is
```

#### Add Provider Case in analyze_conversation
```python
elif self.provider == "new_provider":
    return await self._analyze_with_new_provider_with_retry(conversation, final_prompt, chat_id)
```

### 4. Implement Provider Methods

Add two methods for the new provider:

```python
async def _analyze_with_new_provider_with_retry(self, conversation, prompt, chat_id=None):
    """Wrapper for New Provider API calls with retry logic"""
    # Copy the retry logic from existing providers
    # Adjust error detection keywords as needed
    
async def _analyze_with_new_provider(self, conversation, prompt, chat_id=None, retry_attempt=0):
    """Analyze conversation using New Provider"""
    # Implement the actual API call
    # Track token usage if available
    # Return {"llm_output": result} format
```

### 5. Update Documentation

1. Add the provider to `docs/llm_api_retry_mechanism.md`
2. Include error keywords specific to the provider
3. Document token limits

### 6. Add Environment Variable

Update `.env.example` (if exists) or document that users need:
```
NEW_PROVIDER_API_KEY=your-api-key-here
```

## Testing

Create a test script similar to `test_anthropic.py` to verify:
1. Client initialization
2. API calls work
3. Token tracking functions
4. Retry mechanism handles errors
5. Token doubling on retry

## Example: Adding Anthropic

See the implementation of Anthropic support as a reference:
- Configuration in `config/settings.py`
- Methods in `scripts/run_pipeline.py`
- Error handling for rate limits and server errors
- Token limit management (4096 for all Claude models)

## Best Practices

1. **Error Handling**: Study the provider's error messages to properly detect rate limits and server errors
2. **Token Limits**: Research the actual output token limits for each model
3. **Async Support**: Use the async client if available, otherwise wrap sync calls with `asyncio.run_in_executor`
4. **Token Tracking**: Extract and log token usage for monitoring costs
5. **Retry Logic**: Use exponential backoff with jitter for all providers

## Common Gotchas

1. **Different Error Formats**: Each provider has different error message formats
2. **Token Counting**: Some providers count tokens differently
3. **System vs User Messages**: Some providers handle system prompts differently
4. **Response Format**: Extract the text content correctly from the provider's response object