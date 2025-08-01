"""
Sales Message Filter
Filters out automated sales messages from conversations before rule breaking analysis
"""

import re
import json
from typing import List, Dict, Any

# List of automated messages to exclude
EXCLUDED_MESSAGES = [
    "Is there anything else I can help you with?",
    "What else can I help you with? Or are you ready to get it done now?",
    "I will share with you a list of our best matching maids right away.",
    "Thank you for sharing all this information.",
    "Selecting your preferences would help us choose the right maid for you. 😊",
    "Hello from maids.cc—4.8/5 Google Reviews from more than 11,000 clients 😊—this is Jude.\nYes, all our maids can cook! Would you like to hire a **live‑in maid** or **live‑out maid**?",
    "To get a job as a full‑time maid in Dubai, please WhatsApp us at:\n[http://wa.me/971507497417](http://wa.me/971507497417)\n…our recruitment team will reply in seconds.",
    "If Arabic is spoken at your home, here's a list of our top matching Ethiopian maids ready for hire.",
    r"""Here's our price list:

   **Maid/Nanny live‑in monthly plan:**
   • Filipina: AED 3,500 + 596\*
   • African: AED 2,590 + 390\*
   • Ethiopian: AED 2,590 + 390\*

   > \*For government‑mandated vacation, ticket, and gratuity.

   We also have African and Filipina **live‑out maids** for an additional AED 950/month to cover live‑out expenses.

   Once you find a maid you like, you can save **at least 35%** by switching from the monthly plan to the long‑term plan—just cover her 2‑year visa & salary.

   **Price includes:**
   • Residency Visa + EID
   • Unlimited free replacements
   • Company doctor
   • Salary + ATM card
   • 24/7 client support
   • In‑home maid trainer: cleaning, cooking & childcare
   • Superior service quality from a 4.8/5 Google rating

   No deposits; cancel anytime. No paperwork is required.

   You can do it now, right here on WhatsApp.""",
    "Allow me a moment, please. 😊",
    "Also, even if you don't hire a maid through us, we can still provide a 2‑year visa for your new maid—AED 8,500—via WhatsApp in just 5 minutes.",
    "Based on our conversation…",
    r"""**Maid/Nanny live‑in monthly plan:**
   • Filipina: AED 3,500 + 596\*
   • African: AED 2,590 + 390\*
   • Ethiopian: AED 2,590 + 390\*

   > \*For government‑mandated vacation, ticket, and gratuity.

   We also have African and Filipina live‑out maids for an additional AED 950/month to cover live‑out expenses.

   Once you find a maid you like, you can save **at least 35%** by switching to the long‑term plan—just cover her 2‑year visa & salary.

   **Price includes:**
   • Residency Visa + EID
   • Unlimited free replacements
   • Company doctor
   • Salary + ATM card
   • 24/7 client support
   • In‑home maid trainer: cleaning, cooking & childcare
   • Superior service quality from a 4.8/5 Google rating

   No deposits; cancel anytime.
   No paperwork is required.

   You can do it now, here on WhatsApp.""",
    "Of course! An agent will reach out to you shortly by phone. In the meantime, if there's anything else you'd like assistance with, please let me know here on WhatsApp.",
    r'We couldn\'t find the maid you\'re looking for. Please note that if you (or any other family member) clicks **"Hire and Pay now,"** she will be temporarily removed from the website until the hiring process is complete.'
]


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison by:
    - Converting to lowercase
    - Removing extra whitespace
    - Removing leading/trailing whitespace
    - Normalizing line breaks
    - Removing non-breaking spaces and other unicode whitespace
    """
    if not text:
        return ""
    
    # Convert to lowercase
    normalized = text.lower()
    
    # Replace various types of whitespace with regular space
    normalized = re.sub(r'[\u00A0\u1680\u2000-\u200B\u202F\u205F\u3000]', ' ', normalized)
    
    # Replace multiple spaces/tabs with single space
    normalized = re.sub(r'[ \t]+', ' ', normalized)
    
    # Replace multiple newlines with single newline
    normalized = re.sub(r'\n+', '\n', normalized)
    
    # Replace Windows line endings with Unix
    normalized = normalized.replace('\r\n', '\n')
    
    # Strip leading/trailing whitespace
    normalized = normalized.strip()
    
    return normalized


def is_excluded_message(message_content: str, excluded_messages: List[str] = None) -> bool:
    """
    Check if a message should be excluded based on the exclusion list.
    Uses normalized comparison to handle case and whitespace differences.
    """
    if not message_content:
        return False
    
    if excluded_messages is None:
        excluded_messages = EXCLUDED_MESSAGES
    
    # Normalize the message content
    normalized_content = normalize_text(message_content)
    
    # Check against each excluded message
    for excluded in excluded_messages:
        normalized_excluded = normalize_text(excluded)
        
        # Check for exact match after normalization
        if normalized_content == normalized_excluded:
            return True
        
        # Also check if the excluded message is contained within the content
        # This handles cases where there might be slight variations
        if normalized_excluded in normalized_content or normalized_content in normalized_excluded:
            # Additional check to avoid false positives - ensure it's a substantial match
            # (at least 80% of the shorter text is contained in the longer one)
            shorter = min(len(normalized_excluded), len(normalized_content))
            if shorter > 20:  # Only for messages longer than 20 chars
                return True
    
    return False


def filter_sales_conversations(conversations: List[Dict[str, Any]], departments: List[str] = None) -> List[Dict[str, Any]]:
    """
    Filter automated sales messages from conversations.
    Only applies to MV Sales and CC Sales departments.
    
    Args:
        conversations: List of conversation dictionaries in JSON format
        departments: List of department names to check (defaults to ['MV Sales', 'CC Sales'])
    
    Returns:
        List of filtered conversations with automated messages removed
    """
    if departments is None:
        departments = ['MV Sales', 'CC Sales']
    
    # Normalize department names for comparison
    normalized_departments = [d.lower().replace(' ', '_') for d in departments]
    
    filtered_conversations = []
    total_messages_removed = 0
    
    for conv in conversations:
        # Create a copy to avoid modifying the original
        filtered_conv = conv.copy()
        
        # Filter the conversation messages
        if 'conversation' in filtered_conv:
            original_count = len(filtered_conv['conversation'])
            filtered_messages = []
            
            for message in filtered_conv['conversation']:
                # Only filter normal messages (not tool messages)
                if message.get('type') == 'normal message' and 'content' in message:
                    if is_excluded_message(message['content']):
                        total_messages_removed += 1
                        continue  # Skip this message
                
                # Keep all other messages
                filtered_messages.append(message)
            
            filtered_conv['conversation'] = filtered_messages
            
            # Log if messages were removed
            removed_count = original_count - len(filtered_messages)
            if removed_count > 0:
                print(f"  Removed {removed_count} automated messages from conversation {conv.get('chat_id', 'unknown')}")
        
        filtered_conversations.append(filtered_conv)
    
    if total_messages_removed > 0:
        print(f"📧 Total automated messages removed: {total_messages_removed}")
    
    return filtered_conversations


def filter_sales_conversations_file(input_file: str, output_file: str, department: str) -> int:
    """
    Filter a JSONL file of conversations and save the filtered version.
    
    Args:
        input_file: Path to input JSONL file
        output_file: Path to output JSONL file
        department: Department name for context
    
    Returns:
        Number of conversations processed
    """
    # Check if this department needs filtering
    sales_departments = ['mv sales', 'cc sales', 'mv_sales', 'cc_sales']
    if department.lower().replace(' ', '_') not in sales_departments:
        # No filtering needed, just copy the file
        import shutil
        shutil.copy(input_file, output_file)
        return 0
    
    print(f"🔧 Filtering automated sales messages for {department}...")
    
    conversations = []
    # Read JSONL file
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                conversations.append(json.loads(line))
    
    # Filter conversations
    filtered_conversations = filter_sales_conversations(conversations, [department])
    
    # Write filtered JSONL file
    with open(output_file, 'w', encoding='utf-8') as f:
        for conv in filtered_conversations:
            f.write(json.dumps(conv, ensure_ascii=False) + '\n')
    
    print(f"✅ Filtered {len(filtered_conversations)} conversations")
    return len(filtered_conversations)


# Load excluded messages from file if needed
def load_excluded_messages_from_file(file_path: str = 'excluded_messages_sales.txt') -> List[str]:
    """
    Load excluded messages from a text file.
    Expected format: numbered list with messages, possibly multi-line.
    """
    excluded_messages = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove the XML-like tags if present
        content = re.sub(r'</?Excluded_Messages>', '', content)
        
        # Split by numbers followed by period
        pattern = r'^\d+\.\s+'
        
        # Find all message starts
        lines = content.strip().split('\n')
        current_message = []
        
        for line in lines:
            if re.match(pattern, line):
                # Start of a new message
                if current_message:
                    # Save the previous message
                    message_text = '\n'.join(current_message).strip()
                    if message_text:
                        # Remove the number prefix
                        message_text = re.sub(pattern, '', message_text)
                        excluded_messages.append(message_text)
                # Start new message
                current_message = [re.sub(pattern, '', line)]
            else:
                # Continuation of current message
                current_message.append(line)
        
        # Don't forget the last message
        if current_message:
            message_text = '\n'.join(current_message).strip()
            if message_text:
                excluded_messages.append(message_text)
    
    except FileNotFoundError:
        print(f"⚠️  Excluded messages file not found: {file_path}")
        print("   Using default excluded messages list")
    
    return excluded_messages if excluded_messages else EXCLUDED_MESSAGES 