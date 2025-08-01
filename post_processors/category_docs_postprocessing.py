#!/usr/bin/env python3
"""
Category Docs Post-Processor
Analyzes the output from category_docs analysis and creates clean summary statistics

Reads: LLM_outputs/{date}/category_docs_{dept_name}_{date}.csv
Outputs: Clean CSV with columns:
- Category: The conversation category 
- Count: Number of conversations in this category
- Percentage: Percentage of all conversations in this category
- Clinic Recommendation: Count of conversations with Clinic Recommendation = Yes
- OTC Medication Advice: Count of conversations with OTC Medication Advice = Yes
(Sorted by count, descending)
"""

import pandas as pd
import json
import os
from datetime import datetime, timedelta
from collections import Counter


class CategoryDocsProcessor:
    """Post processor for category docs analysis results"""
    
    def __init__(self):
        # Create directory with date subfolder
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        self.category_docs_dir = f"outputs/category_docs/{date_folder}"
        os.makedirs(self.category_docs_dir, exist_ok=True)
    
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

    def analyze_category_docs_data(self, input_file):
        """
        Analyze category docs prompt results and create clean summary CSV
        
        Args:
            input_file: Path to category docs CSV file
        """
        print(f"📊 Analyzing category docs results from: {input_file}")
        
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
                # Extract categories from the array, handling single values too
                categories = parsed.get('category', [])
                if isinstance(categories, str):
                    categories = [categories]
                elif not isinstance(categories, list):
                    categories = ['null']
                
                # Get the primary category (first one, or 'null' if empty)
                primary_category = categories[0] if categories else 'null'
                
                parsed_results.append({
                    'chat_id': row.get('conversation_id', f'chat_{idx}'),
                    'category': primary_category,
                    'all_categories': categories,
                    'clinic_recommendation': parsed.get('Clinic Recommendation', 'No'),
                    'otc_medication_advice': parsed.get('OTC Medication Advice', 'No'),
                    'reasoning': parsed.get('reasoning', ''),
                    'original_output': llm_output
                })
            else:
                parse_errors += 1
                # Still add to results for counting
                parsed_results.append({
                    'chat_id': row.get('conversation_id', f'chat_{idx}'),
                    'category': 'Parse_Error',
                    'all_categories': ['Parse_Error'],
                    'clinic_recommendation': 'No',
                    'otc_medication_advice': 'No',
                    'reasoning': '',
                    'original_output': llm_output
                })
        
        print(f"✅ Successfully parsed: {len(parsed_results) - parse_errors}/{len(df)} conversations")
        if parse_errors > 0:
            print(f"⚠️  Parse errors: {parse_errors}")
        
        # Create results DataFrame
        results_df = pd.DataFrame(parsed_results)
        
        # Count categories
        category_counts = Counter(results_df['category'])
        clinic_rec_counts = Counter(results_df['clinic_recommendation'])
        otc_counts = Counter(results_df['otc_medication_advice'])
        
        print(f"\n📋 Category Breakdown:")
        for category, count in category_counts.most_common():
            percentage = (count / len(results_df)) * 100
            print(f"  {category}: {count} ({percentage:.1f}%)")
        
        print(f"\n🏥 Clinic Recommendation: {clinic_rec_counts}")
        print(f"💊 OTC Medication Advice: {otc_counts}")
        
        return results_df

    def create_summary_report(self, results_df, department, output_filename):
        """Create clean summary report from parsed results"""
        
        total_chats = len(results_df)
        summary_data = []
        
        # Group by category and calculate statistics
        for category in results_df['category'].unique():
            if category == 'Parse_Error':
                continue  # Skip parse errors from summary
                
            category_data = results_df[results_df['category'] == category]
            category_count = len(category_data)
            
            # Count clinic recommendations and OTC advice in this category
            clinic_rec_yes = len(category_data[category_data['clinic_recommendation'] == 'Yes'])
            otc_yes = len(category_data[category_data['otc_medication_advice'] == 'Yes'])
            
            # Calculate percentage of all chats
            percentage = (category_count / total_chats * 100) if total_chats > 0 else 0
            
            summary_data.append([
                category,
                category_count,
                f"{percentage:.2f}%",
                clinic_rec_yes,
                otc_yes
            ])
        
        # Create summary DataFrame
        summary_df = pd.DataFrame(summary_data, columns=[
            'Category', 
            'Count', 
            'Percentage', 
            'Clinic Recommendation (Yes)', 
            'OTC Medication Advice (Yes)'
        ])
        
        # Sort by count (descending)
        if len(summary_df) > 0:
            summary_df = summary_df.sort_values('Count', ascending=False)
        
        # Save summary
        summary_df.to_csv(output_filename, index=False)
        print(f"💾 Summary saved to: {output_filename}")
        
        # Show quick summary
        print(f"\n📊 Quick Summary for {department}:")
        print(f"Total conversations analyzed: {total_chats}")
        
        # Show top categories
        if len(summary_df) > 0:
            print(f"\nTop categories by volume:")
            for i, (_, row) in enumerate(summary_df.head(5).iterrows()):
                print(f"  {i+1}. {row['Category']}: {row['Count']} conversations ({row['Percentage']})")
                if row['Clinic Recommendation (Yes)'] > 0:
                    print(f"      - Clinic Recommendations: {row['Clinic Recommendation (Yes)']}")
                if row['OTC Medication Advice (Yes)'] > 0:
                    print(f"      - OTC Medication Advice: {row['OTC Medication Advice (Yes)']}")
        
        # Show overall statistics
        total_clinic_rec = results_df['clinic_recommendation'].value_counts().get('Yes', 0)
        total_otc = results_df['otc_medication_advice'].value_counts().get('Yes', 0)
        
        print(f"\nOverall Statistics:")
        print(f"  Total with Clinic Recommendation: {total_clinic_rec} ({(total_clinic_rec/total_chats)*100:.1f}%)")
        print(f"  Total with OTC Medication Advice: {total_otc} ({(total_otc/total_chats)*100:.1f}%)")
        
        return summary_df

    def find_category_docs_files(self):
        """Find all category docs output files in the date-based directory structure"""
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        llm_outputs_dir = f"outputs/LLM_outputs/{date_folder}"
        
        if not os.path.exists(llm_outputs_dir):
            print(f"❌ Directory {llm_outputs_dir} not found")
            return []
        
        category_docs_files = []
        for filename in os.listdir(llm_outputs_dir):
            if filename.startswith('category_docs_') and filename.endswith('.csv'):
                filepath = os.path.join(llm_outputs_dir, filename)
                
                # Extract department from filename: category_docs_{dept}_{mm}_{dd}.csv
                name_part = filename[14:-4]  # Remove 'category_docs_' and '.csv'
                parts = name_part.split('_')
                if len(parts) >= 3:
                    dept_key_parts = parts[:-2]  # Remove last 2 parts (month, day)
                    dept_key = '_'.join(dept_key_parts)
                    category_docs_files.append((filepath, dept_key, filename))
        
        return category_docs_files

    def process_all_departments(self):
        """Process category docs results for all departments"""
        files = self.find_category_docs_files()
        
        if not files:
            print("❌ No category docs files found")
            return False
        
        success_count = 0
        for filepath, dept_key, filename in files:
            try:
                print(f"\n📊 Processing {filename}...")
                
                # Analyze the data
                results_df = self.analyze_category_docs_data(filepath)
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
                output_filename = f"{self.category_docs_dir}/{dept_name}_Category_Docs_Summary.csv"
                summary_df = self.create_summary_report(results_df, dept_name, output_filename)
                
                print(f"✅ Completed {dept_name}")
                success_count += 1
                
            except Exception as e:
                print(f"❌ Error processing {filename}: {str(e)}")
                continue
        
        print(f"\n🎉 Category docs post-processing completed!")
        print(f"   Processed: {success_count}/{len(files)} departments")
        return success_count > 0


def main():
    """Main function for standalone usage"""
    processor = CategoryDocsProcessor()
    processor.process_all_departments()


if __name__ == "__main__":
    main() 