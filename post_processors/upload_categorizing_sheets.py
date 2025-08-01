#!/usr/bin/env python3
"""
Upload categorizing CSV files to Google Spreadsheets
- Main categorizing sheet gets two tabs: yyyy-mm-dd (report) and yyyy-mm-dd-RAW (raw data)
- Snapshot sheet gets updated with overall % Transfer and % Intervention
"""

import pandas as pd
import os
import json
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class CategorizingUploader:
    def __init__(self, credentials_path='credentials.json'):
        """Initialize Categorizing Uploader with Google Sheets integration"""
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Main categorizing sheet ID
        self.categorizing_sheet_id = '1hJUaSX75lgtKY8tnqzWVXF7MXUBGhlltTiHBu_xSM10'
        
        # Snapshot sheet ID (where we update % Transfer and % Intervention)
        self.snapshot_sheet_id = '1XkVcHlkh8fEp7mmBD1Zkavdp2blBLwSABT1dE_sOf74'

    def setup_sheets_api(self):
        """Setup Google Sheets API authentication"""
        try:
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            
            if os.path.exists(self.credentials_path):
                creds = Credentials.from_service_account_file(
                    self.credentials_path, scopes=SCOPES)
                self.service = build('sheets', 'v4', credentials=creds)
                print("✅ Google Sheets API authenticated successfully")
                return True
            else:
                print(f"❌ Credentials file not found: {self.credentials_path}")
                return False
                
        except Exception as e:
            print(f"❌ Error setting up Google Sheets API: {str(e)}")
            return False

    def find_categorizing_files(self):
        """Find categorizing files and their corresponding reports"""
        # Look in yesterday's date subfolder
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        output_dir = f"outputs/LLM_outputs/{date_folder}"
        report_dir = f"outputs/categorizing/{date_folder}"
        
        if not os.path.exists(output_dir):
            print(f"❌ Output directory not found: {output_dir}")
            return []
            
        if not os.path.exists(report_dir):
            print(f"❌ Report directory not found: {report_dir}")
            return []
        
        # Get yesterday's date in mm_dd format
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.strftime('%m_%d')
        
        print(f"🔍 Looking for categorizing files with date: {target_date}")
        
        file_pairs = []
        
        # Find all categorizing raw files
        for filename in os.listdir(output_dir):
            if filename.startswith('categorizing_') and filename.endswith('.csv'):
                if target_date in filename:
                    # Parse filename: categorizing_{dept_key}_{mm}_{dd}.csv
                    # Remove categorizing_ prefix and .csv suffix
                    name_part = filename[13:-4]  # Remove 'categorizing_' and '.csv'
                    
                    # Split by underscores and reconstruct department key
                    parts = name_part.split('_')
                    if len(parts) >= 3:
                        # Last two parts are mm_dd, everything before is department key
                        dept_key_parts = parts[:-2]
                        dept_key = '_'.join(dept_key_parts)
                        
                        # Convert dept_key to proper department name
                        department = self.convert_dept_key_to_name(dept_key)
                        
                        if not department:
                            print(f"⚠️  Unknown department key '{dept_key}' in {filename}, skipping")
                            continue
                        
                        print(f"📁 Matched {filename} -> Department key: '{dept_key}' -> {department}")
                        
                        # Find corresponding report file
                        report_filename = f"{department}_Categorizing_Summary.csv"
                        report_path = os.path.join(report_dir, report_filename)
                        
                        if os.path.exists(report_path):
                            raw_path = os.path.join(output_dir, filename)
                            file_pairs.append({
                                'department': department,
                                'raw_file': raw_path,
                                'report_file': report_path,
                                'date_str': target_date,
                                'dept_key': dept_key
                            })
                            print(f"📁 Found pair: {filename} + {report_filename} -> {department}")
                        else:
                            print(f"⚠️  Missing report for {filename}: {report_filename}")
        
        return file_pairs

    def convert_dept_key_to_name(self, dept_key):
        """Convert department key to proper department name"""
        # Handle MV Resolvers
        if 'mv' in dept_key.lower() and 'resolvers' in dept_key.lower():
            return 'MV Resolvers'
        elif 'mv_resolvers' == dept_key.lower():
            return 'MV Resolvers'
        
        # For now, since only MV Resolvers is supported, return None for others
        return None

    def create_sheet_name(self, date_str, is_raw=False):
        """Create properly formatted sheet name: yyyy-mm-dd or yyyy-mm-dd-RAW"""
        try:
            # Convert mm_dd to yyyy-mm-dd
            month, day = date_str.split('_')
            current_year = datetime.now().year
            formatted_date = f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"
            
            if is_raw:
                return f"{formatted_date}-RAW"
            else:
                return formatted_date
        except:
            return f"{date_str}-RAW" if is_raw else date_str

    def create_new_sheet(self, spreadsheet_id, sheet_name):
        """Create a new sheet in the target spreadsheet"""
        if not self.service:
            print("❌ Google Sheets service not available")
            return False
            
        try:
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=request_body
            ).execute()
            
            print(f"✅ Created new sheet: {sheet_name}")
            return True
            
        except Exception as e:
            if "already exists" in str(e):
                print(f"📋 Sheet already exists: {sheet_name}")
                return True
            else:
                print(f"❌ Error creating sheet {sheet_name}: {str(e)}")
                return False

    def upload_data_to_sheet(self, filepath, spreadsheet_id, sheet_name, is_report=False):
        """Upload CSV data to the specified sheet"""
        if not self.service:
            print("❌ Google Sheets service not available")
            return False
            
        try:
            # Read CSV file
            df = pd.read_csv(filepath)
            print(f"📊 Read {len(df)} rows from {os.path.basename(filepath)}")
            
            # Clean the data for Google Sheets API
            def clean_cell_value(value):
                """Clean cell values to prevent JSON parsing errors while preserving linebreaks"""
                if pd.isna(value):
                    return ""
                value_str = str(value)
                # Keep linebreaks but normalize them to \n for Google Sheets
                value_str = value_str.replace('\r\n', '\n').replace('\r', '\n')
                # Use safe limit to avoid Google Sheets issues
                if len(value_str) > 30000:
                    value_str = value_str[:30000] + "...[TRUNCATED]"
                return value_str
            
            # Convert DataFrame to list of lists with cleaned values
            headers = [str(col) for col in df.columns.tolist()]
            
            cleaned_data = []
            for _, row in df.iterrows():
                cleaned_row = [clean_cell_value(value) for value in row]
                cleaned_data.append(cleaned_row)
            
            # Combine headers with data
            data = [headers]
            data.extend(cleaned_data)
            
            # Clear existing data and upload new data
            range_name = f"{sheet_name}!A:Z"
            
            # Clear the sheet first
            self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            # Upload new data
            body = {
                'values': data
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption='RAW',
                body=body
            ).execute()
            
            data_type = "report" if is_report else "raw data"
            print(f"✅ Uploaded {len(data)} rows of {data_type} to sheet: {sheet_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error uploading to {sheet_name}: {str(e)}")
            return False

    def calculate_overall_percentages(self, raw_file):
        """Calculate overall % Transfer and % Intervention from raw data"""
        try:
            df = pd.read_csv(raw_file)
            print(f"📊 Calculating overall percentages from {len(df)} conversations")
            
            # Parse JSON outputs to get intervention/transfer data
            intervention_count = 0
            transfer_count = 0
            total_parsed = 0
            
            for _, row in df.iterrows():
                llm_output = row.get('llm_output', '')
                if pd.isna(llm_output) or not llm_output.strip():
                    continue
                
                try:
                    # Clean and parse JSON
                    cleaned = str(llm_output).strip()
                    if cleaned.startswith('```json'):
                        cleaned = cleaned.replace('```json', '').replace('```', '').strip()
                    elif cleaned.startswith('```'):
                        cleaned = cleaned.replace('```', '').strip()
                    
                    parsed = json.loads(cleaned)
                    intervention_or_transfer = parsed.get('InterventionOrTransfer', '').lower()
                    
                    if intervention_or_transfer in ['intervention', 'transfer']:
                        total_parsed += 1
                        if intervention_or_transfer == 'intervention':
                            intervention_count += 1
                        elif intervention_or_transfer == 'transfer':
                            transfer_count += 1
                            
                except (json.JSONDecodeError, Exception):
                    continue
            
            if total_parsed == 0:
                print("⚠️  No valid intervention/transfer data found")
                return None, None
            
            # Calculate percentages based on total conversations (not just parsed ones)
            total_conversations = len(df)
            pct_intervention = (intervention_count / total_conversations) * 100
            pct_transfer = (transfer_count / total_conversations) * 100
            
            print(f"📊 Overall Statistics:")
            print(f"   Total conversations: {total_conversations}")
            print(f"   Valid parsed: {total_parsed}")
            print(f"   Interventions: {intervention_count} ({pct_intervention:.2f}% of all chats)")
            print(f"   Transfers: {transfer_count} ({pct_transfer:.2f}% of all chats)")
            
            return pct_intervention, pct_transfer
            
        except Exception as e:
            print(f"❌ Error calculating percentages: {str(e)}")
            return None, None

    def find_column_by_name(self, sheet_id, column_name, sheet_name='Data'):
        """Find column number by searching for column name in header row"""
        if not self.service:
            return None, None
            
        sheet_names_to_try = ['Data', 'Sheet1', 'Main']
        
        for current_sheet_name in sheet_names_to_try:
            try:
                # Get the first row (headers)
                range_name = f"{current_sheet_name}!1:1"
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=sheet_id, range=range_name).execute()
                
                values = result.get('values', [])
                if values and len(values[0]) > 0:
                    headers = values[0]
                    print(f"🔍 Searching for column '{column_name}' in sheet '{current_sheet_name}'...")
                    
                    # First try exact match
                    for i, header in enumerate(headers):
                        if header:
                            header_clean = str(header).strip()
                            if header_clean == column_name:
                                print(f"📍 Found exact match for '{column_name}' at column {i+1} of sheet {current_sheet_name}")
                                return i + 1, current_sheet_name  # 1-based column number
                    
                    # Then try case-insensitive exact match
                    for i, header in enumerate(headers):
                        if header:
                            header_clean = str(header).strip()
                            if header_clean.lower() == column_name.lower():
                                print(f"📍 Found case-insensitive match for '{column_name}' at column {i+1} of sheet {current_sheet_name}")
                                return i + 1, current_sheet_name  # 1-based column number
                            
            except Exception as e:
                continue
        
        print(f"❌ Column '{column_name}' not found in any sheet")
        return None, None

    def find_date_row(self, sheet_id, target_date, sheet_name='Data'):
        """Find row with target date (yyyy-mm-dd format) in column A"""
        if not self.service:
            return None, None
            
        try:
            # Get all data from column A
            range_name = f"{sheet_name}!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id, range=range_name).execute()
            
            values = result.get('values', [])
            
            # Find the row with target date
            for i, row in enumerate(values):
                if row and len(row) > 0:
                    cell_value = str(row[0]).strip()
                    if target_date in cell_value:
                        print(f"✅ Found date {target_date} in row {i+1}")
                        return i + 1, sheet_name
            
            print(f"❌ Date {target_date} not found")
            return None, None
            
        except Exception as e:
            print(f"❌ Error finding date row: {str(e)}")
            return None, None

    def update_cell_value(self, sheet_id, sheet_name, row, col, value):
        """Update a specific cell with the percentage value"""
        if not self.service:
            return False
            
        try:
            # Convert column number to letter
            if col <= 26:
                col_letter = chr(64 + col)  # A-Z
            else:
                first_letter = chr(64 + ((col - 1) // 26))
                second_letter = chr(64 + ((col - 1) % 26) + 1)
                col_letter = first_letter + second_letter
                
            range_name = f"{sheet_name}!{col_letter}{row}"
            
            # Update the cell
            body = {
                'values': [[value]]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"✅ Updated {range_name} with: {value}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating cell: {str(e)}")
            return False

    def update_snapshot_sheet(self, pct_intervention, pct_transfer):
        """Update the snapshot sheet with overall percentages"""
        print(f"\n📊 Updating snapshot sheet with overall percentages...")
        
        # Find yesterday's date in yyyy-mm-dd format
        yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Find the date row
        date_row, sheet_name = self.find_date_row(self.snapshot_sheet_id, yesterday_date)
        if not date_row:
            print(f"❌ Could not find date {yesterday_date} in snapshot sheet")
            return False
        
        # Find % Intervention column
        intervention_col, sheet_name = self.find_column_by_name(self.snapshot_sheet_id, '% Intervention', sheet_name)
        if not intervention_col:
            print("❌ Could not find '% Intervention' column")
            return False
        
        # Find % Transfer column  
        transfer_col, sheet_name = self.find_column_by_name(self.snapshot_sheet_id, '% Transfer', sheet_name)
        if not transfer_col:
            print("❌ Could not find '% Transfer' column")
            return False
        
        # Update both cells
        intervention_value = f"{pct_intervention:.2f}%"
        transfer_value = f"{pct_transfer:.2f}%"
        
        success = True
        success &= self.update_cell_value(self.snapshot_sheet_id, sheet_name, date_row, intervention_col, intervention_value)
        success &= self.update_cell_value(self.snapshot_sheet_id, sheet_name, date_row, transfer_col, transfer_value)
        
        if success:
            print(f"✅ Successfully updated snapshot sheet:")
            print(f"   % Intervention: {intervention_value}")
            print(f"   % Transfer: {transfer_value}")
        
        return success

    def process_all_files(self):
        """Process all categorizing files and upload to Google Sheets"""
        if not self.service:
            print("❌ Google Sheets API not available")
            return
        
        print(f"🚀 Starting categorizing data upload to Google Sheets...")
        
        # Find all categorizing file pairs
        file_pairs = self.find_categorizing_files()
        
        if not file_pairs:
            print("❌ No categorizing file pairs found for yesterday's date")
            return
        
        print(f"📁 Found {len(file_pairs)} department file pairs to upload")
        
        success_count = 0
        overall_intervention_pct = None
        overall_transfer_pct = None
        
        for file_data in file_pairs:
            department = file_data['department']
            raw_file = file_data['raw_file']
            report_file = file_data['report_file']
            date_str = file_data['date_str']
            
            try:
                # Create sheet names
                report_sheet_name = self.create_sheet_name(date_str, is_raw=False)
                raw_sheet_name = self.create_sheet_name(date_str, is_raw=True)
                
                print(f"\n📊 Processing {department}:")
                print(f"  📋 Report: {os.path.basename(report_file)} -> {report_sheet_name}")
                print(f"  📄 Raw: {os.path.basename(raw_file)} -> {raw_sheet_name}")
                
                success = True
                
                # Create and upload report sheet
                if self.create_new_sheet(self.categorizing_sheet_id, report_sheet_name):
                    if not self.upload_data_to_sheet(report_file, self.categorizing_sheet_id, report_sheet_name, is_report=True):
                        success = False
                else:
                    success = False
                
                # Create and upload raw data sheet
                if self.create_new_sheet(self.categorizing_sheet_id, raw_sheet_name):
                    if not self.upload_data_to_sheet(raw_file, self.categorizing_sheet_id, raw_sheet_name, is_report=False):
                        success = False
                else:
                    success = False
                
                # Calculate overall percentages from raw data
                pct_intervention, pct_transfer = self.calculate_overall_percentages(raw_file)
                if pct_intervention is not None and pct_transfer is not None:
                    overall_intervention_pct = pct_intervention
                    overall_transfer_pct = pct_transfer
                
                if success:
                    success_count += 1
                    print(f"✅ Successfully uploaded {department} data")
                    print(f"📋 Spreadsheet URL: https://docs.google.com/spreadsheets/d/{self.categorizing_sheet_id}")
                else:
                    print(f"❌ Failed to upload {department} data")
                    
            except Exception as e:
                print(f"❌ Error processing {department}: {str(e)}")
        
        # Update snapshot sheet with overall percentages
        if overall_intervention_pct is not None and overall_transfer_pct is not None:
            self.update_snapshot_sheet(overall_intervention_pct, overall_transfer_pct)
        
        # Print summary
        print(f"\n📈 Upload Summary:")
        print(f"✅ Successfully uploaded: {success_count}/{len(file_pairs)} departments")

def main():
    """Main function"""
    uploader = CategorizingUploader()
    uploader.process_all_files()
    print("\n✅ Categorizing data upload completed!")

if __name__ == "__main__":
    main() 