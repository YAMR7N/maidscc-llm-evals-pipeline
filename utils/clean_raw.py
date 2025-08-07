import pandas as pd
from datetime import datetime
import numpy as np
import re



def clean_raw_data(csv_path, output_path, filter_agent_messages=False):
    """
    Clean the raw data by determining which tool call is the correct one based on 
    matching "Tool Creation Date" with "Message Sent Time" to find the best match.
    Clear tool data for duplicate tool calls.
    Also excludes conversations that don't contain any bot messages.
    
    Args:
        csv_path (str): Path to the input CSV file with Tool Creation Date
        output_path (str): Path to save the cleaned CSV file
        filter_agent_messages (bool): If True, removes all agent messages from the data
    
    Returns:
        pd.DataFrame: Cleaned dataframe
    """
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Strip whitespace from column names to handle inconsistent exports
    df.columns = df.columns.str.strip()
    
    # Note: Datetime cleaning already done in fetchtableau.py, no need to clean again
    
    # Convert datetime columns (cleaning already done in main script)
    df['Message Sent Time'] = pd.to_datetime(df['Message Sent Time'], errors='coerce', format='mixed')
    
    print("Starting data cleaning process...")
    print(f"Total rows: {len(df)}")
    
    # Filter out conversations that don't have any bot messages
    conversations_with_bot = set()
    for conv_id in df['Conversation ID'].unique():
        conv_df = df[df['Conversation ID'] == conv_id]
        if any(conv_df['Sent By'].str.lower().str.contains('bot', na=False)):
            conversations_with_bot.add(conv_id)
    
    print(f"Conversations with bot messages: {len(conversations_with_bot)}")
    print(f"Conversations without bot messages (will be excluded): {len(df['Conversation ID'].unique()) - len(conversations_with_bot)}")
    
    # Filter dataframe to only include conversations with bot messages
    df = df[df['Conversation ID'].isin(conversations_with_bot)]
    print(f"Rows after excluding conversations without bot: {len(df)}")
    
    # Create a copy to work with
    cleaned_df = df.copy()
    
    # Track statistics
    tools_processed = 0
    duplicates_cleared = 0
    
    # Group by conversation ID
    for conv_id in df['Conversation ID'].unique():
        conv_df = df[df['Conversation ID'] == conv_id].copy()
        
        # Get all rows that have tool data
        tool_rows = conv_df[conv_df['Tool Creation Date'].notna() & 
                           (conv_df['Tool Creation Date'] != '')].copy()
        
        if len(tool_rows) == 0:
            continue
            
        # Convert Tool Creation Date to datetime for comparison (cleaning already done)
        tool_rows['Tool Creation Date'] = pd.to_datetime(tool_rows['Tool Creation Date'], errors='coerce', format='mixed')
        
        # Group by Tool Creation Date, Tool name, and JSON output for more secure grouping
        # Create a composite key for grouping identical tool calls
        tool_rows['tool_group_key'] = (
            tool_rows['Tool Creation Date'].astype(str) + '_' +
            tool_rows['Tools'].fillna('') + '_' +
            tool_rows['Tools Json Output'].fillna('')
        )
        
        # Group by the composite key (same tool call group)
        for group_key in tool_rows['tool_group_key'].unique():
            same_tool_group = tool_rows[tool_rows['tool_group_key'] == group_key]
            
            if len(same_tool_group) <= 1:
                continue  # No duplicates to clean
                
            tools_processed += 1
            
            # Get the creation date for this group
            creation_date = same_tool_group['Tool Creation Date'].iloc[0]
            
            # Find the message with the closest Message Sent Time to Tool Creation Date
            # Filter for rows where Sent By is Bot
            bot_rows = same_tool_group[same_tool_group['Sent By'].str.lower() == 'bot']
            
            if len(bot_rows) > 0:
                # If we have bot messages, find the best match among them
                time_differences = abs(bot_rows['Message Sent Time'] - creation_date)
                if len(time_differences) > 0:
                    best_match_idx = time_differences.idxmin()
                else:
                    best_match_idx = same_tool_group.index[0]  # fallback to first row
            else:
                # If no bot messages, fall back to original behavior
                time_differences = abs(same_tool_group['Message Sent Time'] - creation_date)
                if len(time_differences) > 0:
                    best_match_idx = time_differences.idxmin()
                else:
                    best_match_idx = same_tool_group.index[0]  # fallback to first row
            
            # Clear tool data for all rows except the best match
            for idx in same_tool_group.index:
                if idx != best_match_idx:
                    # Clear tool data for duplicates (convert to appropriate types)
                    cleaned_df.at[idx, 'Tool SUCCESS'] = None
                    cleaned_df.at[idx, 'Tools'] = None
                    cleaned_df.at[idx, 'Tools Json Output'] = None
                    cleaned_df.at[idx, 'Tool Creation Date'] = None
                    duplicates_cleared += 1
    
    print(f"Tool duplicates cleared: {duplicates_cleared}")
    print("Applying additional message deduplication...")
    
    # Additional cleaning layer: Remove duplicate messages
    initial_rows = len(cleaned_df)
    cleaned_df['message_key'] = (
        cleaned_df['Conversation ID'].astype(str) + '_' +
        cleaned_df['TEXT'].fillna('') + '_' +
        cleaned_df['Message Sent Time'].astype(str) + '_' +
        cleaned_df['Sent By'].fillna('') + '_' +
        cleaned_df['Tools'].fillna('') + '_' +
        cleaned_df['Tool Creation Date'].fillna('') + '_' +
        cleaned_df['Tools Json Output'].fillna('')
    )
    
    # Keep only the first occurrence of each message
    cleaned_df = cleaned_df.drop_duplicates(subset=['message_key'], keep='first')
    
    # Remove the temporary message_key column
    cleaned_df = cleaned_df.drop('message_key', axis=1)
    
    message_duplicates_removed = initial_rows - len(cleaned_df)
    
    # Apply agent message filtering if requested
    if filter_agent_messages:
        print("Filtering out agent messages...")
        initial_count = len(cleaned_df)
        # Filter out rows where 'Sent By' is 'Agent' (case-insensitive)
        cleaned_df = cleaned_df[~cleaned_df['Sent By'].str.lower().str.match(r'^agent(_\d+)?$', na=False)]
        agent_messages_removed = initial_count - len(cleaned_df)
        print(f"Agent messages removed: {agent_messages_removed}")
    else:
        agent_messages_removed = 0
    
    # Convert datetime columns back to string format with seconds preserved
    # This ensures Excel will show the full datetime including seconds
    if 'Message Sent Time' in cleaned_df.columns:
        cleaned_df['Message Sent Time'] = cleaned_df['Message Sent Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    if 'Tool Creation Date' in cleaned_df.columns:
        # Only format non-null values
        mask = cleaned_df['Tool Creation Date'].notna()
        cleaned_df.loc[mask, 'Tool Creation Date'] = pd.to_datetime(cleaned_df.loc[mask, 'Tool Creation Date'], errors='coerce', format='mixed').dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Save the cleaned CSV
    cleaned_df.to_csv(output_path, index=False)
    
    print(f"Data cleaning completed!")
    print(f"Unique tool calls processed: {tools_processed}")
    print(f"Tool duplicate entries cleared: {duplicates_cleared}")
    print(f"Message duplicates removed: {message_duplicates_removed}")
    print(f"Total rows removed: {len(df) - len(cleaned_df)}")
    print(f"Final rows: {len(cleaned_df)}")
    print(f"Cleaned data saved to: {output_path}")
    
    return cleaned_df

def analyze_cleaning_results(original_df, cleaned_df):
    """
    Analyze the results of the cleaning process to verify the changes.
    
    Args:
        original_df (pd.DataFrame): Original dataframe
        cleaned_df (pd.DataFrame): Cleaned dataframe
    """
    print("\n" + "="*60)
    print("CLEANING ANALYSIS")
    print("="*60)
    
    # Count tool entries before and after
    original_tool_count = len(original_df[original_df['Tools'].notna() & (original_df['Tools'] != '')])
    cleaned_tool_count = len(cleaned_df[cleaned_df['Tools'].notna() & (cleaned_df['Tools'] != '')])
    
    print(f"Tool entries before cleaning: {original_tool_count}")
    print(f"Tool entries after cleaning: {cleaned_tool_count}")
    print(f"Tool entries removed: {original_tool_count - cleaned_tool_count}")
    print(f"Reduction percentage: {((original_tool_count - cleaned_tool_count) / original_tool_count * 100):.1f}%")
    
    # Sample comparison for first few conversations
    print(f"\nSample comparison for first conversation:")
    conv_id = original_df['Conversation ID'].iloc[0]
    
    original_conv = original_df[original_df['Conversation ID'] == conv_id]
    cleaned_conv = cleaned_df[cleaned_df['Conversation ID'] == conv_id]
    
    original_tools = original_conv[original_conv['Tools'].notna() & (original_conv['Tools'] != '')]
    cleaned_tools = cleaned_conv[cleaned_conv['Tools'].notna() & (cleaned_conv['Tools'] != '')]
    
    print(f"Conversation {conv_id}:")
    print(f"  - Original tool entries: {len(original_tools)}")
    print(f"  - Cleaned tool entries: {len(cleaned_tools)}")

def validate_cleaning(df):
    """
    Validate that the cleaning was done correctly by checking for remaining duplicates.
    
    Args:
        df (pd.DataFrame): Cleaned dataframe
    
    Returns:
        bool: True if validation passes, False otherwise
    """
    print("\n" + "="*60)
    print("VALIDATION")
    print("="*60)
    
    # Check for any remaining duplicate Tool Creation Dates within conversations
    validation_passed = True
    
    for conv_id in df['Conversation ID'].unique():
        conv_df = df[df['Conversation ID'] == conv_id]
        tool_rows = conv_df[conv_df['Tool Creation Date'].notna() & 
                           (conv_df['Tool Creation Date'] != '')]
        
        if len(tool_rows) == 0:
            continue
            
        # Check for duplicate Tool Creation Date values
        duplicate_dates = tool_rows['Tool Creation Date'].duplicated()
        if duplicate_dates.any():
            print(f"WARNING: Found duplicate Tool Creation Dates in conversation {conv_id}")
            validation_passed = False
    
    if validation_passed:
        print("✅ Validation PASSED: No duplicate Tool Creation Dates found")
    else:
        print("❌ Validation FAILED: Duplicate Tool Creation Dates still exist")
    
    return validation_passed

def clean_raw_data_main(input_file, output_file, filter_agent_messages=False):
    
    print("Reading original data...")
    original_df = pd.read_csv(input_file)
    
    print("Cleaning raw data...")
    cleaned_df = clean_raw_data(input_file, output_file, filter_agent_messages)
    
    # Analyze results
    analyze_cleaning_results(original_df, cleaned_df)
    
    # Validate cleaning
    validate_cleaning(cleaned_df)
    
    print(f"\nProcess completed. Check {output_file} for the cleaned data.") 


if __name__ == "__main__":
    input_file = "tableau_exports/Doctors_20250602_151623.csv"
    output_file = "Raw Tableau Data_cleaned.csv"
    
    print("Reading original data...")
    original_df = pd.read_csv(input_file)
    
    print("Cleaning raw data...")
    cleaned_df = clean_raw_data(input_file, output_file)
    
    # Analyze results
    analyze_cleaning_results(original_df, cleaned_df)
    
    # Validate cleaning
    validate_cleaning(cleaned_df)
    
    print(f"\nProcess completed. Check {output_file} for the cleaned data.") 