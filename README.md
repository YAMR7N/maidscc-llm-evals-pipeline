# LLM-as-a-Judge Pipeline

A prompt-agnostic pipeline for automated chatbot conversation analysis using LLMs. This system provides a unified interface for running various analytical prompts across departments with support for multiple LLM providers (OpenAI, Gemini, and Anthropic) and flexible data formats.

## 🔧 Important Modules

### Preprocessing Modules

The preprocessing layer transforms raw Tableau data into various formats optimized for different analysis types:

#### Data Flow
1. **Raw Tableau Data** → `clean_raw.py` → **Cleaned CSV**
2. **Cleaned CSV** → Format Processors → **Analysis-Ready Format**

#### Format Processors

**1. JSON Processor (`json_processor.py`)**
- Converts conversations into structured JSON format
- Groups messages by conversation with metadata
- Ideal for rule-based analysis and structured evaluations

Example output:
```json
{
  "customer_name": "John Doe",
  "chat_id": "conv_12345",
  "conversation": [
    {
      "timestamp": "2025-07-30T10:15:00",
      "sender": "Consumer",
      "type": "normal message",
      "content": "I need help with my order"
    },
    {
      "timestamp": "2025-07-30T10:15:30",
      "sender": "Bot",
      "type": "normal message",
      "content": "I'd be happy to help you with your order."
    }
  ]
}
```

**2. XML Processor (`xml_processor.py`)**
- Formats conversations as XML documents
- Preserves conversation structure with clear message flow
- Best for prompts requiring contextual understanding

Example output:
```xml
<conversation>
<chatID>conv_12345</chatID>
<content>

Consumer: I need help with my order

Bot: I'd be happy to help you with your order.

<tool>
  <n>Order_Lookup_Tool</n>
  <orderID>ORD-789</orderID>
  <status>In Transit</status>
</tool>

Bot: I found your order ORD-789. It's currently in transit.

</content>
</conversation>
```

**3. XML3D Processor (`xml3d_processor.py`)**
- Aggregates multiple days of conversations by customer
- Creates a comprehensive view of customer interactions over time
- Uses yesterday's data + up to 2 historical days

Example output:
```xml
<conversations>
<chat_count>3</chat_count>

<chat><id>conv_001</id><first_message_time>2025-07-28 09:00:00</first_message_time><content>
Consumer: Previous issue with payment
Bot: Let me check that for you...
</content></chat>

<chat><id>conv_002</id><first_message_time>2025-07-29 14:30:00</first_message_time><content>
Consumer: Following up on payment issue
Bot: I see your previous conversation...
</content></chat>

</conversations>
```

**4. Transparent Processor (`transparent_processor.py`)**
- Simple, human-readable format
- Concatenates messages with sender labels
- Minimal processing, preserves original flow

Example output:
```
Consumer: Hello, I have a question about my subscription
Bot: Hello! I'd be happy to help with your subscription question.
Consumer: When does it renew?
Bot: Let me check your account details.
[SYSTEM: Checking subscription status]
Bot: Your subscription renews on August 15th.
```

**5. Segmented Format (`segment.py`)**
- Directly processes raw Tableau data (not cleaned CSV)
- Groups messages by agent/bot changes
- Used primarily for sentiment analysis

### Main Pipeline (`run_pipeline.py`)

The core pipeline engine that:
- **Downloads** data from Tableau with intelligent caching
- **Preprocesses** data into the requested format
- **Processes** through LLMs (OpenAI or Gemini) with concurrent request handling
- **Saves** results in date-organized directories
- **Post-processes** and uploads to Google Sheets (when --with-upload flag is used)

Key features:
- Prompt-agnostic design - easy to add new analysis types
- Automatic model configuration based on prompt type
- Token tracking and usage reporting [[memory:4258039]]
- System prompt fetching from API for dynamic prompts
- Concurrent processing with semaphore control (30 parallel requests)

### Script Runner (`run_all.sh`)

Universal entry point for all pipeline operations.

**Basic Usage:**
```bash
./run_all.sh [COMMAND] [OPTIONS]
```

**Sample Commands:**
```bash
# Sentiment Analysis for all departments
./run_all.sh sa --with-upload

# Rule Breaking for specific departments
./run_all.sh rb --departments "Doctors,CC Sales" --with-upload

# False Promises for MV Resolvers
./run_all.sh false_promises --departments "MV Resolvers" --format xml --with-upload

# FTR Analysis (uses XML3D format)
./run_all.sh ftr --departments "MV Resolvers" --with-upload

# Categorizing for Doctors (prerequisite for misprescription)
./run_all.sh categorizing --departments "Doctors" --with-upload

# Misprescription (run after categorizing)
./run_all.sh misprescription --departments "Doctors" --with-upload
```

**Important:** The `--with-upload` flag:
- Uploads raw LLM output spreadsheets to Google Sheets
- Generates and uploads summary/snapshot spreadsheets for each department
- Essential for dashboard integration and reporting

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# LLM Provider API Keys
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key  # Required for Claude models

# Google Sheets API (for upload functionality)
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json

# Optional: Tableau credentials (if using automatic download)
TABLEAU_USERNAME=your-username
TABLEAU_PASSWORD=your-password
```

### Supported Models

The pipeline supports models from three providers:

**OpenAI:**
- `gpt-4o` (16K tokens)
- `gpt-4o-mini` (16K tokens)
- `o4-mini` (30K tokens)

**Gemini:**
- `gemini-1.5-pro` (20K tokens)
- `gemini-1.5-flash` (20K tokens)
- `gemini-2.0-flash-exp` (20K tokens)
- `gemini-2.5-pro` (20K tokens)
- `gemini-2.5-flash` (20K tokens)

**Anthropic:**
- `claude-3-opus-20240229` (4K tokens)
- `claude-3-sonnet-20240229` (4K tokens)
- `claude-3-haiku-20240307` (4K tokens)
- `claude-3-5-sonnet-20241022` (4K tokens)

## 📊 Prompt Breakdown

### Sentiment Analysis (SA)
- **Format:** Segmented
- **Model:** gpt-4o
- **Scope:** All departments use the same prompt
- **Purpose:** Analyze customer satisfaction and sentiment

### Rule Breaking (RB) 
- **Format:** JSON
- **Model:** o4-mini
- **Status:** Still under prompt engineering
- **Scope:** Department-specific prompts

### MV Resolvers Suite
These prompts primarily target MV Resolvers department:
- **False Promises** - XML format, gemini-2.5-pro [[memory:4632860]]
- **Client Suspecting AI** - JSON format, gemini-2.5-pro
- **Legal Alignment** - XML format, gemini-2.5-pro [[memory:4632860]]
- **Call Request** - XML format, gemini-2.5-pro [[memory:4632860]]
- **Categorizing** - XML format, gemini-2.5-pro [[memory:4251974]]

### Doctors Department Chain
Must be run in sequence:
1. **Categorizing** - XML format, gemini-2.5-flash [[memory:4756302]]
   - Identifies conversations with medical advice
   - **MUST** be run before misprescription or unnecessary clinic recommendation
2. **Misprescription** - XML format, gemini-2.5-flash [[memory:4756302]]
   - Analyzes only conversations flagged with "OTC Medication Advice"
3. **Unnecessary Clinic Recommendation** - XML format, gemini-2.5-flash [[memory:4756302]]
   - Analyzes only conversations flagged with "Clinic Recommendation"

### FTR (First Time Resolution)
- **Format:** XML3D (multi-day customer view)
- **Model:** gemini-2.5-pro
- **Scope:** Currently specific to MV Resolvers
- **Special:** Only metric using 3-day aggregated data