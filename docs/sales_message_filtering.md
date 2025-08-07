# Sales Message Filtering for Rule Breaking Analysis

## Overview

This feature automatically filters out automated sales messages from conversations before running rule breaking analysis for MV Sales and CC Sales departments. This prevents false positives where standard automated messages would be incorrectly flagged as rule violations.

## Implementation Details

### Filter Location
- **File**: `utils/sales_message_filter.py`
- **Integration**: Automatically applied in `run_rule_breaking()` function in `scripts/run_pipeline.py`

### How It Works

1. **Department Check**: Only applies to MV Sales and CC Sales departments
2. **Format Check**: Only works with JSON format (not segmented, XML, etc.)
3. **Message Filtering**: Removes messages that match the excluded list with:
   - **70% similarity matching** using sequence matching algorithm
   - Case-insensitive comparison
   - Whitespace normalization
   - Unicode character handling
   - Containment detection (80% threshold) for messages embedded in longer responses

### Excluded Messages

The filter removes 15 automated messages including:
- "Is there anything else I can help you with?"
- "What else can I help you with? Or are you ready to get it done now?"
- Price list templates
- Standard greetings and closings
- And more (see `excluded_messages_sales.txt`)

### Usage

The filtering is automatic when running rule breaking analysis:

```bash
# For MV Sales or CC Sales with JSON format
python3 scripts/run_pipeline.py --prompt rule_breaking --departments "MV Sales" --format json --with-upload

# Or using the shell script
./run_all.sh rb "MV Sales" --with-upload
```

The similarity threshold (default: 70%) can be adjusted in the code if needed for stricter or more flexible matching.

### Important Notes

1. **Format Requirement**: Must use JSON format for filtering to work
2. **Tool Messages**: Tool messages are never filtered
3. **Message Types**: Only filters "normal message" type messages
4. **Normalization**: Handles variations in capitalization, spacing, and unicode characters

### Statistics

When filtering is applied, you'll see output like:
```
🔧 Filtering automated sales messages for MV Sales...
  Removed 3 automated messages from conversation CH123...
📧 Total automated messages removed: 45
```

## Testing

To test the filter independently:

```python
from utils.sales_message_filter import filter_sales_conversations

conversations = [...]  # Your JSON conversations
filtered = filter_sales_conversations(conversations, ['MV Sales'])
```

## Maintenance

To add or modify excluded messages:
1. Edit `excluded_messages_sales.txt`
2. Or update the `EXCLUDED_MESSAGES` list in `utils/sales_message_filter.py`
3. Test thoroughly to ensure no false positives/negatives 