#!/usr/bin/env python3
"""
Custom script to run sentiment analysis for August 1st data
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

from scripts.run_pipeline import (
    LLMProcessor, load_preprocessed_data, save_llm_outputs,
    preprocess_data, check_preprocessed_output_exists
)
from prompts.base import PromptRegistry
from config.departments import DEPARTMENTS

async def run_sentiment_analysis_aug1():
    """Run sentiment analysis for August 1st data for all departments"""
    
    print("🎯 Running Sentiment Analysis for August 1st Data")
    print("="*60)
    
    # Configuration
    date_str = "2025-08-01"
    date_folder = "2025-08-01"
    date_suffix = "08_01"
    format_type = "segmented"
    model = "gpt-4o"
    
    # Get the prompt
    prompt_registry = PromptRegistry()
    sa_prompt = prompt_registry.get_prompt("sentiment_analysis")
    prompt_text = sa_prompt.get_prompt_text()
    
    # Get all departments
    dept_list = list(DEPARTMENTS.keys())
    
    print(f"📊 Will process {len(dept_list)} departments")
    print(f"📅 Date: {date_str}")
    print(f"🤖 Model: {model}")
    print(f"📄 Format: {format_type}")
    
    # Track overall statistics
    total_conversations = 0
    total_departments_processed = 0
    
    # Create output directory
    output_dir = f"outputs/LLM_outputs/{date_folder}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each department
    for department in dept_list:
        print(f"\n{'='*60}")
        print(f"🏢 Processing {department}...")
        
        try:
            # Check if raw data exists
            raw_file = f"outputs/tableau_exports/{date_folder}/{department}_{date_str.replace('-', '')}.csv"
            
            if not os.path.exists(raw_file):
                print(f"⚠️  Raw data not found: {raw_file}")
                continue
            
            # Check if output already exists
            output_file = f"{output_dir}/saprompt_{department.lower().replace(' ', '_')}_{date_suffix}.csv"
            if os.path.exists(output_file):
                print(f"✅ Output already exists: {output_file}")
                response = input("   Overwrite? (y/n): ")
                if response.lower() != 'y':
                    print("   Skipping...")
                    continue
            
            # Step 1: Preprocess data
            print(f"\n📂 Preprocessing data...")
            
            # Create preprocessing output directory
            preprocessing_dir = f"outputs/preprocessing_output/{date_folder}"
            os.makedirs(preprocessing_dir, exist_ok=True)
            
            # Run preprocessing (we'll do it manually to control the date)
            from utils.clean_raw import clean_raw_data
            from utils.segment import process_conversations as segment_conversations
            
            # Clean the data
            cleaned_file = f"{preprocessing_dir}/{department}_cleaned.csv"
            clean_raw_data(raw_file, cleaned_file, filter_agent_messages=False)
            
            # Segment conversations
            dept_config = DEPARTMENTS[department]
            target_skills = dept_config['skills']
            processed_df = segment_conversations(cleaned_file, target_skills)
            
            # Save segmented data
            segmented_file = f"{preprocessing_dir}/{department}_segmented.csv"
            processed_df.to_csv(segmented_file, index=False)
            
            print(f"   ✅ Preprocessed and saved to: {segmented_file}")
            
            # Step 2: Load preprocessed data
            conversations = processed_df.to_dict('records')
            
            if not conversations:
                print(f"⚠️  No conversations found for {department}")
                continue
            
            print(f"   📊 Found {len(conversations)} conversations")
            
            # Step 3: Process through LLM
            print(f"\n🤖 Processing through {model}...")
            processor = LLMProcessor(model)
            
            # Run the processing
            results = await processor.process_conversations(conversations, prompt_text)
            
            print(f"   ✅ Processed {len(results)} conversations")
            
            # Step 4: Save outputs
            df = pd.DataFrame(results)
            df.to_csv(output_file, index=False)
            print(f"   💾 Saved results to: {output_file}")
            
            # Display token usage
            print(f"   {processor.get_token_summary(department)}")
            
            # Update statistics
            total_conversations += len(results)
            total_departments_processed += 1
            
        except Exception as e:
            print(f"❌ Error processing {department}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n{'='*60}")
    print(f"📊 Summary:")
    print(f"   - Departments processed: {total_departments_processed}/{len(dept_list)}")
    print(f"   - Total conversations: {total_conversations}")
    
    return total_departments_processed > 0

async def run_post_processing_and_upload():
    """Run post-processing and upload for August 1st data"""
    
    print("\n🚀 Running Post-processing and Upload...")
    
    # We need to temporarily modify the date calculation in the processors
    # For now, let's create a custom post-processor for August 1st
    
    from post_processors.sa_post_processing import SAPreprocessor
    from post_processors.upload_sa_sheets import SaprompUploader
    
    # Create custom processor that handles August 1st date
    processor = SAPreprocessor()
    
    # Override the date to August 1st
    import datetime
    original_date_func = datetime.datetime.now
    
    def mock_date():
        # Return August 2nd so that "yesterday" is August 1st
        return datetime.datetime(2025, 8, 2)
    
    # Temporarily replace datetime.now
    datetime.datetime.now = mock_date
    
    try:
        print("📊 Processing sentiment analysis results...")
        
        # Get all departments
        dept_list = list(DEPARTMENTS.keys())
        results = {}
        success_count = 0
        
        for department in dept_list:
            nps = processor.update_department_nps(department)
            if nps is not None:
                results[department] = nps
                success_count += 1
                print(f"   ✅ {department}: NPS = {nps:.2f}")
            else:
                results[department] = None
                print(f"   ⚠️  {department}: No data found")
        
        print(f"\n📈 Processed {success_count}/{len(dept_list)} departments")
        
        # Upload to Google Sheets
        print("\n📤 Uploading to Google Sheets...")
        uploader = SaprompUploader()
        uploader.process_all_files()
        
    finally:
        # Restore original datetime function
        datetime.datetime.now = original_date_func
    
    print("✅ Post-processing and upload completed!")

if __name__ == "__main__":
    # Run the async function
    success = asyncio.run(run_sentiment_analysis_aug1())
    
    if success:
        print("\n🎉 Sentiment Analysis completed successfully!")
        
        # Ask if user wants to run post-processing
        response = input("\nRun post-processing and upload? (y/n): ")
        if response.lower() == 'y':
            asyncio.run(run_post_processing_and_upload())
    else:
        print("\n❌ Sentiment Analysis failed!")