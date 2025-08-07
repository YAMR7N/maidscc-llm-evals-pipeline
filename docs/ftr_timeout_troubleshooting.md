# FTR Timeout Troubleshooting Guide

## Understanding FTR Timeouts

FTR (First Time Resolution) analysis is particularly prone to timeouts due to its unique requirements:

### 1. **XML3D Format Complexity**
- FTR uses the XML3D format which groups all conversations from the same customer over 3 days
- Each "conversation" in the LLM request can contain multiple chats from different days
- This results in much larger input sizes compared to other analyses

### 2. **3-Day Lookback**
- FTR downloads 3 days of conversation history (vs 1 day for most other analyses)
- This triples the amount of data to process
- Customers with high chat volume can have extremely large aggregated conversations

### 3. **Complex Evaluation Logic**
- The FTR prompt requires checking if customers repeated requests across different chat IDs
- This cross-referencing adds computational complexity

## Solutions Implemented

### 1. **Fixed Format Configuration**
- Changed default format from `transparent` to `xml3d` in `run_all.sh`
- This ensures FTR uses the correct multi-day customer view format

### 2. **Increased Timeout Settings**
- Extended timeout for `gpt-4o` from 60s to 120s
- Increased retry attempts from 6 to 8 for FTR's default model
- Token doubling on retry provides up to 32K tokens for complex conversations

### 3. **Retry Mechanism**
- With 8 retries and exponential backoff, the system has multiple chances to process large conversations
- Each retry doubles the token limit, handling progressively larger contexts

## Additional Recommendations

### 1. **Use Alternative Models**
For departments with high chat volume, consider using models with larger context windows:

```bash
# Use gemini-2.0-flash-exp (90s timeout, 10 retries)
./run_all.sh ftr --model gemini-2.0-flash-exp --departments "MV Resolvers"

# Use claude-3-5-sonnet (90s timeout, 10 retries)
./run_all.sh ftr --model claude-3-5-sonnet-20241022 --departments "MV Resolvers"
```

### 2. **Process Departments Separately**
Instead of processing all departments at once, run them individually:

```bash
# Process each department separately
./run_all.sh ftr --departments "MV Resolvers"
./run_all.sh ftr --departments "Doctors"
./run_all.sh ftr --departments "CC Resolvers"
```

### 3. **Monitor High-Volume Customers**
Customers with excessive chat volume over 3 days may still cause timeouts. Consider:
- Implementing customer-level limits in XML3D processing
- Splitting very large customer histories into multiple requests

### 4. **Adjust Concurrency**
For FTR specifically, you might want to reduce concurrency to give each request more resources:

```python
# In scripts/run_pipeline.py, modify the semaphore for FTR
if prompt_type == "ftr":
    semaphore = asyncio.Semaphore(15)  # Reduced from 30
else:
    semaphore = asyncio.Semaphore(30)
```

## Debugging Timeouts

If timeouts persist:

1. **Check the logs** for specific customer names that timeout repeatedly
2. **Examine the XML3D output** to see if certain customers have unusually large conversation histories:
   ```bash
   # Check the preprocessed XML3D file
   wc -l outputs/preprocessing/*/MV_Resolvers_xml3d.csv
   ```

3. **Look for patterns** in timeout messages - if it's always the same conversations, they might need special handling

## Performance Expectations

With the current settings:
- Most conversations should process within 30-60 seconds
- Large conversations may take up to 120 seconds
- With 8 retries and token doubling, success rate should be >95%
- Extremely large customer histories (>50 chats over 3 days) may still fail

## Future Improvements

Consider implementing:
1. Smart chunking for very large customer histories
2. Pre-filtering to exclude automated/system messages
3. Customer-level token limits in XML3D processing
4. Parallel processing of different date ranges