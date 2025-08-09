#!/usr/bin/env python3
"""
Client Suspecting AI Post-processor
Calculates percentage of conversations where customers suspected they were talking to AI
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class ClientSuspectingAiProcessor:
    def __init__(self, credentials_path='credentials.json'):
        """Initialize Client Suspecting AI Processor"""
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Default output directory (can be overridden per target_date in process call)
        date_folder = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        self.client_suspecting_ai_dir = f"outputs/client_suspecting_ai/{date_folder}"
        os.makedirs(self.client_suspecting_ai_dir, exist_ok=True)
        
        # Snapshot sheet IDs for each department
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

    def find_client_suspecting_ai_files(self, target_date: datetime | None = None):
        """Find all client_suspecting_ai files for target_date (defaults to yesterday)"""
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        date_folder = target_date.strftime('%Y-%m-%d')
        output_dir = f"outputs/LLM_outputs/{date_folder}"
        
        client_suspecting_ai_files = []
        
        if not os.path.exists(output_dir):
            print(f"❌ Directory not found: {output_dir}")
            return []
        
        # Date in mm_dd format
        mm_dd = target_date.strftime('%m_%d')
        
        for filename in os.listdir(output_dir):
            if filename.startswith('client_suspecting_ai_') and filename.endswith('.csv'):
                if mm_dd in filename:
                    # Extract department from filename
                    name_part = filename[21:-4]  # Remove 'client_suspecting_ai_' and '.csv'
                    parts = name_part.split('_')
                    if len(parts) >= 3:
                        dept_parts = parts[:-2]
                        dept_key = '_'.join(dept_parts)
                        
                        filepath = os.path.join(output_dir, filename)
                        client_suspecting_ai_files.append((filepath, dept_key, filename, target_date))
        
        return client_suspecting_ai_files

    def calculate_client_suspecting_ai_percentage(self, filepath):
        """Calculate percentage of conversations where client suspected AI"""
        try:
            df = pd.read_csv(filepath)
            
            if df.empty:
                print(f"⚠️  Empty CSV file: {filepath}")
                return None
            
            # Count total conversations
            total_conversations = len(df)
            
            # Count conversations where llm_output is "True" (customer suspected AI)
            # Handle both string "True" and boolean True
            suspected_ai_count = len(df[df['llm_output'].astype(str).str.upper() == 'TRUE'])
            
            # Calculate percentage
            if total_conversations > 0:
                percentage = (suspected_ai_count / total_conversations) * 100
                
                print(f"📊 Client Suspecting AI Analysis:")
                print(f"   Total conversations: {total_conversations}")
                print(f"   Suspected AI: {suspected_ai_count}")
                print(f"   Percentage: {percentage:.1f}%")
                
                return percentage
            else:
                print(f"⚠️  No conversations found in {filepath}")
                return None
                
        except Exception as e:
            print(f"❌ Error calculating percentage from {filepath}: {str(e)}")
            return None

    def convert_dept_key_to_name(self, dept_key):
        """Convert department key to proper name"""
        dept_name = dept_key.replace('_', ' ').title()
        
        # Handle specific mappings
        if dept_name == 'Cc Sales':
            dept_name = 'CC Sales'
        elif dept_name == 'Cc Resolvers':
            dept_name = 'CC Resolvers'
        elif dept_name == 'Mv Resolvers':
            dept_name = 'MV Resolvers'
        elif dept_name == 'Mv Sales':
            dept_name = 'MV Sales'
        
        return dept_name

    def save_summary_report(self, percentage, dept_name):
        """Save a summary report with the percentage"""
        try:
            summary_data = [{
                'Department': dept_name,
                'Total_Conversations': 'See raw data',
                'Suspected_AI_Count': 'See raw data', 
                'Client_Suspecting_AI_Percentage': f"{percentage:.1f}%"
            }]
            
            df = pd.DataFrame(summary_data)
            output_filename = f"{self.client_suspecting_ai_dir}/{dept_name}_Client_Suspecting_AI_Summary.csv"
            df.to_csv(output_filename, index=False)
            
            print(f"✅ Summary report saved: {output_filename}")
            return output_filename
            
        except Exception as e:
            print(f"❌ Error saving summary report: {str(e)}")
            return None

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
            
            print(f"✅ Updated {range_name} with Client Suspecting AI: {value}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating cell: {str(e)}")
            return False

    def update_snapshot_sheet(self, percentage, dept_key, target_date: datetime | None = None):
        """Update the department snapshot sheet with Client Suspecting AI percentage for target_date"""
        dept_name = self.convert_dept_key_to_name(dept_key)
        print(f"\n📊 Updating {dept_name} snapshot sheet with Client Suspecting AI: {percentage:.1f}%")
        
        # Get department-specific sheet ID
        if dept_key not in self.department_sheets:
            print(f"❌ No snapshot sheet configured for department: {dept_key}")
            return False
        
        dept_sheet_id = self.department_sheets[dept_key]
        
        # Determine date in yyyy-mm-dd format
        date_str = (target_date or (datetime.now() - timedelta(days=1))).strftime('%Y-%m-%d')
        
        # Find the date row
        date_row, sheet_name = self.find_date_row(dept_sheet_id, date_str)
        if not date_row:
            print(f"❌ Could not find date {date_str} in snapshot sheet")
            return False
        
        # Find Client Suspecting AI column
        client_suspecting_ai_col, sheet_name = self.find_column_by_name(dept_sheet_id, 'Clients Suspecting AI', sheet_name)
        if not client_suspecting_ai_col:
            print(f"⚠️  Client Suspecting AI column not found in {dept_name} snapshot sheet")
            print(f"💡 Please add a 'Client Suspecting AI' column to the {dept_name} snapshot sheet manually")
            print("💡 The column should be added to the header row in the 'Data' sheet")
            return False
        
        # Update the cell with percentage
        client_suspecting_ai_value = f"{percentage:.1f}%"
        success = self.update_cell_value(dept_sheet_id, sheet_name, date_row, client_suspecting_ai_col, client_suspecting_ai_value)
        
        if success:
            print(f"✅ Successfully updated snapshot sheet with Client Suspecting AI: {client_suspecting_ai_value}")
        
        return success

    def process_all_files(self, target_date: datetime | None = None):
        """Process all client_suspecting_ai files and calculate overall percentage for target_date"""
        print(f"🚀 Starting Client Suspecting AI post-processing...")
        
        # Find files for the provided date
        client_suspecting_ai_files = self.find_client_suspecting_ai_files(target_date)
        
        if not client_suspecting_ai_files:
            print("❌ No client_suspecting_ai files found for yesterday's date")
            return False
        
        print(f"📁 Found {len(client_suspecting_ai_files)} files to process")
        
        # Process each department individually
        successful_departments = 0
        
        # Ensure output summary dir is set for target_date
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        date_folder = target_date.strftime('%Y-%m-%d')
        self.client_suspecting_ai_dir = f"outputs/client_suspecting_ai/{date_folder}"
        os.makedirs(self.client_suspecting_ai_dir, exist_ok=True)

        for filepath, dept_key, filename, td in client_suspecting_ai_files:
            try:
                print(f"\n📊 Processing {filename}...")
                
                # Read the CSV
                df = pd.read_csv(filepath)
                if df.empty:
                    print(f"⚠️  Empty file: {filename}")
                    continue
                
                # Calculate department-specific metrics
                file_total = len(df)
                file_suspected = len(df[df['llm_output'].astype(str).str.upper() == 'TRUE'])
                
                # Calculate percentage for this department
                if file_total > 0:
                    file_percentage = (file_suspected / file_total) * 100
                    
                    dept_name = self.convert_dept_key_to_name(dept_key)
                    print(f"📈 {dept_name}: {file_percentage:.1f}% ({file_suspected}/{file_total})")
                    
                    # Save individual summary
                    self.save_summary_report(file_percentage, dept_name)
                    
                    # Update this department's snapshot sheet
                    if self.service:
                        update_success = self.update_snapshot_sheet(file_percentage, dept_key, target_date)
                        if update_success:
                            successful_departments += 1
                        else:
                            print(f"⚠️  Failed to update {dept_name} snapshot sheet")
                
            except Exception as e:
                print(f"❌ Error processing {filename}: {str(e)}")
                continue
        
        # Summary
        if successful_departments > 0:
            print(f"\n✅ Client Suspecting AI Analysis completed!")
            print(f"   Successfully updated {successful_departments} department snapshot(s)")
            return True
        else:
            print("❌ Failed to update any department snapshots")
            return False

def main():
    """Main function for standalone execution"""
    processor = ClientSuspectingAiProcessor()
    processor.process_all_files()

if __name__ == "__main__":
    main() 