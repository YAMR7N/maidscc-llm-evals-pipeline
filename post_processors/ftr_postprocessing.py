#!/usr/bin/env python3
"""
FTR Post-Processor
Analyzes the output from FTR (First Time Resolution) analysis and creates a combined report
with original data and summary statistics in one sheet.

Reads: LLM_outputs/{date}/ftr_{dept_name}_{date}.csv
Outputs: Combined CSV with columns:
- customer_name, conversation, llm_output, , , Metric, Value
- Original data rows followed by summary statistics
"""

import pandas as pd
import json
import os
import re
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


class FTRProcessor:
    """Post processor for FTR analysis results"""
    
    def __init__(self, target_date=None, credentials_path='credentials.json'):
        # Create directory with date subfolder to match other processors
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        self.target_date = target_date
        date_folder = target_date.strftime('%Y-%m-%d')
        self.ftr_dir = f"outputs/ftr/{date_folder}"
        os.makedirs(self.ftr_dir, exist_ok=True)
        
        # Google Sheets API setup
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Department sheet IDs for snapshot updates
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
        """Initialize Google Sheets API service"""
        try:
            if os.path.exists(self.credentials_path):
                credentials = Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                self.service = build('sheets', 'v4', credentials=credentials)
                print("✅ Google Sheets API initialized successfully")
            else:
                print(f"❌ Credentials file not found: {self.credentials_path}")
                self.service = None
        except Exception as e:
            print(f"❌ Error setting up Google Sheets API: {str(e)}")
            self.service = None
    
    def safe_json_parse(self, json_str):
        """Safely parse JSON string from LLM output"""
        try:
            if pd.isna(json_str) or not json_str.strip():
                return []
            
            # Clean up common JSON formatting issues
            cleaned = str(json_str).strip()
            
            # Remove markdown code blocks if present
            if cleaned.startswith('```json'):
                cleaned = cleaned.replace('```json', '').replace('```', '').strip()
            elif cleaned.startswith('```'):
                cleaned = cleaned.replace('```', '').strip()
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON decode error for: {str(json_str)[:100]}... Error: {e}")
            return []
        except Exception as e:
            print(f"⚠️  Parse error for: {str(json_str)[:100]}... Error: {e}")
            return []
    
    def find_ftr_files(self):
        """Find FTR LLM output files for the target date"""
        date_folder = self.target_date.strftime('%Y-%m-%d')
        date_str = self.target_date.strftime('%m_%d')
        
        llm_outputs_dir = f"outputs/LLM_outputs/{date_folder}"
        
        if not os.path.exists(llm_outputs_dir):
            print(f"❌ LLM outputs directory not found: {llm_outputs_dir}")
            return []
        
        ftr_files = []
        
        # Look for FTR files: ftr_{dept_name}_{date}.csv
        for filename in os.listdir(llm_outputs_dir):
            if filename.startswith('ftr_') and filename.endswith(f'_{date_str}.csv'):
                filepath = os.path.join(llm_outputs_dir, filename)
                
                # Extract department name from filename
                # Pattern: ftr_{dept_name}_{date}.csv
                dept_match = re.match(r'ftr_(.+)_\d{2}_\d{2}\.csv$', filename)
                if dept_match:
                    dept_key = dept_match.group(1)
                    ftr_files.append((filepath, dept_key, filename))
                    print(f"📁 Found FTR file: {filename}")
        
        if not ftr_files:
            print(f"⚠️  No FTR files found in {llm_outputs_dir}")
        
        return ftr_files
    
    def analyze_ftr_data(self, filepath):
        """Analyze FTR data from LLM output CSV and create combined report"""
        try:
            print(f"📊 Analyzing FTR data: {os.path.basename(filepath)}")
            
            # Read the LLM output CSV
            df = pd.read_csv(filepath)
            
            if df.empty:
                print("⚠️  Empty DataFrame")
                return None
            
            print(f"📋 Processing {len(df)} customers...")
            
            # Prepare original data for combined report
            combined_data = []
            
            # Initialize totals for summary
            total_chats_all_customers = 0
            total_resolved_chats_all_customers = 0
            total_customers = 0
            
            # Process each customer and add to combined data
            for _, row in df.iterrows():
                customer_name = str(row['conversation_id'])
                conversation = str(row.get('conversation', ''))
                llm_output = str(row['llm_output'])
                
                # Parse the FTR responses (JSON array of objects with chatResolution field)
                ftr_responses = self.safe_json_parse(llm_output)
                
                # Add original data row
                combined_data.append({
                    'customer_name': customer_name,
                    'conversation': conversation,
                    'llm_output': llm_output,
                    'col4': '',  # Empty column
                    'col5': '',  # Empty column
                    'Metric': '',
                    'Value': ''
                })
                
                # Initialize counts
                total_chats = 0
                resolved_chats = 0
                
                if ftr_responses and isinstance(ftr_responses, list):
                    # Count total chats and resolved chats
                    total_chats = len(ftr_responses)
                    
                    # Count "Yes" responses from the chatResolution field
                    for response in ftr_responses:
                        if isinstance(response, dict) and response.get('chatResolution') == 'Yes':
                            resolved_chats += 1
                
                # Debug: Log sample data for first few customers
                if total_customers < 3 and ftr_responses:
                    print(f"   Customer {customer_name}: {total_chats} chats, {resolved_chats} resolved")
                
                # Add to overall totals
                total_chats_all_customers += total_chats
                total_resolved_chats_all_customers += resolved_chats
                total_customers += 1
            
            # Calculate overall statistics
            overall_ftr_percentage = (total_resolved_chats_all_customers / total_chats_all_customers * 100) if total_chats_all_customers > 0 else 0
            average_chats_per_customer = total_chats_all_customers / total_customers if total_customers > 0 else 0
            
            # Add summary rows at the end
            summary_rows = [
                # Empty row separator
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': '', 'Value': ''},
                # Summary statistics
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': 'Overall FTR Percentage', 'Value': f"{overall_ftr_percentage:.1f}%"},
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': 'Total Customers', 'Value': str(total_customers)},
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': 'Total Chats (3 days)', 'Value': str(total_chats_all_customers)},
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': 'Total Resolved Chats', 'Value': str(total_resolved_chats_all_customers)},
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': 'Total Unresolved Chats', 'Value': str(total_chats_all_customers - total_resolved_chats_all_customers)},
                {'customer_name': '', 'conversation': '', 'llm_output': '', 'col4': '', 'col5': '', 'Metric': 'Average Chats per Customer (3 days)', 'Value': f"{average_chats_per_customer:.1f}"}
            ]
            
            # Combine original data with summary
            combined_data.extend(summary_rows)
            
            # Create DataFrame with correct column names
            combined_df = pd.DataFrame(combined_data)
            combined_df.columns = ['customer_name', 'conversation', 'llm_output', '', '', 'Metric', 'Value']
            
            print(f"✅ Processed {total_customers} customers")
            print(f"📊 Overall FTR: {overall_ftr_percentage:.1f}%")
            print(f"📊 Total chats: {total_chats_all_customers}")
            print(f"📊 Average chats per customer (3 days): {average_chats_per_customer:.1f}")
            
            return {
                'combined_df': combined_df,
                'overall_ftr_percentage': overall_ftr_percentage,
                'total_customers': total_customers,
                'total_chats': total_chats_all_customers,
                'total_resolved': total_resolved_chats_all_customers,
                'average_chats_per_customer': average_chats_per_customer
            }
            
        except Exception as e:
            print(f"❌ Error analyzing FTR data: {str(e)}")
            return None
    
    def create_combined_report(self, analysis_results, dept_name, output_filename):
        """Create combined report with original data and summary"""
        try:
            combined_df = analysis_results['combined_df']
            overall_ftr = analysis_results['overall_ftr_percentage']
            
            # Save combined report
            combined_df.to_csv(output_filename, index=False)
            print(f"💾 Combined report saved: {output_filename}")
            
            return combined_df, overall_ftr
            
        except Exception as e:
            print(f"❌ Error creating combined report: {str(e)}")
            return None, None
    
    def convert_dept_key_to_name(self, dept_key):
        """Convert department key to proper name for display"""
        # Handle underscores and convert to title case
        dept_name = dept_key.replace('_', ' ').title()
        
        # Handle specific department name mappings
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
    
    def index_to_column_letter(self, index):
        """Convert 0-based column index to Google Sheets column letter (A, B, ..., Z, AA, AB, ...)"""
        result = ""
        while index >= 0:
            result = chr(index % 26 + ord('A')) + result
            index = index // 26 - 1
        return result
    
    def find_column_by_name(self, column_name, sheet_id, sheet_name='Data'):
        """Find column letter by exact column name"""
        try:
            # Get the first row (headers)
            range_name = f"{sheet_name}!1:1"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            headers = result.get('values', [[]])[0]
            
            # Try exact case-sensitive match first
            for i, header in enumerate(headers):
                if header and str(header).strip() == column_name:
                    column_letter = self.index_to_column_letter(i)
                    print(f"📍 Found exact match for '{column_name}' at column {column_letter}")
                    return column_letter
            
            # Try case-insensitive match
            for i, header in enumerate(headers):
                if header and str(header).strip().lower() == column_name.lower():
                    column_letter = self.index_to_column_letter(i)
                    print(f"📍 Found case-insensitive match for '{column_name}' at column {column_letter}")
                    return column_letter
            
            print(f"❌ Column '{column_name}' not found in sheet headers")
            return None
            
        except Exception as e:
            print(f"❌ Error finding column: {str(e)}")
            return None
    
    def find_date_row(self, target_date, sheet_id, sheet_name='Data'):
        """Find the row number for a specific date"""
        try:
            # Get all data from column A (assuming dates are in column A)
            range_name = f"{sheet_name}!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            for i, row in enumerate(values):
                if row and len(row) > 0:
                    cell_value = str(row[0]).strip()
                    if cell_value == target_date_str:
                        return i + 1, sheet_name  # Google Sheets is 1-indexed
            
            print(f"❌ Date {target_date_str} not found in column A")
            return None, None
            
        except Exception as e:
            print(f"❌ Error finding date row: {str(e)}")
            return None, None
    
    def update_cell_value(self, range_name, value, sheet_id):
        """Update a specific cell with a value"""
        try:
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
            print(f"❌ Error updating cell {range_name}: {str(e)}")
            return False
    
    def update_snapshot_sheet(self, ftr_percentage, dept_key):
        """Update FTR percentage in department snapshot sheet for yesterday's date"""
        try:
            if not self.service:
                print("❌ Google Sheets API not available")
                return False
            
            # Get department sheet ID
            if dept_key not in self.department_sheets:
                print(f"❌ No snapshot sheet configured for department: {dept_key}")
                return False
                
            sheet_id = self.department_sheets[dept_key]
            yesterday = datetime.now() - timedelta(days=1)
            
            # Find the column for "FTR" or fallback to "First Time resolution on actionable chats"
            col_letter = self.find_column_by_name("FTR", sheet_id)
            if not col_letter:
                print("⚠️ 'FTR' column not found, trying fallback column name...")
                col_letter = self.find_column_by_name("First Time resolution on actionable chats", sheet_id)
                if col_letter:
                    print("✅ Found fallback column 'First Time resolution on actionable chats'")
                else:
                    print("❌ Neither 'FTR' nor 'First Time resolution on actionable chats' column found")
                    print("💡 Please manually add one of these columns to the snapshot sheet")
                    return False
            
            # Find the row for yesterday's date
            date_row, sheet_name = self.find_date_row(yesterday, sheet_id)
            if not date_row:
                print(f"⚠️ Could not find date {yesterday.strftime('%Y-%m-%d')} in snapshot sheet")
                return False
            
            # Update the cell with FTR percentage
            range_name = f"{sheet_name}!{col_letter}{date_row}"
            success = self.update_cell_value(range_name, f"{ftr_percentage:.1f}%", sheet_id)
            
            if success:
                dept_name = dept_key.replace('_', ' ').title()
                print(f"📊 Updated {dept_name} snapshot sheet with FTR: {ftr_percentage:.1f}%")
            
            return success
            
        except Exception as e:
            print(f"❌ Error updating snapshot sheet: {str(e)}")
            return False
    
    def process_all_files(self):
        """Process all FTR files and generate combined reports"""
        print(f"🚀 Starting FTR post-processing...")
        
        # Find all FTR files
        ftr_files = self.find_ftr_files()
        
        if not ftr_files:
            print("❌ No FTR files found to process")
            return False
        
        success_count = 0
        overall_results = {}
        
        for filepath, dept_key, filename in ftr_files:
            try:
                print(f"\n📊 Processing {filename}...")
                
                # Analyze the data
                analysis_results = self.analyze_ftr_data(filepath)
                if not analysis_results:
                    continue
                
                # Create proper department name
                dept_name = self.convert_dept_key_to_name(dept_key)
                
                # Create combined report
                output_filename = f"{self.ftr_dir}/{dept_name}_FTR_Combined.csv"
                combined_df, overall_ftr = self.create_combined_report(
                    analysis_results, dept_name, output_filename
                )
                
                if combined_df is not None:
                    overall_results[dept_name] = {
                        'ftr_percentage': overall_ftr,
                        'total_customers': analysis_results['total_customers'],
                        'total_chats': analysis_results['total_chats'],
                        'avg_chats': analysis_results['average_chats_per_customer']
                    }
                    
                    # Update department snapshot sheet
                    if self.service and dept_key in self.department_sheets:
                        update_success = self.update_snapshot_sheet(overall_ftr, dept_key)
                        if update_success:
                            success_count += 1
                            print(f"✅ Completed {dept_name} (snapshot updated)")
                        else:
                            print(f"⚠️  Completed {dept_name} (failed to update snapshot)")
                    else:
                        print(f"⚠️  Completed {dept_name} (no snapshot sheet configured)")
                        success_count += 1
                
            except Exception as e:
                print(f"❌ Error processing {filename}: {str(e)}")
                continue
        
        # Print overall summary
        if overall_results:
            print(f"\n🎉 FTR Processing Summary:")
            print(f"✅ Successfully processed: {success_count}/{len(ftr_files)} departments")
            print(f"\n📊 FTR Results by Department:")
            for dept, results in overall_results.items():
                print(f"  {dept}:")
                print(f"    FTR: {results['ftr_percentage']:.1f}%")
                print(f"    Customers: {results['total_customers']}")
                print(f"    Total Chats: {results['total_chats']}")
                print(f"    Avg Chats/Customer: {results['avg_chats']:.1f}")
        
        return success_count > 0


def main():
    """Main function for standalone execution"""
    processor = FTRProcessor()
    processor.process_all_files()


if __name__ == "__main__":
    main() 