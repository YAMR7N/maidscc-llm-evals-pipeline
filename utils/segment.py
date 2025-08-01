import pandas as pd
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def preprocess_data(df):
    """Sort by conversation ID and message sent time, remove duplicates"""
    df = df.sort_values(by=['Conversation ID', 'Message Sent Time'])
    df = df.drop_duplicates(subset=['Conversation ID', 'Message Sent Time'], keep='first')
    return df

def segment_conversation(conv_data):
    """Segments a single conversation into parts based on agent or bot changes and marks messages with [IDENTIFIER] if conditions met."""
    segments = []
    current_segment = []
    current_agent = None
    first_agent_or_bot_encountered = False
    last_skill = None
    marking = False
    skill_name_length_limit = 23

    for index, row in conv_data.iterrows():
        sender = str(row["Sent By"]).strip().lower()
        message = row["TEXT"]
        skill = row["Skill"]

        # Check marking condition
        if last_skill is None and skill.startswith("GPT_DOCTOR"):
            marking = True
        elif marking and (len(skill) > skill_name_length_limit):
            marking = False

        # Identify if it's from agent or bot
        if sender in ["agent", "bot"]:
            if not first_agent_or_bot_encountered:
                current_agent = row["Agent Name"] if sender == "agent" else "BOT"
                first_agent_or_bot_encountered = True
            else:
                next_agent = row["Agent Name"] if sender == "agent" else "BOT"
                if next_agent != current_agent:
                    if current_segment:
                        segments.append((current_agent, last_skill, current_segment))
                        current_segment = []
                    current_agent = next_agent

            last_skill = skill  # Always update skill on agent/bot message

        # Add [IDENTIFIER] if marking is True and sender is agent or bot
        if marking and sender in ["agent", "bot"]:
            current_segment.append(f"[IDENTIFIER] {sender.capitalize()}: {message}")
        else:
            current_segment.append(f"{sender.capitalize()}: {message}")

    # Add final segment
    if current_segment:
        segments.append((current_agent, last_skill, current_segment))

    return segments

def process_conversations(input_csv, target_skills=["GPT_MAIDSAT_FILIPINA_OUTSIDE", "GPT_MAIDSAT_FILIPINA_PHILIPPINES"]):
    """Process conversations and segment them, aggregating by Conversation ID. Only includes conversations with bot messages."""
    df = pd.read_csv(input_csv)
    df = preprocess_data(df)

    # First, filter out conversations that don't have any bot messages
    conversations_with_bot = set()
    for conv_id, conv_data in df.groupby("Conversation ID"):
        if any(conv_data["Sent By"].str.lower().str.contains('bot', na=False)):
            conversations_with_bot.add(conv_id)
    
    logging.info(f"Total conversations: {len(df.groupby('Conversation ID'))}")
    logging.info(f"Conversations with bot messages: {len(conversations_with_bot)}")
    logging.info(f"Conversations without bot messages (excluded): {len(df.groupby('Conversation ID')) - len(conversations_with_bot)}")

    # Track conversations that contain target skills AND have bot messages
    target_skill_conversations = set()
    for conv_id, conv_data in df.groupby("Conversation ID"):
        if conv_id in conversations_with_bot and any(skill in conv_data["Skill"].values for skill in target_skills):
            target_skill_conversations.add(conv_id)

    logging.info(f"Found {len(target_skill_conversations)} conversations with target skills and bot messages")

    all_segments = []
    customer_name_map = df.groupby("Conversation ID")["Customer Name"].first().to_dict()

    for conv_id, conv_data in df.groupby("Conversation ID"):
        if conv_id not in target_skill_conversations:
            continue
        conv_data = conv_data[conv_data["Message Type"] == "Normal Message"]
        segments = segment_conversation(conv_data)
        customer_name = customer_name_map.get(conv_id, "")
        for agent, last_skill, segment_messages in segments:
            all_segments.append([
                conv_id,
                customer_name,
                last_skill,
                agent,
                "\n".join(segment_messages)
            ])

    segmented_df = pd.DataFrame(
        all_segments,
        columns=["Conversation ID", "Customer Name", "Last Skill", "Agent Name", "Messages"]
    )

    # Filter: keep only segments that include consumer messages
    segmented_df = segmented_df[segmented_df["Messages"].str.contains("Consumer:", na=False)]

    # Keep only conversations that used target skills
    segmented_df = segmented_df[segmented_df["Conversation ID"].isin(target_skill_conversations)]

    # Aggregate by Conversation ID (not Customer Name)
    agg_functions = {
        'Customer Name': 'first',
        'Last Skill': 'first',
        'Agent Name': lambda x: ', '.join(x.astype(str).unique()),
        'Messages': lambda x: '\n'.join(x.astype(str))
    }

    merged_df = segmented_df.groupby('Conversation ID').agg(agg_functions).reset_index()
    merged_df['Conversation ID'] = merged_df['Conversation ID'].astype(str)

    return merged_df