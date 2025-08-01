#!/usr/bin/env python3
"""
Policy Frequency Analysis Script
Analyzes policies causing escalation and generates frequency table

Reads: LLM_outputs/{date}/policy_escalation_{dept_name}_{date}.csv
Outputs: Policy frequency table saved in outputs/policy_escalation/{date}/
"""

import pandas as pd
import json
import os
import sys
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path

def safe_json_parse(json_str):
    """Safely parse JSON string from LLM output"""
    try:
        if pd.isna(json_str) or not json_str.strip():
            return {}
        
        # Clean up common JSON formatting issues
        cleaned = str(json_str).strip()
        
        # Remove markdown code blocks if present
        if cleaned.startswith('```json'):
            cleaned = cleaned.replace('```json', '').replace('```', '').strip()
        elif cleaned.startswith('```'):
            cleaned = cleaned.replace('```', '').strip()
        
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON decode error for: {str(json_str)[:50]}... Error: {e}")
        return {}
    except Exception as e:
        print(f"⚠️  Parse error for: {str(json_str)[:50]}... Error: {e}")
        return {}

def analyze_policy_frequency(filepath):
    """Analyze policy escalation frequency from CSV file"""
    print(f"📊 Analyzing policy frequency: {os.path.basename(filepath)}")
    
    # Read the CSV
    df = pd.read_csv(filepath)
    
    if df.empty:
        print("⚠️  Empty DataFrame")
        return None
    
    # Extract policies from LLM outputs
    policies = []
    total_conversations = len(df)
    valid_jsons = 0
    escalations_found = 0
    
    for _, row in df.iterrows():
        conversation_id = str(row['conversation_id'])
        llm_output = row['llm_output']
        
        # Parse JSON output
        parsed_output = safe_json_parse(llm_output)
        
        if parsed_output and isinstance(parsed_output, dict):
            valid_jsons += 1
            
            # Get PolicyToCauseEscalation
            policy = parsed_output.get('PolicyToCauseEscalation', 'N/A')
            
            # Only count non-N/A policies (these are the actual escalations)
            if policy and policy != 'N/A':
                escalations_found += 1
                # Clean up policy text for better readability
                clean_policy = policy.strip()
                
                # Truncate very long policies for the table
                # if len(clean_policy) > 150:
                #     clean_policy = clean_policy[:150] + "..."
                
                policies.append(clean_policy)
    
    if not policies:
        print("⚠️  No policy escalations found (all PolicyToCauseEscalation were 'N/A')")
        return None
    
    # Count policy frequencies
    policy_counts = Counter(policies)
    
    # Create frequency table
    frequency_data = []
    for policy, count in policy_counts.most_common():
        frequency_data.append({
            'Policy': policy,
            'Count': count,
            'Percentage': f"{(count / escalations_found * 100):.1f}%"
        })
    
    frequency_df = pd.DataFrame(frequency_data)
    
    print(f"✅ Analysis complete:")
    print(f"   Total conversations: {total_conversations}")
    print(f"   Valid JSON outputs: {valid_jsons}")
    print(f"   Policy escalations found: {escalations_found}")
    print(f"   Unique policies causing escalation: {len(policy_counts)}")
    
    return frequency_df, {
        'total_conversations': total_conversations,
        'valid_jsons': valid_jsons,
        'escalations_found': escalations_found,
        'unique_policies': len(policy_counts)
    }

def find_policy_escalation_files(date_str=None):
    """Find policy escalation files for a specific date"""
    if date_str is None:
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        date_str = yesterday.strftime('%m_%d')
    else:
        # Parse provided date
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date_folder = date_str
            date_str = date_obj.strftime('%m_%d')
        except ValueError:
            print(f"❌ Invalid date format. Use YYYY-MM-DD")
            return []
    
    llm_outputs_dir = f"outputs/LLM_outputs/{date_folder}"
    
    if not os.path.exists(llm_outputs_dir):
        print(f"❌ LLM outputs directory not found: {llm_outputs_dir}")
        return []
    
    policy_files = []
    for filename in os.listdir(llm_outputs_dir):
        if filename.startswith('policy_escalation_') and filename.endswith(f'_{date_str}.csv'):
            filepath = os.path.join(llm_outputs_dir, filename)
            policy_files.append((filepath, filename, date_folder))
    
    return policy_files

def save_analysis_results(frequency_df, stats, output_filename):
    """Save clean analysis results"""
    
    # Save just the frequency data - no formatting or comments
    frequency_df.to_csv(output_filename, index=False)
    print(f"💾 Policy frequency analysis saved: {output_filename}")
    
    return output_filename

def main():
    """Main function"""
    # Parse command line arguments
    date_filter = None
    if len(sys.argv) > 1:
        date_filter = sys.argv[1]
    
    print(f"🔍 Policy Escalation Frequency Analysis")
    if date_filter:
        print(f"📅 Analyzing data for: {date_filter}")
    else:
        print(f"📅 Analyzing data for yesterday")
    
    # Find policy escalation files
    policy_files = find_policy_escalation_files(date_filter)
    
    if not policy_files:
        print("❌ No policy escalation files found")
        return False
    
    success_count = 0
    
    for filepath, filename, date_folder in policy_files:
        try:
            print(f"\n📁 Processing: {filename}")
            
            # Analyze policy frequency
            result = analyze_policy_frequency(filepath)
            if not result:
                continue
            
            frequency_df, stats = result
            
            # Extract department name from filename
            import re
            dept_match = re.match(r'policy_escalation_(.+)_\d{2}_\d{2}\.csv$', filename)
            if dept_match:
                dept_key = dept_match.group(1)
                dept_name = dept_key.replace('_', ' ').title()
                
                # Handle specific mappings
                if dept_name == 'Mv Resolvers':
                    dept_name = 'MV Resolvers'
                elif dept_name == 'Mv Sales':
                    dept_name = 'MV Sales'
                elif dept_name == 'Cc Sales':
                    dept_name = 'CC Sales'
                elif dept_name == 'Cc Resolvers':
                    dept_name = 'CC Resolvers'
            else:
                dept_name = "Unknown"
            
            # Create output directory
            output_dir = f"outputs/policy_escalation/{date_folder}"
            os.makedirs(output_dir, exist_ok=True)
            
            # Save analysis
            output_filename = f"{output_dir}/{dept_name}_Policy_Frequency_Analysis.csv"
            save_analysis_results(frequency_df, stats, output_filename)
            
            success_count += 1
            print(f"✅ Completed analysis for {dept_name}")
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}")
            continue
    
    print(f"\n🎉 Policy frequency analysis completed!")
    print(f"✅ Successfully processed: {success_count}/{len(policy_files)} files")
    
    return success_count > 0

if __name__ == "__main__":
    main() 