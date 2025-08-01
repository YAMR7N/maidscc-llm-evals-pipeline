import os
import pandas as pd
import json
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class CallRequestProcessor:
    def __init__(self, credentials_path='credentials.json'):
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Directory for call request outputs
        yesterday = datetime.now() - timedelta(days=1)
        self.call_request_dir = f"outputs/call_request/{yesterday.strftime('%Y-%m-%d')}"
        os.makedirs(self.call_request_dir, exist_ok=True)
        
        # Snapshot sheet for metric tracking
        self.snapshot_sheet_id = '1XkVcHlkh8fEp7mmBD1Zkavdp2blBLwSABT1dE_sOf74'
    
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
    
    def safe_json_parse(self, json_str):
        """Safely parse JSON, handling various formatting issues"""
        if not json_str or pd.isna(json_str):
            return None
        
        try:
            # Handle string representation
            json_str = str(json_str).strip()
            
            # Handle markdown code blocks
            if json_str.startswith('```json') and json_str.endswith('```'):
                start_idx = json_str.find('{')
                end_idx = json_str.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = json_str[start_idx:end_idx].strip()
            elif json_str.startswith('```') and json_str.endswith('```'):
                # Handle general code blocks
                lines = json_str.split('\n')
                if len(lines) > 2:
                    json_str = '\n'.join(lines[1:-1]).strip()
            
            # Try to parse JSON
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠️ Failed to parse JSON: {json_str[:100]}...")
            return None
    
    def calculate_call_request_metrics(self, filepath):
        """Calculate call request metrics: call request rate and retention rate"""
        try:
            df = pd.read_csv(filepath)
            print(f"📊 Processing {len(df)} call request records from {os.path.basename(filepath)}")
            
            total_conversations = 0
            call_requests_count = 0
            retained_count = 0
            no_retention_count = 0
            
            for index, row in df.iterrows():
                llm_output = row.get('llm_output', '')
                if not llm_output or pd.isna(llm_output):
                    continue
                
                # Parse JSON output
                parsed_json = self.safe_json_parse(llm_output)
                if not parsed_json:
                    continue
                
                total_conversations += 1
                
                # Check if CallRequested is True
                call_requested = parsed_json.get('CallRequested', '').strip().lower()
                if call_requested == 'true':
                    call_requests_count += 1
                    
                    # Check rebuttal result
                    rebuttal_result = parsed_json.get('CallRequestRebuttalResult', parsed_json.get('CallRequestRebutalResult', '')).strip()
                    if rebuttal_result == 'Retained':
                        retained_count += 1
                    elif rebuttal_result == 'NoRetention':
                        no_retention_count += 1
            
            if total_conversations == 0:
                print("⚠️ No valid conversations found for call request analysis")
                return 0.0, 0.0
            
            # Calculate metrics
            call_request_rate = (call_requests_count / total_conversations) * 100
            
            # Rebuttal result: percentage of call requests that resulted in no retention (failure rate)
            if call_requests_count > 0:
                rebuttal_result_rate = (no_retention_count / call_requests_count) * 100
            else:
                rebuttal_result_rate = 0.0
            
            print(f"📈 Call Request Analysis Results:")
            print(f"   Total conversations analyzed: {total_conversations}")
            print(f"   Call requests made: {call_requests_count}")
            print(f"   Successfully retained: {retained_count}")
            print(f"   Not retained: {no_retention_count}")
            print(f"   Call request rate: {call_request_rate:.1f}%")
            print(f"   Rebuttal result rate (no retention): {rebuttal_result_rate:.1f}%")
            
            return round(call_request_rate, 1), round(rebuttal_result_rate, 1)
            
        except Exception as e:
            print(f"❌ Error calculating call request metrics: {str(e)}")
            return 0.0, 0.0
    
    def save_summary_report(self, call_request_rate, rebuttal_result_rate, dept_name):
        """Save individual department call request metrics summary"""
        try:
            summary_data = {
                'Department': [dept_name],
                'Call Request Rate (%)': [call_request_rate],
                'Rebuttal Result Rate (%)': [rebuttal_result_rate],
                'Date': [datetime.now().strftime('%Y-%m-%d')]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_filename = f"{self.call_request_dir}/{dept_name}_Call_Request_Summary.csv"
            summary_df.to_csv(summary_filename, index=False)
            
            print(f"💾 Saved call request metrics summary: {summary_filename}")
            return summary_filename
            
        except Exception as e:
            print(f"❌ Error saving call request summary: {str(e)}")
            return None
    
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
    
    def update_snapshot_sheet(self, call_request_rate, rebuttal_result_rate):
        """Update call request metrics in snapshot sheet for yesterday's date"""
        try:
            if not self.service:
                print("❌ Google Sheets API not available")
                return False
            
            yesterday = datetime.now() - timedelta(days=1)
            
            # Find the row for yesterday's date first
            date_row = self.find_date_row(yesterday)
            if not date_row:
                print(f"⚠️ Could not find date {yesterday.strftime('%Y-%m-%d')} in snapshot sheet")
                return False
            
            success_count = 0
            
            # Update "Call Request" column
            call_request_col = self.find_column_by_name("Call Request")
            if call_request_col:
                range_name = f"Data!{call_request_col}{date_row}"
                if self.update_cell_value(range_name, f"{call_request_rate}%"):
                    print(f"📊 Updated 'Call Request' column with: {call_request_rate}%")
                    success_count += 1
            else:
                print("⚠️ Please manually add 'Call Request' column to the snapshot sheet")
            
            # Update "Rebuttal Result" column
            rebuttal_result_col = self.find_column_by_name("Rebuttal Result")
            if rebuttal_result_col:
                range_name = f"Data!{rebuttal_result_col}{date_row}"
                if self.update_cell_value(range_name, f"{rebuttal_result_rate}%"):
                    print(f"📊 Updated 'Rebuttal Result' column with: {rebuttal_result_rate}%")
                    success_count += 1
            else:
                print("⚠️ Please manually add 'Rebuttal Result' column to the snapshot sheet")
            
            return success_count > 0
            
        except Exception as e:
            print(f"❌ Error updating snapshot sheet: {str(e)}")
            return False
    
    def find_call_request_files(self):
        """Find all call request LLM output files"""
        files = []
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        llm_outputs_dir = f"outputs/LLM_outputs/{date_folder}"
        
        if not os.path.exists(llm_outputs_dir):
            print(f"⚠️ LLM outputs directory not found: {llm_outputs_dir}")
            return files
        
        for filename in os.listdir(llm_outputs_dir):
            if filename.startswith('call_request_') and filename.endswith('.csv'):
                filepath = os.path.join(llm_outputs_dir, filename)
                # Extract department from filename
                dept_part = filename.replace('call_request_', '').replace('.csv', '')
                # Remove date suffix (format: _MM_DD)
                if '_' in dept_part:
                    dept_key = '_'.join(dept_part.split('_')[:-2])
                else:
                    dept_key = dept_part
                
                files.append((filepath, dept_key, filename))
                print(f"📁 Found call request file: {filename}")
        
        return files
    
    def process_all_files(self):
        """Process all call request files and update metrics"""
        try:
            files = self.find_call_request_files()
            
            if not files:
                print("ℹ️ No call request files found to process")
                return
            
            total_call_request_rate = 0
            total_rebuttal_result_rate = 0
            successful_files = 0
            
            for filepath, dept_key, filename in files:
                print(f"\n📊 Processing {filename}...")
                
                # Calculate metrics for this department
                call_request_rate, rebuttal_result_rate = self.calculate_call_request_metrics(filepath)
                
                if rebuttal_result_rate is not None:
                    # Create proper department name
                    dept_name = dept_key.replace('_', ' ').title()
                    
                    # Handle specific department name mappings
                    if dept_name == 'Mv Resolvers':
                        dept_name = 'MV Resolvers'
                    elif dept_name == 'Mv Sales':
                        dept_name = 'MV Sales'
                    elif dept_name == 'Cc Sales':
                        dept_name = 'CC Sales'
                    elif dept_name == 'Cc Resolvers':
                        dept_name = 'CC Resolvers'
                    
                    # Save individual summary
                    self.save_summary_report(call_request_rate, rebuttal_result_rate, dept_name)
                    
                    total_call_request_rate += call_request_rate
                    total_rebuttal_result_rate += rebuttal_result_rate
                    successful_files += 1
                    
                    print(f"✅ {dept_name}: {call_request_rate}% call requests, {rebuttal_result_rate}% rebuttal result rate")
                
                else:
                    print(f"❌ Failed to process {filename}")
            
            # Update snapshot sheet with average rates if we have data
            if successful_files > 0:
                average_call_request_rate = total_call_request_rate / successful_files
                average_rebuttal_result_rate = total_rebuttal_result_rate / successful_files
                self.update_snapshot_sheet(round(average_call_request_rate, 1), round(average_rebuttal_result_rate, 1))
                print(f"\n📈 Call request analysis completed!")
                print(f"   Average call request rate: {average_call_request_rate:.1f}%")
                print(f"   Average rebuttal result rate: {average_rebuttal_result_rate:.1f}%")
                print(f"   Processed {successful_files} department(s)")
            else:
                print("\n⚠️ No valid call request data found to process")
                
        except Exception as e:
            print(f"❌ Error in call request processing: {str(e)}") 