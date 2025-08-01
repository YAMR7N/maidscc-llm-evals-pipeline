#!/usr/bin/env python3
"""
Policy Escalation Post-Processor
Analyzes the output from Policy Escalation analysis and calculates metrics

Reads: LLM_outputs/{date}/policy_escalation_{dept_name}_{date}.csv
Calculates: Policy Escalations = (CustomerEscalation = true / total output) * 100
"""

import pandas as pd
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


class PolicyEscalationProcessor:
    """Post processor for Policy Escalation analysis results"""
    
    def __init__(self, credentials_path='credentials.json'):
        # Create directory with date subfolder to match other processors
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        self.policy_escalation_dir = f"outputs/policy_escalation/{date_folder}"
        os.makedirs(self.policy_escalation_dir, exist_ok=True)
        
        # Google Sheets API setup for snapshot updates
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Snapshot sheet for metric tracking
        self.snapshot_sheet_id = '1XkVcHlkh8fEp7mmBD1Zkavdp2blBLwSABT1dE_sOf74'
    
    def safe_json_parse(self, json_str):
        """Safely parse JSON string from LLM output"""
        try:
            if pd.isna(json_str) or not json_str.strip():
                return {}
            
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
            return {}
        except Exception as e:
            print(f"⚠️  Parse error for: {str(json_str)[:100]}... Error: {e}")
            return {}
    
    def setup_sheets_api(self):
        """Initialize Google Sheets API service"""
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            print("✅ Google Sheets API initialized successfully")
        except Exception as e:
            print(f"❌ Error setting up Google Sheets API: {str(e)}")
            self.service = None
    
    def index_to_column_letter(self, index):
        """Convert 0-based index to Google Sheets column letter (A, B, ..., Z, AA, AB, ...)"""
        result = ""
        while index >= 0:
            result = chr(ord('A') + (index % 26)) + result
            index = index // 26 - 1
            if index < 0:
                break
        return result

    def find_column_by_name(self, column_name, sheet_name='Data'):
        """Find column letter by searching for exact column name"""
        try:
            # Get the first row to search for column headers
            range_name = f"{sheet_name}!1:1"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.snapshot_sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return None
            
            headers = values[0]
            print(f"🔍 Searching for column '{column_name}' in headers...")
            
            for i, header in enumerate(headers):
                if header:
                    header_clean = str(header).strip()
                    col_letter = self.index_to_column_letter(i)
                    
                    # Exact match first
                    if header_clean == column_name:
                        print(f"📍 Found exact match for '{column_name}' at column {col_letter}")
                        return col_letter
            
            # If no exact match, try case-insensitive exact match
            for i, header in enumerate(headers):
                if header:
                    header_clean = str(header).strip()
                    if header_clean.lower() == column_name.lower():
                        col_letter = self.index_to_column_letter(i)
                        print(f"📍 Found case-insensitive match for '{column_name}' at column {col_letter}")
                        return col_letter
            
            print(f"⚠️ Column '{column_name}' not found in snapshot sheet")
            print(f"Available columns: {[str(h).strip() for h in headers if h]}")
            return None
            
        except Exception as e:
            print(f"❌ Error finding column: {str(e)}")
            return None
    
    def find_date_row(self, target_date, sheet_name='Data'):
        """Find the row number for a specific date"""
        try:
            # Get column A (dates) to search
            range_name = f"{sheet_name}!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.snapshot_sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return None
            
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            for i, row in enumerate(values):
                if row and len(row) > 0:
                    date_cell = str(row[0]).strip()
                    if target_date_str in date_cell:
                        row_number = i + 1  # Sheets are 1-indexed
                        print(f"📍 Found date {target_date_str} at row {row_number}")
                        return row_number
            
            print(f"⚠️ Date {target_date_str} not found in snapshot sheet")
            return None
            
        except Exception as e:
            print(f"❌ Error finding date row: {str(e)}")
            return None
    
    def update_cell_value(self, range_name, value):
        """Update a specific cell with a value"""
        try:
            body = {
                'values': [[value]]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.snapshot_sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"✅ Updated {range_name} with value: {value}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating cell {range_name}: {str(e)}")
            return False
    
    def update_snapshot_sheet(self, percentage):
        """Update policy escalation percentage in snapshot sheet for yesterday's date"""
        try:
            if not self.service:
                print("❌ Google Sheets API not available")
                return False
            
            yesterday = datetime.now() - timedelta(days=1)
            
            # Find the column for "Policy to cause escalation"
            col_letter = self.find_column_by_name("Policy to cause escalation")
            if not col_letter:
                print("⚠️ Please manually add 'Policy to cause escalation' column to the snapshot sheet")
                return False
            
            # Find the row for yesterday's date
            date_row = self.find_date_row(yesterday)
            if not date_row:
                print(f"⚠️ Could not find date {yesterday.strftime('%Y-%m-%d')} in snapshot sheet")
                return False
            
            # Update the cell
            range_name = f"Data!{col_letter}{date_row}"
            success = self.update_cell_value(range_name, f"{percentage}%")
            
            if success:
                print(f"📊 Updated snapshot sheet with policy escalation percentage: {percentage}%")
            
            return success
            
        except Exception as e:
            print(f"❌ Error updating snapshot sheet: {str(e)}")
            return False
    
    def find_policy_escalation_files(self):
        """Find Policy Escalation LLM output files for yesterday's date"""
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        date_str = yesterday.strftime('%m_%d')
        
        llm_outputs_dir = f"outputs/LLM_outputs/{date_folder}"
        
        if not os.path.exists(llm_outputs_dir):
            print(f"❌ LLM outputs directory not found: {llm_outputs_dir}")
            return []
        
        policy_escalation_files = []
        
        # Look for Policy Escalation files: policy_escalation_{dept_name}_{date}.csv
        for filename in os.listdir(llm_outputs_dir):
            if filename.startswith('policy_escalation_') and filename.endswith(f'_{date_str}.csv'):
                filepath = os.path.join(llm_outputs_dir, filename)
                
                # Extract department name from filename
                # Pattern: policy_escalation_{dept_name}_{date}.csv
                dept_match = re.match(r'policy_escalation_(.+)_\d{2}_\d{2}\.csv$', filename)
                if dept_match:
                    dept_key = dept_match.group(1)
                    policy_escalation_files.append((filepath, dept_key, filename))
                    print(f"📁 Found Policy Escalation file: {filename}")
        
        if not policy_escalation_files:
            print(f"⚠️  No Policy Escalation files found in {llm_outputs_dir}")
        
        return policy_escalation_files
    
    def analyze_policy_escalation_data(self, filepath):
        """Analyze Policy Escalation data from LLM output CSV"""
        try:
            print(f"📊 Analyzing Policy Escalation data: {os.path.basename(filepath)}")
            
            # Read the LLM output CSV
            df = pd.read_csv(filepath)
            
            if df.empty:
                print("⚠️  Empty DataFrame")
                return None
            
            print(f"📋 Processing {len(df)} conversations...")
            
            # Initialize counters
            total_outputs = 0
            customer_escalation_true_count = 0
            valid_outputs = 0
            
            # Process each conversation
            for _, row in df.iterrows():
                conversation_id = str(row['conversation_id'])
                llm_output = row['llm_output']
                
                # Parse the JSON response
                parsed_output = self.safe_json_parse(llm_output)
                
                total_outputs += 1
                
                if parsed_output and isinstance(parsed_output, dict):
                    valid_outputs += 1
                    customer_escalation = parsed_output.get('CustomerEscalation', False)
                    
                    # Count true escalations
                    if customer_escalation is True or (isinstance(customer_escalation, str) and customer_escalation.lower() == 'true'):
                        customer_escalation_true_count += 1
                else:
                    print(f"⚠️  Invalid JSON output for conversation: {conversation_id}")
            
            # Calculate policy escalation percentage
            policy_escalation_percentage = (customer_escalation_true_count / total_outputs * 100) if total_outputs > 0 else 0
            
            print(f"✅ Processed {total_outputs} conversations")
            print(f"📊 Valid outputs: {valid_outputs}")
            print(f"📊 Customer escalations (true): {customer_escalation_true_count}")
            print(f"📊 Policy Escalation percentage: {policy_escalation_percentage:.1f}%")
            
            return {
                'original_df': df,
                'policy_escalation_percentage': policy_escalation_percentage,
                'total_outputs': total_outputs,
                'valid_outputs': valid_outputs,
                'customer_escalation_true_count': customer_escalation_true_count
            }
            
        except Exception as e:
            print(f"❌ Error analyzing Policy Escalation data: {str(e)}")
            return None
    
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
    
    def save_processed_data(self, analysis_results, dept_name):
        """Process data but don't save duplicate files (original LLM output already exists)"""
        try:
            # Don't save duplicate data - the original LLM output file already contains this data
            # Just return a reference to the original file for consistency
            original_df = analysis_results['original_df']
            
            print(f"✅ Policy escalation data processed (no duplicate file saved)")
            print(f"📁 Original data available in LLM_outputs directory")
            
            # Return a placeholder filename for consistency with other processors
            return "processed_in_memory"
            
        except Exception as e:
            print(f"❌ Error processing policy escalation data: {str(e)}")
            return None
    
    def process_all_files(self):
        """Process all Policy Escalation files and calculate metrics"""
        print(f"🚀 Starting Policy Escalation post-processing...")
        
        # Find all Policy Escalation files
        policy_escalation_files = self.find_policy_escalation_files()
        
        if not policy_escalation_files:
            print("❌ No Policy Escalation files found to process")
            return False
        
        success_count = 0
        overall_results = {}
        
        for filepath, dept_key, filename in policy_escalation_files:
            try:
                print(f"\n📊 Processing {filename}...")
                
                # Analyze the data
                analysis_results = self.analyze_policy_escalation_data(filepath)
                if not analysis_results:
                    continue
                
                # Create proper department name
                dept_name = self.convert_dept_key_to_name(dept_key)
                
                # Process data (without saving duplicate file)
                result = self.save_processed_data(analysis_results, dept_name)
                
                if result:
                    overall_results[dept_name] = {
                        'policy_escalation_percentage': analysis_results['policy_escalation_percentage'],
                        'total_outputs': analysis_results['total_outputs'],
                        'valid_outputs': analysis_results['valid_outputs'],
                        'customer_escalation_true_count': analysis_results['customer_escalation_true_count'],
                        'source_file': filepath  # Reference to original LLM output file
                    }
                    success_count += 1
                    print(f"✅ Completed {dept_name}")
                
            except Exception as e:
                print(f"❌ Error processing {filename}: {str(e)}")
                continue
        
        # Print overall summary
        if overall_results:
            print(f"\n🎉 Policy Escalation Processing Summary:")
            print(f"✅ Successfully processed: {success_count}/{len(policy_escalation_files)} departments")
            print(f"\n📊 Policy Escalation Results by Department:")
            for dept, results in overall_results.items():
                print(f"  {dept}:")
                print(f"    Policy Escalation: {results['policy_escalation_percentage']:.1f}%")
                print(f"    Total Outputs: {results['total_outputs']}")
                print(f"    Valid Outputs: {results['valid_outputs']}")
                print(f"    Customer Escalations: {results['customer_escalation_true_count']}")
            
            # Update snapshot sheet with average policy escalation percentage
            total_percentage = sum(results['policy_escalation_percentage'] for results in overall_results.values())
            average_percentage = total_percentage / len(overall_results)
            self.update_snapshot_sheet(round(average_percentage, 1))
            
            print(f"\n📈 Policy escalation analysis completed!")
            print(f"   Average policy escalation percentage: {average_percentage:.1f}%")
            print(f"   Processed {success_count} department(s)")
        else:
            print("\n⚠️ No valid policy escalation data found to process")
        
        return success_count > 0


def main():
    """Main function for standalone execution"""
    processor = PolicyEscalationProcessor()
    processor.process_all_files()


if __name__ == "__main__":
    main() 