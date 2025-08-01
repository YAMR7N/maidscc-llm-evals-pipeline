#!/usr/bin/env python3
"""
Upload false promises CSV files to Google Spreadsheets
- Main false promises sheet gets one tab: yyyy-mm-dd (LLM outputs)
- Snapshot sheet gets updated with % False Promises (RogueAnswer/NormalAnswer * 100)
"""

import pandas as pd
import os
import json
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class FalsePromisesUploader:
    def __init__(self, credentials_path='credentials.json'):
        """Initialize False Promises Uploader with Google Sheets integration"""
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Main false promises sheet ID
        self.false_promises_sheet_id = '12DXUaXOffHVVTj3ErFLmwWnCAEk1e-ljeA6OWACOen4'
        
        # Snapshot sheet ID (where we update % False Promises)
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

    def find_false_promises_files(self):
        """Find false promises files"""
        # Look in yesterday's date subfolder
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        output_dir = f"outputs/LLM_outputs/{date_folder}"
        
        if not os.path.exists(output_dir):
            print(f"❌ Output directory not found: {output_dir}")
            return []
        
        # Get yesterday's date in mm_dd format
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.strftime('%m_%d')
        
        print(f"🔍 Looking for false promises files with date: {target_date}")
        
        false_promises_files = []
        
        # Find all false promises files
        for filename in os.listdir(output_dir):
            if filename.startswith('false_promises_') and filename.endswith('.csv'):
                if target_date in filename:
                    # Parse filename: false_promises_{dept_key}_{mm}_{dd}.csv
                    # Remove false_promises_ prefix and .csv suffix
                    name_part = filename[15:-4]  # Remove 'false_promises_' and '.csv'
                    
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
                        
                        filepath = os.path.join(output_dir, filename)
                        false_promises_files.append({
                            'department': department,
                            'file': filepath,
                            'date_str': target_date,
                            'dept_key': dept_key,
                            'filename': filename
                        })
                        print(f"📁 Found: {filename} -> {department}")
        
        return false_promises_files

    def convert_dept_key_to_name(self, dept_key):
        """Convert department key to proper department name"""
        # Handle MV Resolvers
        if 'mv' in dept_key.lower() and 'resolvers' in dept_key.lower():
            return 'MV Resolvers'
        elif 'mv_resolvers' == dept_key.lower():
            return 'MV Resolvers'
        
        # For now, since only MV Resolvers is supported, return None for others
        return None

    def create_sheet_name(self, date_str):
        """Create properly formatted sheet name: yyyy-mm-dd"""
        try:
            # Convert mm_dd to yyyy-mm-dd
            month, day = date_str.split('_')
            current_year = datetime.now().year
            formatted_date = f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"
            return formatted_date
        except:
            return date_str

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

    def upload_data_to_sheet(self, filepath, spreadsheet_id, sheet_name):
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
            
            print(f"✅ Uploaded {len(data)} rows to sheet: {sheet_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error uploading to {sheet_name}: {str(e)}")
            return False

    def calculate_false_promises_percentage(self, filepath):
        """Calculate % False Promises (RogueAnswer count / NormalAnswer count * 100)"""
        try:
            df = pd.read_csv(filepath)
            print(f"📊 Calculating false promises percentage from {len(df)} conversations")
            
            # Parse JSON outputs to get chatResolution data
            rogue_count = 0
            normal_count = 0
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
                    chat_resolution = parsed.get('chatResolution', '').strip()
                    
                    if chat_resolution in ['RogueAnswer', 'NormalAnswer']:
                        total_parsed += 1
                        if chat_resolution == 'RogueAnswer':
                            rogue_count += 1
                        elif chat_resolution == 'NormalAnswer':
                            normal_count += 1
                            
                except (json.JSONDecodeError, Exception):
                    continue
            
            if len(df) == 0:
                print("⚠️  No conversations found - cannot calculate percentage")
                return None
            
            # Calculate percentage: RogueAnswer / Total Chats * 100
            false_promises_pct = (rogue_count / len(df)) * 100
            
            print(f"📊 False Promises Statistics:")
            print(f"   Total conversations: {len(df)}")
            print(f"   Valid parsed: {total_parsed}")
            print(f"   RogueAnswer: {rogue_count}")
            print(f"   NormalAnswer: {normal_count}")
            print(f"   % False Promises: {false_promises_pct:.2f}% (RogueAnswer/Total Chats)")
            
            return false_promises_pct
            
        except Exception as e:
            print(f"❌ Error calculating false promises percentage: {str(e)}")
            return None

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

    def update_snapshot_sheet(self, false_promises_pct):
        """Update the snapshot sheet with % False Promises"""
        print(f"\n📊 Updating snapshot sheet with % False Promises...")
        
        # Find yesterday's date in yyyy-mm-dd format
        yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Find the date row
        date_row, sheet_name = self.find_date_row(self.snapshot_sheet_id, yesterday_date)
        if not date_row:
            print(f"❌ Could not find date {yesterday_date} in snapshot sheet")
            return False
        
        # Find % False Promises column
        false_promises_col, sheet_name = self.find_column_by_name(self.snapshot_sheet_id, '% False Promises', sheet_name)
        if not false_promises_col:
            print("❌ Could not find '% False Promises' column")
            return False
        
        # Update the cell
        false_promises_value = f"{false_promises_pct:.2f}%"
        
        success = self.update_cell_value(self.snapshot_sheet_id, sheet_name, date_row, false_promises_col, false_promises_value)
        
        if success:
            print(f"✅ Successfully updated snapshot sheet:")
            print(f"   % False Promises: {false_promises_value}")
        
        return success

    def process_all_files(self):
        """Process all false promises files and upload to Google Sheets"""
        if not self.service:
            print("❌ Google Sheets API not available")
            return
        
        print(f"🚀 Starting false promises data upload to Google Sheets...")
        
        # Find all false promises files
        false_promises_files = self.find_false_promises_files()
        
        if not false_promises_files:
            print("❌ No false promises files found for yesterday's date")
            return
        
        print(f"📁 Found {len(false_promises_files)} false promises files to upload")
        
        success_count = 0
        false_promises_pct = None
        
        for file_data in false_promises_files:
            department = file_data['department']
            filepath = file_data['file']
            date_str = file_data['date_str']
            filename = file_data['filename']
            
            try:
                # Create sheet name
                sheet_name = self.create_sheet_name(date_str)
                
                print(f"\n📊 Processing {department}:")
                print(f"  📄 File: {filename} -> {sheet_name}")
                
                success = True
                
                # Create and upload sheet
                if self.create_new_sheet(self.false_promises_sheet_id, sheet_name):
                    if not self.upload_data_to_sheet(filepath, self.false_promises_sheet_id, sheet_name):
                        success = False
                else:
                    success = False
                
                # Calculate false promises percentage
                pct = self.calculate_false_promises_percentage(filepath)
                if pct is not None:
                    false_promises_pct = pct
                
                if success:
                    success_count += 1
                    print(f"✅ Successfully uploaded {department} data")
                    print(f"📋 Spreadsheet URL: https://docs.google.com/spreadsheets/d/{self.false_promises_sheet_id}")
                else:
                    print(f"❌ Failed to upload {department} data")
                    
            except Exception as e:
                print(f"❌ Error processing {department}: {str(e)}")
        
        # Update snapshot sheet with % False Promises
        if false_promises_pct is not None:
            self.update_snapshot_sheet(false_promises_pct)
        
        # Print summary
        print(f"\n📈 Upload Summary:")
        print(f"✅ Successfully uploaded: {success_count}/{len(false_promises_files)} files")

def main():
    """Main function"""
    uploader = FalsePromisesUploader()
    uploader.process_all_files()
    print("\n✅ False promises data upload completed!")

if __name__ == "__main__":
    main() 