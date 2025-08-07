# Filipina Loss of Interest Analysis Implementation

## Overview

The Filipina Loss of Interest analysis is a specialized pipeline that analyzes conversations where Filipino maid applicants dropped off at various stages of the application process. It uses dynamic prompts based on the `last_skill` field in the conversation to apply stage-specific evaluation criteria.

## Features

1. **Dynamic Prompt Selection**: Automatically selects the appropriate prompt based on the last skill recorded in the conversation
2. **Case-Insensitive Matching**: Skills are matched case-insensitively for flexibility
3. **8 Different Stage-Specific Prompts**: Each addressing different drop-off points in the application funnel

## Supported Skills and Their Prompts

### 1. Outside Pending Facephoto
- **Skill**: `Filipina_Outside_Pending_Facephoto`
- **Context**: Maid is outside UAE/Philippines and didn't provide profile picture
- **Focus**: Why profile picture wasn't submitted

### 2. Outside Pending Passport
- **Skill**: `Filipina_Outside_Pending_Passport`
- **Context**: Maid provided profile picture but not passport
- **Focus**: Barriers to passport submission

### 3. Outside UAE Pending Joining Date
- **Skill**: `Filipina_Outside_UAE_Pending_Joining_Date`
- **Context**: Maid in third country (not UAE/Philippines) didn't provide joining date
- **Focus**: Timing and release constraints

### 4. In Philippines Pending Valid Visa
- **Skill**: `Filipina_in_PHl_Pending_valid_visa`
- **Context**: Maid in Philippines didn't provide active visa proof
- **Focus**: Visa availability and eligibility

### 5. In Philippines Pending Passport
- **Skill**: `Filipina_in_PHL_Pending_Passport`
- **Context**: Maid in Philippines provided visa but not passport
- **Focus**: Passport-specific barriers

### 6. In Philippines Pending Facephoto
- **Skill**: `Filipina_in_PHl_Pending_Facephoto`
- **Context**: Maid in Philippines provided visa/passport but not profile picture
- **Focus**: Final step hesitation

### 7. In Philippines Pending OEC From Maid
- **Skill**: `Filipina_in_PHl_Pending_OEC_From_maid`
- **Context**: Maid needs to obtain OEC herself
- **Focus**: OEC process barriers

### 8. In Philippines Pending OEC From Company
- **Skill**: `Filipina_in_PHl_Pending_OEC_From_Company`
- **Context**: Company assisting with OEC
- **Focus**: Company assistance process issues

## Usage

### Command Line

```bash
# Run the analysis
python scripts/run_pipeline.py \
    --prompt filipina_loss_of_interest \
    --departments Filipina \
    --format xml \
    --model gemini-2.5-pro

# With upload to Google Sheets
python scripts/run_pipeline.py \
    --prompt filipina_loss_of_interest \
    --departments Filipina \
    --format xml \
    --model gemini-2.5-pro \
    --with-upload
```

### Shell Script Integration

Add to `run_daily_pipeline.sh` or create a dedicated script:

```bash
#!/bin/bash
# Run Filipina Loss of Interest Analysis

echo "🇵🇭 Running Filipina Loss of Interest Analysis..."
python scripts/run_pipeline.py \
    --prompt filipina_loss_of_interest \
    --departments Filipina \
    --format xml \
    --model gemini-2.5-pro \
    --with-upload
```

## Technical Implementation

### Prompt Selection Logic

1. **Exact Match**: First tries exact case-insensitive match
2. **Pattern Matching**: Falls back to pattern matching for common skill components
3. **Default Prompt**: Uses generic prompt if no match found

### Key Components

1. **Prompt File**: `prompts/filipina_loss_of_interest.py`
   - Contains all 8 stage-specific prompts
   - Implements dynamic selection logic
   - Case-insensitive skill matching

2. **Pipeline Function**: `run_filipina_loss_of_interest()` in `scripts/run_pipeline.py`
   - Forces XML format (required for `last_skill` field)
   - Processes conversations with skill-aware prompts
   - Provides skill distribution summary

3. **Data Requirements**:
   - Must use XML format to access `last_skill` field
   - Requires Filipina department data from Tableau
   - Works with conversations that have valid `last_skill` values

## Output

### Files Generated

1. **LLM Output**: `outputs/LLM_outputs/{date}/filipina_loss_of_interest_filipina_{date}.csv`
   - Contains conversation_id, conversation, last_skill, and llm_output
   - Structured analysis of drop-off reasons

2. **Skill Distribution**: Printed to console showing conversation counts per skill

### Analysis Categories

Each prompt evaluates conversations against these main categories:
- Legitimacy Issues
- Pending Employer Release
- Financial Concerns
- Cancelled Applications
- Alternative Job Preferences
- Stopped Answering
- Misunderstanding in Application Process
- Vacation Plans
- Document/Process Specific Issues

## Extending the System

### Adding New Skills

To add support for new skills:

1. Add the skill pattern and prompt to `_load_skill_prompts()` in `prompts/filipina_loss_of_interest.py`
2. Update the pattern matching logic in `get_prompt_text()` if needed
3. Document the new skill in this guide

### Creating Post-Processing

To add post-processing:

1. Create `post_processors/filipina_loss_of_interest_postprocessing.py`
2. Analyze drop-off patterns by skill
3. Generate summary statistics and insights
4. Update snapshot sheet with key metrics

## Best Practices

1. **Regular Monitoring**: Run daily to track application funnel health
2. **Skill Validation**: Periodically check for new skills in the data
3. **Prompt Tuning**: Adjust prompts based on analysis accuracy
4. **Cross-Reference**: Compare with other department patterns

## Troubleshooting

### Common Issues

1. **No conversations found**: Check if Filipina data exists for the date
2. **Default prompt used**: Verify skill names match expected patterns
3. **XML format required**: Pipeline automatically switches to XML

### Debug Mode

Enable detailed logging by adding debug prints:
```python
print(f"🔍 Filipina Loss of Interest - Last skill: '{last_skill}'")
```

## Integration with Existing Pipeline

This analysis integrates seamlessly with the existing pipeline:
- Uses standard caching mechanism
- Follows established file naming conventions
- Compatible with existing post-processing framework
- Supports all standard pipeline options (dry-run, model selection, etc.)