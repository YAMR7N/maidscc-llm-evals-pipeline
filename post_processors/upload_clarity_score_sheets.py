import pandas as pd
import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

class ClarityScoreUploader:
    def __init__(self, credentials_path='credentials.json'):
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Department to Sheet ID mapping from the extracted folder
        self.department_sheets = {
            'CC Resolvers': '167sK6mqyHYMxpUvxyFPk4fDf2ubM_S3t9gmZz7T8xxw',
            'CC Sales': '1hFknnkEbbuiyBAU2OUoAMyKp0qc9zqK3o99_Z2rECLs',
            'Delighters': '1swKfrq3kMV9-u-HLcCZRadoJffiBhndw4yv87LdIvsY',
            'Doctors': '1OZuuxlXi7c0OjWhwLbjxkHh34mZSqYXTBC-Rbo5wVAg',
            'MV Resolvers': '1AUN7_sJkFZXxhz63HM6FngRh-z3S6S5r4_D8hssAUHU',
            'MV Sales': '1xWX9BxmqqNC9q7-nBbcakeyb5kxp0sfXYVtRBu-W28k',
            'African': '1xpVYUS7Or8lPKRLM3m1_JhDWDBWg3lPC5ZD0e2--QA0',
            'Ethiopian': '1u1uZpTuEki3q8-zq86FsYw-GHccqwJShPJBuyk7SSdI',
            'Filipina': '1bC9PaP9DSicy6YqEGMPHeknhbPhNvyw-YK5GvitvFls',
        }
        
    def setup_sheets_api(self):
        """Setup Google Sheets API connection"""
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            print("✅ Google Sheets API connection established for clarity score upload")
        except Exception as e:
            print(f"❌ Error setting up Google Sheets API: {str(e)}")
    
    def convert_dept_key_to_name(self, dept_key):
        """Convert department key from filename to proper department name"""
        # Handle various department key formats
        dept_mapping = {
            'mv_resolvers': 'MV Resolvers',
            'mv_sales': 'MV Sales',
            'cc_resolvers': 'CC Resolvers', 
            'cc_sales': 'CC Sales',
            'african': 'African',
            'ethiopian': 'Ethiopian',
            'filipina': 'Filipina',
            'doctors': 'Doctors',
            'delighters': 'Delighters'
        }
        
        # Normalize the key and lookup
        normalized_key = dept_key.lower().replace(' ', '_')
        return dept_mapping.get(normalized_key, dept_key.replace('_', ' ').title())
    
    def create_new_sheet(self, sheet_id, sheet_name):
        """Create a new sheet within the spreadsheet"""
        try:
            request = {
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }
            
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': [request]}
            ).execute()
            
            print(f"✅ Created new sheet: {sheet_name}")
            return True
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"📋 Sheet '{sheet_name}' already exists")
                return True
            else:
                print(f"❌ Error creating sheet '{sheet_name}': {str(e)}")
                return False
    
    def upload_data_to_sheet(self, sheet_id, sheet_name, df):
        """Upload dataframe to specific sheet with proper data cleaning"""
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
            range_name = f"{sheet_name}!A1"
            
            # Clear the sheet first
            self.service.spreadsheets().values().clear(
                spreadsheetId=sheet_id,
                range=f"{sheet_name}!A:Z"
            ).execute()
            
            # Upload new data
            body = {
                'values': data
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"✅ Uploaded {len(data)} rows to {sheet_name}")
            return True
        except Exception as e:
            print(f"❌ Error uploading data to {sheet_name}: {str(e)}")
            return False
    
    def find_clarity_score_files(self):
        """Find all clarity score LLM output files"""
        files_found = []
        llm_outputs_dir = f"outputs/LLM_outputs/{(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')}"
        
        if not os.path.exists(llm_outputs_dir):
            print(f"⚠️  LLM outputs directory not found: {llm_outputs_dir}")
            return []
        
        for filename in os.listdir(llm_outputs_dir):
            if filename.startswith('clarity_score_') and filename.endswith('.csv'):
                filepath = os.path.join(llm_outputs_dir, filename)
                # Extract department key from filename
                dept_key = filename.replace('clarity_score_', '').replace('.csv', '').replace('_07_29', '').replace('_07_28', '').replace('_07_27', '')
                files_found.append((filepath, dept_key, filename))
                print(f"📁 Found clarity score file: {filename}")
        
        return files_found
    
    def process_all_files(self):
        """Process and upload all clarity score files to Google Sheets"""
        files = self.find_clarity_score_files()
        
        if not files:
            print("❌ No clarity score files found to upload")
            return
        
        print(f"📤 Uploading {len(files)} clarity score files to Google Sheets...")
        
        # Get yesterday's date for sheet naming
        yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        uploaded_count = 0
        
        for filepath, dept_key, filename in files:
            try:
                print(f"\n📤 Processing {filename}...")
                
                # Convert department key to proper name
                dept_name = self.convert_dept_key_to_name(dept_key)
                
                # Check if we have a sheet ID for this department
                if dept_name not in self.department_sheets:
                    print(f"⚠️  No Google Sheet found for department: {dept_name}")
                    print(f"     Available departments: {list(self.department_sheets.keys())}")
                    continue
                
                sheet_id = self.department_sheets[dept_name]
                
                # Read the CSV file
                df = pd.read_csv(filepath)
                
                if df.empty:
                    print(f"⚠️  Empty file: {filename}")
                    continue
                
                # Create new sheet with yesterday's date as name
                sheet_name = yesterday_date
                
                # Create the sheet (will do nothing if it already exists)
                if self.create_new_sheet(sheet_id, sheet_name):
                    # Upload the data
                    if self.upload_data_to_sheet(sheet_id, sheet_name, df):
                        uploaded_count += 1
                        print(f"✅ Successfully uploaded {dept_name} clarity score data")
                        print(f"   📊 Rows uploaded: {len(df)}")
                        print(f"   🔗 Sheet: {sheet_name} in {dept_name} spreadsheet")
                    else:
                        print(f"❌ Failed to upload data for {dept_name}")
                else:
                    print(f"❌ Failed to create/access sheet for {dept_name}")
                    
            except Exception as e:
                print(f"❌ Error processing {filename}: {str(e)}")
                continue
        
        print(f"\n🎉 Clarity score upload completed!")
        print(f"   Successfully uploaded: {uploaded_count}/{len(files)} files")
        print(f"   Sheet name format: {yesterday_date}")
        
        if uploaded_count < len(files):
            print(f"\n⚠️  Some uploads failed. Please check the logs above.")
            failed_count = len(files) - uploaded_count
            print(f"   Failed uploads: {failed_count}")
        
        return uploaded_count > 0 