import os
import pandas as pd
import json
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class LegalAlignmentProcessor:
    def __init__(self, credentials_path='credentials.json'):
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Directory for legal alignment outputs
        yesterday = datetime.now() - timedelta(days=1)
        self.legal_alignment_dir = f"outputs/legal_alignment/{yesterday.strftime('%Y-%m-%d')}"
        os.makedirs(self.legal_alignment_dir, exist_ok=True)
        
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
    
    def calculate_legal_metrics(self, filepath):
        """Calculate both legal alignment metrics"""
        try:
            df = pd.read_csv(filepath)
            print(f"📊 Processing {len(df)} legal alignment records from {os.path.basename(filepath)}")
            
            total_conversations = 0
            legal_concerns_count = 0
            escalated_count = 0
            
            for index, row in df.iterrows():
                llm_output = row.get('llm_output', '')
                if not llm_output or pd.isna(llm_output):
                    continue
                
                # Parse JSON output
                parsed_json = self.safe_json_parse(llm_output)
                if not parsed_json:
                    continue
                
                total_conversations += 1
                
                # Check if LegalityConcerned is True
                legality_concerned = parsed_json.get('LegalityConcerned', '').strip().lower()
                if legality_concerned == 'true':
                    legal_concerns_count += 1
                    
                    # For cases with legal concerns, check escalation outcome
                    escalation_outcome = parsed_json.get('EscalationOutcome', '').strip()
                    if escalation_outcome.lower() == 'escalated':
                        escalated_count += 1
            
            if total_conversations == 0:
                print("⚠️ No valid conversations found for legal alignment analysis")
                return 0.0, 0.0
            
            # Metric 1: (EscalationOutcome = Escalated / LegalityConcerned = True) * 100
            escalation_rate = 0.0
            if legal_concerns_count > 0:
                escalation_rate = (escalated_count / legal_concerns_count) * 100
            
            # Metric 2: (LegalityConcerned = true / Total Output) * 100
            legal_concerns_percentage = (legal_concerns_count / total_conversations) * 100
            
            print(f"📈 Legal Alignment Analysis Results:")
            print(f"   Total conversations analyzed: {total_conversations}")
            print(f"   Legal concerns identified: {legal_concerns_count}")
            print(f"   Cases escalated: {escalated_count}")
            print(f"   Escalation rate: {escalation_rate:.1f}% (escalated/legal concerns)")
            print(f"   Legal concerns percentage: {legal_concerns_percentage:.1f}% (legal concerns/total)")
            
            return round(escalation_rate, 1), round(legal_concerns_percentage, 1)
            
        except Exception as e:
            print(f"❌ Error calculating legal metrics: {str(e)}")
            return 0.0, 0.0
    
    def save_summary_report(self, escalation_rate, legal_concerns_percentage, dept_name):
        """Save individual department legal alignment metrics summary"""
        try:
            summary_data = {
                'Department': [dept_name],
                'Escalation Rate (%)': [escalation_rate],
                'Legal Concerns Percentage (%)': [legal_concerns_percentage],
                'Date': [datetime.now().strftime('%Y-%m-%d')]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_filename = f"{self.legal_alignment_dir}/{dept_name}_Legal_Alignment_Summary.csv"
            summary_df.to_csv(summary_filename, index=False)
            
            print(f"💾 Saved legal alignment metrics summary: {summary_filename}")
            return summary_filename
            
        except Exception as e:
            print(f"❌ Error saving legal alignment summary: {str(e)}")
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
    
    def update_snapshot_sheet(self, escalation_rate, legal_concerns_percentage):
        """Update both legal alignment metrics in snapshot sheet for yesterday's date"""
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
            
            # Update Escalation Outcome column
            escalation_col = self.find_column_by_name("Escalation Outcome")
            if escalation_col:
                range_name = f"Data!{escalation_col}{date_row}"
                if self.update_cell_value(range_name, f"{escalation_rate}%"):
                    print(f"📊 Updated Escalation Outcome: {escalation_rate}%")
                    success_count += 1
                else:
                    print(f"❌ Failed to update Escalation Outcome")
            else:
                print("⚠️ Column 'Escalation Outcome' not found in snapshot sheet")
            
            # Update Clients Questioning Legalties column
            legal_concerns_col = self.find_column_by_name("Clients Questioning Legalties")
            if legal_concerns_col:
                range_name = f"Data!{legal_concerns_col}{date_row}"
                if self.update_cell_value(range_name, f"{legal_concerns_percentage}%"):
                    print(f"📊 Updated Clients Questioning Legalties: {legal_concerns_percentage}%")
                    success_count += 1
                else:
                    print(f"❌ Failed to update Clients Questioning Legalties")
            else:
                print("⚠️ Column 'Clients Questioning Legalties' not found in snapshot sheet")
            
            # Return success if at least one update worked
            return success_count > 0
            
        except Exception as e:
            print(f"❌ Error updating snapshot sheet: {str(e)}")
            return False
    
    def find_legal_alignment_files(self):
        """Find all legal alignment LLM output files"""
        files = []
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        llm_outputs_dir = f"outputs/LLM_outputs/{date_folder}"
        
        if not os.path.exists(llm_outputs_dir):
            print(f"⚠️ LLM outputs directory not found: {llm_outputs_dir}")
            return files
        
        for filename in os.listdir(llm_outputs_dir):
            if filename.startswith('legal_alignment_') and filename.endswith('.csv'):
                filepath = os.path.join(llm_outputs_dir, filename)
                # Extract department from filename
                dept_part = filename.replace('legal_alignment_', '').replace('.csv', '')
                # Remove date suffix (format: _MM_DD)
                if '_' in dept_part:
                    dept_key = '_'.join(dept_part.split('_')[:-2])
                else:
                    dept_key = dept_part
                
                files.append((filepath, dept_key, filename))
                print(f"📁 Found legal alignment file: {filename}")
        
        return files
    
    def process_all_files(self):
        """Process all legal alignment files and update metrics"""
        try:
            files = self.find_legal_alignment_files()
            
            if not files:
                print("ℹ️ No legal alignment files found to process")
                return
            
            total_escalation_rate = 0
            total_legal_concerns_percentage = 0
            successful_files = 0
            
            for filepath, dept_key, filename in files:
                print(f"\n📊 Processing {filename}...")
                
                # Calculate both metrics for this department
                escalation_rate, legal_concerns_percentage = self.calculate_legal_metrics(filepath)
                
                if escalation_rate is not None and legal_concerns_percentage is not None:
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
                    self.save_summary_report(escalation_rate, legal_concerns_percentage, dept_name)
                    
                    total_escalation_rate += escalation_rate
                    total_legal_concerns_percentage += legal_concerns_percentage
                    successful_files += 1
                    
                    print(f"✅ {dept_name}: {escalation_rate}% escalation rate, {legal_concerns_percentage}% legal concerns")
                
                else:
                    print(f"❌ Failed to process {filename}")
            
            # Update snapshot sheet with average metrics if we have data
            if successful_files > 0:
                avg_escalation_rate = total_escalation_rate / successful_files
                avg_legal_concerns_percentage = total_legal_concerns_percentage / successful_files
                self.update_snapshot_sheet(round(avg_escalation_rate, 1), round(avg_legal_concerns_percentage, 1))
                print(f"\n📈 Legal alignment analysis completed!")
                print(f"   Average escalation rate: {avg_escalation_rate:.1f}%")
                print(f"   Average legal concerns percentage: {avg_legal_concerns_percentage:.1f}%")
                print(f"   Processed {successful_files} department(s)")
            else:
                print("\n⚠️ No valid legal alignment data found to process")
                
        except Exception as e:
            print(f"❌ Error in legal alignment processing: {str(e)}") 