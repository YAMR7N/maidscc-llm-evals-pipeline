#!/usr/bin/env python3
"""
Rule Breaking Post-Processing Script
Analyzes rule violations from LLM outputs and creates summaries
"""

import pandas as pd
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class RuleBreakingProcessor:
    def __init__(self, credentials_path='credentials.json'):
        """Initialize Rule Breaking Processor with Google Sheets integration"""
        self.credentials_path = credentials_path
        self.service = None
        self.setup_sheets_api()
        
        # Department sheet IDs from sa_post_processing.py
        self.department_sheets = {
            'Doctors': '1STHimb0IJ077iuBtTOwsa-GD8jStjU3SiBW7yBWom-E',
            'Delighters': '1PV0ZmobUYKHGZvHC7IfJ1t6HrJMTFi6YRbpISCouIfQ',
            'CC Sales': '1te1fbAXhURIUO0EzQ2Mrorv3a6GDtEVM_5np9TO775o',
            'CC Resolvers': '1QdmaTc5F2VUJ0Yu0kNF9d6ETnkMOlOgi18P7XlBSyHg',
            'Filipina': '1E5wHZKSDXQZlHIb3sV4ZWqIxvboLduzUEU0eupK7tys',
            'African': '1__KlrVjcpR8RoYfTYMYZ_EgddUSXMhK3bJO0fTGwDig',
            'Ethiopian': '1ENzdgiwUEtBSb5sHZJWs5aG8g2H62Low8doaDZf8s90',
            'MV Resolvers': '1XkVcHlkh8fEp7mmBD1Zkavdp2blBLwSABT1dE_sOf74',
            'MV Sales': '1agrl9hlBhemXkiojuWKbqiMHKUzxGgos4JSkXxw7NAk'
        }
        
        # Ensure output directory exists with date subfolder
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        self.rule_breaking_dir = f"outputs/rule_breaking/{date_folder}"
        os.makedirs(self.rule_breaking_dir, exist_ok=True)

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

    def find_rule_breaking_column(self, sheet_id, sheet_name='Sheet1'):
        """Find the column number for 'Rule Breaking' header"""
        if not self.service:
            print("❌ Google Sheets service not available")
            return None, None
            
        # Try different sheet names - prioritize Data first
        sheet_names_to_try = ['Data', sheet_name, 'Sheet1', 'Main']
        
        for current_sheet_name in sheet_names_to_try:
            try:
                print(f"🔍 Looking for 'Rule Breaking' column in sheet: {current_sheet_name}")
                # Get the first row (header row) across a wide range
                range_name = f"{current_sheet_name}!1:1"
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=sheet_id, range=range_name).execute()
                
                values = result.get('values', [])
                
                if values and len(values) > 0:
                    header_row = values[0]
                    # Look for "Rule Breaking" in the header row
                    for col_idx, header in enumerate(header_row):
                        if header and "Rule Breaking" in str(header):
                            column_number = col_idx + 1  # Convert to 1-based indexing
                            print(f"✅ Found 'Rule Breaking' in column {column_number} (sheet: {current_sheet_name})")
                            return column_number, current_sheet_name
                
                print(f"🔍 'Rule Breaking' column not found in sheet {current_sheet_name}")
                
            except Exception as e:
                pass
        
        print(f"❌ 'Rule Breaking' column not found in any sheet")
        return None, None

    def find_date_row(self, sheet_id, target_date, sheet_name='Sheet1'):
        """Find row with target date (2025-07-12 format) in column A"""
        if not self.service:
            print("❌ Google Sheets service not available")
            return None, None
            
        # Try different sheet names - prioritize Data first
        sheet_names_to_try = ['Data', sheet_name, 'Sheet1', 'Main']
        
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
                            return i + 1, current_sheet_name
                
                print(f"🔍 Date {target_date} not found in sheet {current_sheet_name}")
                
            except Exception as e:
                pass
        
        print(f"❌ Date {target_date} not found in any sheet")
        return None, None

    def update_cell_value(self, sheet_id, sheet_name, row, col, value):
        """Update a specific cell with the rule breaking percentage"""
        if not self.service:
            print("❌ Google Sheets service not available")
            return False
            
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
            
            # Update the cell
            body = {
                'values': [[value]]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"✅ Updated {range_name} with Rule Breaking %: {value}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating cell: {str(e)}")
            return False

    def find_rule_breaking_files(self):
        """Find rule_breaking files for YESTERDAY'S date only in LLM_outputs"""
        # Look in yesterday's date subfolder
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        output_dir = f"outputs/LLM_outputs/{date_folder}"
        rule_breaking_files = []
        
        # Get yesterday's date in mm_dd format
        yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%m_%d')
        print(f"🔍 Looking for rule breaking files from yesterday: {yesterday_date}")
        
        if not os.path.exists(output_dir):
            print(f"❌ Directory not found: {output_dir}")
            return []
        
        for filename in os.listdir(output_dir):
            if filename.startswith('rule_breaking_') and filename.endswith('.csv'):
                # Check if filename ends with yesterday's date: rule_breaking_dept_name_mm_dd.csv
                if filename.endswith(f'_{yesterday_date}.csv'):
                    # Extract department from filename: rule_breaking_dept_name_mm_dd.csv
                    parts = filename.replace('.csv', '').split('_')
                    if len(parts) >= 3:
                        dept_part = '_'.join(parts[2:-2])  # Handle multi-word department names
                        filepath = os.path.join(output_dir, filename)
                        rule_breaking_files.append((filepath, dept_part, filename))
                        print(f"📁 Found yesterday's file: {filename} -> Department: {dept_part}")
                else:
                    print(f"⏭️  Skipping old file: {filename} (not from {yesterday_date})")
        
        print(f"✅ Found {len(rule_breaking_files)} rule breaking files for yesterday ({yesterday_date})")
        return rule_breaking_files

    def extract_json_from_llm_output(self, llm_output_str):
        """Extract JSON content from LLM output, handling both markdown and plain JSON"""
        import re
        
        # Clean up the string
        llm_output_str = llm_output_str.strip()
        
        # Try to extract JSON from markdown code blocks first
        # Look for ```json ... ``` or ``` ... ``` patterns
        json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        match = re.search(json_pattern, llm_output_str, re.DOTALL)
        
        if match:
            # Extract content from code block
            json_content = match.group(1).strip()
            return json_content
        
        # If no markdown code blocks found, return the original string
        return llm_output_str

    def analyze_rule_breaking_data(self, filepath):
        """Analyze rule breaking data from a CSV file"""
        try:
            df = pd.read_csv(filepath)
            print(f"📊 Reading {len(df)} conversations from {os.path.basename(filepath)}")
            
            # Initialize counters
            total_convs = 0
            conv_violations = Counter()  # Count of conversations by number of violations
            
            # First pass: collect all possible rules from all conversations
            all_rules = set()
            conversations_data = []
            
            for _, row in df.iterrows():
                try:
                    llm_output_str = str(row['llm_output'])
                    
                    # Skip empty or invalid responses
                    if pd.isna(row['llm_output']) or llm_output_str.strip() in ['', 'nan', '(empty)']:
                        continue
                    
                    # Extract JSON content, handling markdown code blocks
                    json_content = self.extract_json_from_llm_output(llm_output_str)
                    llm_output = json.loads(json_content)
                    
                    # Handle cases where LLM returns a list instead of a dict
                    if isinstance(llm_output, list):
                        # If it's a list, wrap it in a dict with 'messages' key
                        llm_output = {'messages': llm_output, 'chat_id': row['conversation_id']}
                    elif not isinstance(llm_output, dict):
                        # Skip if it's neither list nor dict
                        print(f"⚠️  Unexpected LLM output format: {type(llm_output)}, Chat ID {row['conversation_id']}")
                        continue
                    
                    conv_violation_count = 0
                    violated_rules_in_conv = set()
                    messages_data = []
                    
                    # Process each message in the conversation
                    for message in llm_output.get('messages', []):
                        if not isinstance(message, dict):
                            print(f"⚠️  Message is not a dict: {type(message)}, Chat ID {llm_output.get('chat_id', 'unknown')}")
                            continue
                            
                        violated_rules = message.get('violated_rules', [])
                        
                        # Normalize rule formatting (remove extra spaces after colon and replace underscores with spaces)
                        normalized_rules = []
                        for rule in violated_rules:
                            # Replace ": " with ":" to standardize formatting
                            normalized_rule = rule.replace(': ', ':')
                            # Replace underscores with spaces in rule titles
                            if ':' in normalized_rule:
                                rule_num, rule_title = normalized_rule.split(':', 1)
                                rule_title = rule_title.replace('_', ' ')
                                normalized_rule = f"{rule_num}:{rule_title}"
                            normalized_rules.append(normalized_rule)
                        
                        # Collect all rules (normalized)
                        all_rules.update(normalized_rules)
                        violated_rules = normalized_rules  # Use normalized rules going forward
                        
                        # Count violations for this message
                        if violated_rules:
                            conv_violation_count += len(violated_rules)
                            for rule in violated_rules:
                                violated_rules_in_conv.add(rule)
                        
                        messages_data.append(violated_rules)
                    
                    # Normalize conversation-level violated rules too
                    normalized_conv_rules = set()
                    for rule in violated_rules_in_conv:
                        # Apply same normalization as message-level rules
                        normalized_rule = rule.replace(': ', ':')
                        if ':' in normalized_rule:
                            rule_num, rule_title = normalized_rule.split(':', 1)
                            rule_title = rule_title.replace('_', ' ')
                            normalized_rule = f"{rule_num}:{rule_title}"
                        normalized_conv_rules.add(normalized_rule)
                    
                    conversations_data.append({
                        'messages': messages_data,
                        'violated_rules_in_conv': normalized_conv_rules,
                        'conv_violation_count': conv_violation_count
                    })
                    
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    #print error with conv id and row number
                    print(f"⚠️  Error parsing: {str(e)}, Chat ID {row['conversation_id']}")
                    continue
            
            # Initialize rule_stats with all rules
            rule_stats = {}
            for rule in all_rules:
                rule_stats[rule] = {
                    'total_convs': 0, 'good_convs': 0, 'broken_convs': 0,
                    'good_msgs': 0, 'broken_msgs': 0
                }
            
            # Second pass: update statistics for all rules for each conversation
            total_convs = len(conversations_data)
            
            for conv_data in conversations_data:
                violated_rules_in_conv = conv_data['violated_rules_in_conv']
                conv_violation_count = conv_data['conv_violation_count']
                messages_data = conv_data['messages']
                
                # Categorize conversation by violation count
                if conv_violation_count == 0:
                    conv_violations[0] += 1
                elif conv_violation_count == 1:
                    conv_violations[1] += 1
                elif conv_violation_count == 2:
                    conv_violations[2] += 1
                else:
                    conv_violations[3] += 1  # 3+ violations
                
                # Update statistics for ALL rules
                for rule in all_rules:
                    # Update total conversations for all rules
                    rule_stats[rule]['total_convs'] += 1
                    
                    # Update conversation statistics
                    if rule in violated_rules_in_conv:
                        rule_stats[rule]['broken_convs'] += 1
                    else:
                        rule_stats[rule]['good_convs'] += 1
                    
                    # Update message statistics
                    for message_violations in messages_data:
                        if rule in message_violations:
                            rule_stats[rule]['broken_msgs'] += 1
                        else:
                            rule_stats[rule]['good_msgs'] += 1
            
            return {
                'total_convs': total_convs,
                'conv_violations': conv_violations,
                'rule_stats': rule_stats
            }
            
        except Exception as e:
            print(f"❌ Error analyzing {filepath}: {str(e)}")
            return None

    def create_summary_report(self, analysis_results, department, output_filename):
        """Create a summary report similar to the example CSV"""
        try:
            total_convs = analysis_results['total_convs']
            conv_violations = analysis_results['conv_violations']
            rule_stats = analysis_results['rule_stats']
            
            # Calculate percentages
            convs_with_violations = total_convs - conv_violations.get(0, 0)
            pct_convs_ge_1 = (convs_with_violations / total_convs * 100) if total_convs > 0 else 0
            
            # Create summary rows
            summary_data = []
            
            # Chatbot summary
            summary_data.append([
                department,
                total_convs,
                conv_violations.get(0, 0),
                conv_violations.get(1, 0),
                conv_violations.get(2, 0),
                conv_violations.get(3, 0),
                f"{pct_convs_ge_1:.2f}%"
            ])
            
            # Empty row
            summary_data.append(['', '', '', '', '', '', ''])
            
            # Rule breakdown header
            summary_data.append([
                'Rule Title',
                'Total Convs',
                'Good Convs',
                'Broken Convs',
                'Good Msgs',
                'Broken Msgs',
                '% Convs Broken'
            ])
            
            # Sort rules by percentage of conversations broken (descending)
            sorted_rules = sorted(
                rule_stats.items(),
                key=lambda x: (x[1]['broken_convs'] / max(x[1]['total_convs'], 1)) * 100,
                reverse=True
            )
            
            for rule, stats in sorted_rules:
                pct_broken = (stats['broken_convs'] / max(stats['total_convs'], 1)) * 100
                summary_data.append([
                    rule,
                    stats['total_convs'],
                    stats['good_convs'],
                    stats['broken_convs'],
                    stats['good_msgs'],
                    stats['broken_msgs'],
                    f"{pct_broken:.2f}%"
                ])
            
            # Create DataFrame and save
            columns = [
                'Chat-bot', 'Total Convs', '0 violations', '1 violation',
                '2 violations', '3+ violations', '% convs ≥ 1'
            ]
            df = pd.DataFrame(summary_data)
            df.columns = columns
            
            df.to_csv(output_filename, index=False)
            print(f"✅ Summary report saved to: {output_filename}")
            
            return pct_convs_ge_1  # Return the percentage for uploading to sheets
            
        except Exception as e:
            print(f"❌ Error creating summary report: {str(e)}")
            return None

    def upload_to_google_sheets(self, department, percentage_value):
        """Upload the rule breaking percentage to Google Sheets"""
        print(f"\n📊 Uploading {department} rule breaking percentage: {percentage_value:.2f}%")
        
        # Get sheet ID for the department
        sheet_id = self.department_sheets.get(department)
        if not sheet_id:
            print(f"❌ No sheet ID found for {department}")
            return False
        
        # Find the 'Rule Breaking' column
        column_result = self.find_rule_breaking_column(sheet_id)
        if not column_result or len(column_result) != 2:
            print(f"❌ Could not find 'Rule Breaking' column for {department}")
            return False
            
        column, found_sheet_name = column_result
        if not column or not found_sheet_name:
            print(f"❌ Could not find 'Rule Breaking' column for {department}")
            return False
        
        # Find row with yesterday's date
        yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        date_row, found_sheet_name = self.find_date_row(sheet_id, yesterday_date, found_sheet_name)
        
        if not date_row:
            print(f"❌ Could not find yesterday's date ({yesterday_date}) in {department} sheet")
            return False
        
        # Update the cell with percentage
        formatted_percentage = f"{percentage_value:.2f}%"
        success = self.update_cell_value(sheet_id, found_sheet_name, date_row, column, formatted_percentage)
        
        if success:
            print(f"✅ Successfully updated {department} sheet with {formatted_percentage}")
        else:
            print(f"❌ Failed to update {department} sheet")
            
        return success

    def process_all_departments(self):
        """Process all rule breaking files and upload to Google Sheets"""
        print("🚀 Starting Rule Breaking post-processing...")
        
        # Find all rule breaking files
        rule_breaking_files = self.find_rule_breaking_files()
        
        if not rule_breaking_files:
            print("❌ No rule breaking files found")
            return
        
        print(f"📁 Found {len(rule_breaking_files)} files to process")
        
        success_count = 0
        
        for filepath, dept_key, filename in rule_breaking_files:
            try:
                print(f"\n📊 Processing {filename}...")
                
                # Analyze the data
                analysis_results = self.analyze_rule_breaking_data(filepath)
                if not analysis_results:
                    continue
                
                # Create proper department name
                # Handle prompt prefixes in filenames (mvr_, ccs_, mvs_, doc_, etc.)
                dept_name = dept_key.replace('_', ' ').title()
                
                # Map prompt-prefixed department names to actual department names
                if dept_name == 'Mvr Mv Resolvers':
                    dept_name = 'MV Resolvers'
                elif dept_name == 'Ccs Cc Sales':
                    dept_name = 'CC Sales'
                elif dept_name == 'Mvs Mv Sales':
                    dept_name = 'MV Sales'
                elif dept_name == 'Doc Doctors':
                    dept_name = 'Doctors'
                # Handle standard cases without prompt prefixes
                elif dept_name == 'Cc Sales':
                    dept_name = 'CC Sales'
                elif dept_name == 'Cc Resolvers':
                    dept_name = 'CC Resolvers'
                elif dept_name == 'Mv Resolvers':
                    dept_name = 'MV Resolvers'
                elif dept_name == 'Mv Sales':
                    dept_name = 'MV Sales'
                
                # Create summary report
                output_filename = f"Rule_Breaking/{dept_name}_Rule_Breaking_Summary.csv"
                percentage_ge_1 = self.create_summary_report(analysis_results, dept_name, output_filename)
                
                if percentage_ge_1 is not None:
                    # Upload to Google Sheets
                    if self.upload_to_google_sheets(dept_name, percentage_ge_1):
                        success_count += 1
                    
            except Exception as e:
                print(f"❌ Error processing {filename}: {str(e)}")
        
        # Print final summary
        print(f"\n📈 Processing Summary:")
        print(f"✅ Successfully processed and uploaded: {success_count}/{len(rule_breaking_files)} departments")
        print(f"📁 Summary reports saved in: ./Rule_Breaking/")

def main():
    """Main function"""
    processor = RuleBreakingProcessor()
    processor.process_all_departments()
    print("\n✅ Rule Breaking post-processing completed!")

if __name__ == "__main__":
    main()
