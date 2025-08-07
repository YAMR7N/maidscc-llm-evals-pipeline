# LLM API Retry Mechanism

## Overview

The LLM Judge Pipeline now includes a robust retry mechanism for OpenAI, Gemini, and Anthropic API calls to handle transient failures, timeouts, and rate limiting. This ensures maximum reliability when processing conversations through any LLM model.

## Features

- **Exponential Backoff**: Retry delays increase exponentially with each attempt to avoid overwhelming the API
- **Jitter**: Random jitter is added to retry delays to prevent thundering herd problems
- **Timeout Protection**: Each API call is wrapped in a timeout to prevent hanging requests
- **Smart Error Detection**: Automatically detects and handles rate limits and server errors
- **Concurrent Processing**: Failed requests are retried without blocking other concurrent requests
- **Token Doubling on Retry**: Automatically doubles the max token limit on retry attempts to handle large prompts

## Configuration

You can configure retry behavior per model in `config/settings.py`. The same configuration options work for both OpenAI and Gemini models:

```python
# Gemini example
"gemini-1.5-pro": {
    "provider": "gemini", 
    "temperature": 0.0,
    "max_retries": 6,        # Maximum retry attempts (default: 6)
    "base_delay": 1.0,       # Base delay in seconds (default: 1.0)
    "max_delay": 30.0,       # Maximum delay in seconds (default: 30.0)
    "timeout_seconds": 60.0  # Timeout per attempt in seconds (default: 60.0)
}

# OpenAI example with custom retry settings
"gpt-4o": {
    "provider": "openai",
    "temperature": 0.0,
    "max_retries": 10,        # More retries for critical processes
    "base_delay": 2.0,       # Longer initial delay
    "timeout_seconds": 90.0  # Longer timeout for complex prompts
}

# Anthropic example
"claude-3-5-sonnet-20241022": {
    "provider": "anthropic",
    "temperature": 0.0,
    "max_retries": 10,
    "timeout_seconds": 90.0
}
```

## Retry Logic

1. **First Attempt**: The API call is made with the configured timeout
2. **On Failure**:
   - **Timeout**: Retries with exponential backoff
   - **Rate Limit Errors**: Retries with longer delay (minimum 5 seconds)
   - **Server Errors (5xx)**: Retries with exponential backoff
   - **Other Errors**: No retry (immediate failure)
3. **Backoff Calculation**: `delay = min(base_delay * (2^attempt) + random(0,1), max_delay)`

## Error Handling

The mechanism handles several types of errors for both providers:

### Common Errors (Both Providers)
- **Timeouts**: `asyncio.TimeoutError`
- **Server Errors**: Detected by keywords: "500", "502", "503", "504", "server error", "service unavailable"

### Gemini-Specific
- **Rate Limits**: Keywords: "rate limit", "quota", "resource exhausted", "429", "too many requests"

### OpenAI-Specific  
- **Rate Limits**: Keywords: "rate limit", "rate_limit", "429", "too many requests", "insufficient_quota"
- **Server Errors**: Keywords: "internal server error", "server_error"

### Anthropic-Specific
- **Rate Limits**: Keywords: "rate limit", "ratelimiterror", "429", "too many requests"
- **Server Errors**: Keywords: "apistatusererror", "internal server error"

## Logging

The retry mechanism provides detailed logging:

- `⏱️` Timeout notifications with retry information
- `⚠️` Error messages with truncated details
- `🔄` Retry attempts with delay information
- `❌` Final failure after all retries exhausted

## Example Output

```
⏱️  Timeout for ABC12345 (attempt 1/6). Retrying in 1.7s...
🔄 Retry 1/5 with 2x tokens (40,000 tokens)
⚠️  Gemini error for XYZ67890: 429 Resource has been exhausted (e.g. check quota)...
🔄 Retrying (attempt 2/6) in 5.3s...
❌ Gemini error for DEF34567 after 6 attempts: 503 Service Unavailable...
```

## Token Doubling Feature

The retry mechanism automatically doubles the maximum token limit on retry attempts. This is particularly useful for:

- **Large System Prompts**: Conversations with extensive system prompts (like the 57KB Doctors prompt)
- **Complex Categorization**: Tasks that require analyzing long conversations with detailed prompts
- **Edge Cases**: Handling conversations that are just at the token limit boundary

### Token Limits by Model

| Model | Normal Limit | On Retry (2x) |
|-------|--------------|---------------|
| gpt-4o | 16,000 | 32,000 |
| o4-mini | 30,000 | 60,000 |
| gpt-4o-mini | 16,000 | 32,000 |
| gemini-1.5-pro | 20,000 | 40,000 |
| gemini-1.5-flash | 20,000 | 40,000 |
| gemini-2.0-flash-exp | 20,000 | 40,000 |
| claude-3-opus | 4,096 | 8,192 |
| claude-3-sonnet | 4,096 | 8,192 |
| claude-3-haiku | 4,096 | 8,192 |
| claude-3.5-sonnet | 4,096 | 8,192 |

## Performance Considerations

- The retry mechanism maintains the overall concurrency limit (30 concurrent requests)
- Failed requests don't block the processing of other conversations
- Exponential backoff prevents API flooding
- Jitter prevents synchronized retry storms

## Best Practices

1. **Monitor Retry Rates**: High retry rates may indicate API issues or quota problems
2. **Adjust Timeouts**: Increase timeout_seconds for complex prompts or large conversations
3. **Rate Limit Handling**: Consider reducing concurrency if rate limits are frequently hit
4. **Error Analysis**: Check logs for patterns in failures to optimize retry configuration

## Implementation Details

The retry logic is implemented in:
- `scripts/run_pipeline.py`: 
  - `_analyze_with_openai_with_retry()` method for OpenAI
  - `_analyze_with_gemini_with_retry()` method for Gemini
  - `_analyze_with_anthropic_with_retry()` method for Anthropic
- Configuration in `config/settings.py`
- Maintains compatibility with existing concurrent processing
- Retry configuration is stored in `self.retry_config` for each LLMProcessor instance
- Anthropic support requires `ANTHROPIC_API_KEY` environment variable