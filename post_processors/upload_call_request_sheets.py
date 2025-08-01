import os
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class CallRequestUploader:
    def __init__(self, credentials_path='credentials.json'):
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Department sheets mapping - currently only MV Resolvers has a sheet
        self.department_sheets = {
            'MV Resolvers': '1uer1eNI-RhqY6jnkdpNkhUecISMNNQLGAlGaeVCWmiA',
        }
    
    def setup_sheets_api(self):
        """Initialize Google Sheets API service"""
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            print("✅ Google Sheets API initialized successfully")
        except Exception as e:
            print(f"❌ Error setting up Google Sheets API: {str(e)}")
            self.service = None
    
    def create_new_sheet(self, spreadsheet_id, sheet_name):
        """Create a new sheet in the spreadsheet"""
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
            if "already exists" in str(e).lower():
                print(f"📄 Sheet '{sheet_name}' already exists")
                return True
            else:
                print(f"❌ Error creating sheet {sheet_name}: {str(e)}")
                return False
    
    def upload_data_to_sheet(self, spreadsheet_id, sheet_name, df):
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
            
            # Prepare cleaned data for upload
            values = [cleaned_df.columns.tolist()] + cleaned_df.values.tolist()
            
            # Clear existing content first
            clear_range = f"{sheet_name}!A:Z"
            self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=clear_range
            ).execute()
            
            # Upload new data
            body = {
                'values': values
            }
            
            range_name = f"{sheet_name}!A1"
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
            print(f"❌ Error uploading data to {sheet_name}: {str(e)}")
            return False
    
    def find_call_request_files(self):
        """Find all call request LLM output files"""
        files = []
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        llm_outputs_dir = f"outputs/LLM_outputs/{date_folder}"
        
        if not os.path.exists(llm_outputs_dir):
            print(f"⚠️ LLM outputs directory not found: {llm_outputs_dir}")
            return files
        
        for filename in os.listdir(llm_outputs_dir):
            if filename.startswith('call_request_') and filename.endswith('.csv'):
                filepath = os.path.join(llm_outputs_dir, filename)
                # Extract department from filename
                dept_part = filename.replace('call_request_', '').replace('.csv', '')
                # Remove date suffix (format: _MM_DD)
                if '_' in dept_part:
                    dept_key = '_'.join(dept_part.split('_')[:-2])
                else:
                    dept_key = dept_part
                
                files.append((filepath, dept_key, filename))
                print(f"📁 Found call request file: {filename}")
        
        return files
    
    def process_all_files(self):
        """Process and upload all call request files"""
        try:
            if not self.service:
                print("❌ Google Sheets API not available")
                return
            
            files = self.find_call_request_files()
            
            if not files:
                print("ℹ️ No call request files found to upload")
                return
            
            yesterday = datetime.now() - timedelta(days=1)
            sheet_name = yesterday.strftime('%Y-%m-%d')
            
            successful_uploads = 0
            
            for filepath, dept_key, filename in files:
                try:
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
                    
                    print(f"\n📤 Processing {dept_name}...")
                    
                    # Check if we have a sheet for this department
                    if dept_name not in self.department_sheets:
                        print(f"⚠️ No Google Sheet configured for {dept_name}")
                        print(f"   Available departments: {list(self.department_sheets.keys())}")
                        continue
                    
                    spreadsheet_id = self.department_sheets[dept_name]
                    
                    # Read the data
                    df = pd.read_csv(filepath)
                    print(f"📊 Found {len(df)} records for {dept_name}")
                    
                    if len(df) == 0:
                        print(f"⚠️ No data to upload for {dept_name}")
                        continue
                    
                    # Create new sheet if needed
                    if self.create_new_sheet(spreadsheet_id, sheet_name):
                        # Upload the data
                        if self.upload_data_to_sheet(spreadsheet_id, sheet_name, df):
                            successful_uploads += 1
                            print(f"✅ Successfully uploaded {dept_name} call request data")
                        else:
                            print(f"❌ Failed to upload {dept_name} data")
                    else:
                        print(f"❌ Failed to create/access sheet for {dept_name}")
                        
                except Exception as e:
                    print(f"❌ Error processing {filename}: {str(e)}")
                    continue
            
            print(f"\n📈 Upload Summary:")
            print(f"✅ Successfully uploaded: {successful_uploads}/{len(files)} departments")
            
            if successful_uploads > 0:
                print(f"📅 All data uploaded to sheets named: {sheet_name}")
            
        except Exception as e:
            print(f"❌ Error in call request upload process: {str(e)}")

# For backwards compatibility and direct execution
def main():
    uploader = CallRequestUploader()
    uploader.process_all_files()

if __name__ == "__main__":
    main() 