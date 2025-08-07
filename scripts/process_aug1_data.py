#!/usr/bin/env python3
"""
Process August 1st data: Convert Excel to CSV, rename, and run sentiment analysis
"""

import pandas as pd
import os
import sys
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def convert_and_rename_files():
    """Convert Excel files to CSV and rename them according to convention"""
    
    source_dir = "outputs/tableau_exports/2025-08-01"
    
    # Mapping of Excel filenames to target CSV names
    file_mappings = {
        "Sales CC.xlsx": "CC Sales_20250801.csv",
        "Applicants.xlsx": ["African_20250801.csv", "Ethiopian_20250801.csv", "Filipina_20250801.csv"],
        "Delighters.xlsx": "Delighters_20250801.csv",
        "MV Department.xlsx": "MV Resolvers_20250801.csv",
        "Doctors.xlsx": "Doctors_20250801.csv",
        "CC Department.xlsx": "CC Resolvers_20250801.csv",
        "Sales MV.xlsx": "MV Sales_20250801.csv"
    }
    
    converted_files = []
    
    for excel_file, csv_names in file_mappings.items():
        excel_path = os.path.join(source_dir, excel_file)
        
        if not os.path.exists(excel_path):
            print(f"⚠️  File not found: {excel_path}")
            continue
            
        print(f"📄 Converting {excel_file}...")
        
        try:
            # Read Excel file
            df = pd.read_excel(excel_path)
            
            # Handle multiple output files (for Applicants)
            if isinstance(csv_names, list):
                for csv_name in csv_names:
                    csv_path = os.path.join(source_dir, csv_name)
                    df.to_csv(csv_path, index=False)
                    print(f"   ✅ Saved as {csv_name}")
                    converted_files.extend(csv_names)
            else:
                csv_path = os.path.join(source_dir, csv_names)
                df.to_csv(csv_path, index=False)
                print(f"   ✅ Saved as {csv_names}")
                converted_files.append(csv_names)
                
        except Exception as e:
            print(f"   ❌ Error converting {excel_file}: {str(e)}")
    
    return converted_files

def run_sentiment_analysis():
    """Run sentiment analysis on all departments for August 1st data"""
    
    print("\n🚀 Running Sentiment Analysis Pipeline for August 1st data...")
    
    # Build the command
    cmd = [
        "python3", 
        "scripts/run_pipeline.py",
        "--prompt", "sentiment_analysis",
        "--departments", "all",
        "--format", "segmented",
        "--model", "gpt-4o",
        "--with-upload"
    ]
    
    print(f"📝 Command: {' '.join(cmd)}")
    
    # Note: The pipeline is designed to run on yesterday's data
    # We'll need to temporarily adjust the system date or modify the pipeline
    print("\n⚠️  Note: The pipeline is designed to process yesterday's data.")
    print("   Since we're running it for August 1st, the pipeline will need adjustment.")
    
    # For now, let's inform the user about this limitation
    return False

def main():
    """Main function"""
    print("🎯 Processing August 1st Tableau Data")
    print("="*60)
    
    # Step 1: Convert and rename files
    print("\n📂 Step 1: Converting Excel files to CSV...")
    converted_files = convert_and_rename_files()
    
    if not converted_files:
        print("❌ No files were converted successfully")
        return
    
    print(f"\n✅ Successfully converted {len(set(converted_files))} files")
    
    # Step 2: Run sentiment analysis
    print("\n📊 Step 2: Running Sentiment Analysis...")
    
    # Since the pipeline expects yesterday's data, we need a different approach
    print("\n📋 Next Steps:")
    print("1. The Excel files have been converted to CSV format")
    print("2. The files are now in: outputs/tableau_exports/2025-08-01/")
    print("3. To run sentiment analysis on August 1st data, you would need to:")
    print("   - Either wait until August 2nd (when Aug 1 becomes 'yesterday')")
    print("   - Or modify the pipeline to accept a specific date parameter")
    print("\n💡 Alternative: I can create a custom script to run sentiment analysis on August 1st data specifically.")
    
    response = input("\nWould you like me to create a custom script for August 1st sentiment analysis? (y/n): ")
    if response.lower() == 'y':
        print("Creating custom script...")
        # We would create a custom script here similar to the policy escalation one
    else:
        print("Files are ready for manual processing.")

if __name__ == "__main__":
    main()