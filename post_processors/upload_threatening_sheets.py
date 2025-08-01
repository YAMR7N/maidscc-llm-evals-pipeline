import pandas as pd
import os
import glob
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError

class ThreateningUploader:
    def __init__(self, credentials_path='credentials.json'):
        """Initialize the threatening uploader with Google Sheets API"""
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Department to Google Sheet ID mapping
        self.department_sheets = {
            'MV Resolvers': '1ulcfC7Z748YQbX-gH3kBCHxKfcz88ZJPevR28mSgBug',
        }
    
    def setup_sheets_api(self):
        """Setup Google Sheets API connection"""
        try:
            if os.path.exists(self.credentials_path):
                SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
                creds = Credentials.from_service_account_file(self.credentials_path, scopes=SCOPES)
                self.service = build('sheets', 'v4', credentials=creds)
                print("✅ Google Sheets API initialized for threatening upload")
            else:
                print(f"❌ Credentials file not found: {self.credentials_path}")
        except Exception as e:
            print(f"❌ Error setting up Google Sheets API: {str(e)}")
            self.service = None

    def get_department_name_from_filename(self, filename):
        """Extract and normalize department name from filename"""
        # threatening_mv_resolvers_07_28.csv -> mv_resolvers
        parts = filename.replace('.csv', '').split('_')
        if len(parts) >= 4 and parts[0] == 'threatening':
            dept_key = '_'.join(parts[1:-2])  # Everything between 'threatening_' and '_MM_DD'
            
            # Convert to proper department name
            dept_name = dept_key.replace('_', ' ').title()
            
            # Handle specific mappings
            if dept_name == 'Mv Resolvers':
                return 'MV Resolvers'
            elif dept_name == 'Mv Sales':
                return 'MV Sales'  
            elif dept_name == 'Cc Sales':
                return 'CC Sales'
            elif dept_name == 'Cc Resolvers':
                return 'CC Resolvers'
            else:
                return dept_name
        
        return None

    def create_sheet_if_not_exists(self, spreadsheet_id, sheet_name):
        """Create a new sheet if it doesn't exist"""
        try:
            # Get current sheets
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
            
            if sheet_name not in existing_sheets:
                print(f"📄 Creating new sheet: {sheet_name}")
                request = {
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }
                
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': [request]}
                ).execute()
                
                return True
            else:
                print(f"📄 Sheet '{sheet_name}' already exists")
                return True
                
        except Exception as e:
            print(f"❌ Error creating sheet {sheet_name}: {str(e)}")
            return False

    def upload_to_sheet(self, spreadsheet_id, sheet_name, df):
        """Upload DataFrame to Google Sheet with proper data cleaning"""
        try:
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
            cleaned_df = df.copy()
            for column in cleaned_df.columns:
                cleaned_df[column] = cleaned_df[column].apply(clean_cell_value)
            
            # Prepare cleaned data for upload (convert to list of lists)
            values = [cleaned_df.columns.tolist()] + cleaned_df.values.tolist()
            
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
            
        except HttpError as e:
            print(f"❌ HTTP Error uploading to {sheet_name}: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Error uploading to {sheet_name}: {str(e)}")
            return False

    def process_threatening_file(self, filepath):
        """Process a single threatening file and upload to appropriate sheet"""
        try:
            filename = os.path.basename(filepath)
            print(f"\n📊 Processing threatening file: {filename}")
            
            # Get department name
            dept_name = self.get_department_name_from_filename(filename)
            if not dept_name:
                print(f"❌ Could not extract department from filename: {filename}")
                return False
            
            # Check if we have a sheet for this department
            if dept_name not in self.department_sheets:
                print(f"⚠️ No Google Sheet configured for department: {dept_name}")
                print(f"💡 Please add {dept_name} to the department_sheets mapping")
                return False
            
            spreadsheet_id = self.department_sheets[dept_name]
            
            # Load the data
            df = pd.read_csv(filepath)
            if df.empty:
                print(f"⚠️ Empty file: {filename}")
                return False
            
            # Filter to only include the columns we want to upload
            columns_to_upload = ['conversation_id', 'conversation', 'llm_output']
            df_filtered = df[columns_to_upload].copy()
            
            # Create sheet name with yesterday's date
            yesterday = datetime.now() - timedelta(days=1)
            sheet_name = yesterday.strftime('%Y-%m-%d')
            
            # Create sheet if needed and upload
            if self.create_sheet_if_not_exists(spreadsheet_id, sheet_name):
                success = self.upload_to_sheet(spreadsheet_id, sheet_name, df_filtered)
                if success:
                    print(f"✅ Successfully uploaded {dept_name} threatening data to Google Sheets")
                    print(f"   📄 Sheet: {sheet_name}")
                    print(f"   📊 Rows: {len(df_filtered)}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error processing threatening file {filepath}: {str(e)}")
            return False

    def find_threatening_files(self):
        """Find all threatening LLM output files for yesterday"""
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        date_str = yesterday.strftime('%m_%d')
        
        # Look for threatening files
        pattern = f"outputs/LLM_outputs/{date_folder}/threatening_*_{date_str}.csv"
        files = glob.glob(pattern)
        
        print(f"🔍 Looking for threatening files in: {pattern}")
        print(f"📁 Found {len(files)} threatening file(s)")
        
        return files

    def process_all_files(self):
        """Process all threatening files and upload to Google Sheets"""
        if not self.service:
            print("❌ Google Sheets API not available")
            return False
        
        print("🚀 Starting threatening data upload to Google Sheets...")
        
        files = self.find_threatening_files()
        
        if not files:
            print("📝 No threatening files found to upload")
            return True
        
        success_count = 0
        total_files = len(files)
        
        for filepath in files:
            if self.process_threatening_file(filepath):
                success_count += 1
        
        print(f"\n📈 Upload Summary:")
        print(f"✅ Successfully uploaded: {success_count}/{total_files} files")
        
        if success_count < total_files:
            print(f"⚠️ Failed uploads: {total_files - success_count}")
        
        return success_count > 0 