#!/usr/bin/env python3
"""
Categorizing Post-Processor
Analyzes the output from categorizing analysis and creates clean summary statistics

Reads: LLM_outputs/{date}/categorizing_{dept_name}_{date}.csv
Outputs: Clean CSV with columns:
- Category: The conversation category (N/A excluded)
- Count: Number of conversations in this category
- Category %: Percentage of all chats that belong to this category
- Coverage Per Category %: Percentage of chats IN THIS CATEGORY that were handled by bot
- Intervention By Agent %: Percentage of ALL chats that had intervention in this category
- Transferred by Bot %: Percentage of ALL chats that were transferred in this category
- %AllChatsNotHandled: Sum of Intervention + Transfer percentages (all relative to total chats)

Note: All percentages except "Coverage Per Category %" are calculated relative to TOTAL chats.
      "Coverage Per Category %" is calculated relative to the category's count.
(Sorted by Count, descending)
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
            # Handle new format where columns are already extracted
            if all(col in df.columns for col in ['Categories', 'InterventionOrTransfer?', 'CategoryCausingInterventionOrTransfer']):
                print(f"ℹ️  Using pre-extracted format (no llm_output column)")
                return self.analyze_pre_extracted_data(df)
            else:
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

    def analyze_pre_extracted_data(self, df):
        """Analyze categorizing data where columns are already extracted"""
        parsed_results = []
        
        for idx, row in df.iterrows():
            # Parse comma-separated categories
            categories_str = str(row.get('Categories', ''))
            if pd.isna(row.get('Categories')) or categories_str == 'nan':
                categories_list = []
            else:
                categories_list = [cat.strip() for cat in categories_str.split(',') if cat.strip() and cat.strip() != 'N/A']
            
            intervention_or_transfer = str(row.get('InterventionOrTransfer?', 'N/A'))
            if pd.isna(row.get('InterventionOrTransfer?')) or intervention_or_transfer == 'nan':
                intervention_or_transfer = 'N/A'
                
            category_causing = str(row.get('CategoryCausingInterventionOrTransfer', 'N/A'))
            if pd.isna(row.get('CategoryCausingInterventionOrTransfer')) or category_causing == 'nan':
                category_causing = 'N/A'
            
            parsed_results.append({
                'chat_id': row.get('conversation_id', f'chat_{idx}'),
                'categories': categories_list,
                'intervention_or_transfer': intervention_or_transfer,
                'category_causing_intervention_transfer': category_causing,
                'original_output': f"Pre-extracted: Categories={categories_str}, Intervention={intervention_or_transfer}"
            })
        
        print(f"✅ Successfully parsed: {len(parsed_results)}/{len(df)} conversations")
        
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
        
        total_chats = len(results_df)
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
            
            # Calculate coverage percentage relative to category count, others relative to total chats
            coverage_per_category_pct = (chats_handled_by_bot / category_count * 100) if category_count > 0 else 0
            intervention_by_agent_pct = (chats_intervention / total_chats * 100) if total_chats > 0 else 0
            transferred_by_bot_pct = (chats_transfer / total_chats * 100) if total_chats > 0 else 0
            
            # %AllChatsNotHandled = transferred by bot + intervention by agent (both relative to total chats)
            pct_all_chats_not_handled = intervention_by_agent_pct + transferred_by_bot_pct
            
            # Note: intervention_by_agent_pct + transferred_by_bot_pct will sum to the portion of this category
            # relative to total chats that were not handled by bot (coverage_per_category_pct is different)
            
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
        
        # Add Total row with overall intervention/transfer percentages
        total_intervention = sum(1 for _, row in results_df.iterrows() if row['intervention_or_transfer'] == 'Intervention')
        total_transfer = sum(1 for _, row in results_df.iterrows() if row['intervention_or_transfer'] == 'Transfer')
        total_na = sum(1 for _, row in results_df.iterrows() if row['intervention_or_transfer'] == 'N/A')
        
        # Calculate percentages relative to total chats
        total_intervention_pct = (total_intervention / total_chats * 100) if total_chats > 0 else 0
        total_transfer_pct = (total_transfer / total_chats * 100) if total_chats > 0 else 0
        total_coverage_pct = (total_na / total_chats * 100) if total_chats > 0 else 0
        total_not_handled_pct = total_intervention_pct + total_transfer_pct
        
        # Add Total row
        total_row = pd.DataFrame([{
            'Category': 'TOTAL',
            'Count': total_chats,
            'Category %': '100.00%',
            'Coverage Per Category %': f"{total_coverage_pct:.2f}%",
            'Intervention By Agent %': f"{total_intervention_pct:.2f}%",
            'Transferred by Bot %': f"{total_transfer_pct:.2f}%",
            '%AllChatsNotHandled': f"{total_not_handled_pct:.2f}%"
        }])
        
        # Append Total row to summary
        summary_df = pd.concat([summary_df, total_row], ignore_index=True)
        
        # Save summary
        summary_df.to_csv(output_filename, index=False)
        print(f"💾 Summary saved to: {output_filename}")
        
        # Show quick summary
        print(f"\n📊 Quick Summary for {department}:")
        print(f"Total conversations analyzed: {total_chats}")
        
        # Show top 5 categories by count
        if len(summary_df) > 0:
            print(f"\nTop categories by volume:")
            for i, row in summary_df.head(5).iterrows():
                print(f"  {i+1}. {row['Category']}: {row['Count']} chats ({row['Category %']} of all chats)")
                print(f"      Bot handled: {row['Coverage Per Category %']} of all chats")
                print(f"      Intervention: {row['Intervention By Agent %']} of all chats")  
                print(f"      Transfer: {row['Transferred by Bot %']} of all chats")
        
        # Show overall intervention/transfer split
        int_counts = results_df['intervention_or_transfer'].value_counts()
        print(f"\nOverall Intervention/Transfer split:")
        for int_type, count in int_counts.items():
            percentage = (count / total_chats * 100)
            print(f"  {int_type}: {count} ({percentage:.1f}%)")
        
        # Show TOTAL row info
        total_row_data = summary_df[summary_df['Category'] == 'TOTAL'].iloc[0]
        print(f"\n📊 TOTAL Summary:")
        print(f"  Coverage (Bot handled): {total_row_data['Coverage Per Category %']}")
        print(f"  Intervention by Agent: {total_row_data['Intervention By Agent %']}")
        print(f"  Transferred by Bot: {total_row_data['Transferred by Bot %']}")
        print(f"  Total Not Handled: {total_row_data['%AllChatsNotHandled']}")
        
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