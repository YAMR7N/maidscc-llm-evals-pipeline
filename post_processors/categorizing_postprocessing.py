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
                parsed_results.append({
                    'chat_id': row.get('conversation_id', f'chat_{idx}'),
                    'intervention_or_transfer': parsed.get('InterventionOrTransfer', 'Unknown'),
                    'category': parsed.get('Category', 'Unknown'),
                    'original_output': llm_output
                })
            else:
                parse_errors += 1
                # Still add to results for counting
                parsed_results.append({
                    'chat_id': row.get('conversation_id', f'chat_{idx}'),
                    'intervention_or_transfer': 'Parse_Error',
                    'category': 'Parse_Error',
                    'original_output': llm_output
                })
        
        print(f"✅ Successfully parsed: {len(parsed_results) - parse_errors}/{len(df)} conversations")
        if parse_errors > 0:
            print(f"⚠️  Parse errors: {parse_errors}")
        
        # Create results DataFrame
        results_df = pd.DataFrame(parsed_results)
        
        # Count categories
        category_counts = Counter(results_df['category'])
        intervention_counts = Counter(results_df['intervention_or_transfer'])
        
        print(f"\n📋 Category Breakdown:")
        for category, count in category_counts.most_common():
            percentage = (count / len(results_df)) * 100
            print(f"  {category}: {count} ({percentage:.1f}%)")
        
        print(f"\n🔄 Intervention/Transfer Breakdown:")
        for int_type, count in intervention_counts.most_common():
            percentage = (count / len(results_df)) * 100
            print(f"  {int_type}: {count} ({percentage:.1f}%)")
        
        return results_df

    def create_summary_report(self, results_df, department, output_filename):
        """Create clean summary report from parsed results"""
        
        # Create new format: Category analysis with intervention/transfer percentages per category
        total_chats = len(results_df)
        summary_data = []
        
        # Group by category and calculate percentages
        for category in results_df['category'].unique():
            if category in ['Parse_Error', 'N/A']:
                continue  # Skip parse errors and N/A from analysis
                
            category_data = results_df[results_df['category'] == category]
            category_total = len(category_data)
            
            # Count intervention/transfer within this category
            intervention_in_category = len(category_data[category_data['intervention_or_transfer'] == 'Intervention'])
            transfer_in_category = len(category_data[category_data['intervention_or_transfer'] == 'Transfer'])
            
            # Calculate percentages as proportion of ALL chats (so they sum to % of ALL chats)
            pct_intervention = (intervention_in_category / total_chats * 100) if total_chats > 0 else 0
            pct_transfer = (transfer_in_category / total_chats * 100) if total_chats > 0 else 0
            pct_of_all_chats = (category_total / total_chats * 100) if total_chats > 0 else 0
            
            summary_data.append([
                category,
                f"{pct_intervention:.2f}%",
                f"{pct_transfer:.2f}%", 
                f"{pct_of_all_chats:.2f}%"
            ])
        
        # Create summary DataFrame with new format
        summary_df = pd.DataFrame(summary_data, columns=['Category', '% Intervention', '% Transfers', '% of ALL chats'])
        
        # Sort by % of ALL chats (descending) - need to convert percentage strings to float for sorting
        if len(summary_df) > 0:
            summary_df['sort_key'] = summary_df['% of ALL chats'].str.rstrip('%').astype(float)
            summary_df = summary_df.sort_values('sort_key', ascending=False).drop('sort_key', axis=1)
        
        # Save summary
        summary_df.to_csv(output_filename, index=False)
        print(f"💾 Summary saved to: {output_filename}")
        
        # Show quick summary
        print(f"\n📊 Quick Summary for {department}:")
        print(f"Total conversations analyzed: {len(results_df)}")
        
        # Show top 5 categories by % of all chats
        if len(summary_df) > 0:
            print(f"\nTop categories by volume:")
            for i, (_, row) in enumerate(summary_df.head(5).iterrows()):
                print(f"  {i+1}. {row['Category']}: {row['% of ALL chats']} of all chats")
                print(f"      (Intervention: {row['% Intervention']}, Transfer: {row['% Transfers']})")
        
        # Show overall intervention/transfer split
        int_counts = results_df['intervention_or_transfer'].value_counts()
        print(f"\nOverall Intervention/Transfer split:")
        for int_type, count in int_counts.items():
            percentage = (count / len(results_df)) * 100
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