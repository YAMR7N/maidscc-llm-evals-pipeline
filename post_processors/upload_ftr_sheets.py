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
        
        # Main FTR sheet ID
        self.ftr_sheet_id = '1_20GZcWM5jLCNYkE8v2_CLxi7vTUvR3IRakWKcWZmfA'
        
        # Snapshot sheet ID (where we update FTR percentage)
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

    def update_snapshot_sheet(self, ftr_percentage):
        """Update the snapshot sheet with FTR percentage"""
        print(f"\n📊 Updating snapshot sheet with FTR: {ftr_percentage:.1f}%")
        
        # Find yesterday's date in yyyy-mm-dd format (FTR analysis is for yesterday's data)
        yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Find the date row
        date_row, sheet_name = self.find_date_row(self.snapshot_sheet_id, yesterday_date)
        if not date_row:
            print(f"❌ Could not find date {yesterday_date} in snapshot sheet")
            return False
        
        # Find FTR column
        ftr_col, sheet_name = self.find_column_by_name(self.snapshot_sheet_id, 'FTR', sheet_name)
        if not ftr_col:
            print("⚠️  FTR column not found in snapshot sheet")
            print("💡 Please add an 'FTR' column to the snapshot sheet manually")
            print("💡 The FTR column should be added to the header row in the 'Data' sheet")
            return False
        
        # Update the cell with percentage
        ftr_value = f"{ftr_percentage:.1f}%"
        success = self.update_cell_value(self.snapshot_sheet_id, sheet_name, date_row, ftr_col, ftr_value)
        
        if success:
            print(f"✅ Successfully updated snapshot sheet with FTR: {ftr_value}")
        
        return success

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
        ftr_files = []
        for filename in os.listdir(ftr_dir):
            if filename.endswith('_FTR_Combined.csv'):
                filepath = os.path.join(ftr_dir, filename)
                ftr_files.append(filepath)
        
        if not ftr_files:
            print(f"❌ No FTR combined files found in {ftr_dir}")
            return False
        
        # For now, process the first FTR file found (you can modify this to combine multiple departments)
        filepath = ftr_files[0]
        print(f"📁 Processing FTR file: {os.path.basename(filepath)}")
        
        # Extract FTR percentage for snapshot update
        ftr_percentage = self.extract_ftr_percentage(filepath)
        
        # Create new sheet
        if self.create_new_sheet(self.ftr_sheet_id, sheet_name):
            # Upload data
            if self.upload_data_to_sheet(filepath, self.ftr_sheet_id, sheet_name):
                print(f"✅ Successfully uploaded FTR data")
                print(f"📋 Sheet URL: https://docs.google.com/spreadsheets/d/{self.ftr_sheet_id}")
                
                # Update snapshot sheet with FTR percentage
                if ftr_percentage is not None:
                    self.update_snapshot_sheet(ftr_percentage)
                
                return True
        
        return False


def main():
    """Main function for standalone execution"""
    uploader = FTRUploader()
    uploader.process_all_files()


if __name__ == "__main__":
    main() 