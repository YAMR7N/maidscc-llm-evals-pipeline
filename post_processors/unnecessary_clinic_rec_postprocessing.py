import pandas as pd
import os
import glob
import json
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

class UnnecessaryClinicRecProcessor:
    def __init__(self, credentials_path='credentials.json'):
        """Initialize the unnecessary clinic rec processor with Google Sheets API setup"""
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        self.snapshot_sheet_id = '1STHimb0IJ077iuBtTOwsa-GD8jStjU3SiBW7yBWom-E'
        
        # Create output directory for summaries
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        self.output_dir = f"outputs/unnecessary_clinic_rec/{date_folder}"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def setup_sheets_api(self):
        """Setup Google Sheets API connection"""
        try:
            if os.path.exists(self.credentials_path):
                # Define the scope for Google Sheets API
                SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
                
                # Load credentials from the service account key file
                creds = Credentials.from_service_account_file(self.credentials_path, scopes=SCOPES)
                
                # Build the service object for Sheets API
                self.service = build('sheets', 'v4', credentials=creds)
                print("✅ Google Sheets API initialized successfully")
            else:
                print(f"❌ Credentials file not found: {self.credentials_path}")
                
        except Exception as e:
            print(f"❌ Error setting up Google Sheets API: {str(e)}")
            self.service = None

    def safe_json_parse(self, json_str):
        """Safely parse JSON string from LLM output"""
        try:
            if pd.isna(json_str) or not json_str.strip():
                return None
            
            # Clean up common JSON formatting issues
            cleaned = str(json_str).strip()
            
            # Remove markdown code blocks if present
            if cleaned.startswith('```json') and cleaned.endswith('```'):
                start_idx = cleaned.find('{')
                end_idx = cleaned.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    cleaned = cleaned[start_idx:end_idx].strip()
            elif cleaned.startswith('```') and cleaned.endswith('```'):
                cleaned = cleaned.replace('```', '').strip()
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON decode error for: {str(json_str)[:100]}... Error: {e}")
            return None
        except Exception as e:
            print(f"⚠️ Unexpected error parsing: {str(json_str)[:100]}... Error: {e}")
            return None
    
    def calculate_unnecessary_clinic_percentage(self, filepath):
        """Calculate unnecessary clinic recommendation percentage from LLM output file"""
        try:
            # Read the CSV file
            df = pd.read_csv(filepath)
            
            if df.empty:
                print(f"⚠️ Empty file: {filepath}")
                return 0.0
            
            total_conversations = 0
            could_avoid_count = 0
            parsing_errors = 0
            
            for index, row in df.iterrows():
                llm_output = row.get('llm_output', '')
                total_conversations += 1
                
                # Parse the JSON output
                parsed_result = self.safe_json_parse(llm_output)
                
                if parsed_result:
                    could_avoid_visit = parsed_result.get('could_avoid_visit', False)
                    if could_avoid_visit is True:
                        could_avoid_count += 1
                else:
                    parsing_errors += 1
            
            if total_conversations == 0:
                return 0.0
            
            percentage = (could_avoid_count / total_conversations) * 100
            
            print(f"📊 Unnecessary Clinic Rec Analysis Results:")
            print(f"   Total conversations analyzed: {total_conversations}")
            print(f"   Could avoid visit cases: {could_avoid_count}")
            print(f"   Parsing errors: {parsing_errors}")
            print(f"   Unnecessary clinic rec percentage: {percentage:.1f}%")
            
            return round(percentage, 1)
            
        except Exception as e:
            print(f"❌ Error calculating unnecessary clinic rec percentage: {str(e)}")
            return 0.0
    
    def save_summary_report(self, percentage, dept_name):
        """Save individual department unnecessary clinic rec summary"""
        try:
            summary_data = {
                'Department': [dept_name],
                'Unnecessary Clinic Rec Percentage (%)': [percentage],
                'Date': [datetime.now().strftime('%Y-%m-%d')]
            }
            
            summary_df = pd.DataFrame(summary_data)
            output_filename = f"{self.output_dir}/{dept_name}_Unnecessary_Clinic_Rec_Summary.csv"
            summary_df.to_csv(output_filename, index=False)
            
            print(f"💾 Saved unnecessary clinic rec summary: {output_filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving unnecessary clinic rec summary: {str(e)}")
            return False

    def index_to_column_letter(self, index):
        """Convert 0-based column index to Google Sheets column letter (A, B, ..., Z, AA, AB, ...)"""
        result = ""
        while index >= 0:
            result = chr(index % 26 + ord('A')) + result
            index = index // 26 - 1
        return result

    def find_column_by_name(self, column_name, sheet_name='Data'):
        """Find column letter by exact column name with detailed debugging"""
        try:
            print(f"🔍 Searching for column '{column_name}' in headers...")
            
            # Get the first row (headers)
            range_name = f"{sheet_name}!1:1"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.snapshot_sheet_id,
                range=range_name
            ).execute()
            
            headers = result.get('values', [[]])[0]
            
            # Try exact case-sensitive match first
            for i, header in enumerate(headers):
                if header == column_name:
                    column_letter = self.index_to_column_letter(i)
                    print(f"📍 Found exact match for '{column_name}' at column {column_letter}")
                    return column_letter
            
            # Try exact case-insensitive match
            for i, header in enumerate(headers):
                if header.lower() == column_name.lower():
                    column_letter = self.index_to_column_letter(i)
                    print(f"📍 Found case-insensitive match for '{column_name}' at column {column_letter}")
                    return column_letter
            
            print(f"❌ Column '{column_name}' not found in sheet headers")
            return None
            
        except Exception as e:
            print(f"❌ Error finding column: {str(e)}")
            return None

    def find_date_row(self, target_date, sheet_name='Data'):
        """Find the row number for a specific date"""
        try:
            # Get all data from column A (assuming dates are in column A)
            range_name = f"{sheet_name}!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.snapshot_sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            for i, row in enumerate(values):
                if row and len(row) > 0:
                    cell_value = str(row[0]).strip()
                    if cell_value == target_date_str:
                        print(f"✅ Found date {target_date_str} in row {i + 1}")
                        return i + 1  # Google Sheets is 1-indexed
            
            print(f"❌ Date {target_date_str} not found in column A")
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
        """Update unnecessary clinic rec percentage in snapshot sheet for yesterday's date"""
        try:
            if not self.service:
                print("❌ Google Sheets API not available")
                return False
            
            yesterday = datetime.now() - timedelta(days=1)
            
            # Find the column for "Unnecessary clinic recommendations"
            col_letter = self.find_column_by_name("Unnecessary clinic recommendations")
            if not col_letter:
                print("⚠️ Column 'Unnecessary clinic recommendations' not found in snapshot sheet")
                return False
            
            # Find the row for yesterday's date
            date_row = self.find_date_row(yesterday)
            if not date_row:
                print(f"⚠️ Could not find date {yesterday.strftime('%Y-%m-%d')} in snapshot sheet")
                return False
            
            # Update the cell with unnecessary clinic rec percentage
            range_name = f"Data!{col_letter}{date_row}"
            success = self.update_cell_value(range_name, f"{percentage}%")
            
            if success:
                print(f"📊 Updated snapshot sheet with unnecessary clinic rec percentage: {percentage}% for {yesterday.strftime('%Y-%m-%d')}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error updating snapshot sheet: {str(e)}")
            return False

    def find_unnecessary_clinic_rec_files(self):
        """Find all unnecessary clinic rec LLM output files"""
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        date_str = yesterday.strftime('%m_%d')
        
        # Look for unnecessary clinic rec files in LLM_outputs
        pattern = f"outputs/LLM_outputs/{date_folder}/unnecessary_clinic_rec_*_{date_str}.csv"
        files = glob.glob(pattern)
        
        result = []
        for filepath in files:
            filename = os.path.basename(filepath)
            # Extract department key from filename: unnecessary_clinic_rec_doctors_07_29.csv
            parts = filename.replace('.csv', '').split('_')
            if len(parts) >= 5 and parts[0] == 'unnecessary' and parts[1] == 'clinic' and parts[2] == 'rec':
                dept_key = '_'.join(parts[3:-2])  # Everything between 'unnecessary_clinic_rec_' and '_MM_DD'
                result.append((filepath, dept_key, filename))
        
        return result

    def process_all_files(self):
        """Process all unnecessary clinic rec files and update snapshot"""
        print("🔍 Looking for unnecessary clinic rec analysis files...")
        
        files = self.find_unnecessary_clinic_rec_files()
        
        if not files:
            print("📝 No unnecessary clinic rec files found to process")
            return False
        
        print(f"📁 Found {len(files)} unnecessary clinic rec file(s) to process")
        
        total_percentage = 0
        successful_files = 0
        
        for filepath, dept_key, filename in files:
            print(f"\n📊 Processing {filename}...")
            
            # Calculate percentage for this department
            percentage = self.calculate_unnecessary_clinic_percentage(filepath)
            
            if percentage is not None:
                # Create proper department name
                dept_name = dept_key.replace('_', ' ').title()
                
                # Handle specific department name mappings
                if dept_name == 'Doctors':
                    dept_name = 'Doctors'
                
                # Save individual summary
                self.save_summary_report(percentage, dept_name)
                
                total_percentage += percentage
                successful_files += 1
                
                print(f"✅ {dept_name}: {percentage}% unnecessary clinic recommendations")
            
            else:
                print(f"❌ Failed to process {filename}")
        
        # Update snapshot sheet with average percentage if we have data
        if successful_files > 0:
            average_percentage = total_percentage / successful_files
            self.update_snapshot_sheet(round(average_percentage, 1))
            print(f"\n📈 Unnecessary clinic rec analysis completed!")
            print(f"   Average unnecessary clinic rec percentage: {average_percentage:.1f}%")
            print(f"   Processed {successful_files} department(s)")
        else:
            print("\n⚠️ No valid unnecessary clinic rec data found to process")
        
        return successful_files > 0 