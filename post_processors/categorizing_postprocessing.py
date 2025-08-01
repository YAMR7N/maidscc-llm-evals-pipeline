#!/usr/bin/env python3
"""
Categorizing Post-Processor
Analyzes the output from categorizing analysis and creates clean summary statistics

Reads: LLM_outputs/{date}/categorizing_{dept_name}_{date}.csv
Outputs: Clean CSV with columns:
- Category: The conversation category (N/A excluded)
- % Intervention: Percentage of ALL chats that are interventions in this category
- % Transfers: Percentage of ALL chats that are transfers in this category  
- % of ALL chats: Percentage of all chats that belong to this category
Note: % Intervention + % Transfers = % of ALL chats for each category
(Sorted by % of ALL chats, descending)
"""

import pandas as pd
import json
import os
from datetime import datetime, timedelta
from collections import Counter


class CategorizingProcessor:
    """Post processor for categorizing analysis results"""
    
    def __init__(self):
        # Create directory with date subfolder to match uploader expectations
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        self.categorizing_dir = f"outputs/categorizing/{date_folder}"
        os.makedirs(self.categorizing_dir, exist_ok=True)
    
    def safe_json_parse(self, json_str):
        """Safely parse JSON string from LLM output"""
        try:
            if pd.isna(json_str) or not json_str.strip():
                return None
            
            # Clean up common JSON formatting issues
            cleaned = str(json_str).strip()
            
            # Remove markdown code blocks if present
            if cleaned.startswith('```json'):
                cleaned = cleaned.replace('```json', '').replace('```', '').strip()
            elif cleaned.startswith('```'):
                cleaned = cleaned.replace('```', '').strip()
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"JSON decode error for: {str(json_str)[:100]}... Error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error parsing: {str(json_str)[:100]}... Error: {e}")
            return None

    def analyze_categorizing_data(self, input_file):
        """
        Analyze categorizing prompt results and create clean summary CSV
        
        Args:
            input_file: Path to categorizing CSV file
        """
        print(f"📊 Analyzing categorizing results from: {input_file}")
        
        # Read the input file
        try:
            df = pd.read_csv(input_file)
            print(f"📈 Loaded {len(df)} conversations")
        except Exception as e:
            print(f"❌ Error reading input file: {e}")
            return None
        
        # Check if required columns exist
        if 'llm_output' not in df.columns:
            print(f"❌ Error: 'llm_output' column not found. Available columns: {list(df.columns)}")
            return None
        
        # Parse JSON outputs
        parsed_results = []
        parse_errors = 0
        
        for idx, row in df.iterrows():
            llm_output = row['llm_output']
            parsed = self.safe_json_parse(llm_output)
            
            if parsed:
                # Extract categories list and intervention/transfer info
                categories_data = parsed.get('Categories', [])
                intervention_or_transfer = parsed.get('InterventionOrTransfer', 'N/A')
                category_causing = parsed.get('CategoryCausingInterventionOrTransfer', 'N/A')
                
                # Handle different possible formats for Categories
                categories_list = []
                if isinstance(categories_data, list):
                    for cat in categories_data:
                        if isinstance(cat, dict) and 'CategoryName' in cat:
                            categories_list.append(cat['CategoryName'])
                elif isinstance(categories_data, dict):
                    # If it's a single category as dict
                    if 'CategoryName' in categories_data:
                        categories_list.append(categories_data['CategoryName'])
                
                parsed_results.append({
                    'chat_id': row.get('conversation_id', f'chat_{idx}'),
                    'categories': categories_list,
                    'intervention_or_transfer': intervention_or_transfer,
                    'category_causing_intervention_transfer': category_causing,
                    'original_output': llm_output
                })
            else:
                parse_errors += 1
                # Still add to results for counting
                parsed_results.append({
                    'chat_id': row.get('conversation_id', f'chat_{idx}'),
                    'categories': [],
                    'intervention_or_transfer': 'Parse_Error',
                    'category_causing_intervention_transfer': 'Parse_Error',
                    'original_output': llm_output
                })
        
        print(f"✅ Successfully parsed: {len(parsed_results) - parse_errors}/{len(df)} conversations")
        if parse_errors > 0:
            print(f"⚠️  Parse errors: {parse_errors}")
        
        # Create results DataFrame
        results_df = pd.DataFrame(parsed_results)
        
        # Print intervention/transfer breakdown
        intervention_counts = Counter(results_df['intervention_or_transfer'])
        print(f"\n🔄 Intervention/Transfer Breakdown:")
        for int_type, count in intervention_counts.most_common():
            percentage = (count / len(results_df)) * 100
            print(f"  {int_type}: {count} ({percentage:.1f}%)")
        
        return results_df

    def create_summary_report(self, results_df, department, output_filename):
        """Create clean summary report from parsed results"""
        
        # Get all unique categories from all chats
        all_categories = set()
        for categories_list in results_df['categories']:
            all_categories.update(categories_list)
        
        # Calculate overall percentage of chats not handled by bot
        total_chats = len(results_df)
        chats_not_handled = len(results_df[results_df['intervention_or_transfer'].isin(['Intervention', 'Transfer'])])
        pct_all_chats_not_handled = (chats_not_handled / total_chats * 100) if total_chats > 0 else 0
        
        summary_data = []
        
        # Process each category
        for category in sorted(all_categories):
            if category in ['Parse_Error', 'N/A', '']:
                continue  # Skip invalid categories
            
            # Find all chats that contain this category
            chats_with_category = []
            for idx, row in results_df.iterrows():
                if category in row['categories']:
                    chats_with_category.append(row)
            
            category_count = len(chats_with_category)
            
            if category_count == 0:
                continue
            
            # Calculate metrics
            category_pct = (category_count / total_chats * 100) if total_chats > 0 else 0
            
            # Count by intervention/transfer status for this category
            chats_handled_by_bot = sum(1 for chat in chats_with_category if chat['intervention_or_transfer'] == 'N/A')
            chats_intervention = sum(1 for chat in chats_with_category if chat['intervention_or_transfer'] == 'Intervention')
            chats_transfer = sum(1 for chat in chats_with_category if chat['intervention_or_transfer'] == 'Transfer')
            
            # Calculate percentages relative to category count
            coverage_per_category_pct = (chats_handled_by_bot / category_count * 100) if category_count > 0 else 0
            intervention_by_agent_pct = (chats_intervention / category_count * 100) if category_count > 0 else 0
            transferred_by_bot_pct = (chats_transfer / category_count * 100) if category_count > 0 else 0
            
            summary_data.append({
                'Category': category,
                'Count': category_count,
                'Category %': f"{category_pct:.2f}%",
                'Coverage Per Category %': f"{coverage_per_category_pct:.2f}%",
                'Intervention By Agent %': f"{intervention_by_agent_pct:.2f}%",
                'Transferred by Bot %': f"{transferred_by_bot_pct:.2f}%",
                '%AllChatsNotHandled': f"{pct_all_chats_not_handled:.2f}%"
            })
        
        # Create summary DataFrame
        summary_df = pd.DataFrame(summary_data)
        
        # Sort by Count (descending)
        if len(summary_df) > 0:
            summary_df = summary_df.sort_values('Count', ascending=False)
        
        # Save summary
        summary_df.to_csv(output_filename, index=False)
        print(f"💾 Summary saved to: {output_filename}")
        
        # Show quick summary
        print(f"\n📊 Quick Summary for {department}:")
        print(f"Total conversations analyzed: {total_chats}")
        print(f"Overall chats not handled by bot: {chats_not_handled} ({pct_all_chats_not_handled:.1f}%)")
        
        # Show top 5 categories by count
        if len(summary_df) > 0:
            print(f"\nTop categories by volume:")
            for i, row in summary_df.head(5).iterrows():
                print(f"  {i+1}. {row['Category']}: {row['Count']} chats ({row['Category %']})")
                print(f"      Coverage: {row['Coverage Per Category %']}, Intervention: {row['Intervention By Agent %']}, Transfer: {row['Transferred by Bot %']}")
        
        # Show overall intervention/transfer split
        int_counts = results_df['intervention_or_transfer'].value_counts()
        print(f"\nOverall Intervention/Transfer split:")
        for int_type, count in int_counts.items():
            percentage = (count / total_chats * 100)
            print(f"  {int_type}: {count} ({percentage:.1f}%)")
        
        return summary_df

    def find_categorizing_files(self):
        """Find all categorizing output files in the date-based directory structure"""
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        llm_outputs_dir = f"outputs/LLM_outputs/{date_folder}"
        
        if not os.path.exists(llm_outputs_dir):
            print(f"❌ Directory {llm_outputs_dir} not found")
            return []
        
        categorizing_files = []
        for filename in os.listdir(llm_outputs_dir):
            if filename.startswith('categorizing_') and filename.endswith('.csv'):
                filepath = os.path.join(llm_outputs_dir, filename)
                
                # Extract department from filename: categorizing_{dept}_{mm}_{dd}.csv
                name_part = filename[13:-4]  # Remove 'categorizing_' and '.csv'
                parts = name_part.split('_')
                if len(parts) >= 3:
                    dept_key_parts = parts[:-2]  # Remove last 2 parts (month, day)
                    dept_key = '_'.join(dept_key_parts)
                    categorizing_files.append((filepath, dept_key, filename))
        
        return categorizing_files

    def process_all_departments(self):
        """Process categorizing results for all departments"""
        files = self.find_categorizing_files()
        
        if not files:
            print("❌ No categorizing files found")
            return False
        
        success_count = 0
        for filepath, dept_key, filename in files:
            try:
                print(f"\n📊 Processing {filename}...")
                
                # Analyze the data
                results_df = self.analyze_categorizing_data(filepath)
                if results_df is None:
                    continue
                
                # Create proper department name
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
                
                # Create summary report
                output_filename = f"{self.categorizing_dir}/{dept_name}_Categorizing_Summary.csv"
                summary_df = self.create_summary_report(results_df, dept_name, output_filename)
                
                print(f"✅ Completed {dept_name}")
                success_count += 1
                
            except Exception as e:
                print(f"❌ Error processing {filename}: {str(e)}")
                continue
        
        print(f"\n🎉 Categorizing post-processing completed!")
        print(f"   Processed: {success_count}/{len(files)} departments")
        return success_count > 0


def main():
    """Main function for standalone usage"""
    processor = CategorizingProcessor()
    processor.process_all_departments()


if __name__ == "__main__":
    main() 