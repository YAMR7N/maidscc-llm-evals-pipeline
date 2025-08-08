import pandas as pd
import json
import re
from datetime import datetime

def clean_datetime_format(datetime_str):
    """
    Clean datetime format by handling various malformed datetime strings - only if needed.
    Converts '7/10/2025 3:50:36â¯PM' to '7/10/2025 3:50:36 PM'
    Converts '7/10/2025 3:50:â¯PM' to '7/10/2025 3:50 PM' 
    """
    if not datetime_str or isinstance(datetime_str, type(None)):
        return datetime_str
    
    # Convert to string if not already
    datetime_str = str(datetime_str)
    
    try:
        # Try to parse the datetime as-is
        pd.to_datetime(datetime_str, errors='coerce', format='mixed')
        return datetime_str  # If successful, return as-is
    except:
        # If it fails, apply cleaning
        pass
    
    # Only apply cleaning if the original datetime couldn't be parsed
    # Handle case where we have colon followed by space and AM/PM (missing seconds)
    if ':' in datetime_str and (' PM' in datetime_str or ' AM' in datetime_str):
        # Find the last colon and check if it's followed by space and AM/PM
        last_colon_idx = datetime_str.rfind(':')
        after_colon = datetime_str[last_colon_idx + 1:]
        if after_colon.strip() in ['PM', 'AM']:
            # Remove the colon and everything between it and AM/PM
            cleaned = datetime_str[:last_colon_idx] + ' ' + after_colon.strip()
            return cleaned
    
    # Handle original case with invisible characters
    if len(datetime_str) >= 5:
        # Delete the third, fourth, and fifth to last characters and add space
        # Remove characters at positions -5, -4, -3 (third, fourth, fifth to last)
        cleaned = datetime_str[:-5] + datetime_str[-2:]
        # Add space between time and AM/PM
        cleaned = cleaned[:-2] + ' ' + cleaned[-2:]
        return cleaned
    
    return datetime_str

def safe_json_loads(json_str):
    try:
        if pd.isna(json_str):
            return {}
        # Remove invisible unicode characters and strip whitespace
        cleaned = str(json_str).replace('\u202f', '').replace('\xa0', '').strip()
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Silently handle malformed JSON - common in raw data
        return "INVALID_JSON"
    except Exception:
        return "INVALID_JSON"



def convert_conversation_to_json(csv_path, target_skills=None):
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Clean datetime format first, then convert for sorting
    df['Message Sent Time'] = df['Message Sent Time'].apply(clean_datetime_format)
    df['Message Sent Time'] = pd.to_datetime(df['Message Sent Time'], errors='coerce', format='mixed')
    
    # Sort the entire dataframe by Conversation ID and Message Sent Time
    df = df.sort_values(['Conversation ID', 'Message Sent Time'])
    
    # Get unique conversation IDs
    conversation_ids = df['Conversation ID'].unique()
    
    # List to store individual conversations (no grouping by customer)
    all_conversations = []
    
    # Use provided target_skills or default to doctors skills for backward compatibility
    if target_skills is None:
        target_skills = ["GPT_RESOLVERS_BOT", "GPT_MV_RESOLVERS"]

    for conv_id in conversation_ids:
        # Filter messages for this conversation
        conv_messages = df[df['Conversation ID'] == conv_id]

        skills = list(set(conv_messages['Skill'].tolist()))
        # Case-insensitive skill matching
        skills_lower = [skill.lower() for skill in skills if skill]
        target_skills_lower = [ts.lower() for ts in target_skills if ts]
        if not any(skill in target_skills_lower for skill in skills_lower):
            continue

        # Get unique participants
        participants = sorted(list(set(conv_messages['Sent By'].tolist())))
        # Check if any participant is 'bot' (case-insensitive)
        if not any(p.lower() == "bot" for p in participants) or not any(p.lower() == "consumer" for p in participants):
            # print("No bot or consumer found in " + conv_id)
            continue
        
        # Get customer name for this conversation
        customer_name = conv_messages['Customer Name'].iloc[0] if pd.notna(conv_messages['Customer Name'].iloc[0]) else "Unknown"
        customer_name = str(customer_name)
        
        # Create conversation object with customer name included
        conversation = {
            "customer_name": customer_name,
            "chat_id": str(conv_id),
            "conversation": []
        }
        
        # Track last message details
        last_message_time = None
        last_message_text = None
        last_message_sender = None
        last_message_type = None
        
        # Process each message
        for _, row in conv_messages.iterrows():
            current_time = pd.to_datetime(row['Message Sent Time'], errors='coerce', format='mixed').isoformat()
            current_text = str(row['TEXT']) if pd.notna(row['TEXT']) else ""
            current_sender = str(row['Sent By']) if pd.notna(row['Sent By']) else ""
            current_skill = str(row['Skill']) if pd.notna(row['Skill']) else ""
            current_type = str(row['Message Type']).lower() if pd.notna(row['Message Type']) else ""


            if current_type == "transfer" or current_type == "private message" or current_sender.lower() == "system":
                continue
            
            if current_sender.lower() == "bot" and current_skill not in target_skills:
                # print("Found bot message and not a target skill " + conv_id)
                current_sender = "Agent_1"

            if (current_text == "" or pd.isna(row['TEXT'])) and current_type == "normal message":
                # print("Found empty message " + conv_id)
                current_text = "[Doc/Image]"

            # Check if this is a duplicate message (same time, text, sender, and type)
            is_duplicate = (current_time == last_message_time and 
                          current_text == last_message_text and 
                          current_sender == last_message_sender and 
                          current_type == last_message_type)
            
            # Add tool message if it exists and Tools column is present
            if 'Tools' in row.index and pd.notna(row['Tools']):
                tool_creation_date = pd.to_datetime(row['Tool Creation Date'], errors='coerce', format='mixed')
                tool_message = {
                    "timestamp": tool_creation_date.isoformat(),
                    "sender": current_sender,
                    "type": "tool",
                    "tool": str(row['Tools']),
                    "result": safe_json_loads(row['Tools Json Output'])
                }
                conversation["conversation"].append(tool_message)

            # If there's a message and it's not a duplicate, add it
            if current_text and not is_duplicate:
                message = {
                    "timestamp": current_time,
                    "sender": current_sender,
                    "type": current_type,
                    "content": current_text
                }
                conversation["conversation"].append(message)
                
                # Update last message details
                last_message_time = current_time
                last_message_text = current_text
                last_message_sender = current_sender
                last_message_type = current_type
        
        # Keep all messages - no trailing message removal
        
        # Add conversation directly to the list (no grouping by customer)
        all_conversations.append(conversation)
    
    # Return flat list of conversations (no grouping by customer)
    return all_conversations

def save_conversations_to_json(conversations, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, indent=2, ensure_ascii=False)

def generate_conversations_json(input_csv, output_json):
    conversations = convert_conversation_to_json(input_csv)
    save_conversations_to_json(conversations, output_json)

# if __name__ == "__main__":
#     input_csv = "outputs/cleaned_raw_data (2).csv"  # Replace with your CSV file path
#     output_json = "outputs/conversations_testing.json"
    
#     conversations = convert_conversation_to_json(input_csv)
#     save_conversations_to_json(conversations, output_json)
