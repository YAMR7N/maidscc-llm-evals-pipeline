import os
import logging
from datetime import datetime, timedelta
from tableau_api_lib import TableauServerConnection
from tableau_api_lib.utils import querying
from dotenv import load_dotenv
import csv
from io import StringIO

# Set up simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class TableauDownloadCSV:
    def __init__(self):
        load_dotenv()
        self.config = {
            'tableau_prod': {
                'server': os.getenv('TABLEAU_SERVER_URL'),
                'api_version': '3.26',
                'personal_access_token_name': os.getenv('TABLEAU_TOKEN_NAME'),
                'personal_access_token_secret': os.getenv('TABLEAU_TOKEN_SECRET'),
                'site_name': os.getenv('TABLEAU_SITE_ID'),
                'site_url': os.getenv('TABLEAU_SITE_ID')
            }
        }
        self.config['tableau_prod'].pop('username', None)
        self.config['tableau_prod'].pop('password', None)
        self.conn = TableauServerConnection(self.config, env='tableau_prod')

    def download_csv(self, workbook_name, view_name, from_date=None, to_date=None, output=None, required_headers=None):
        if required_headers is None:
            raise ValueError("required_headers parameter must be provided.")
        
        logging.info("Signing in to Tableau server...")
        self.conn.sign_in()
        
        try:
            workbook_id = self._get_workbook_id(workbook_name)
            view_id = self._get_view_id(workbook_id, workbook_name, view_name)
            filters = self._build_filters(from_date, to_date)
            
            logging.info(f"Filters being sent to Tableau: {filters}")
            logging.info("Downloading CSV data from Tableau view...")
            resp = self.conn.query_view_data(view_id, parameter_dict=filters)
            resp.raise_for_status()
            
            # Fix encoding issue - force UTF-8 decoding
            logging.info(f"Response encoding detected as: {resp.encoding}")
            if resp.encoding != 'utf-8':
                logging.info("Forcing UTF-8 encoding for response")
                resp.encoding = 'utf-8'
            
            base_export_dir = os.getenv('TABLEAU_EXPORTS_DIR', './outputs/tableau_exports')
            
            # Create date-based subfolder (using yesterday's date since we use yesterday in pipeline)
            yesterday = datetime.now() - timedelta(days=1)
            date_folder = yesterday.strftime('%Y-%m-%d')
            export_dir = os.path.join(base_export_dir, date_folder)
            os.makedirs(export_dir, exist_ok=True)
            
            filename = self._generate_filename(output, view_name)
            filepath = os.path.join(export_dir, filename)
            
            # Get the properly encoded text
            csv_text = resp.text
            
            filtered_csv = self._filter_csv_headers(csv_text, required_headers)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(filtered_csv)
            
            logging.info(f"CSV exported to: {filepath}")
            self._delete_old_csvs(export_dir, view_name, exclude_filename=filename)
            
            return filepath
            
        finally:
            logging.info("Signing out from Tableau server.")
            self.conn.sign_out()

    def _get_workbook_id(self, workbook_name):
        logging.info("Fetching workbooks...")
        workbooks = querying.get_workbooks_dataframe(self.conn)
        if workbook_name not in workbooks['name'].values:
            logging.error(f"Workbook '{workbook_name}' not found.")
            raise ValueError(f"Workbook '{workbook_name}' not found.")
        
        workbook_id = workbooks[workbooks['name'] == workbook_name]['id'].iloc[0]
        logging.info(f"Accessing workbook: {workbook_name} (ID: {workbook_id})")
        return workbook_id

    def _get_view_id(self, workbook_id, workbook_name, view_name):
        logging.info("Fetching views for the workbook...")
        views = querying.get_views_for_workbook_dataframe(self.conn, workbook_id)
        if view_name not in views['name'].values:
            logging.error(f"View '{view_name}' not found in workbook '{workbook_name}'.")
            raise ValueError(f"View '{view_name}' not found in workbook '{workbook_name}'.")
        
        view_id = views[views['name'] == view_name]['id'].iloc[0]
        logging.info(f"Accessing view: {view_name} (ID: {view_id})")
        return view_id

    def _build_filters(self, from_date, to_date):
        filters = {}
        if from_date:
            from_str = self._convert_to_date(from_date)
            filters["filter_from"] = f"vf_From={from_str}"
        
        if to_date:
            to_str = self._convert_to_date(to_date)
            filters["filter_to"] = f"vf_To={to_str}"
        else:
            now_str = datetime.now().strftime('%Y-%m-%d')
            filters["filter_to"] = f"vf_To={now_str}"
        
        logging.info(f"Tableau filters being used: {filters}")
        return filters

    @staticmethod
    def _convert_to_date(date):
        if isinstance(date, datetime):
            return date.strftime('%Y-%m-%d')
        try:
            return datetime.fromisoformat(date).strftime('%Y-%m-%d')
        except ValueError:
            return datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')

    @staticmethod
    def _generate_filename(output, view_name):
        if output and output.lower().endswith('.csv'):
            # Extract just the filename from the path if a full path is provided
            return os.path.basename(output)
        return f"{output or view_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"

    def _filter_csv_headers(self, csv_data, required_headers):
        # Clean unwanted encoding artifacts
        cleaned_csv_data = csv_data
        
        # Common encoding artifacts to clean
        encoding_fixes = {
            'â¯': ' ',           # Non-breaking space artifact
            'â€™': "'",          # Right single quotation mark
            'â€œ': '"',          # Left double quotation mark  
            'â€': '"',           # Right double quotation mark
            'â€"': '—',          # Em dash
            'â€"': '–',          # En dash
            'Â': '',             # Latin capital letter A with circumflex artifact
        }
        
        for artifact, replacement in encoding_fixes.items():
            cleaned_csv_data = cleaned_csv_data.replace(artifact, replacement)
        
        # Additional cleanup for common UTF-8 misinterpretation patterns
        try:
            # Try to fix UTF-8 text that was incorrectly decoded as latin-1
            test_encode = cleaned_csv_data.encode('latin-1')
            try:
                utf8_fixed = test_encode.decode('utf-8')
                cleaned_csv_data = utf8_fixed
                logging.info("Applied UTF-8 encoding fix to CSV data")
            except UnicodeDecodeError:
                # If that fails, stick with the cleaned version
                logging.info("Applied basic encoding artifact cleanup to CSV data")
        except UnicodeEncodeError:
            # If latin-1 encoding fails, use the cleaned version as-is
            logging.info("Using cleaned CSV data without re-encoding")
        
        input_io = StringIO(cleaned_csv_data)
        reader = csv.DictReader(input_io)
        
        output_io = StringIO()
        writer = csv.DictWriter(output_io, fieldnames=required_headers)
        writer.writeheader()
        
        for row in reader:
            writer.writerow({h: row.get(h, "") for h in required_headers})
        
        return output_io.getvalue()

    def _delete_old_csvs(self, export_dir, view_name, exclude_filename):
        prefix = view_name.replace(' ', '_')
        for fname in os.listdir(export_dir):
            if fname.startswith(prefix) and fname.endswith('.csv') and fname != exclude_filename:
                try:
                    os.remove(os.path.join(export_dir, fname))
                    logging.info(f"Deleted old CSV file: {fname}")
                except Exception as e:
                    logging.warning(f"Could not delete file {fname}: {e}")
