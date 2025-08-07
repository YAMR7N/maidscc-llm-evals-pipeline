# Loss of Interest Analysis Implementation

## Overview

The Loss of Interest analysis is a universal system designed to understand why applicants drop off at various stages of the application process. It uses dynamic prompts based on:
- **Department**: Different departments may have different application flows
- **Last Skill**: The specific stage where the applicant dropped off

## Current Configuration

### Supported Departments
- **Filipina**: Fully configured with 8 different skill-based prompts

### Filipina Department Skills
The system recognizes the following skills for Filipina applicants:

1. **filipina_outside_pending_facephoto**
   - Applicants outside Philippines who haven't submitted profile photo
   
2. **filipina_outside_pending_passport**
   - Applicants outside Philippines who haven't submitted passport

3. **filipina_outside_uae_pending_joining_date**
   - Applicants in countries other than UAE/Philippines who haven't provided joining date

4. **filipina_in_phl_pending_valid_visa**
   - Applicants in Philippines who haven't submitted active visa

5. **filipina_in_phl_pending_passport**
   - Applicants in Philippines who haven't submitted passport

6. **filipina_in_phl_pending_facephoto**
   - Applicants in Philippines who haven't submitted profile photo

7. **filipina_in_phl_pending_oec_from_maid**
   - Applicants in Philippines who need to provide OEC themselves

8. **filipina_in_phl_pending_oec_from_company**
   - Applicants in Philippines where company assists with OEC

## Usage

### Command Line
```bash
# Run for Filipina department
./run_all.sh loss_of_interest --departments "Filipina"

# With upload to Google Sheets
./run_all.sh loss_of_interest --departments "Filipina" --with-upload

# Dry run
./run_all.sh loss_of_interest --departments "Filipina" --dry-run

# Direct Python execution
python3 scripts/run_pipeline.py \
    --prompt loss_of_interest \
    --departments "Filipina" \
    --format xml \
    --model gemini-2.5-pro
```

### Requirements
- **Format**: Must be XML (to access `last_skill` field)
- **Model**: Default is `gemini-2.5-pro`

## Adding New Departments

To add loss of interest analysis for a new department:

1. **Update the prompt file** (`prompts/loss_of_interest.py`):
   ```python
   def _load_department_prompts(self) -> Dict[str, Dict[str, str]]:
       return {
           "filipina": self._load_filipina_prompts(),
           "your_new_dept": self._load_your_new_dept_prompts(),  # Add this
       }
   
   def _load_your_new_dept_prompts(self) -> Dict[str, str]:
       return {
           "skill_name_1": """Your prompt for skill 1""",
           "skill_name_2": """Your prompt for skill 2""",
           # Add more skills as needed
       }
   ```

2. **Update default departments** in `scripts/run_pipeline.py` if needed:
   ```python
   if departments == "all":
       dept_list = ["Filipina", "YourNewDept"]  # Add new dept here
   ```

## Technical Details

### Dynamic Prompt Selection
The system uses a two-level selection process:
1. First, it identifies the department from the conversation data
2. Then, it selects the appropriate prompt based on the `last_skill` field

### Case-Insensitive Matching
All skill matching is case-insensitive to handle variations in data formatting.

### Fallback Mechanism
If no specific prompt matches, a default generic prompt is used.

## Output

The analysis generates insights about:
- **Reason Category**: High-level category of the drop-off reason
- **Reason Subcategory**: Specific reason within the category
- **Explanation**: Brief explanation of why the applicant dropped off
- **OEC Country**: (For some skills) The applicant's last working country

## Future Enhancements

1. **Post-processing**: Implement aggregation and reporting of drop-off reasons
2. **Google Sheets Upload**: Automate uploading of analysis results
3. **Additional Departments**: Add support for more departments as needed
4. **Visualization**: Create dashboards showing drop-off patterns by skill and reason