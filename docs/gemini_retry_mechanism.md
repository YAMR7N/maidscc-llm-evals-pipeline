# LLM API Retry Mechanism

## Overview

The LLM Judge Pipeline now includes a robust retry mechanism for both Gemini and OpenAI API calls to handle transient failures, timeouts, and rate limiting. This ensures maximum reliability when processing conversations through any LLM model.

## Features

- **Exponential Backoff**: Retry delays increase exponentially with each attempt to avoid overwhelming the API
- **Jitter**: Random jitter is added to retry delays to prevent thundering herd problems
- **Timeout Protection**: Each API call is wrapped in a timeout to prevent hanging requests
- **Smart Error Detection**: Automatically detects and handles rate limits and server errors
- **Concurrent Processing**: Failed requests are retried without blocking other concurrent requests

## Configuration

You can configure retry behavior per model in `config/settings.py`:

```python
"gemini-1.5-pro": {
    "provider": "gemini", 
    "temperature": 0.0,
    "max_retries": 3,        # Maximum retry attempts (default: 3)
    "base_delay": 1.0,       # Base delay in seconds (default: 1.0)
    "max_delay": 30.0,       # Maximum delay in seconds (default: 30.0)
    "timeout_seconds": 60.0  # Timeout per attempt in seconds (default: 60.0)
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

The mechanism handles several types of errors:

- **Timeouts**: `asyncio.TimeoutError`
- **Rate Limits**: Detected by keywords: "rate limit", "quota", "resource exhausted", "429", "too many requests"
- **Server Errors**: Detected by keywords: "500", "502", "503", "504", "server error", "service unavailable"

## Logging

The retry mechanism provides detailed logging:

- `⏱️` Timeout notifications with retry information
- `⚠️` Error messages with truncated details
- `🔄` Retry attempts with delay information
- `❌` Final failure after all retries exhausted

## Example Output

```
⏱️  Timeout for ABC12345 (attempt 1/3). Retrying in 1.7s...
⚠️  Gemini error for XYZ67890: 429 Resource has been exhausted (e.g. check quota)...
🔄 Retrying (attempt 2/5) in 5.3s...
❌ Gemini error for DEF34567 after 3 attempts: 503 Service Unavailable...
```

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
- `scripts/run_pipeline.py`: `_analyze_with_gemini_with_retry()` method
- Configuration in `config/settings.py`
- Maintains compatibility with existing concurrent processing