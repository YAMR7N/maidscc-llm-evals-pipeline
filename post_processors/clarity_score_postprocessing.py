import pandas as pd
import json
import os
import re
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

class ClarityScoreProcessor:
    def __init__(self, credentials_path='credentials.json'):
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Yesterday's date for processing
        yesterday = datetime.now() - timedelta(days=1)
        self.clarity_score_dir = f"outputs/clarity_score/{yesterday.strftime('%Y-%m-%d')}"
        os.makedirs(self.clarity_score_dir, exist_ok=True)
        
        # Department snapshot sheet IDs for metric updates
        self.department_sheets = {
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
        """Setup Google Sheets API connection"""
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            print("✅ Google Sheets API connection established")
        except Exception as e:
            print(f"❌ Error setting up Google Sheets API: {str(e)}")
    
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
                # Remove prefix and extension
                dept_key = filename.replace('clarity_score_', '').replace('.csv', '')
                # Remove date suffixes (format: _MM_DD or_08_05)
                dept_key = re.sub(r'_\d{2}_\d{2}$', '', dept_key)
                files_found.append((filepath, dept_key, filename))
                print(f"📁 Found clarity score file: {filename}")
        
        return files_found
    
    def safe_json_parse(self, json_str):
        """Safely parse JSON with fallback handling"""
        if not json_str or pd.isna(json_str):
            return None
        
        # Clean the string
        json_str = str(json_str).strip()
        if not json_str:
            return None
        
        # Handle JSON wrapped in markdown code blocks
        if '```json' in json_str and '```' in json_str[json_str.find('```json') + 7:]:
            # Extract JSON from markdown code block with newlines
            start_idx = json_str.find('```json') + 7
            end_idx = json_str.find('```', start_idx)
            if end_idx != -1:
                json_str = json_str[start_idx:end_idx].strip()
        elif json_str.startswith('```') and '```' in json_str[3:]:
            # Extract JSON from generic code block
            start_idx = 3
            end_idx = json_str.find('```', start_idx)
            if end_idx != -1:
                json_str = json_str[start_idx:end_idx].strip()
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to fix common JSON issues
            try:
                # Remove extra whitespace and newlines
                cleaned = ' '.join(json_str.split())
                return json.loads(cleaned)
            except:
                print(f"⚠️  Failed to parse JSON: {json_str[:100]}...")
                return None
    
    def calculate_clarity_score_percentage(self, filepath):
        """Calculate clarity score percentage from LLM outputs"""
        try:
            df = pd.read_csv(filepath)
            
            if 'llm_output' not in df.columns:
                print(f"❌ No llm_output column found in {filepath}")
                return None
            
            total_conversations = len(df)
            valid_responses = 0
            total_messages = 0
            total_clarifications = 0
            
            for _, row in df.iterrows():
                parsed_json = self.safe_json_parse(row['llm_output'])
                
                if parsed_json and isinstance(parsed_json, dict):
                    if 'Total' in parsed_json and 'ClarificationMessages' in parsed_json:
                        try:
                            total = int(parsed_json['Total'])
                            clarifications = int(parsed_json['ClarificationMessages'])
                            
                            if total > 0:  # Valid conversation
                                total_messages += total
                                total_clarifications += clarifications
                                valid_responses += 1
                        except (ValueError, TypeError):
                            continue
            
            if total_messages == 0:
                print(f"⚠️  No valid clarity data found in {filepath}")
                return 0.0
            
            # Calculate clarification percentage: (clarification messages / total messages) * 100
            clarification_percentage = (total_clarifications / total_messages) * 100
            
            print(f"📊 Clarity Score Calculation:")
            print(f"   Total conversations analyzed: {valid_responses}/{total_conversations}")
            print(f"   Total customer messages: {total_messages}")
            print(f"   Clarification requests: {total_clarifications}")
            print(f"   Clarification percentage: {clarification_percentage:.1f}%")
            
            return round(clarification_percentage, 1)
            
        except Exception as e:
            print(f"❌ Error calculating clarity score for {filepath}: {str(e)}")
            return None
    
    def convert_dept_key_to_name(self, dept_key):
        """Convert department key to proper display name"""
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
        
        # Normalize the key
        normalized_key = dept_key.lower().replace(' ', '_')
        return dept_mapping.get(normalized_key, dept_key.replace('_', ' ').title())
    
    def save_summary_report(self, percentage, dept_name):
        """Save individual department clarification percentage summary"""
        summary_data = {
            'Department': [dept_name],
            'Clarification Percentage (%)': [percentage],
            'Date': [(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_filename = f"{self.clarity_score_dir}/{dept_name}_Clarity_Score_Summary.csv"
        summary_df.to_csv(summary_filename, index=False)
        
        print(f"💾 Saved clarification percentage summary: {summary_filename}")
        return summary_filename
    
    def find_column_by_name(self, sheet_id, column_name, sheet_name='Data'):
        """Find column index by name in Google Sheet"""
        try:
            range_name = f"{sheet_name}!1:1"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id, range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return None
            
            headers = values[0]
            for i, header in enumerate(headers):
                if header == column_name:
                    return i + 1  # Return 1-based index
            
            return None
        except Exception as e:
            print(f"❌ Error finding column '{column_name}': {str(e)}")
            return None
    
    def find_date_row(self, sheet_id, target_date, sheet_name='Data'):
        """Find row index for a specific date in Google Sheet"""
        try:
            range_name = f"{sheet_name}!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id, range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return None
            
            for i, row in enumerate(values):
                if row and len(row) > 0:
                    cell_value = str(row[0]).strip()
                    if cell_value == target_date:
                        return i + 1  # Return 1-based index
            
            return None
        except Exception as e:
            print(f"❌ Error finding date row for '{target_date}': {str(e)}")
            return None
    
    def update_cell_value(self, sheet_id, sheet_name, row, col, value):
        """Update a specific cell value in Google Sheet"""
        try:
            # Convert column number to letter
            col_letter = chr(ord('A') + col - 1) if col <= 26 else f"A{chr(ord('A') + col - 27)}"
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
            
            print(f"✅ Updated {range_name} with value: {value}")
            return True
        except Exception as e:
            print(f"❌ Error updating cell {sheet_name}!{col_letter}{row}: {str(e)}")
            return False
    
    def update_snapshot_sheet(self, percentage, dept_key):
        """Update clarification percentage in department snapshot sheet for yesterday's date"""
        try:
            # Get department sheet ID
            if dept_key not in self.department_sheets:
                print(f"❌ No snapshot sheet configured for department: {dept_key}")
                return False
                
            sheet_id = self.department_sheets[dept_key]
            yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Find the "Clarity Score" column
            clarity_col = self.find_column_by_name(sheet_id, "Clarity Score")
            if not clarity_col:
                print(f"⚠️  Could not find 'Clarity Score' column in {dept_key} snapshot sheet")
                print(f"   Please manually add a 'Clarity Score' column to the {dept_key} snapshot sheet")
                return False
            
            # Find yesterday's date row
            date_row = self.find_date_row(sheet_id, yesterday_date)
            if not date_row:
                print(f"⚠️  Could not find date {yesterday_date} in {dept_key} snapshot sheet")
                return False
            
            # Update the cell
            success = self.update_cell_value(
                sheet_id, 
                'Data', 
                date_row, 
                clarity_col, 
                f"{percentage}%"
            )
            
            if success:
                print(f"📊 Updated {dept_key} snapshot sheet with clarification percentage: {percentage}% for {yesterday_date}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error updating {dept_key} snapshot sheet: {str(e)}")
            return False
    
    def process_all_files(self):
        """Process all clarity score files and update metrics"""
        files = self.find_clarity_score_files()
        
        if not files:
            print("❌ No clarity score files found to process")
            return
        
        print(f"📊 Processing {len(files)} clarity score files...")
        
        processed_count = 0
        success_count = 0
        
        for filepath, dept_key, filename in files:
            try:
                print(f"\n📊 Processing {filename}...")
                
                # Calculate clarification percentage for this department
                clarification_percentage = self.calculate_clarity_score_percentage(filepath)
                
                if clarification_percentage is not None:
                    # Convert department key to proper name
                    dept_name = self.convert_dept_key_to_name(dept_key)
                    
                    # Save individual summary
                    self.save_summary_report(clarification_percentage, dept_name)
                    processed_count += 1
                    

                    
                    print(f"✅ {dept_name}: {clarification_percentage}% clarification score")
                    
                    # Update department snapshot sheet
                    if self.service and dept_key in self.department_sheets:
                        update_success = self.update_snapshot_sheet(clarification_percentage, dept_key)
                        if update_success:
                            success_count += 1
                            print(f"✅ {dept_name}: {clarification_percentage}% clarification score (snapshot updated)")
                        else:
                            print(f"⚠️  {dept_name}: {clarification_percentage}% clarification score (failed to update snapshot)")
                    else:
                        print(f"⚠️  {dept_name}: {clarification_percentage}% clarification score (no snapshot sheet configured)")
                        success_count += 1
                    
            except Exception as e:
                print(f"❌ Error processing {filename}: {str(e)}")
                continue
        
        # Summary of processing
        if processed_count > 0:
            print(f"\n📈 Clarity Score Analysis completed!")
            print(f"   Processed {processed_count} department(s)")
        else:
            print("❌ No valid clarity data found across all departments")
        
        print(f"\n🎉 Clarification percentage analysis completed!")
        print(f"   Successfully processed: {processed_count}/{len(files)} files")


def main():
    """Main function for standalone execution"""
    processor = ClarityScoreProcessor()
    processor.process_all_files()


if __name__ == "__main__":
    main() 