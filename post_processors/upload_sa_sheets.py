#!/usr/bin/env python3
"""
Upload saprompt CSV files to individual department Google Spreadsheets
Each file creates a new sheet named with yyyy-mm-dd format
"""

import pandas as pd
import os
import re
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class SaprompUploader:
    def __init__(self, credentials_path='credentials.json'):
        """Initialize SA Prompt Uploader with Google Sheets integration"""
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Department sheet IDs as provided by user
        self.department_sheets = {
            'African': '1ygyak-GQINyUMnUf828KLBZX_U0pTvVAOmsSPZdH0dA',
            'CC Resolvers': '1qL3qWGNfIJZek6ZDr5g6yauegdt5Y8zDXDNxRroGK84',
            'CC Sales': '13YEU9kJEX7LFp8KnbY6XXnGIvW5H574qIljy_GN4Yxs',
            'Delighters': '1FmA1MfDQGQP0BGVJF0aW8d7IPd1L9Hd7RUa98CsUXOM',
            'Doctors': '1JIQCPsMn8fMw1UwcNUSoLjgBtfShbDIxjJUtWOLBIxw',
            'Ethiopian': '19ZK3agSB_R8cGbk-0bxITB0DeTN1NetOjFzhxaj90oo',
            'Filipina': '1Shz1_H7ifpZIT9jzhxDy4zIA_Qth2n8aiclsUusZgdQ',
            'MV Resolvers': '1fkF4xglbJaMOOFr7wdOpvaGmrL5IOJF19NXwOV6YOg0',
            'MV Sales': '1PvWLMDV6hMGtQfcVFyXAjzOPNAo_kaV9D9n0BFpKw9Q',
        }
        
        # Department name mapping for proper formatting
        self.department_name_mapping = {
            'african': 'African',
            'cc_resolvers': 'CC Resolvers',
            'cc_sales': 'CC Sales',
            'delighters': 'Delighters',
            'doctors': 'Doctors',
            'ethiopian': 'Ethiopian',
            'filipina': 'Filipina',
            'mv_resolvers': 'MV Resolvers',
            'mv_sales': 'MV Sales'
        }

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

    def find_saprompt_files(self):
        """Find all saprompt files from yesterday's date"""
        # Look in yesterday's date subfolder
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        output_dir = f"outputs/LLM_outputs/{date_folder}"
        saprompt_files = []
        
        if not os.path.exists(output_dir):
            print(f"❌ Directory not found: {output_dir}")
            return []
        
        # Get yesterday's date in mm_dd format
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.strftime('%m_%d')
        
        print(f"🔍 Looking for saprompt files with date: {target_date}")
        
        for filename in os.listdir(output_dir):
            if filename.startswith('saprompt_') and filename.endswith('.csv'):
                # Check if this file matches yesterday's date pattern
                if target_date in filename:
                    # Extract department from filename: saprompt_{dept}_{mm}_{dd}.csv
                    # Remove saprompt_ prefix and .csv suffix
                    name_part = filename[9:-4]  # Remove 'saprompt_' and '.csv'
                    
                    # Split by underscores and reconstruct department name
                    parts = name_part.split('_')
                    if len(parts) >= 3:
                        # Last two parts are mm_dd, everything before is department
                        dept_parts = parts[:-2]
                        dept_key = '_'.join(dept_parts)
                        
                        filepath = os.path.join(output_dir, filename)
                        saprompt_files.append((filepath, dept_key, filename, target_date))
                        print(f"📁 Found: {filename} -> Department: {dept_key}")
        
        return saprompt_files

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
                # Truncate very long values that might cause issues
                if len(value_str) > 50000:  # Google Sheets cell limit
                    value_str = value_str[:50000] + "..."
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

    def process_all_files(self):
        """Process all saprompt files and upload to Google Sheets"""
        if not self.service:
            print("❌ Google Sheets API not available")
            return
        
        print(f"🚀 Starting saprompt data upload to Google Sheets...")
        
        # Find all saprompt files
        saprompt_files = self.find_saprompt_files()
        
        if not saprompt_files:
            print("❌ No saprompt files found for yesterday's date")
            return
        
        print(f"📁 Found {len(saprompt_files)} files to upload")
        
        success_count = 0
        
        for filepath, dept_key, filename, date_str in saprompt_files:
            try:
                # Get proper department name
                # dept_key is guaranteed to be a string from find_saprompt_files
                dept_name = self.department_name_mapping.get(dept_key, dept_key.replace('_', ' ').title())
                
                # Get spreadsheet ID for this department
                spreadsheet_id = self.department_sheets.get(dept_name)
                if not spreadsheet_id:
                    print(f"❌ No spreadsheet ID found for department: {dept_name}")
                    continue
                
                # Create sheet name in yyyy-mm-dd format
                sheet_name = self.create_sheet_name(date_str)
                print(f"\n📊 Processing {filename} -> {dept_name} -> Sheet: {sheet_name}")
                
                # Create sheet if it doesn't exist
                if self.create_new_sheet(spreadsheet_id, sheet_name):
                    # Upload data
                    if self.upload_data_to_sheet(filepath, spreadsheet_id, sheet_name):
                        success_count += 1
                        print(f"✅ Successfully uploaded {filename} to {dept_name}")
                        print(f"📋 Sheet URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
                    else:
                        print(f"❌ Failed to upload {filename}")
                else:
                    print(f"❌ Failed to create sheet for {filename}")
                    
            except Exception as e:
                print(f"❌ Error processing {filename}: {str(e)}")
        
        # Print summary
        print(f"\n📈 Upload Summary:")
        print(f"✅ Successfully uploaded: {success_count}/{len(saprompt_files)} files")

def main():
    """Main function"""
    uploader = SaprompUploader()
    uploader.process_all_files()
    print("\n✅ Saprompt data upload completed!")

if __name__ == "__main__":
    main()
