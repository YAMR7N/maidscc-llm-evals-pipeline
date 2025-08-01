#!/usr/bin/env python3
"""
FTR Post-Processor
Analyzes the output from FTR (First Time Resolution) analysis and creates a combined report
with original data and summary statistics in one sheet.

Reads: LLM_outputs/{date}/ftr_{dept_name}_{date}.csv
Outputs: Combined CSV with columns:
- customer_name, conversation, llm_output, , , Metric, Value
- Original data rows followed by summary statistics
"""

import pandas as pd
import json
import os
import re
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path


class FTRProcessor:
    """Post processor for FTR analysis results"""
    
    def __init__(self):
        # Create directory with date subfolder to match other processors
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        self.ftr_dir = f"outputs/ftr/{date_folder}"
        os.makedirs(self.ftr_dir, exist_ok=True)
    
    def safe_json_parse(self, json_str):
        """Safely parse JSON string from LLM output"""
        try:
            if pd.isna(json_str) or not json_str.strip():
                return []
            
            # Clean up common JSON formatting issues
            cleaned = str(json_str).strip()
            
            # Remove markdown code blocks if present
            if cleaned.startswith('```json'):
                cleaned = cleaned.replace('```json', '').replace('```', '').strip()
            elif cleaned.startswith('```'):
                cleaned = cleaned.replace('```', '').strip()
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON decode error for: {str(json_str)[:100]}... Error: {e}")
            return []
        except Exception as e:
            print(f"⚠️  Parse error for: {str(json_str)[:100]}... Error: {e}")
            return []
    
    def find_ftr_files(self):
        """Find FTR LLM output files for yesterday's date"""
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        date_str = yesterday.strftime('%m_%d')
        
        llm_outputs_dir = f"outputs/LLM_outputs/{date_folder}"
        
        if not os.path.exists(llm_outputs_dir):
            print(f"❌ LLM outputs directory not found: {llm_outputs_dir}")
            return []
        
        ftr_files = []
        
        # Look for FTR files: ftr_{dept_name}_{date}.csv
        for filename in os.listdir(llm_outputs_dir):
            if filename.startswith('ftr_') and filename.endswith(f'_{date_str}.csv'):
                filepath = os.path.join(llm_outputs_dir, filename)
                
                # Extract department name from filename
                # Pattern: ftr_{dept_name}_{date}.csv
                dept_match = re.match(r'ftr_(.+)_\d{2}_\d{2}\.csv$', filename)
                if dept_match:
                    dept_key = dept_match.group(1)
                    ftr_files.append((filepath, dept_key, filename))
                    print(f"📁 Found FTR file: {filename}")
        
        if not ftr_files:
            print(f"⚠️  No FTR files found in {llm_outputs_dir}")
        
        return ftr_files
    
    def analyze_ftr_data(self, filepath):
        """Analyze FTR data from LLM output CSV and create combined report"""
        try:
            print(f"📊 Analyzing FTR data: {os.path.basename(filepath)}")
            
            # Read the LLM output CSV
            df = pd.read_csv(filepath)
            
            if df.empty:
                print("⚠️  Empty DataFrame")
                return None
            
            print(f"📋 Processing {len(df)} customers...")
            
            # Prepare original data for combined report
            combined_data = []
            
            # Initialize totals for summary
            total_chats_all_customers = 0
            total_resolved_chats_all_customers = 0
            total_customers = 0
            
            # Process each customer and add to combined data
            for _, row in df.iterrows():
                customer_name = str(row['conversation_id'])
                conversation = str(row.get('conversation', ''))
                llm_output = str(row['llm_output'])
                
                # Parse the FTR responses (JSON array of "Yes"/"No")
                ftr_responses = self.safe_json_parse(llm_output)
                
                # Add original data row
                combined_data.append({
                    'customer_name': customer_name,
                    'conversation': conversation,
                    'llm_output': llm_output,
                    'col4': '',  # Empty column
                    'col5': '',  # Empty column
                    'Metric': '',
                    'Value': ''
                })
                
                # Initialize counts
                total_chats = 0
                resolved_chats = 0
                
                if ftr_responses:
                    # Count total chats and resolved chats
                    total_chats = len(ftr_responses)
                    resolved_chats = ftr_responses.count('Yes')
                
                # Add to overall totals
                total_chats_all_customers += total_chats
                total_resolved_chats_all_customers += resolved_chats
                total_customers += 1
            
            # Calculate overall statistics
            overall_ftr_percentage = (total_resolved_chats_all_customers / total_chats_all_customers * 100) if total_chats_all_customers > 0 else 0
            average_chats_per_customer = total_chats_all_customers / total_customers if total_customers > 0 else 0
            
            # Add summary rows at the end
            summary_rows = [
                # Empty row separator
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': '', 'Value': ''},
                # Summary statistics
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': 'Overall FTR Percentage', 'Value': f"{overall_ftr_percentage:.1f}%"},
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': 'Total Customers', 'Value': str(total_customers)},
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': 'Total Chats (3 days)', 'Value': str(total_chats_all_customers)},
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': 'Total Resolved Chats', 'Value': str(total_resolved_chats_all_customers)},
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': 'Total Unresolved Chats', 'Value': str(total_chats_all_customers - total_resolved_chats_all_customers)},
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': 'Average Chats per Customer (3 days)', 'Value': f"{average_chats_per_customer:.1f}"}
            ]
            
            # Combine original data with summary
            combined_data.extend(summary_rows)
            
            # Create DataFrame with correct column names
            combined_df = pd.DataFrame(combined_data)
            combined_df.columns = ['customer_name', 'conversation', 'llm_output', '', '', 'Metric', 'Value']
            
            print(f"✅ Processed {total_customers} customers")
            print(f"📊 Overall FTR: {overall_ftr_percentage:.1f}%")
            print(f"📊 Total chats: {total_chats_all_customers}")
            print(f"📊 Average chats per customer (3 days): {average_chats_per_customer:.1f}")
            
            return {
                'combined_df': combined_df,
                'overall_ftr_percentage': overall_ftr_percentage,
                'total_customers': total_customers,
                'total_chats': total_chats_all_customers,
                'total_resolved': total_resolved_chats_all_customers,
                'average_chats_per_customer': average_chats_per_customer
            }
            
        except Exception as e:
            print(f"❌ Error analyzing FTR data: {str(e)}")
            return None
    
    def create_combined_report(self, analysis_results, dept_name, output_filename):
        """Create combined report with original data and summary"""
        try:
            combined_df = analysis_results['combined_df']
            overall_ftr = analysis_results['overall_ftr_percentage']
            
            # Save combined report
            combined_df.to_csv(output_filename, index=False)
            print(f"💾 Combined report saved: {output_filename}")
            
            return combined_df, overall_ftr
            
        except Exception as e:
            print(f"❌ Error creating combined report: {str(e)}")
            return None, None
    
    def convert_dept_key_to_name(self, dept_key):
        """Convert department key to proper name for display"""
        # Handle underscores and convert to title case
        dept_name = dept_key.replace('_', ' ').title()
        
        # Handle specific department name mappings
        if dept_name == 'Mv Resolvers':
            return 'MV Resolvers'
        elif dept_name == 'Mv Sales':
            return 'MV Sales'
        elif dept_name == 'Cc Sales':
            return 'CC Sales'
        elif dept_name == 'Cc Resolvers':
            return 'CC Resolvers'
        else:
            return dept_name
    
    def process_all_files(self):
        """Process all FTR files and generate combined reports"""
        print(f"🚀 Starting FTR post-processing...")
        
        # Find all FTR files
        ftr_files = self.find_ftr_files()
        
        if not ftr_files:
            print("❌ No FTR files found to process")
            return False
        
        success_count = 0
        overall_results = {}
        
        for filepath, dept_key, filename in ftr_files:
            try:
                print(f"\n📊 Processing {filename}...")
                
                # Analyze the data
                analysis_results = self.analyze_ftr_data(filepath)
                if not analysis_results:
                    continue
                
                # Create proper department name
                dept_name = self.convert_dept_key_to_name(dept_key)
                
                # Create combined report
                output_filename = f"{self.ftr_dir}/{dept_name}_FTR_Combined.csv"
                combined_df, overall_ftr = self.create_combined_report(
                    analysis_results, dept_name, output_filename
                )
                
                if combined_df is not None:
                    overall_results[dept_name] = {
                        'ftr_percentage': overall_ftr,
                        'total_customers': analysis_results['total_customers'],
                        'total_chats': analysis_results['total_chats'],
                        'avg_chats': analysis_results['average_chats_per_customer']
                    }
                    success_count += 1
                    print(f"✅ Completed {dept_name}")
                
            except Exception as e:
                print(f"❌ Error processing {filename}: {str(e)}")
                continue
        
        # Print overall summary
        if overall_results:
            print(f"\n🎉 FTR Processing Summary:")
            print(f"✅ Successfully processed: {success_count}/{len(ftr_files)} departments")
            print(f"\n📊 FTR Results by Department:")
            for dept, results in overall_results.items():
                print(f"  {dept}:")
                print(f"    FTR: {results['ftr_percentage']:.1f}%")
                print(f"    Customers: {results['total_customers']}")
                print(f"    Total Chats: {results['total_chats']}")
                print(f"    Avg Chats/Customer: {results['avg_chats']:.1f}")
        
        return success_count > 0


def main():
    """Main function for standalone execution"""
    processor = FTRProcessor()
    processor.process_all_files()


if __name__ == "__main__":
    main() 