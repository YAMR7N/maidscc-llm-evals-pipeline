#!/usr/bin/env python3
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import os
import sys

class UnnecessaryClinicRecUploader:
    def __init__(self):
        """Initialize Google Sheets API client for unnecessary clinic rec uploads"""
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        self.credentials_path = "credentials.json"  # Fixed: root directory, not config/
        self.unnecessary_clinic_rec_sheet_id = "1dZw0qyFCX3L2XuG-GTdNOO2bR73BB198lfJ-zvf1OSI"
        
        try:
            self.credentials = Credentials.from_service_account_file(
                self.credentials_path, scopes=self.scope
            )
            self.client = gspread.authorize(self.credentials)
            print("✅ Google Sheets API initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Google Sheets API: {e}")
            self.client = None

    def upload_unnecessary_clinic_rec_data(self, csv_file_path: str, department: str):
        """
        Upload unnecessary clinic rec analysis data to Google Sheets
        
        Args:
            csv_file_path: Path to the unnecessary clinic rec CSV file
            department: Department name (e.g., "Doctors")
        """
        if not self.client:
            print("❌ Google Sheets client not initialized")
            return False

        try:
            # Read the CSV file
            df = pd.read_csv(csv_file_path)
            print(f"📊 Read {len(df)} rows from {csv_file_path}")
            
            # Get yesterday's date in YYYY-MM-DD format for sheet name
            yesterday = datetime.now() - timedelta(days=1)
            sheet_name = yesterday.strftime("%Y-%m-%d")
            
            # Open the spreadsheet
            spreadsheet = self.client.open_by_key(self.unnecessary_clinic_rec_sheet_id)
            print(f"📋 Opened unnecessary clinic rec spreadsheet")
            
            # Try to get the sheet, create if it doesn't exist
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                print(f"📄 Found existing sheet: {sheet_name}")
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                print(f"📄 Created new sheet: {sheet_name}")
            
            # Clear the sheet first
            worksheet.clear()
            
            # Prepare data for upload - only keep necessary columns
            upload_columns = ['conversation_id', 'conversation', 'llm_output']
            if all(col in df.columns for col in upload_columns):
                upload_df = df[upload_columns].copy()
            else:
                print(f"⚠️ Expected columns not found. Available: {list(df.columns)}")
                upload_df = df.copy()
            
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
            
            # Clean the DataFrame before converting to values
            for column in upload_df.columns:
                upload_df[column] = upload_df[column].apply(clean_cell_value)
            
            # Convert DataFrame to list of lists for upload
            data_to_upload = [upload_df.columns.tolist()] + upload_df.values.tolist()
            
            # Upload data
            worksheet.update(data_to_upload, value_input_option='RAW')
            
            print(f"✅ Successfully uploaded {len(upload_df)} rows to {sheet_name}")
            print(f"🔗 Sheet URL: https://docs.google.com/spreadsheets/d/{self.unnecessary_clinic_rec_sheet_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error uploading unnecessary clinic rec data: {e}")
            return False

    def process_all_files(self):
        """Process all unnecessary clinic rec files and upload to Google Sheets"""
        if not self.client:
            print("❌ Cannot process files - Google Sheets client not initialized")
            print("💡 This is expected in test environments without credentials")
            return
        
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        base_dir = f"outputs/LLM_outputs/{date_folder}"
        
        if not os.path.exists(base_dir):
            print(f"⚠️ No LLM outputs directory found: {base_dir}")
            return
        
        # Find all unnecessary clinic rec files
        processed_count = 0
        for filename in os.listdir(base_dir):
            if filename.startswith('unnecessary_clinic_rec_') and filename.endswith('.csv'):
                # Extract department from filename
                # Format: unnecessary_clinic_rec_doctors_07_29.csv
                parts = filename.replace('unnecessary_clinic_rec_', '').replace('.csv', '').split('_')
                if len(parts) >= 2:
                    dept_name = '_'.join(parts[:-2])  # Everything except last 2 parts (date)
                    dept_name = dept_name.replace('_', ' ').title()  # Convert to proper department name
                    
                    file_path = os.path.join(base_dir, filename)
                    print(f"\n📂 Processing {filename} for {dept_name}...")
                    
                    success = self.upload_unnecessary_clinic_rec_data(file_path, dept_name)
                    if success:
                        processed_count += 1
        
        print(f"\n📊 Upload Summary: {processed_count} files processed successfully")


def main():
    """Test the unnecessary clinic rec uploader"""
    if len(sys.argv) != 3:
        print("Usage: python upload_unnecessary_clinic_rec_sheets.py <csv_file_path> <department>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    department = sys.argv[2]
    
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        sys.exit(1)
    
    uploader = UnnecessaryClinicRecUploader()
    success = uploader.upload_unnecessary_clinic_rec_data(csv_file, department)
    
    if success:
        print("✅ Unnecessary clinic rec upload completed successfully")
    else:
        print("❌ Unnecessary clinic rec upload failed")


if __name__ == "__main__":
    main() 