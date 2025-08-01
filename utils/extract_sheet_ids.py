#!/usr/bin/env python3
"""
Extract Google Sheet IDs from Google Drive folders
Configurable tool for various use cases
"""

import argparse
import json
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Predefined configurations for different projects
FOLDER_CONFIGS = {
    'client_suspecting_ai': {
        'folder_id': '1ObYjXDuOK7SBwUZ7Q-9WJeCn5WqGNG-g',
        'description': 'Client Suspecting AI analysis sheets',
        'department_mapping': {
            'CC Resolvers': 'CC Resolvers',
            'CC Sales': 'CC Sales',
            'Delighters': 'Delighters',
            'Doctors': 'Doctors',
            'MaidsAT African': 'African',
            'MaidsAT Ethiopian': 'Ethiopian',
            'MaidsAT Filipina': 'Filipina',
            'MV Resolvers': 'MV Resolvers',
            'MV Sales': 'MV Sales'
        }
    },
    'sa_sheets': {
        'folder_id': 'UPDATE_WITH_SA_FOLDER_ID',
        'description': 'Sentiment Analysis sheets',
        'department_mapping': {
            # Add SA specific mappings when needed
        }
    }
}

def extract_folder_id_from_url(url):
    """Extract folder ID from Google Drive URL"""
    if '/folders/' in url:
        return url.split('/folders/')[1].split('/')[0].split('?')[0]
    return url

def extract_sheet_ids(folder_id, department_mapping=None, credentials_path='credentials.json', output_format='python', variable_name='department_sheets'):
    """
    Extract Google Sheet IDs from a Drive folder
    
    Args:
        folder_id: Google Drive folder ID or URL
        department_mapping: Dict mapping sheet names to desired department names
        credentials_path: Path to Google service account credentials
        output_format: 'python', 'json', or 'csv'
        variable_name: Variable name for Python output
    """
    try:
        # Extract folder ID if URL provided
        folder_id = extract_folder_id_from_url(folder_id)
        
        # Setup Google Drive API
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        if not os.path.exists(credentials_path):
            print(f"❌ Credentials file not found: {credentials_path}")
            return False
            
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        print(f"🔍 Accessing Google Drive folder: {folder_id}")

        # List all files in the folder
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'",
            fields='files(id,name)'
        ).execute()

        files = results.get('files', [])

        if not files:
            print("❌ No Google Sheets found in the folder")
            return False

        print(f"📁 Found {len(files)} Google Sheets in the folder")
        
        # Process files and create mapping
        sheet_mapping = {}
        for file in files:
            name = file['name']
            sheet_id = file['id']
            
            # Apply department mapping if provided
            if department_mapping:
                dept_name = department_mapping.get(name, name)
            else:
                dept_name = name
                
            sheet_mapping[dept_name] = sheet_id

        # Output in requested format
        if output_format == 'python':
            print(f"\n{variable_name} = {{")
            for dept_name, sheet_id in sorted(sheet_mapping.items()):
                print(f"    '{dept_name}': '{sheet_id}',")
            print("}")
            
        elif output_format == 'json':
            print(f"\n{json.dumps(sheet_mapping, indent=2)}")
            
        elif output_format == 'csv':
            print("\nDepartment,Sheet ID")
            for dept_name, sheet_id in sorted(sheet_mapping.items()):
                print(f"{dept_name},{sheet_id}")
        
        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Extract Google Sheet IDs from Drive folders')
    parser.add_argument('--config', choices=list(FOLDER_CONFIGS.keys()), 
                       help='Use predefined configuration')
    parser.add_argument('--folder-id', help='Google Drive folder ID or URL')
    parser.add_argument('--output-format', choices=['python', 'json', 'csv'], 
                       default='python', help='Output format')
    parser.add_argument('--variable-name', default='department_sheets',
                       help='Variable name for Python output')
    parser.add_argument('--credentials', default='credentials.json',
                       help='Path to credentials file')
    parser.add_argument('--list-configs', action='store_true',
                       help='List available configurations')
    
    args = parser.parse_args()
    
    if args.list_configs:
        print("📋 Available configurations:")
        for config_name, config in FOLDER_CONFIGS.items():
            print(f"  {config_name}: {config['description']}")
            print(f"    Folder ID: {config['folder_id']}")
            print()
        return
    
    # Determine which configuration to use
    if args.config:
        if args.config not in FOLDER_CONFIGS:
            print(f"❌ Unknown configuration: {args.config}")
            return
        config = FOLDER_CONFIGS[args.config]
        folder_id = config['folder_id']
        department_mapping = config['department_mapping']
        print(f"📋 Using configuration: {args.config} - {config['description']}")
    elif args.folder_id:
        folder_id = args.folder_id
        department_mapping = None
        print(f"📋 Using custom folder ID: {folder_id}")
    else:
        print("❌ Must specify either --config or --folder-id")
        parser.print_help()
        return
    
    # Extract sheet IDs
    success = extract_sheet_ids(
        folder_id=folder_id,
        department_mapping=department_mapping,
        credentials_path=args.credentials,
        output_format=args.output_format,
        variable_name=args.variable_name
    )
    
    if success:
        print("\n✅ Sheet ID extraction completed!")
    else:
        print("\n❌ Sheet ID extraction failed!")

if __name__ == "__main__":
    main() 