#!/usr/bin/env python3
"""
Upload Policy Escalation CSV files to Google Spreadsheets
- Main Policy Escalation sheet gets one tab: yyyy-mm-dd (LLM outputs)
- Calculates policy escalation metric but doesn't post it anywhere for now
"""

import pandas as pd
import os
import json
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class PolicyEscalationUploader:
    def __init__(self, credentials_path='credentials.json'):
        """Initialize Policy Escalation Uploader with Google Sheets integration"""
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Policy Escalation sheet IDs by department
        self.policy_escalation_sheet_ids = {
            'mv_resolvers': '1Fv6IzSYEAoLQhfPlFMPUb8mwNP9B723lUDv9dJHODSs',
            'doctors': '1JbZOR18qYmFah-ByM0227clI0_22wfmHwymYR6zwWAE'
        }
        
        # Will be set based on files found
        self.policy_escalation_sheet_id = None

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
    
    def clean_cell_value(self, value):
        """Clean cell values to prevent JSON parsing errors"""
        if pd.isna(value):
            return ""
        value_str = str(value)
        # Normalize line breaks
        value_str = value_str.replace('\r\n', '\n').replace('\r', '\n')
        # Truncate very long values that might cause issues
        if len(value_str) > 50000:  # Google Sheets cell limit
            value_str = value_str[:50000] + "..."
        return value_str
    
    def upload_dataframe_to_sheet(self, df, spreadsheet_id, sheet_name, append=False):
        """Upload a pandas DataFrame to a specific sheet"""
        try:
            # Clean the DataFrame before converting to values
            cleaned_df = df.copy()
            for column in cleaned_df.columns:
                cleaned_df[column] = cleaned_df[column].apply(self.clean_cell_value)
            
            # Prepare cleaned data for upload
            values = [cleaned_df.columns.tolist()] + cleaned_df.values.tolist()
            
            if append:
                # Append to existing data
                range_name = f"{sheet_name}!A:A"
                result = self.service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    insertDataOption='INSERT_ROWS',
                    body={'values': values[1:]}  # Skip headers when appending
                ).execute()
                print(f"✅ Appended {len(values)-1} rows to {sheet_name}")
            else:
                # Clear existing content first
                clear_range = f"{sheet_name}!A:Z"
                self.service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range=clear_range
                ).execute()
                
                # Upload new data
                range_name = f"{sheet_name}!A1"
                body = {
                    'values': values
                }
                
                result = self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    body=body
                ).execute()
                
                rows_updated = result.get('updatedRows', 0)
                print(f"✅ Uploaded {rows_updated} rows to {sheet_name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error uploading DataFrame to {sheet_name}: {str(e)}")
            return False
    
    def process_frequency_analysis(self, date_folder, date_str):
        """Process and upload policy frequency analysis to summary sheet"""
        try:
            print(f"\n📊 Processing Policy Frequency Analysis for summary sheet...")
            
            # Check if frequency analysis files exist
            analysis_dir = f"outputs/policy_escalation/{date_folder}"
            if not os.path.exists(analysis_dir):
                print(f"⚠️ Policy frequency analysis directory not found: {analysis_dir}")
                return
            
            # Find frequency analysis files
            frequency_files = []
            for filename in os.listdir(analysis_dir):
                if filename.endswith('_Policy_Frequency_Analysis.csv'):
                    filepath = os.path.join(analysis_dir, filename)
                    # Extract department from filename
                    dept_name = filename.replace('_Policy_Frequency_Analysis.csv', '')
                    frequency_files.append((filepath, dept_name))
            
            if not frequency_files:
                print("ℹ️ No policy frequency analysis files found to upload")
                return
            
            # Create summary sheet name
            summary_sheet_name = f"{date_folder}-summary"
            
            # Create the summary sheet
            if not self.create_new_sheet(self.policy_escalation_sheet_id, summary_sheet_name):
                return
            
            first_upload = True
            success_count = 0
            
            for filepath, dept_name in frequency_files:
                try:
                    print(f"   📁 Processing frequency analysis for {dept_name}...")
                    
                    # Read the frequency analysis CSV
                    df = pd.read_csv(filepath)
                    print(f"   📊 Found {len(df)} policy entries for {dept_name}")
                    
                    # Upload to the summary sheet
                    if first_upload:
                        # First department - clear and upload
                        self.upload_dataframe_to_sheet(df, self.policy_escalation_sheet_id, summary_sheet_name)
                        first_upload = False
                    else:
                        # Subsequent departments - append without headers
                        self.upload_dataframe_to_sheet(df, self.policy_escalation_sheet_id, summary_sheet_name, append=True)
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"   ❌ Error processing {dept_name}: {str(e)}")
                    continue
            
            if success_count > 0:
                print(f"✅ Successfully uploaded {success_count} frequency analyses to summary sheet: {summary_sheet_name}")
            
        except Exception as e:
            print(f"❌ Error in frequency analysis processing: {str(e)}")

    def process_all_files(self):
        """Process all Policy Escalation files and upload to Google Sheets"""
        if not self.service:
            print("❌ Google Sheets API not available")
            return False
        
        print(f"🚀 Starting Policy Escalation data upload to Google Sheets...")
        
        # Get yesterday's date for file naming
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        date_str = yesterday.strftime('%m_%d')
        sheet_name = date_folder  # Use yyyy-mm-dd format for sheet name
        
        # Look for Policy Escalation LLM output files (use raw LLM outputs, not processed ones)
        llm_outputs_dir = f"outputs/LLM_outputs/{date_folder}"
        
        if not os.path.exists(llm_outputs_dir):
            print(f"❌ LLM outputs directory not found: {llm_outputs_dir}")
            return False
        
        # Find Policy Escalation LLM output files
        policy_escalation_files = []
        for filename in os.listdir(llm_outputs_dir):
            if filename.startswith('policy_escalation_') and filename.endswith(f'_{date_str}.csv'):
                filepath = os.path.join(llm_outputs_dir, filename)
                policy_escalation_files.append(filepath)
        
        if not policy_escalation_files:
            print(f"❌ No Policy Escalation files found in {llm_outputs_dir}")
            return False
        
        # Process each file and upload to separate sheets
        success_count = 0
        uploaded_departments = []  # Track which departments were uploaded for summary
        
        for filepath in policy_escalation_files:
            filename = os.path.basename(filepath)
            print(f"📁 Processing Policy Escalation file: {filename}")
            
            # Determine department and sheet ID for this specific file
            department_key = None
            if 'doctors' in filename.lower():
                department_key = 'doctors'
            elif 'mv_resolvers' in filename.lower():
                department_key = 'mv_resolvers'
            
            if not department_key or department_key not in self.policy_escalation_sheet_ids:
                print(f"⚠️ Could not determine department for file: {filename}")
                continue
                
            # Set the sheet ID for this specific file
            current_sheet_id = self.policy_escalation_sheet_ids[department_key]
            print(f"✅ Using sheet ID for {department_key}: {current_sheet_id}")
            
            # Extract department name for display
            import re
            dept_match = re.match(r'policy_escalation_(.+)_\d{2}_\d{2}\.csv$', filename)
            if dept_match:
                dept_key = dept_match.group(1)
                # Convert to proper department name
                dept_name = dept_key.replace('_', ' ').title()
                if dept_name == 'Mv Resolvers':
                    dept_name = 'MV Resolvers'
                elif dept_name == 'Mv Sales':
                    dept_name = 'MV Sales'
                elif dept_name == 'Cc Sales':
                    dept_name = 'CC Sales'
                elif dept_name == 'Cc Resolvers':
                    dept_name = 'CC Resolvers'
            
            # Always use only date for sheet name (yyyy-mm-dd format)
            dept_sheet_name = sheet_name
            
            # Create new sheet
            if self.create_new_sheet(current_sheet_id, dept_sheet_name):
                # Upload data
                if self.upload_data_to_sheet(filepath, current_sheet_id, dept_sheet_name):
                    print(f"✅ Successfully uploaded Policy Escalation data for {dept_name} to sheet {dept_sheet_name}")
                    success_count += 1
                    uploaded_departments.append((department_key, current_sheet_id))
        
        if success_count > 0:
            print(f"✅ Successfully uploaded {success_count} Policy Escalation files")
            
            # Process frequency analysis for each uploaded department
            for dept_key, sheet_id in uploaded_departments:
                self.policy_escalation_sheet_id = sheet_id  # Set for this department's summary
                print(f"\n📊 Processing frequency analysis for {dept_key}...")
                self.process_frequency_analysis(date_folder, date_str)
                print(f"📋 {dept_key.title()} Sheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
            
            return True
        else:
            print(f"❌ No files were successfully uploaded")
            return False


def main():
    """Main function for standalone execution"""
    uploader = PolicyEscalationUploader()
    uploader.process_all_files()


if __name__ == "__main__":
    main() 