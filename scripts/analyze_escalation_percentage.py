#!/usr/bin/env python3
"""
Analyze policy escalation results to calculate escalation percentage
"""

import pandas as pd
import json
import sys
from pathlib import Path

def analyze_escalation_results(filepath):
    """Analyze policy escalation results and calculate percentages"""
    
    print(f"Analyzing: {filepath}")
    print("="*60)
    
    # Read the CSV file
    df = pd.read_csv(filepath)
    
    total_conversations = len(df)
    escalation_count = 0
    policy_counts = {}
    
    # Process each row
    for idx, row in df.iterrows():
        try:
            llm_output = row['llm_output']
            
            # Parse JSON output
            if isinstance(llm_output, str) and llm_output.strip():
                # Clean the output if needed
                output_json = json.loads(llm_output)
                
                # Count escalations
                if output_json.get('CustomerEscalation', False):
                    escalation_count += 1
                    
                    # Track which policies caused escalations
                    policy = output_json.get('PolicyToCauseEscalation', 'N/A')
                    if policy != 'N/A':
                        # Handle multiple policies separated by semicolons
                        if ';' in policy:
                            policies = [p.strip() for p in policy.split(';')]
                            for p in policies:
                                policy_counts[p] = policy_counts.get(p, 0) + 1
                        else:
                            policy_counts[policy] = policy_counts.get(policy, 0) + 1
                            
        except Exception as e:
            print(f"Error processing row {idx}: {e}")
            continue
    
    # Calculate percentage
    escalation_percentage = (escalation_count / total_conversations * 100) if total_conversations > 0 else 0
    
    # Print results
    print(f"\n📊 ESCALATION ANALYSIS RESULTS:")
    print(f"   Total conversations analyzed: {total_conversations}")
    print(f"   Conversations with escalation: {escalation_count}")
    print(f"   Escalation percentage: {escalation_percentage:.1f}%")
    
    # Print top policies causing escalations
    if policy_counts:
        print(f"\n📋 TOP POLICIES CAUSING ESCALATION:")
        sorted_policies = sorted(policy_counts.items(), key=lambda x: x[1], reverse=True)
        
        for i, (policy, count) in enumerate(sorted_policies[:5], 1):
            percentage = (count / escalation_count * 100) if escalation_count > 0 else 0
            # Truncate long policies for display
            display_policy = policy[:100] + "..." if len(policy) > 100 else policy
            print(f"\n   {i}. [{count} times, {percentage:.1f}% of escalations]")
            print(f"      {display_policy}")
    
    return {
        'total_conversations': total_conversations,
        'escalation_count': escalation_count,
        'escalation_percentage': escalation_percentage,
        'policy_counts': policy_counts
    }

if __name__ == "__main__":
    # Analyze August 3rd results
    aug3_file = "outputs/LLM_outputs/2025-08-03/policy_escalation_doctors_08_03.csv"
    
    if Path(aug3_file).exists():
        analyze_escalation_results(aug3_file)
    else:
        print(f"❌ File not found: {aug3_file}")
    
    # Also check if August 4th results exist
    print("\n" + "="*60 + "\n")
    aug4_file = "outputs/LLM_outputs/2025-08-04/policy_escalation_doctors_08_04.csv"
    
    if Path(aug4_file).exists():
        print("Also found August 4th results:")
        analyze_escalation_results(aug4_file)