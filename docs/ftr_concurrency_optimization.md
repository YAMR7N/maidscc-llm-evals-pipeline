# FTR Concurrency Optimization

## Problem
FTR analysis with XML3D format was experiencing excessive timeouts due to:
- **Large payloads**: XML3D aggregates 3 days of conversation data per customer
- **High concurrency**: 30 concurrent requests overwhelming the API
- **Cascading effect**: Timeouts trigger retries with doubled tokens, making payloads even larger

## Solution
Implemented dynamic concurrency control based on data format:
- **XML3D format**: 10 concurrent requests (heavy payloads)
- **Other formats**: 20 concurrent requests (lighter payloads)
- **Default**: 30 concurrent requests (for non-FTR analyses)

## Implementation
1. Modified `LLMProcessor.process_conversations()` to accept `max_concurrent` parameter
2. Updated `run_llm_processing()` to pass through concurrency settings
3. FTR analysis now detects format and adjusts concurrency accordingly

## Benefits
- Fewer timeouts on initial attempts
- More stable API performance
- Better resource utilization
- Reduced retry overhead

## Configuration
The concurrency limits can be adjusted in `run_ftr_analysis()`:
```python
max_concurrent = 10 if format_type == "xml3d" else 20
```

## Monitoring
The pipeline now logs the concurrency limit being used:
```
🔧 Using concurrency limit: 10 (reduced for xml3d format)
🚦 Starting LLM processing with 10 concurrent requests...
```