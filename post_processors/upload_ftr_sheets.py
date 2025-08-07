#!/usr/bin/env python3
"""
Upload FTR CSV files to Google Spreadsheets
- Main FTR sheet gets one tab: yyyy-mm-dd (combined data with original + summary)
- Snapshot sheet gets updated with FTR percentage in "FTR" column
"""

import pandas as pd
import os
import json
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class FTRUploader:
    def __init__(self, credentials_path='credentials.json'):
        """Initialize FTR Uploader with Google Sheets integration"""
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Department FTR sheet IDs - one sheet per department
        self.department_ftr_sheets = {
            'doctors': '19EppEaiNO_9rb4HJpLEQOWvy7dB52INzIJxUEzOqqGQ',
            'delighters': '1x5gOsmg7nJfuKSxuJgGDSVC5x6Hyfse-oL-s62-WZ8k',
            'cc_sales': '16c_wgKVSwQu8L8kTBhid1nHbYK24PJOQFWOZaxPyOFg',
            'cc_resolvers': '1MMBq3OLlWnnuVGoYoSl6YtHC_zu-599OtswQpxCjrbQ',
            'filipina': '1akUETcjIoP-MsPHW9xad3Nbe67ECa7dzSj3usynZ_Ww',
            'african': '1SF9_6ucjNT3rxRyST-s1d-FtyePFMLRPC5vzx94lFoY',
            'ethiopian': '1SpVkmEQDnXyM0KtmUV0vyYfADBiJwowVdg6LdXzUiRI',
            'mv_resolvers': '1_20GZcWM5jLCNYkE8v2_CLxi7vTUvR3IRakWKcWZmfA',
            'mv_sales': '1rSJRPTOPUXKNkXNFXKy-W7SW0mKCxiybgPnpa6p7LA8'
        }
        
        # Department snapshot sheet IDs (for updating FTR percentages)
        self.department_snapshot_sheets = {
            'doctors': '1STHimb0IJ077iuBtTOwsa-GD8jStjU3SiBW7yBWom-E',
            'delighters': '1PV0ZmobUYKHGZvHC7IfJ1t6HrJMTFi6YRbpISCouIfQ',
            'cc_sales': '1te1fbAXhURIUO0EzQ2Mrorv3a6GDtEVM_5np9TO775o',
            'cc_resolvers': '1QdmaTc5F2VUJ0Yu0kNF9d6ETnkMOlOgi18P7XlBSyHg',
            'filipina': '1E5wHZKSDXQZlHIb3sV4ZWqIxvboLduzUEU0eupK7tys',
            'african': '1__KlrVjcpR8RoYfTYMYZ_EgddUSXMhK3bJO0fTGwDig',
            'ethiopian': '1ENzdgiwUEtBSb5sHZJWs5aG8g2H62Low8doaDZf8s90',
            'mv_resolvers': '1XkVcHlkh8fEp7mmBD1Zkavdp2blBLwSABT1dE_sOf74',
            'mv_sales': '1agrl9hlBhemXkiojuWKbqiMHKUzxGgos4JSkXxw7NAk'
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

    def extract_ftr_percentage(self, filepath):
        """Extract FTR percentage from the combined CSV file"""
        try:
            df = pd.read_csv(filepath)
            
            # Look for the row with "Overall FTR Percentage" in Metric column
            ftr_row = df[df['Metric'] == 'Overall FTR Percentage']
            
            if not ftr_row.empty:
                ftr_value = ftr_row['Value'].iloc[0]
                # Extract percentage number (remove % sign)
                if isinstance(ftr_value, str) and '%' in ftr_value:
                    return float(ftr_value.replace('%', ''))
                else:
                    return float(ftr_value)
            
            return None
            
        except Exception as e:
            print(f"❌ Error extracting FTR percentage: {str(e)}")
            return None

    def create_new_sheet(self, spreadsheet_id, sheet_name):
        """Create a new sheet in the spreadsheet"""
        try:
            if not self.service:
                print("❌ Google Sheets service not available")
                return False
            
            # Check if sheet already exists
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
            
            if sheet_name in existing_sheets:
                print(f"📋 Sheet '{sheet_name}' already exists")
                return True
            
            # Create new sheet
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=request_body
            ).execute()
            
            print(f"✅ Created new sheet: {sheet_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating sheet: {str(e)}")
            return False

    def upload_data_to_sheet(self, filepath, spreadsheet_id, sheet_name):
        """Upload CSV data to specific sheet"""
        try:
            if not self.service:
                print("❌ Google Sheets service not available")
                return False
            
            # Read CSV file
            df = pd.read_csv(filepath)
            
            # Clean the data for Google Sheets API
            df = df.fillna('')
            
            # Convert to list of lists for API
            values = [df.columns.tolist()] + df.values.tolist()
            
            # Keep linebreaks but normalize them to \n for Google Sheets
            for i, row in enumerate(values):
                for j, cell in enumerate(row):
                    value_str = str(cell)
                    # Use safe limit to avoid Google Sheets issues
                    if len(value_str) > 30000:  # Safer limit for Google Sheets
                        values[i][j] = value_str[:30000] + "... [TRUNCATED]"
                    else:
                        # Normalize line breaks
                        values[i][j] = value_str.replace('\r\n', '\n').replace('\r', '\n')
            
            # Clear existing data in the sheet
            clear_range = f"{sheet_name}!A:Z"
            self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=clear_range
            ).execute()
            
            # Upload new data
            range_name = f"{sheet_name}!A1"
            value_input_option = 'RAW'
            
            request_body = {
                'values': values,
                'majorDimension': 'ROWS'
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=request_body
            ).execute()
            
            print(f"✅ Uploaded {len(df)} rows to {sheet_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error uploading data: {str(e)}")
            return False

    def find_column_by_name(self, sheet_id, column_name, sheet_name='Data'):
        """Find a column by exact name in the specified sheet"""
        try:
            range_name = f"{sheet_name}!1:1"  # Read header row
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values or not values[0]:
                return None, sheet_name
                
            header_row = values[0]
            print(f"🔍 Searching for column '{column_name}' in sheet '{sheet_name}'...")
            
            # First try exact match
            for i, header in enumerate(header_row):
                if header:
                    header_clean = str(header).strip()
                    if header_clean == column_name:
                        print(f"📍 Found exact match for '{column_name}' at column {i + 1}")
                        return i + 1, sheet_name  # Return 1-based column index
            
            # Then try case-insensitive exact match
            for i, header in enumerate(header_row):
                if header:
                    header_clean = str(header).strip()
                    if header_clean.upper() == column_name.upper():
                        print(f"📍 Found case-insensitive match for '{column_name}' at column {i + 1}")
                        return i + 1, sheet_name  # Return 1-based column index
            
            print(f"⚠️ Column '{column_name}' not found in sheet '{sheet_name}'")
            print(f"Available columns: {[str(h).strip() for h in header_row if h]}")
            return None, sheet_name
            
        except Exception as e:
            print(f"❌ Error finding column '{column_name}': {str(e)}")
            return None, sheet_name

    def find_date_row(self, sheet_id, target_date, sheet_name='Data'):
        """Find the row containing the target date"""
        try:
            range_name = f"{sheet_name}!A:A"  # Read date column
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return None, sheet_name
                
            for i, row in enumerate(values[1:], start=2):  # Skip header, start from row 2
                if row and len(row) > 0:
                    date_cell = str(row[0]).strip()
                    if target_date in date_cell:
                        return i, sheet_name  # Return 1-based row index
                        
            return None, sheet_name
            
        except Exception as e:
            print(f"❌ Error finding date row '{target_date}': {str(e)}")
            return None, sheet_name

    def update_cell_value(self, sheet_id, sheet_name, row, col, value):
        """Update a specific cell with a value"""
        try:
            # Convert column number to letter (1=A, 2=B, etc.)
            if col <= 26:
                col_letter = chr(64 + col)  # A-Z
            else:
                # For columns beyond Z
                first_letter = chr(64 + ((col - 1) // 26))
                second_letter = chr(64 + ((col - 1) % 26) + 1)
                col_letter = first_letter + second_letter
                
            range_name = f"{sheet_name}!{col_letter}{row}"
            
            body = {
                'values': [[value]]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"✅ Updated {range_name} with FTR: {value}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating cell: {str(e)}")
            return False

    def update_snapshot_sheet(self, ftr_percentage, dept_key):
        """Update the department's snapshot sheet with FTR percentage"""
        if dept_key not in self.department_snapshot_sheets:
            print(f"❌ No snapshot sheet configured for department: {dept_key}")
            return False
            
        snapshot_sheet_id = self.department_snapshot_sheets[dept_key]
        print(f"\n📊 Updating {dept_key} snapshot sheet with FTR: {ftr_percentage:.1f}%")
        
        # Find yesterday's date in yyyy-mm-dd format (FTR analysis is for yesterday's data)
        yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Find the date row
        date_row, sheet_name = self.find_date_row(snapshot_sheet_id, yesterday_date)
        if not date_row:
            print(f"❌ Could not find date {yesterday_date} in {dept_key} snapshot sheet")
            return False
        
        # Find FTR column or fallback to "First Time resolution on actionable chats"
        ftr_col, sheet_name = self.find_column_by_name(snapshot_sheet_id, 'FTR', sheet_name)
        if not ftr_col:
            print(f"⚠️  'FTR' column not found in {dept_key} snapshot sheet, trying fallback column name...")
            ftr_col, sheet_name = self.find_column_by_name(snapshot_sheet_id, 'First Time resolution on actionable chats', sheet_name)
            if ftr_col:
                print(f"✅ Found fallback column 'First Time resolution on actionable chats' in {dept_key} snapshot sheet")
            else:
                print(f"❌ Neither 'FTR' nor 'First Time resolution on actionable chats' column found in {dept_key} snapshot sheet")
                print(f"💡 Please add one of these columns to the {dept_key} snapshot sheet manually")
                print(f"💡 The column should be added to the header row in the 'Data' sheet")
                return False
        
        # Update the cell with percentage
        ftr_value = f"{ftr_percentage:.1f}%"
        success = self.update_cell_value(snapshot_sheet_id, sheet_name, date_row, ftr_col, ftr_value)
        
        if success:
            print(f"✅ Successfully updated {dept_key} snapshot sheet with FTR: {ftr_value}")
        
        return success

    def extract_department_from_filename(self, filename):
        """Extract department key from filename"""
        # Remove file extension and split by underscore
        parts = filename.replace('.csv', '').split('_')
        
        # Department name mapping
        dept_mapping = {
            'doctors': 'doctors',
            'delighters': 'delighters',
            'cc': {
                'sales': 'cc_sales',
                'resolvers': 'cc_resolvers'
            },
            'mv': {
                'sales': 'mv_sales',
                'resolvers': 'mv_resolvers'
            },
            'filipina': 'filipina',
            'african': 'african',
            'ethiopian': 'ethiopian'
        }
        
        # Try to match department from filename
        filename_lower = filename.lower()
        
        if 'doctors' in filename_lower:
            return 'doctors'
        elif 'delighters' in filename_lower:
            return 'delighters'
        elif 'cc_sales' in filename_lower or ('cc' in filename_lower and 'sales' in filename_lower):
            return 'cc_sales'
        elif 'cc_resolvers' in filename_lower or ('cc' in filename_lower and 'resolvers' in filename_lower):
            return 'cc_resolvers'
        elif 'mv_sales' in filename_lower or ('mv' in filename_lower and 'sales' in filename_lower):
            return 'mv_sales'
        elif 'mv_resolvers' in filename_lower or ('mv' in filename_lower and 'resolvers' in filename_lower):
            return 'mv_resolvers'
        elif 'filipina' in filename_lower:
            return 'filipina'
        elif 'african' in filename_lower:
            return 'african'
        elif 'ethiopian' in filename_lower:
            return 'ethiopian'
        
        return None

    def process_all_files(self):
        """Process all FTR files and upload to Google Sheets"""
        if not self.service:
            print("❌ Google Sheets API not available")
            return False
        
        print(f"🚀 Starting FTR data upload to Google Sheets...")
        
        # Get yesterday's date for file naming
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        sheet_name = date_folder  # Use yyyy-mm-dd format for sheet name
        
        # Look for FTR combined files
        ftr_dir = f"outputs/ftr/{date_folder}"
        
        if not os.path.exists(ftr_dir):
            print(f"❌ FTR directory not found: {ftr_dir}")
            return False
        
        # Find combined FTR files
        success_count = 0
        processed_departments = []
        
        for filename in os.listdir(ftr_dir):
            if filename.endswith('_FTR_Combined.csv'):
                filepath = os.path.join(ftr_dir, filename)
                
                # Extract department from filename
                dept_key = self.extract_department_from_filename(filename)
                if not dept_key:
                    print(f"⚠️  Could not determine department from filename: {filename}")
                    continue
                
                if dept_key not in self.department_ftr_sheets:
                    print(f"⚠️  No FTR sheet configured for department: {dept_key}")
                    continue
                
                ftr_sheet_id = self.department_ftr_sheets[dept_key]
                
                # Skip if placeholder ID
                if 'REPLACE_WITH' in ftr_sheet_id:
                    print(f"⚠️  FTR sheet ID not configured for {dept_key}. Please create the sheet and update the ID.")
                    continue
                
                print(f"\n📁 Processing {dept_key} FTR file: {filename}")
                
                # Extract FTR percentage for snapshot update
                ftr_percentage = self.extract_ftr_percentage(filepath)
                
                # Create new sheet tab for this date
                if self.create_new_sheet(ftr_sheet_id, sheet_name):
                    # Upload data
                    if self.upload_data_to_sheet(filepath, ftr_sheet_id, sheet_name):
                        print(f"✅ Successfully uploaded {dept_key} FTR data")
                        print(f"📋 Sheet URL: https://docs.google.com/spreadsheets/d/{ftr_sheet_id}")
                        
                        # Update snapshot sheet with FTR percentage
                        if ftr_percentage is not None:
                            self.update_snapshot_sheet(ftr_percentage, dept_key)
                        
                        success_count += 1
                        processed_departments.append(dept_key)
        
        if success_count > 0:
            print(f"\n✅ Successfully processed {success_count} department(s): {', '.join(processed_departments)}")
            return True
        else:
            print(f"\n❌ No FTR files were successfully processed")
            return False


def main():
    """Main function for standalone execution"""
    uploader = FTRUploader()
    uploader.process_all_files()


if __name__ == "__main__":
    main() 