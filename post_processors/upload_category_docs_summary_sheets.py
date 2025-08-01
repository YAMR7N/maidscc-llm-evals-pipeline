import os
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class CategoryDocsSummaryUploader:
    def __init__(self, credentials_path='credentials.json'):
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # This uploader uses the same sheet ID as the main category docs uploader
        self.category_docs_sheet_id = '1OfEAXeSIbcQu9a9zW3KlZIR8qmhSrr2oUOkRV3LxUDU'
    
    def setup_sheets_api(self):
        """Initialize Google Sheets API service"""
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            print("✅ Google Sheets API initialized for category docs summary upload")
        except Exception as e:
            print(f"❌ Error setting up Google Sheets API: {str(e)}")
            self.service = None
    
    def create_sheet(self, spreadsheet_id, sheet_name):
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
            
            print(f"✅ Created new summary sheet: {sheet_name}")
            return True
            
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"📄 Summary sheet '{sheet_name}' already exists")
                return True
            else:
                print(f"❌ Error creating summary sheet {sheet_name}: {str(e)}")
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
            print(f"✅ Uploaded {rows_updated} rows to summary sheet {sheet_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error uploading data to summary sheet {sheet_name}: {str(e)}")
            return False
    
    def find_category_docs_summary_files(self):
        """Find all category docs summary files"""
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        summary_dir = f"outputs/category_docs/{date_folder}"
        
        if not os.path.exists(summary_dir):
            print(f"⚠️ Summary directory not found: {summary_dir}")
            return []
        
        summary_files = []
        for filename in os.listdir(summary_dir):
            if filename.endswith('_Category_Docs_Summary.csv'):
                filepath = os.path.join(summary_dir, filename)
                # Extract department from filename
                dept_name = filename.replace('_Category_Docs_Summary.csv', '')
                summary_files.append((filepath, dept_name, filename))
        
        return summary_files
    
    def process_all_files(self):
        """Process and upload all category docs summary files"""
        try:
            if not self.service:
                print("❌ Google Sheets API not available")
                return
            
            files = self.find_category_docs_summary_files()
            
            if not files:
                print("ℹ️ No category docs summary files found to upload")
                return
            
            print(f"🚀 Starting category docs summary upload to Google Sheets...")
            print(f"📁 Found {len(files)} summary file(s)")
            
            yesterday = datetime.now() - timedelta(days=1)
            summary_sheet_name = f"{yesterday.strftime('%Y-%m-%d')} summary"
            
            success_count = 0
            
            for filepath, dept_name, filename in files:
                try:
                    print(f"\n📊 Processing summary file: {filename}")
                    
                    # Read the summary CSV
                    df = pd.read_csv(filepath)
                    print(f"📊 Found {len(df)} category summaries for {dept_name}")
                    
                    # Ensure the summary sheet exists
                    self.create_sheet(self.category_docs_sheet_id, summary_sheet_name)
                    
                    # Add department header to the data
                    department_header = pd.DataFrame([[f"=== {dept_name} Category Analysis ==="]], columns=['Summary'])
                    empty_row = pd.DataFrame([[""]], columns=['Summary'])
                    
                    # Combine department header, empty row, and summary data
                    upload_df = pd.concat([department_header, empty_row, df], ignore_index=True)
                    
                    # Upload to the summary sheet (append mode for multiple departments)
                    if success_count == 0:
                        # First department - clear and upload
                        self.upload_to_sheet(self.category_docs_sheet_id, summary_sheet_name, upload_df)
                    else:
                        # Subsequent departments - append
                        self.append_to_sheet(self.category_docs_sheet_id, summary_sheet_name, upload_df)
                    
                    print(f"✅ Successfully uploaded {dept_name} category docs summary")
                    print(f"   📄 Sheet: {summary_sheet_name}")
                    print(f"   📊 Categories: {len(df)}")
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"❌ Error uploading {filename}: {str(e)}")
                    continue
            
            print(f"\n📈 Upload Summary:")
            print(f"✅ Successfully uploaded: {success_count}/{len(files)} files")
            if success_count > 0:
                print(f"📄 All summaries uploaded to sheet: {summary_sheet_name}")
                print(f"🔗 Sheet URL: https://docs.google.com/spreadsheets/d/{self.category_docs_sheet_id}")
            
        except Exception as e:
            print(f"❌ Error in category docs summary upload process: {str(e)}")
    
    def append_to_sheet(self, spreadsheet_id, sheet_name, df):
        """Append DataFrame to existing sheet data"""
        try:
            def clean_cell_value(value):
                """Clean cell values to prevent JSON parsing errors"""
                if pd.isna(value):
                    return ""
                value_str = str(value)
                value_str = value_str.replace('\r\n', '\n').replace('\r', '\n')
                if len(value_str) > 50000:
                    value_str = value_str[:50000] + "..."
                return value_str
            
            # Clean the DataFrame
            cleaned_df = df.copy()
            for column in cleaned_df.columns:
                cleaned_df[column] = cleaned_df[column].apply(clean_cell_value)
            
            # Prepare data (no headers for append)
            values = cleaned_df.values.tolist()
            
            # Append data to the sheet
            range_name = f"{sheet_name}!A:A"  # This will append to the end
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            print(f"✅ Appended {len(values)} rows to summary sheet")
            return True
            
        except Exception as e:
            print(f"❌ Error appending data to summary sheet: {str(e)}")
            return False 