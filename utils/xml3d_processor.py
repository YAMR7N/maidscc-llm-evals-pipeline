"""
XML3D Processor for conversation data
Converts multiple days of cleaned CSV conversations to XML format grouped by customer name
Uses yesterday (mandatory) plus up to 2 additional recent available days from historical data
Output: One row per customer with all their chats in XML format over the available days
"""

import pandas as pd
import json
import re
import os
from datetime import datetime, timedelta
import xml.sax.saxutils as saxutils
from pathlib import Path
import sys

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.tableau_downloader import TableauDownloadCSV
from utils.clean_raw import clean_raw_data
from config.departments import DEPARTMENTS
from config.settings import DATA_PROCESSING


def safe_json_loads(json_str):
    """Safely parse JSON strings with error handling"""
    try:
        if pd.isna(json_str):
            return {}
        # Remove invisible unicode characters and strip whitespace
        cleaned = str(json_str).replace('\u202f', '').replace('\xa0', '').strip()
        
        # Handle empty or whitespace-only strings
        if not cleaned:
            return {}
            
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Silently handle JSON decode errors to avoid terminal flooding
        return str(json_str) if json_str else {}
    except Exception:
        return str(json_str) if json_str else {}


def format_tool_with_name_as_xml(tool_name, tool_output):
    """
    Convert tool name and output to XML format, showing tool name and all parameters
    (Same logic as xml_processor.py)
    """
    escaped_tool_name = saxutils.escape(str(tool_name))
    
    if isinstance(tool_output, dict):
        if not tool_output:  # Empty dict
            return f"<tool>\n  <n>{escaped_tool_name}</n>\n  <o>{{}}</o>\n</tool>"
        
        # Format all parameters/properties
        params_xml = ""
        for key, value in tool_output.items():
            escaped_key = saxutils.escape(str(key))
            if isinstance(value, (dict, list)):
                # Convert complex objects to JSON string
                escaped_value = saxutils.escape(json.dumps(value, indent=2))
            else:
                escaped_value = saxutils.escape(str(value))
            params_xml += f"  <{escaped_key}>{escaped_value}</{escaped_key}>\n"
        
        return f"<tool>\n  <n>{escaped_tool_name}</n>\n{params_xml}</tool>"
    
    elif isinstance(tool_output, str):
        if not tool_output.strip():  # Empty string
            escaped_output = "{}"
        else:
            escaped_output = saxutils.escape(tool_output)
        return f"<tool>\n  <n>{escaped_tool_name}</n>\n  <o>{escaped_output}</o>\n</tool>"
    
    else:
        # Handle other types (None, numbers, etc.)
        if tool_output is None or tool_output == "":
            escaped_output = "{}"
        else:
            escaped_output = saxutils.escape(str(tool_output))
        return f"<tool>\n  <n>{escaped_tool_name}</n>\n  <o>{escaped_output}</o>\n</tool>"


def download_and_clean_3_days_data(department: str):
    """Download and clean data for the most recent 3 available days"""
    print(f"📅 Collecting 3 days of available data for {department}...")
    
    dept_config = DEPARTMENTS[department]
    tableau_view = dept_config['tableau_view']
    
    yesterday = datetime.now() - timedelta(days=1)
    
    # Yesterday is mandatory
    mandatory_days = [(yesterday, "Yesterday", True)]
    
    # Find 2 more available days by looking backwards
    available_days = []
    current_day = yesterday - timedelta(days=1)  # Start from day before yesterday
    max_lookback = 14  # Look back up to 2 weeks to find data
    
    print(f"🔍 Looking for 2 additional available days before yesterday...")
    
    for days_back in range(1, max_lookback + 1):
        check_date = yesterday - timedelta(days=days_back)
        date_folder = check_date.strftime('%Y-%m-%d')
        day_str = check_date.strftime('%Y%m%d')
        cache_filename = f"{department}_{day_str}.csv"
        cache_filepath = f"outputs/tableau_exports/{date_folder}/{cache_filename}"

        # Check if this day's data exists
        if os.path.exists(cache_filepath):
            day_label = f"Day -{days_back}"
            available_days.append((check_date, day_label, False))  # Can't download historical data
            print(f"  ✅ Found {day_label} ({date_folder})")
            
            # Stop when we have 2 additional days
            if len(available_days) >= 2:
                break
    
    # Check if we found enough days
    if len(available_days) < 2:
        print(f"\n⚠️  WARNING: Only found {len(available_days)} additional days of historical data")
        print(f"📋 XML3D works best with 3 days, but will proceed with available data")
        print(f"💡 Consider running historical downloads to build up more data")
    
    # Combine mandatory yesterday with available historical days (most recent first)
    all_days = mandatory_days + available_days[:2]  # Take up to 2 additional days
    
    print(f"\n📋 Will process {len(all_days)} days total:")
    for target_date, day_label, can_download in all_days:
        print(f"  - {day_label}: {target_date.strftime('%Y-%m-%d')}")
    
    cleaned_files = []
    
    # Process each day
    for target_date, day_label, can_download in all_days:
        day_str = target_date.strftime('%Y%m%d')
        date_folder = target_date.strftime('%Y-%m-%d')
        
        print(f"\n📋 Processing {day_label} ({date_folder})...")
        
        # Check for existing cached data first
        cache_filename = f"{department}_{day_str}.csv"
        cache_filepath = f"outputs/tableau_exports/{date_folder}/{cache_filename}"
        
        raw_file = None
        if os.path.exists(cache_filepath):
            print(f"📋 Using cached data: {cache_filepath}")
            raw_file = cache_filepath
        elif can_download:  # Only download fresh data for yesterday
            print(f"📥 Downloading fresh data for yesterday...")
            downloader = TableauDownloadCSV()
            required_headers = DATA_PROCESSING['required_headers']
            
            raw_file = downloader.download_csv(
                workbook_name="8 Department wise tables for chats & calls",
                view_name=tableau_view,
                from_date=target_date.strftime('%Y-%m-%d'),
                to_date=target_date.strftime('%Y-%m-%d'),
                output=cache_filename,
                required_headers=required_headers
            )
        else:
            print(f"❌ ERROR: Required data missing for {day_label} (this shouldn't happen)")
            continue
        
        if raw_file and os.path.exists(raw_file):
            # Clean the data
            preprocessing_dir = f"outputs/preprocessing_output/{date_folder}"
            os.makedirs(preprocessing_dir, exist_ok=True)
            
            cleaned_file = f"{preprocessing_dir}/{department}_cleaned.csv"
            
            # Clean datetime columns first (same as main pipeline)
            df = pd.read_csv(raw_file)
            from scripts.run_pipeline import LLMProcessor
            processor = LLMProcessor()
            cleaned_df = processor.clean_datetime_columns_df(df)
            
            # Save cleaned datetime version temporarily
            temp_cleaned_path = raw_file.replace('.csv', '_temp_cleaned.csv')
            cleaned_df.to_csv(temp_cleaned_path, index=False)
            
            try:
                # Clean raw data
                clean_raw_data(temp_cleaned_path, cleaned_file)
                cleaned_files.append(cleaned_file)
                print(f"✅ Cleaned data saved: {cleaned_file}")
            finally:
                # Clean up temporary file
                if os.path.exists(temp_cleaned_path):
                    os.remove(temp_cleaned_path)
        else:
            print(f"❌ Could not find or download data for {target_date.strftime('%Y-%m-%d')}")
    
    print(f"\n📊 Successfully prepared {len(cleaned_files)} days of data for XML3D processing")
    return cleaned_files


def combine_cleaned_data(cleaned_files):
    """Combine multiple cleaned CSV files into one DataFrame"""
    print(f"🔄 Combining {len(cleaned_files)} cleaned datasets...")
    
    all_dataframes = []
    total_rows = 0
    
    for file_path in cleaned_files:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            all_dataframes.append(df)
            total_rows += len(df)
            date_from_path = file_path.split('/')[-2]  # Extract date from path
            print(f"  📊 {date_from_path}: {len(df)} rows")
    
    if not all_dataframes:
        print("❌ No data files to combine")
        return None
    
    # Combine all dataframes
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    print(f"✅ Combined dataset: {len(combined_df)} total rows from {len(cleaned_files)} days")
    
    return combined_df


def preprocess_conversations(df, target_skills):
    """Preprocess conversations - filter by conversations containing target skills and sort"""
    print(f"🔄 Preprocessing conversations...")
    
    # Filter by conversations that contain target skills (not individual messages)
    initial_count = len(df)
    
    # Group by Conversation ID and check if any message in each conversation has target skills
    conversation_ids_with_target_skills = set()
    for conv_id in df['Conversation ID'].unique():
        conv_messages = df[df['Conversation ID'] == conv_id]
        skills_in_conv = conv_messages['Skill'].fillna('').tolist()
        # Case-insensitive skill matching
        skills_lower = [skill.lower() for skill in skills_in_conv if skill]
        target_skills_lower = [ts.lower() for ts in target_skills if ts]
        if any(skill in target_skills_lower for skill in skills_lower):
            conversation_ids_with_target_skills.add(conv_id)
    
    # Keep all messages from conversations that contain target skills
    df_filtered = df[df['Conversation ID'].isin(conversation_ids_with_target_skills)].copy()
    filtered_count = len(df_filtered)
    
    print(f"📊 Filtered by conversations containing skills {target_skills}: {filtered_count}/{initial_count} rows")
    print(f"📊 Kept {len(conversation_ids_with_target_skills)} conversations that contain target skills")
    
    if filtered_count == 0:
        print("⚠️  No conversations found matching target skills")
        return None
    
    # Sort by Customer Name, then Conversation ID, then Message Sent Time
    df_sorted = df_filtered.sort_values(['Customer Name', 'Conversation ID', 'Message Sent Time'])
    print(f"✅ Sorted conversations by customer name and timestamp")
    
    return df_sorted


def convert_conversations_to_xml3d(df, target_skills):
    """Convert conversations to XML3D format grouped by customer name"""
    print(f"🔄 Converting conversations to XML3D format...")
    
    # Step 1: First group by Conversation ID to get complete conversations
    conversation_ids = df['Conversation ID'].unique()
    print(f"📋 Found {len(conversation_ids)} unique conversations")
    
    # Step 2: Process each conversation and extract customer name
    complete_conversations = {}  # {customer_name: [conversation_data, ...]}
    
    processed_conversations = 0
    for conv_id in conversation_ids:
        # Get all messages for this conversation
        conv_messages = df[df['Conversation ID'] == conv_id]
        
        # Check if conversation contains target skills
        skills_series = conv_messages['Skill'].fillna('')
        skills = list(set(skills_series.tolist()))
        # Case-insensitive skill matching
        skills_lower = [skill.lower() for skill in skills if skill]
        target_skills_lower = [ts.lower() for ts in target_skills if ts]
        if not any(skill in target_skills_lower for skill in skills_lower):
            continue
        
        # Get unique participants
        sent_by_series = conv_messages['Sent By'].fillna('')
        participants = sorted(list(set(sent_by_series.tolist())))
        
        # Check if any participant is 'bot' or 'agent' (case-insensitive)
        has_bot_or_agent = any(p.lower() in ["bot", "agent"] for p in participants)
        has_consumer = any(p.lower() == "consumer" for p in participants)
        if not has_bot_or_agent or not has_consumer:
            continue
        
        # Extract customer name from any message in this conversation that has it
        customer_names_in_conv = conv_messages['Customer Name'].fillna('').astype(str)
        valid_customer_names = [name for name in customer_names_in_conv if name and name.strip() and name != 'nan' and name.lower() != 'unknown']
        
        if valid_customer_names:
            # Use the first valid customer name found
            customer_name = valid_customer_names[0].strip()
        else:
            # Skip conversations without valid customer names or with "Unknown" names
            continue
        
        # Get first message timestamp for this conversation
        first_message_time = conv_messages['Message Sent Time'].min()
        first_message_time_str = str(first_message_time) if pd.notna(first_message_time) else ""
        
        # Process the conversation content
        conversation_xml = process_single_conversation(conv_messages, conv_id, first_message_time_str, target_skills)
        
        if conversation_xml:
            # Add to customer's conversation list
            if customer_name not in complete_conversations:
                complete_conversations[customer_name] = []
            complete_conversations[customer_name].append({
                'xml': conversation_xml,
                'first_time': pd.to_datetime(first_message_time_str) if first_message_time_str else pd.Timestamp.min
            })
            processed_conversations += 1
    
    print(f"✅ Processed {processed_conversations} valid conversations for {len(complete_conversations)} customers")
    
    # Step 3: Group conversations by customer name and create final XML
    xml3d_conversations = []
    
    for customer_name, conversations in complete_conversations.items():
        # Sort conversations by first message time
        conversations.sort(key=lambda x: x['first_time'])
        
        # Combine all conversations for this customer
        customer_chats_xml = [conv['xml'] for conv in conversations]
        all_chats_xml = "\n\n".join(customer_chats_xml)
        
        # Build the full conversations XML structure
        conversations_xml = f"""<conversations>
<chat_count>{len(conversations)}</chat_count>

{all_chats_xml}

</conversations>"""
        
        # Add to final list
        xml3d_conversations.append({
            'customer_name': customer_name,
            'content_xml_view': conversations_xml,
            'chat_count': len(conversations)
        })
    
    return xml3d_conversations


def process_single_conversation(conv_messages, conv_id, first_message_time_str, target_skills):
    """Process a single conversation and return its XML representation"""
    # Start building XML content for this conversation
    content_parts = []
    
    # Sort messages by timestamp to ensure chronological order
    conv_messages_sorted = conv_messages.sort_values('Message Sent Time')
    
    # Track last message details for duplicate detection
    last_message_time = None
    last_message_text = None
    last_message_sender = None
    last_message_type = None
    
    # Process each message in this conversation (now in chronological order)
    for _, row in conv_messages_sorted.iterrows():
        message_time = row['Message Sent Time']
        if pd.notna(message_time):
            current_time = str(message_time)
        else:
            current_time = ""
        
        text_value = row['TEXT']
        current_text = str(text_value) if pd.notna(text_value) else ""
        
        sent_by_value = row['Sent By']
        current_sender = str(sent_by_value) if pd.notna(sent_by_value) else ""
        
        skill_value = row['Skill']
        current_skill = str(skill_value) if pd.notna(skill_value) else ""
        
        message_type_value = row['Message Type']
        current_type = str(message_type_value).lower() if pd.notna(message_type_value) else ""
        
        # Skip transfer and private messages
        if current_type == "transfer" or current_type == "private message":
            continue
        
        # Handle bot messages from non-target skills
        if current_sender.lower() == "bot" and current_skill not in target_skills:
            current_sender = "Agent_1"
        
        # Handle empty messages
        if (current_text == "" or pd.isna(text_value)) and current_type == "normal message":
            current_text = "[Doc/Image]"
        
        # Check if this is a duplicate message
        is_duplicate = (current_time == last_message_time and 
                      current_text == last_message_text and 
                      current_sender == last_message_sender and 
                      current_type == last_message_type)
        
        # Add tool message if it exists
        if pd.notna(row['Tools']):
            tool_name = str(row['Tools']) if pd.notna(row['Tools']) else "Unknown_Tool"
            tool_output = safe_json_loads(row['Tools Json Output'])
            tool_xml = format_tool_with_name_as_xml(tool_name, tool_output)
            content_parts.append(tool_xml)
        
        # If there's a message and it's not a duplicate, add it
        if current_text and not is_duplicate:
            # Escape XML special characters in the message content
            escaped_text = saxutils.escape(current_text)
            
            # Special formatting for system messages
            if current_sender.lower() == "system":
                message_line = f"[SYSTEM: {escaped_text}]"
            else:
                message_line = f"{current_sender}: {escaped_text}"
            
            content_parts.append(message_line)
            
            # Update last message details
            last_message_time = current_time
            last_message_text = current_text
            last_message_sender = current_sender
            last_message_type = current_type
    
    # Only return XML if we have content
    if content_parts:
        # Join all content parts with newlines
        content_xml = "\n\n".join(content_parts)
        
        # Build the chat XML structure
        chat_xml = f"""<chat><id>{saxutils.escape(str(conv_id))}</id><first_message_time>{saxutils.escape(first_message_time_str)}</first_message_time><content>

{content_xml}

</content></chat>"""
        
        return chat_xml
    
    return None


def save_xml3d_conversations_to_csv(conversations, output_path):
    """Save XML3D conversations to CSV, ordered by chat count (descending)"""
    print(f"📊 Sorting {len(conversations)} customers by chat count...")
    
    # Sort by chat count descending
    conversations_sorted = sorted(conversations, key=lambda x: x['chat_count'], reverse=True)
    
    # Create DataFrame with only the required columns
    df = pd.DataFrame([{
        'customer_name': conv['customer_name'],
        'content_xml_view': conv['content_xml_view']
    } for conv in conversations_sorted])
    
    # Save to CSV
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    # Print summary statistics
    total_chats = sum(conv['chat_count'] for conv in conversations_sorted)
    print(f"💾 Saved XML3D conversations to: {output_path}")
    print(f"📊 Summary: {len(conversations_sorted)} customers, {total_chats} total chats")
    
    # Show top 5 customers by chat count
    print(f"🏆 Top 5 customers by chat count:")
    for i, conv in enumerate(conversations_sorted[:5], 1):
        print(f"  {i}. {conv['customer_name']}: {conv['chat_count']} chats")
    
    return output_path


def create_xml3d_view(department: str, target_skills=None):
    """
    Main function to generate XML3D conversations for the most recent available days
    Always includes yesterday, plus up to 2 additional recent days found in historical data
    """
    print(f"🔄 Creating XML3D view for {department}")
    
    try:
        # Use department skills if target_skills not provided
        if target_skills is None:
            dept_config = DEPARTMENTS[department]
            target_skills = dept_config['skills']
        
        print(f"🎯 Target skills: {target_skills}")
        
        # Step 1: Download and clean data for available days (yesterday + up to 2 historical days)
        cleaned_files = download_and_clean_3_days_data(department)
        
        if not cleaned_files:
            print("❌ XML3D processing cannot continue without any available data")
            return None
        
        # Step 2: Combine all cleaned data
        combined_df = combine_cleaned_data(cleaned_files)
        
        if combined_df is None or combined_df.empty:
            print("❌ No combined data available")
            return None
        
        # Step 3: Preprocess conversations
        processed_df = preprocess_conversations(combined_df, target_skills)
        
        if processed_df is None or processed_df.empty:
            print("❌ No conversations found after preprocessing")
            return None
        
        # Step 4: Convert to XML3D format
        conversations = convert_conversations_to_xml3d(processed_df, target_skills)
        
        if not conversations:
            print("❌ No conversations found matching criteria")
            return None
        
        # Step 5: Save to CSV
        yesterday = datetime.now() - timedelta(days=1)
        date_folder = yesterday.strftime('%Y-%m-%d')
        preprocessing_dir = f"outputs/preprocessing_output/{date_folder}"
        os.makedirs(preprocessing_dir, exist_ok=True)
        
        output_path = f"{preprocessing_dir}/{department}_xml3d.csv"
        save_xml3d_conversations_to_csv(conversations, output_path)
        
        print(f"✅ XML3D processing completed: {len(conversations)} customers")
        return output_path
        
    except Exception as e:
        print(f"❌ XML3D processing failed: {str(e)}")
        return None


# For standalone usage
def main():
    """Main function for standalone usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert conversations to XML3D format (multi-day customer view)')
    parser.add_argument('--department', required=True, help='Department to process')
    parser.add_argument('--skills', nargs='*', help='Target skills to filter (optional)')
    
    args = parser.parse_args()
    
    result = create_xml3d_view(args.department, args.skills)
    
    if result:
        print(f"✅ Success! XML3D conversations saved to: {result}")
    else:
        print("❌ Failed to create XML3D view")


if __name__ == "__main__":
    main() 