#!/usr/bin/env python3
"""
Custom script to run policy escalation analysis for August 3rd Doctors department data
"""

import sys
import os
import pandas as pd
import asyncio
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.run_pipeline import LLMProcessor, load_preprocessed_data, save_llm_outputs
from prompts.base import PromptRegistry

async def run_policy_escalation_aug3():
    """Run policy escalation for August 3rd Doctors department"""
    
    print("🎯 Running Policy Escalation Analysis for August 3rd Doctors Department")
    print("="*60)
    
    # Configuration
    department = "Doctors"
    date_str = "2025-08-03"
    format_type = "xml"
    model = "gpt-4o-mini"  # Using the recommended model for policy escalation
    
    # Get the prompt
    prompt_registry = PromptRegistry()
    policy_escalation_prompt = prompt_registry.get_prompt("policy_escalation")
    prompt_text = policy_escalation_prompt.get_prompt_text()
    
    # Check if preprocessed data exists
    preprocessed_file = f"outputs/preprocessing_output/{date_str}/Doctors_xml.csv"
    
    if not os.path.exists(preprocessed_file):
        print(f"❌ Preprocessed XML data not found: {preprocessed_file}")
        print("   Please ensure the data has been preprocessed in XML format first.")
        return False
    
    print(f"✅ Found preprocessed data: {preprocessed_file}")
    
    # Check if output already exists
    output_file = f"outputs/LLM_outputs/{date_str}/policy_escalation_doctors_08_03.csv"
    if os.path.exists(output_file):
        print(f"⚠️  Output already exists: {output_file}")
        response = input("Do you want to overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Exiting without processing.")
            return False
    
    # Load preprocessed data
    print(f"\n📂 Loading preprocessed data...")
    conversations = load_preprocessed_data(preprocessed_file, format_type)
    print(f"   Loaded {len(conversations)} conversations")
    
    # Process through LLM
    print(f"\n🤖 Processing through {model}...")
    processor = LLMProcessor(model)
    
    # Run the processing
    results = await processor.process_conversations(conversations, prompt_text)
    
    print(f"\n✅ Processed {len(results)} conversations")
    
    # Create output directory if it doesn't exist
    output_dir = f"outputs/LLM_outputs/{date_str}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save outputs with modified function to handle the date
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    print(f"\n💾 Saved results to: {output_file}")
    
    # Display token usage
    print(f"\n{processor.get_token_summary(department)}")
    
    # Run post-processing
    print(f"\n📊 Running post-processing...")
    try:
        # We need to temporarily modify the date calculation in the postprocessor
        # For now, let's just inform the user
        print("   Note: Post-processing uses yesterday's date by default.")
        print("   To process August 3rd data, you may need to run post-processing separately.")
        
        # Create the expected output structure for post-processing
        print(f"\n📋 Summary:")
        print(f"   - Department: {department}")
        print(f"   - Date: {date_str}")
        print(f"   - Conversations processed: {len(results)}")
        print(f"   - Output file: {output_file}")
        
    except Exception as e:
        print(f"⚠️  Post-processing note: {str(e)}")
    
    return True

if __name__ == "__main__":
    # Run the async function
    success = asyncio.run(run_policy_escalation_aug3())
    
    if success:
        print("\n🎉 Policy Escalation analysis completed successfully!")
        print("\n📝 Next steps:")
        print("   1. Review the output file in outputs/LLM_outputs/2025-08-03/")
        print("   2. Run post-processing if needed")
        print("   3. Upload to Google Sheets if required")
    else:
        print("\n❌ Policy Escalation analysis failed!")