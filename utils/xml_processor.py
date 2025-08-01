"""
XML Processor for conversation data
Converts cleaned CSV conversations to XML format for LLM processing
"""

import pandas as pd
import json
import re
from datetime import datetime
import xml.sax.saxutils as saxutils


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
        # Return the original string instead of "INVALID_JSON" 
        return str(json_str) if json_str else {}
    except Exception:
        # Return the original string instead of "INVALID_JSON"
        return str(json_str) if json_str else {}


def format_tool_with_name_as_xml(tool_name, tool_output):
    """
    Convert tool name and output to XML format, showing tool name and all parameters
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


def format_tool_result_as_xml(tool_result):
    """
    Convert tool result (dict or string) to XML format
    """
    if isinstance(tool_result, dict):
        if 'name' in tool_result and 'properties' in tool_result:
            # Format: Transfer_tool with Team property
            tool_name = saxutils.escape(str(tool_result['name']))
            properties = tool_result.get('properties', {})
            if isinstance(properties, dict) and 'Team' in properties:
                team = saxutils.escape(str(properties['Team']))
                return f"<tool>\n  <n>{tool_name}</n>\n  <team>{team}</team>\n</tool>"
            else:
                # Generic properties handling
                props_xml = ""
                for key, value in properties.items():
                    escaped_key = saxutils.escape(str(key))
                    escaped_value = saxutils.escape(str(value))
                    props_xml += f"  <{escaped_key}>{escaped_value}</{escaped_key}>\n"
                return f"<tool>\n  <n>{tool_name}</n>\n{props_xml}</tool>"
        else:
            # Generic dict handling
            props_xml = ""
            for key, value in tool_result.items():
                escaped_key = saxutils.escape(str(key))
                escaped_value = saxutils.escape(str(value))
                props_xml += f"  <{escaped_key}>{escaped_value}</{escaped_key}>\n"
            return f"<tool>\n{props_xml}</tool>"
    else:
        # String or other format
        escaped_result = saxutils.escape(str(tool_result))
        return f"<tool>\n  <r>{escaped_result}</r>\n</tool>"


def preprocess_conversations(df):
    """Preprocess conversations - datetime cleaning already done by clean_raw.py"""
    # Sort the entire dataframe by Conversation ID and Message Sent Time
    df = df.sort_values(['Conversation ID', 'Message Sent Time'])
    return df


def convert_conversation_to_xml(csv_path, target_skills=None):
    """Convert conversations from CSV to XML format"""
    print(f"🔄 Converting conversations to XML format...")
    
    # Read the CSV file
    df = pd.read_csv(csv_path)
    print(f"📊 Loaded {len(df)} messages")
    
    # Preprocess the data
    df = preprocess_conversations(df)
    
    # Get unique conversation IDs
    conversation_ids = df['Conversation ID'].unique()
    print(f"📋 Found {len(conversation_ids)} unique conversations")
    
    # List to store XML conversations
    xml_conversations = []
    
    # Default target skills if none provided
    if target_skills is None:
        target_skills = ["GPT_RESOLVERS_BOT", "GPT_MV_RESOLVERS"]

    processed_count = 0
    for conv_id in conversation_ids:
        # Filter messages for this conversation
        conv_messages = df[df['Conversation ID'] == conv_id]

        # Check if conversation contains target skills
        skills_series = conv_messages['Skill'].fillna('')
        skills = list(set(skills_series.tolist()))
        if not any(skill in target_skills for skill in skills):
            continue

        # Get unique participants
        sent_by_series = conv_messages['Sent By'].fillna('')
        participants = sorted(list(set(sent_by_series.tolist())))
        
        # Check if any participant is 'bot' or 'agent' (case-insensitive)
        has_bot_or_agent = any(p.lower() in ["bot", "agent"] for p in participants)
        has_consumer = any(p.lower() == "consumer" for p in participants)
        if not has_bot_or_agent or not has_consumer:
            continue
        
        # Start building XML content
        content_parts = []
        
        # Track last message details for duplicate detection
        last_message_time = None
        last_message_text = None
        last_message_sender = None
        last_message_type = None
        
        # Track the last skill seen in the conversation
        last_skill = ""
        
        # Process each message
        for _, row in conv_messages.iterrows():
            message_time = row['Message Sent Time']
            if pd.notna(message_time):
                current_time = str(message_time)  # Already cleaned by clean_raw.py
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

            # Check if this is a duplicate message (same time, text, sender, and type)
            is_duplicate = (current_time == last_message_time and 
                          current_text == last_message_text and 
                          current_sender == last_message_sender and 
                          current_type == last_message_type)
            
            # Update last skill if we have a skill value and this is not a duplicate
            if current_skill and not is_duplicate and current_skill != "nan":
                last_skill = current_skill
            
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
        
        # Only proceed if we have content
        if content_parts:
            # Join all content parts with newlines
            content_xml = "\n\n".join(content_parts)
            
            # Build the full XML structure
            full_xml = f"""<conversation>
<chatID>{saxutils.escape(str(conv_id))}</chatID>
<content>

{content_xml}

</content>
</conversation>"""
            
            # Add to conversations list with last_skill column
            xml_conversations.append({
                'conversation_id': str(conv_id),
                'content_xml_view': full_xml,
                'last_skill': last_skill
            })
            
            processed_count += 1
    
    print(f"✅ Converted {processed_count} conversations to XML")
    return xml_conversations


def save_conversations_to_csv(conversations, output_path):
    """Save conversations to CSV with columns: conversation_id, content_xml_view, last_skill"""
    df = pd.DataFrame(conversations)
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"💾 Saved XML conversations to: {output_path}")
    return output_path


def create_xml_view(cleaned_csv_path, output_path, target_skills=None):
    """
    Main function to generate XML conversations and save to CSV
    Compatible with the existing pipeline structure
    """
    print(f"🔄 Creating XML view from {cleaned_csv_path}")
    
    try:
        # Convert conversations to XML
        conversations = convert_conversation_to_xml(cleaned_csv_path, target_skills)
        
        if not conversations:
            print("⚠️  No conversations found matching criteria")
            return None
        
        # Save to CSV
        save_conversations_to_csv(conversations, output_path)
        
        print(f"✅ XML processing completed: {len(conversations)} conversations")
        return output_path
        
    except Exception as e:
        print(f"❌ XML processing failed: {str(e)}")
        return None


# For standalone usage
def main():
    """Main function for standalone usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert conversations to XML format')
    parser.add_argument('--input', required=True, help='Input cleaned CSV file')
    parser.add_argument('--output', required=True, help='Output XML CSV file')
    parser.add_argument('--skills', nargs='*', help='Target skills to filter')
    
    args = parser.parse_args()
    
    result = create_xml_view(args.input, args.output, args.skills)
    
    if result:
        print(f"✅ Success! XML conversations saved to: {result}")
    else:
        print("❌ Failed to create XML view")


if __name__ == "__main__":
    main() 