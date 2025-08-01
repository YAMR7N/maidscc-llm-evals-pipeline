import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def create_transparent_view(cleaned_csv_path, output_csv_path):
    """
    Create transparent view of chats from cleaned data
    """
    try:
        # Read cleaned data
        df = pd.read_csv(cleaned_csv_path)
        logging.info(f"Loaded cleaned data: {len(df)} rows")
        
        # Convert Message Sent Time to datetime and sort
        df['Message Sent Time'] = pd.to_datetime(df['Message Sent Time'], errors='coerce', format='mixed')
        df = df.sort_values(['Conversation ID', 'Message Sent Time'])
        
        results = []
        
        # Process each conversation
        for conv_id in df['Conversation ID'].unique():
            conv_data = df[df['Conversation ID'] == conv_id].copy()
            
            # Remove duplicate tool messages
            conv_data = remove_duplicate_tool_messages(conv_data)
            
            # Format messages
            messages = format_messages(conv_data)
            
            results.append({
                'conversation ID': conv_id,
                'Messages': messages
            })
            
        # Save results
        results_df = pd.DataFrame(results)
        results_df.to_csv(output_csv_path, index=False)
        
        logging.info(f"Transparent view saved to: {output_csv_path}")
        logging.info(f"Processed {len(results)} conversations")
        
        return results_df
        
    except Exception as e:
        logging.error(f"Error creating transparent view: {e}")
        return None

def remove_duplicate_tool_messages(conv_data):
    """
    Remove rows that have Tools AND duplicate TEXT with adjacent rows
    """
    # First, identify all duplicate messages (same TEXT and timestamp)
    conv_data['duplicate_key'] = conv_data['TEXT'].astype(str) + '_' + conv_data['Message Sent Time'].astype(str)
    
    rows_to_keep = []
    processed_duplicates = set()
    
    for i, row in conv_data.iterrows():
        duplicate_key = row['duplicate_key']
        
        # If this is a duplicate group we haven't processed yet
        if duplicate_key in processed_duplicates:
            continue
            
        # Find all rows with the same duplicate key
        same_messages = conv_data[conv_data['duplicate_key'] == duplicate_key]
        
        if len(same_messages) > 1:
            # Multiple identical messages found
            # Keep the one without tools, or the first one if all have tools
            preferred_row = None
            for _, dup_row in same_messages.iterrows():
                if pd.isna(dup_row['Tools']) or dup_row['Tools'] == '':
                    preferred_row = dup_row.name
                    break
            
            # If no row without tools, keep the first one
            if preferred_row is None:
                preferred_row = same_messages.index[0]
            
            rows_to_keep.append(preferred_row)
            processed_duplicates.add(duplicate_key)
        else:
            # Single message, keep it
            rows_to_keep.append(i)
            processed_duplicates.add(duplicate_key)
    
    # Remove the temporary column
    result = conv_data.loc[rows_to_keep].drop('duplicate_key', axis=1)
    return result

def format_messages(conv_data):
    """
    Format messages as Sender: message
    """
    formatted_messages = []
    
    for _, row in conv_data.iterrows():
        sender = str(row['Sent By']).strip()
        message = str(row['TEXT']).strip()
        
        if sender.lower() == 'system':
            formatted_messages.append(f"[SYSTEM: {message}]")
        else:
            formatted_messages.append(f"{sender.capitalize()}: {message}")
    
    return '\n'.join(formatted_messages)

if __name__ == "__main__":
    cleaned_csv_path = "cleaned_data.csv"
    output_csv_path = "transparent_view.csv"
    
    create_transparent_view(cleaned_csv_path, output_csv_path)
