#!/usr/bin/env python3
"""
Upload loss_of_interest CSV files to individual department Google Spreadsheets
Each file creates a new sheet named with yyyy-mm-dd format
"""

import pandas as pd
import os
import re
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.sheets import SHEET_MANAGER

class LossOfInterestUploader:
    def __init__(self, credentials_path='credentials.json', target_date=None):
        """Initialize Loss of Interest Uploader with Google Sheets integration"""
        self.credentials_path = credentials_path
        self.service = None
        self.target_date = target_date if target_date else datetime.now() - timedelta(days=1)
        self.setup_sheets_api()
        
        # Department name mapping for proper formatting
        self.department_name_mapping = {
            'african': 'African',
            'cc_resolvers': 'CC Resolvers',
            'cc_sales': 'CC Sales',
            'delighters': 'Delighters',
            'doctors': 'Doctors',
            'ethiopian': 'Ethiopian',
            'filipina': 'Filipina',
            'mv_resolvers': 'MV Resolvers',
            'mv_sales': 'MV Sales'
        }

    def setup_sheets_api(self):
        """Setup Google Sheets API authentication"""
        try:
            if not os.path.exists(self.credentials_path):
                print(f"❌ Credentials file not found: {self.credentials_path}")
                print("Please ensure credentials.json is in the config directory")
                return False
                
            creds = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=creds)
            return True
        except Exception as e:
            print(f"❌ Failed to setup Google Sheets API: {str(e)}")
            return False

    def find_loss_of_interest_files(self):
        """Find all loss_of_interest files from the target date"""
        # Look in target date's subfolder
        date_folder = self.target_date.strftime('%Y-%m-%d')
        output_dir = f"outputs/LLM_outputs/{date_folder}"
        loss_of_interest_files = []
        
        if not os.path.exists(output_dir):
            print(f"❌ Directory not found: {output_dir}")
            return []
        
        # Get target date in mm_dd format
        target_date = self.target_date.strftime('%m_%d')
        
        # Look for loss_of_interest files
        for file in os.listdir(output_dir):
            if file.startswith('loss_of_interest_') and file.endswith(f'_{target_date}.csv'):
                loss_of_interest_files.append(os.path.join(output_dir, file))
        
        return loss_of_interest_files

    def extract_department_from_filename(self, filename):
        """Extract department name from filename"""
        # Pattern: loss_of_interest_<department>_mm_dd.csv
        base_name = os.path.basename(filename)
        match = re.match(r'loss_of_interest_(.+?)_\d{2}_\d{2}\.csv', base_name)
        if match:
            dept_key = match.group(1).lower()
            return self.department_name_mapping.get(dept_key, match.group(1))
        return None

    def create_or_update_sheet(self, spreadsheet_id, sheet_name, data):
        """Create a new sheet or update existing one with the data"""
        try:
            # Get list of existing sheets
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
            
            # If sheet exists, handle it
            if sheet_name in existing_sheets:
                # Check if this is the only sheet
                if len(existing_sheets) > 1:
                    # Safe to delete
                    sheet_id = None
                    for sheet in spreadsheet['sheets']:
                        if sheet['properties']['title'] == sheet_name:
                            sheet_id = sheet['properties']['sheetId']
                            break
                    
                    if sheet_id is not None:
                        # Delete the existing sheet
                        request = {
                            'requests': [
                                {
                                    'deleteSheet': {
                                        'sheetId': sheet_id
                                    }
                                }
                            ]
                        }
                        self.service.spreadsheets().batchUpdate(
                            spreadsheetId=spreadsheet_id, 
                            body=request
                        ).execute()
                        print(f"♻️  Deleted existing sheet: {sheet_name}")
                else:
                    # Can't delete the only sheet, just clear and update it
                    print(f"🔄 Updating existing sheet: {sheet_name}")
                    
                    # Clear the sheet
                    self.service.spreadsheets().values().clear(
                        spreadsheetId=spreadsheet_id,
                        range=f"{sheet_name}!A:Z"
                    ).execute()
                    
                    # Update with new data
                    values = [data.columns.tolist()] + data.values.tolist()
                    body = {'values': values}
                    
                    self.service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f"{sheet_name}!A1",
                        valueInputOption='USER_ENTERED',
                        body=body
                    ).execute()
                    
                    # Get sheet ID for formatting
                    for sheet in spreadsheet['sheets']:
                        if sheet['properties']['title'] == sheet_name:
                            existing_sheet_id = sheet['properties']['sheetId']
                            # Apply formatting
                            self._apply_sheet_formatting(spreadsheet_id, existing_sheet_id, len(data), len(data.columns))
                            break
                    
                    print(f"📊 Uploaded {len(data)} rows to sheet")
                    return True
            
            # Create new sheet
            request = {
                'requests': [
                    {
                        'addSheet': {
                            'properties': {
                                'title': sheet_name,
                                'gridProperties': {
                                    'rowCount': len(data) + 10,
                                    'columnCount': len(data.columns) + 2
                                }
                            }
                        }
                    }
                ]
            }
            
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, 
                body=request
            ).execute()
            
            print(f"✅ Created new sheet: {sheet_name}")
            
            # Prepare data for upload
            values = [data.columns.tolist()] + data.values.tolist()
            
            # Update the sheet with data
            body = {
                'values': values
            }
            
            range_name = f"{sheet_name}!A1"
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            # Get the new sheet ID
            new_sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
            
            # Apply formatting to the new sheet
            self._apply_sheet_formatting(spreadsheet_id, new_sheet_id, len(data), len(data.columns))
            
            print(f"📊 Uploaded {len(data)} rows to sheet")
            return True
            
        except Exception as e:
            print(f"❌ Error creating/updating sheet: {str(e)}")
            return False
    
    def _apply_sheet_formatting(self, spreadsheet_id, sheet_id, num_rows, num_cols):
        """Apply formatting to a sheet"""
        try:
            requests = [
                # 1. Format header row (bold, centered, 12pt, black background, white text)
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {
                                    'red': 0.0,
                                    'green': 0.0,
                                    'blue': 0.0
                                },
                                'textFormat': {
                                    'foregroundColor': {
                                        'red': 1.0,
                                        'green': 1.0,
                                        'blue': 1.0
                                    },
                                    'bold': True,
                                    'fontSize': 12
                                },
                                'horizontalAlignment': 'CENTER',
                                'verticalAlignment': 'MIDDLE',
                                'wrapStrategy': 'WRAP'
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)'
                    }
                },
                # 2. Apply text wrapping to all data cells
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 1,
                            'endRowIndex': num_rows + 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'wrapStrategy': 'WRAP',
                                'verticalAlignment': 'TOP'
                            }
                        },
                        'fields': 'userEnteredFormat(wrapStrategy,verticalAlignment)'
                    }
                },
                # 3. Auto-resize columns
                {
                    'autoResizeDimensions': {
                        'dimensions': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': num_cols
                        }
                    }
                },
                # 4. Set minimum row height for header
                {
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'ROWS',
                            'startIndex': 0,
                            'endIndex': 1
                        },
                        'properties': {
                            'pixelSize': 35
                        },
                        'fields': 'pixelSize'
                    }
                },
                # 5. Freeze header row
                {
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet_id,
                            'gridProperties': {
                                'frozenRowCount': 1
                            }
                        },
                        'fields': 'gridProperties.frozenRowCount'
                    }
                }
            ]
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
            
        except Exception as e:
            print(f"⚠️  Warning: Could not apply formatting: {str(e)}")

    def upload_file(self, filepath, department_name):
        """Upload a single loss_of_interest file to its department sheet"""
        try:
            # Get sheet ID from config
            try:
                sheet_id = SHEET_MANAGER.get_sheet_id(department_name, "loss_of_interest")
            except ValueError as e:
                print(f"⚠️  No loss_of_interest sheet configured for {department_name}")
                return False
            
            # Read the CSV file
            df = pd.read_csv(filepath)
            
            if df.empty:
                print(f"⚠️  Empty file: {filepath}")
                return False
            
            # Use the data as-is without processing
            processed_df = df
            
            # Create sheet name with date
            sheet_name = self.target_date.strftime('%Y-%m-%d')
            
            # Upload to Google Sheets
            success = self.create_or_update_sheet(sheet_id, sheet_name, processed_df)
            
            if success:
                print(f"✅ Successfully uploaded {department_name} loss_of_interest data")
                print(f"📎 View at: https://docs.google.com/spreadsheets/d/{sheet_id}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error uploading {filepath}: {str(e)}")
            return False

    def process_all_files(self):
        """Process all loss_of_interest files and upload to their respective sheets"""
        if not self.service:
            print("❌ Google Sheets API not initialized")
            return
        
        files = self.find_loss_of_interest_files()
        
        if not files:
            print(f"❌ No loss_of_interest files found for {self.target_date.strftime('%Y-%m-%d')}")
            return
        
        print(f"✅ Found {len(files)} loss_of_interest files")
        
        success_count = 0
        for filepath in files:
            department = self.extract_department_from_filename(filepath)
            if department:
                print(f"\n📤 Processing {department}...")
                if self.upload_file(filepath, department):
                    success_count += 1
            else:
                print(f"⚠️  Could not extract department from filename: {filepath}")
        
        print(f"\n📊 Summary: Successfully uploaded {success_count}/{len(files)} files")


def main():
    """Main function for standalone usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload loss_of_interest results to Google Sheets')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD format)')
    
    args = parser.parse_args()
    
    # Parse target date
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Invalid date format: {args.date}. Use YYYY-MM-DD")
            return
    
    uploader = LossOfInterestUploader(target_date=target_date)
    uploader.process_all_files()


if __name__ == "__main__":
    main()