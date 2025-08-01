import pandas as pd
import os
import glob
import json
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

class ThreateningProcessor:
    def __init__(self, credentials_path='credentials.json'):
        """Initialize the threatening processor with Google Sheets API setup"""
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        self.snapshot_sheet_id = '1XkVcHlkh8fEp7mmBD1Zkavdp2blBLwSABT1dE_sOf74'
        
        # Create output directory for summaries
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        self.threatening_dir = f"outputs/threatening/{date_folder}"
        os.makedirs(self.threatening_dir, exist_ok=True)
    
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

    def safe_parse_output(self, llm_output_str):
        """Parse LLM output safely, handling various formats"""
        if pd.isna(llm_output_str) or not llm_output_str:
            return None
        
        output_str = str(llm_output_str).strip()
        
        # Direct True/False values
        if output_str.lower() == 'true':
            return True
        elif output_str.lower() == 'false':
            return False
        
        # Handle cases where LLM might output additional text
        if 'true' in output_str.lower():
            return True
        elif 'false' in output_str.lower():
            return False
        
        print(f"⚠️ Could not parse LLM output: {output_str}")
        return None
    
    def calculate_threatening_percentage(self, filepath):
        """Calculate threatening percentage from LLM output file"""
        try:
            # Read the CSV file
            df = pd.read_csv(filepath)
            
            if df.empty:
                print(f"⚠️ Empty file: {filepath}")
                return 0.0
            
            total_conversations = 0
            threatening_count = 0
            parsing_errors = 0
            
            for index, row in df.iterrows():
                llm_output = row.get('llm_output', '')
                total_conversations += 1
                
                # Parse the LLM output
                parsed_result = self.safe_parse_output(llm_output)
                
                if parsed_result is True:
                    threatening_count += 1
                elif parsed_result is None:
                    parsing_errors += 1
            
            if total_conversations == 0:
                return 0.0
            
            percentage = (threatening_count / total_conversations) * 100
            
            print(f"📊 Threatening Analysis Results:")
            print(f"   Total conversations analyzed: {total_conversations}")
            print(f"   Threatening cases found: {threatening_count}")
            print(f"   Parsing errors: {parsing_errors}")
            print(f"   Threatening percentage: {percentage:.1f}%")
            
            return round(percentage, 1)
            
        except Exception as e:
            print(f"❌ Error calculating threatening percentage: {str(e)}")
            return 0.0
    
    def save_summary_report(self, percentage, dept_name):
        """Save individual department threatening summary"""
        try:
            summary_data = {
                'Department': [dept_name],
                'Threatening Percentage (%)': [percentage],
                'Date': [datetime.now().strftime('%Y-%m-%d')]
            }
            
            summary_df = pd.DataFrame(summary_data)
            output_filename = f"{self.threatening_dir}/{dept_name}_Threatening_Summary.csv"
            summary_df.to_csv(output_filename, index=False)
            
            print(f"💾 Saved threatening summary: {output_filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving threatening summary: {str(e)}")
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
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating cell {range_name}: {str(e)}")
            return False

    def update_snapshot_sheet(self, percentage):
        """Update threatening percentage in snapshot sheet for yesterday's date"""
        try:
            if not self.service:
                print("❌ Google Sheets API not available")
                return False
            
            yesterday = datetime.now() - timedelta(days=1)
            
            # Find the column for "Threatening Case Identifier"
            col_letter = self.find_column_by_name("Threatening Case Identifier")
            if not col_letter:
                print("⚠️ Please manually add 'Threatening Case Identifier' column to the snapshot sheet")
                return False
            
            # Find the row for yesterday's date
            date_row = self.find_date_row(yesterday)
            if not date_row:
                print(f"⚠️ Could not find date {yesterday.strftime('%Y-%m-%d')} in snapshot sheet")
                return False
            
            # Update the cell with threatening percentage
            range_name = f"Data!{col_letter}{date_row}"
            success = self.update_cell_value(range_name, f"{percentage}%")
            
            if success:
                print(f"📊 Updated snapshot sheet with threatening percentage: {percentage}%")
            
            return success
            
        except Exception as e:
            print(f"❌ Error updating snapshot sheet: {str(e)}")
            return False

    def find_threatening_files(self):
        """Find all threatening LLM output files"""
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        date_str = yesterday.strftime('%m_%d')
        
        # Look for threatening files in LLM_outputs
        pattern = f"outputs/LLM_outputs/{date_folder}/threatening_*_{date_str}.csv"
        files = glob.glob(pattern)
        
        result = []
        for filepath in files:
            filename = os.path.basename(filepath)
            # Extract department key from filename: threatening_mv_resolvers_07_28.csv
            parts = filename.replace('.csv', '').split('_')
            if len(parts) >= 4 and parts[0] == 'threatening':
                dept_key = '_'.join(parts[1:-2])  # Everything between 'threatening_' and '_MM_DD'
                result.append((filepath, dept_key, filename))
        
        return result

    def process_all_files(self):
        """Process all threatening files and update snapshot"""
        print("🔍 Looking for threatening analysis files...")
        
        files = self.find_threatening_files()
        
        if not files:
            print("📝 No threatening files found to process")
            return False
        
        print(f"📁 Found {len(files)} threatening file(s) to process")
        
        total_percentage = 0
        successful_files = 0
        
        for filepath, dept_key, filename in files:
            print(f"\n📊 Processing {filename}...")
            
            # Calculate percentage for this department
            percentage = self.calculate_threatening_percentage(filepath)
            
            if percentage is not None:
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
                self.save_summary_report(percentage, dept_name)
                
                total_percentage += percentage
                successful_files += 1
                
                print(f"✅ {dept_name}: {percentage}% threatening cases")
            
            else:
                print(f"❌ Failed to process {filename}")
        
        # Update snapshot sheet with average percentage if we have data
        if successful_files > 0:
            average_percentage = total_percentage / successful_files
            self.update_snapshot_sheet(round(average_percentage, 1))
            print(f"\n📈 Threatening analysis completed!")
            print(f"   Average threatening percentage: {average_percentage:.1f}%")
            print(f"   Processed {successful_files} department(s)")
        else:
            print("\n⚠️ No valid threatening data found to process")
        
        return successful_files > 0 