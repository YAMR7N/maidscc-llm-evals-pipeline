#!/usr/bin/env python3
"""
Upload rule breaking CSV files to individual department Google Spreadsheets
Each department gets two sheets: yyyy-mm-dd (report) and yyyy-mm-dd-RAW (raw data)
"""

import pandas as pd
import os
import re
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class RuleBreakingUploader:
    def __init__(self, credentials_path='credentials.json'):
        """Initialize Rule Breaking Uploader with Google Sheets integration"""
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Department sheet IDs extracted from Google Drive folder
        # https://drive.google.com/drive/u/8/folders/1RyWc64eQtIBSMpTBQeNT3odcQZ4Z5b-a
        self.department_sheets = {
            'Doctors': '1V2d9vw_VFcAdTlLtkXRTpi4xJupLHQhsMvrTRtKSjgI',
            'MV Sales': '1vLLhy31Mu28aWOXtRoWMwpGHwIvalcReUO4C-zIGm7Q',
            'MV Resolvers': '1jNZeBGOjz6MUevrbadTBxRUb3OJ8PN1Kh1NHNeotNsM',
            'CC Sales': '1iqVKp4O6Tp4C4_Humy88FAQPlCJgQncS59Foxa1fiSo',
            'Ethiopian': '1AkPaP_Z6qtlHYzXCScUmMxuf9Jxm0nXvYYaTJtB7lcQ',
            'African': '1I4pglnJ9HFEsWXi_IDXc4I8-L55WZgLtn-LXf01IAwU',
            'Filipina': '1ADrFeuqrq9O6quOCcjdkseiWU1H2q5a13_Gxri1mUao',
            'Delighters': '1Zjvd2tGbs7ibmOv8V62Y6sYlL_INu5IgvVRR-Q5Nnq4',
            'CC Resolvers': '19GiEzoFz81sZ1rRYHkvabh_yNvtEndhnjtFDvmKt_bM'
        }
        
        # Rule breaking file prefix to department mapping (updated for actual file names)
        self.prefix_to_department = {
            'doc': 'Doctors',
            'doctors': 'Doctors',
            'ccs': 'CC Sales',
            'cc': 'CC Sales',  # Handle both cc and ccs
            'cc_sales': 'CC Sales',
            'mvr': 'MV Resolvers', 
            'mv_resolvers': 'MV Resolvers',
            'mv': 'MV Resolvers',  # Handle generic mv prefix
            'mvs': 'MV Sales',
            'mv_sales': 'MV Sales',
            'african': 'African',
            'ethiopian': 'Ethiopian', 
            'filipina': 'Filipina',
            'cc_resolvers': 'CC Resolvers',
            'delighters': 'Delighters'
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

    def find_rule_breaking_files(self):
        """Find rule breaking files and their corresponding reports"""
        # Look in yesterday's date subfolder
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        output_dir = f"outputs/LLM_outputs/{date_folder}"
        report_dir = f"outputs/rule_breaking/{date_folder}"
        
        if not os.path.exists(output_dir):
            print(f"❌ Output directory not found: {output_dir}")
            return []
            
        if not os.path.exists(report_dir):
            print(f"❌ Report directory not found: {report_dir}")
            return []
        
        # Get yesterday's date in mm_dd format
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.strftime('%m_%d')
        
        print(f"🔍 Looking for rule breaking files with date: {target_date}")
        
        file_pairs = []
        
        # Find all rule breaking raw files
        for filename in os.listdir(output_dir):
            if filename.startswith('rule_breaking_') and filename.endswith('.csv'):
                if target_date in filename:
                    # Parse filename: rule_breaking_{dept_key}_{mm}_{dd}.csv
                    # Remove rule_breaking_ prefix and .csv suffix
                    name_part = filename[14:-4]  # Remove 'rule_breaking_' and '.csv'
                    
                    # Split by underscores and reconstruct department key
                    parts = name_part.split('_')
                    if len(parts) >= 3:
                        # Last two parts are mm_dd, everything before is department key
                        dept_key_parts = parts[:-2]
                        dept_key = '_'.join(dept_key_parts)
                        
                        # Try to find department by full key first, then by parts
                        department = self.prefix_to_department.get(dept_key)
                        if not department:
                            # If full key doesn't work, try just the first part as prefix
                            prefix = dept_key_parts[0]
                            department = self.prefix_to_department.get(prefix)
                        
                        if not department:
                            print(f"⚠️  Unknown department key '{dept_key}' (prefix: '{dept_key_parts[0]}') in {filename}, skipping")
                            continue
                        
                        print(f"📁 Matched {filename} -> Department key: '{dept_key}' -> {department}")
                        
                        # Find corresponding report file
                        report_filename = f"{department}_Rule_Breaking_Summary.csv"
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
                # Use much lower limit to avoid Google Sheets issues
                if len(value_str) > 30000:  # Safer limit for Google Sheets
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

    def process_all_files(self):
        """Process all rule breaking files and upload to Google Sheets"""
        if not self.service:
            print("❌ Google Sheets API not available")
            return
        
        print(f"🚀 Starting rule breaking data upload to Google Sheets...")
        
        # Find all rule breaking file pairs
        file_pairs = self.find_rule_breaking_files()
        
        if not file_pairs:
            print("❌ No rule breaking file pairs found for yesterday's date")
            return
        
        print(f"📁 Found {len(file_pairs)} department file pairs to upload")
        
        success_count = 0
        
        for file_data in file_pairs:
            department = file_data['department']
            raw_file = file_data['raw_file']
            report_file = file_data['report_file']
            date_str = file_data['date_str']
            
            try:
                # Get spreadsheet ID for this department
                spreadsheet_id = self.department_sheets.get(department)
                if not spreadsheet_id:
                    print(f"❌ No spreadsheet ID found for department: {department}")
                    continue
                
                # Create sheet names
                report_sheet_name = self.create_sheet_name(date_str, is_raw=False)
                raw_sheet_name = self.create_sheet_name(date_str, is_raw=True)
                
                print(f"\n📊 Processing {department}:")
                print(f"  📋 Report: {os.path.basename(report_file)} -> {report_sheet_name}")
                print(f"  📄 Raw: {os.path.basename(raw_file)} -> {raw_sheet_name}")
                
                success = True
                
                # Create and upload report sheet
                if self.create_new_sheet(spreadsheet_id, report_sheet_name):
                    if not self.upload_data_to_sheet(report_file, spreadsheet_id, report_sheet_name, is_report=True):
                        success = False
                else:
                    success = False
                
                # Create and upload raw data sheet
                if self.create_new_sheet(spreadsheet_id, raw_sheet_name):
                    if not self.upload_data_to_sheet(raw_file, spreadsheet_id, raw_sheet_name, is_report=False):
                        success = False
                else:
                    success = False
                
                if success:
                    success_count += 1
                    print(f"✅ Successfully uploaded {department} data")
                    print(f"📋 Spreadsheet URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
                else:
                    print(f"❌ Failed to upload {department} data")
                    
            except Exception as e:
                print(f"❌ Error processing {department}: {str(e)}")
        
        # Print summary
        print(f"\n📈 Upload Summary:")
        print(f"✅ Successfully uploaded: {success_count}/{len(file_pairs)} departments")
        
        # Show departments without data (for future-proofing info)
        uploaded_depts = {file_data['department'] for file_data in file_pairs}
        all_depts = set(self.department_sheets.keys())
        missing_depts = all_depts - uploaded_depts
        
        if missing_depts:
            print(f"\nℹ️  Departments without rule breaking data: {', '.join(sorted(missing_depts))}")

def main():
    """Main function"""
    uploader = RuleBreakingUploader()
    uploader.process_all_files()
    print("\n✅ Rule breaking data upload completed!")

if __name__ == "__main__":
    main()
