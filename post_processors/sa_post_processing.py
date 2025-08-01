"""
Preprocessing and uploading to google sheets
"""
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class SAPreprocessor:
    def __init__(self, credentials_path='credentials.json'):
        """Initialize SA Preprocessor with Google Sheets integration"""
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # 9 Department Google Spreadsheet IDs - UPDATE WITH YOUR ACTUAL IDs
        self.department_sheets = {
            'Doctors': '1STHimb0IJ077iuBtTOwsa-GD8jStjU3SiBW7yBWom-E',
            'Delighters': '1PV0ZmobUYKHGZvHC7IfJ1t6HrJMTFi6YRbpISCouIfQ',
            'CC Sales': '1te1fbAXhURIUO0EzQ2Mrorv3a6GDtEVM_5np9TO775o',
            'CC Resolvers': '1QdmaTc5F2VUJ0Yu0kNF9d6ETnkMOlOgi18P7XlBSyHg',  # CC Department
            'Filipina': '1E5wHZKSDXQZlHIb3sV4ZWqIxvboLduzUEU0eupK7tys',
            'African': '1__KlrVjcpR8RoYfTYMYZ_EgddUSXMhK3bJO0fTGwDig',
            'Ethiopian': '1ENzdgiwUEtBSb5sHZJWs5aG8g2H62Low8doaDZf8s90',
            'MV Resolvers': '1XkVcHlkh8fEp7mmBD1Zkavdp2blBLwSABT1dE_sOf74',
            'MV Sales': '1agrl9hlBhemXkiojuWKbqiMHKUzxGgos4JSkXxw7NAk'
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

    def find_sentiment_analysis_column(self, sheet_id, sheet_name='Sheet1'):
        """Find the column number for 'Sentiment Analysis' header"""
        if not self.service:
            print("❌ Google Sheets service not available")
            return None
            
        # Try different sheet names - prioritize Data first
        sheet_names_to_try = ['Data', sheet_name, 'Main']
        
        for current_sheet_name in sheet_names_to_try:
            try:
                print(f"🔍 Looking for 'Sentiment Analysis' column in sheet: {current_sheet_name}")
                # Get the first row (header row) across a wide range
                range_name = f"{current_sheet_name}!1:1"
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=sheet_id, range=range_name).execute()
                
                values = result.get('values', [])
                
                if values and len(values) > 0:
                    header_row = values[0]
                    # Look for "Sentiment Analysis" in the header row
                    for col_idx, header in enumerate(header_row):
                        if header and "Sentiment Analysis" in str(header):
                            column_number = col_idx + 1  # Convert to 1-based indexing
                            print(f"✅ Found 'Sentiment Analysis' in column {column_number} (sheet: {current_sheet_name})")
                            return column_number, current_sheet_name
                
                print(f"🔍 'Sentiment Analysis' column not found in sheet {current_sheet_name}")
                
            except Exception as e:
                #print(f"❌ Error accessing sheet {current_sheet_name}: {str(e)}")
                pass
        
        print(f"❌ 'Sentiment Analysis' column not found in any sheet")
        return None, None

    def calculate_weighted_nps(self, nps_scores):
        """Calculate weighted average using the specified formula"""
        if not nps_scores:
            return 0
            
        # Count NPS scores 1-5
        nps_counts = {i: nps_scores.count(i) for i in range(1, 6)}
        
        # Apply weighted formula
        numerator = (nps_counts[1]*2) + (nps_counts[2]*3) + (nps_counts[3]*3) + (nps_counts[4]*4) + (nps_counts[5]*10)
        denominator = (nps_counts[1]*2) + (nps_counts[2]*1.5) + (nps_counts[3]*1) + (nps_counts[4]*1) + (nps_counts[5]*2)
        
        return numerator / denominator if denominator > 0 else 0

    def extract_nps_from_file(self, filepath):
        """Extract NPS scores from llm_output column"""
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            return []
            
        try:
            df = pd.read_csv(filepath)
            nps_scores = []
            
            if 'llm_output' not in df.columns:
                print(f"❌ Column 'llm_output' not found in {filepath}")
                return []
            
            for _, row in df.iterrows():
                try:
                    llm_output_str = str(row['llm_output'])
                    llm_output = json.loads(llm_output_str)
                    nps_score = llm_output.get('NPS_score', 0)
                    if isinstance(nps_score, int) and 1 <= nps_score <= 5:
                        nps_scores.append(nps_score)
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
                    
            print(f"✅ Extracted {len(nps_scores)} valid NPS scores from {filepath}")
            return nps_scores
            
        except Exception as e:
            print(f"❌ Error reading {filepath}: {str(e)}")
            return []

    def find_date_row(self, sheet_id, target_date, sheet_name='Sheet1'):
        """Find row with target date (2025-07-12 format) in column A"""
        if not self.service:
            print("❌ Google Sheets service not available")
            return None, None
            
        # Try different sheet names - prioritize Data first
        sheet_names_to_try = ['Data', sheet_name, 'Main']
        
        for current_sheet_name in sheet_names_to_try:
            try:
                print(f"🔍 Trying sheet: {current_sheet_name}")
                # Get all data from column A
                range_name = f"{current_sheet_name}!A:A"
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=sheet_id, range=range_name).execute()
                
                values = result.get('values', [])
                
                # Find the row with target date
                for i, row in enumerate(values):
                    if row and len(row) > 0:
                        cell_value = str(row[0]).strip()
                        if target_date in cell_value:
                            print(f"✅ Found date {target_date} in sheet {current_sheet_name}, row {i+1}")
                            return i + 1, current_sheet_name  # Return both row and sheet name
                
                print(f"🔍 Date {target_date} not found in sheet {current_sheet_name}")
                
            except Exception as e:
                #print(f"❌ Error accessing sheet {current_sheet_name}: {str(e)}")
                pass
        
        print(f"❌ Date {target_date} not found in any sheet")
        return None, None

    def update_cell_value(self, sheet_id, sheet_name, row, col, value):
        """Update a specific cell with the NPS value"""
        if not self.service:
            print("❌ Google Sheets service not available")
            return False
            
        try:
            # Convert column number to letter (1=A, 2=B, ..., 16=P, 17=Q)
            if col <= 26:
                col_letter = chr(64 + col)  # A-Z
            else:
                # For columns beyond Z (not needed here but good to have)
                first_letter = chr(64 + ((col - 1) // 26))
                second_letter = chr(64 + ((col - 1) % 26) + 1)
                col_letter = first_letter + second_letter
                
            range_name = f"{sheet_name}!{col_letter}{row}"
            
            # Update the cell
            body = {
                'values': [[round(value, 2)]]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"✅ Updated {range_name} with NPS: {round(value, 2)}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating cell: {str(e)}")
            return False

    def update_department_nps(self, department):
        """Calculate and update NPS for a single department"""
        print(f"\n📊 Processing {department}...")
        
        try:
            # 1. Generate filepath: doctors_07_14.csv format
            yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%m_%d')
            
            dept_name = department.lower().replace(' ', '_')
            # Create path with date subfolder
            yesterday = datetime.now() - timedelta(days=1)
            date_folder = yesterday.strftime('%Y-%m-%d')
            filepath = f"outputs/LLM_outputs/{date_folder}/saprompt_{dept_name}_{yesterday_date}.csv"
            
            # 2. Extract NPS scores from llm_output1 column
            nps_scores = self.extract_nps_from_file(filepath)
            if not nps_scores:
                print(f"❌ No valid NPS scores found for {department}")
                return None
            
            # 3. Calculate weighted average
            weighted_nps = self.calculate_weighted_nps(nps_scores)
            print(f"📈 Calculated weighted NPS: {weighted_nps:.2f}")
            
            # 4. Get Google Sheet info
            sheet_id = self.department_sheets.get(department)
            if not sheet_id:
                print(f"❌ Missing sheet ID for {department}")
                return weighted_nps
                
            # Find the column for 'Sentiment Analysis'
            column_result = self.find_sentiment_analysis_column(sheet_id)
            if not column_result or len(column_result) != 2:
                print(f"❌ Could not find 'Sentiment Analysis' column for {department}")
                return weighted_nps
                
            column, found_sheet_name = column_result
            if not column or not found_sheet_name:
                print(f"❌ Could not find 'Sentiment Analysis' column for {department}")
                return weighted_nps
            
            # 5. Find row with yesterday's date (2025-07-13 format)
            yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            date_row, found_sheet_name = self.find_date_row(sheet_id, yesterday_date)
            
            if not date_row or not found_sheet_name:
                print(f"❌ Could not find yesterday's date ({yesterday_date}) in {department} sheet")
                return weighted_nps
            
            # 6. Update the designated column with NPS score
            success = self.update_cell_value(sheet_id, found_sheet_name, date_row, column, weighted_nps)
            
            if success:
                print(f"✅ Successfully updated {department} sheet")
            else:
                print(f"❌ Failed to update {department} sheet")
                
            return weighted_nps
            
        except Exception as e:
            print(f"❌ Error processing {department}: {str(e)}")
            return None

    def process_all_departments(self):
        """Process all 9 departments"""
        print("🚀 Starting SA preprocessing for all departments...")
        
        if not self.service:
            print("❌ Google Sheets API not available")
            return
        
        results = {}
        success_count = 0
        
        for department in self.department_sheets.keys():
            nps = self.update_department_nps(department)
            if nps is not None:
                results[department] = nps
                success_count += 1
            else:
                results[department] = None
        
        # Print summary
        print(f"\n📈 Summary: Processed {success_count}/{len(self.department_sheets)} departments")
        print("\n📊 NPS Results:")
        for dept, nps in results.items():
            if nps is not None:
                print(f"  {dept}: {nps:.2f}")
            else:
                print(f"  {dept}: Failed")
        
        return results

def main():
    """Main function"""
    # Initialize the preprocessor
    preprocessor = SAPreprocessor()
    
    # Process all departments
    results = preprocessor.process_all_departments()
    
    print("\n✅ SA Preprocessing completed!")

if __name__ == "__main__":
    main()