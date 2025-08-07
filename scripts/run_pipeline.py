#!/usr/bin/env python3
"""
Main LLM-as-a-Judge Pipeline Entry Point
Implements the complete pipeline flow:
1. Download from Tableau
2. Preprocess data based on format 
3. Send through OpenAI/LLM
4. Save OpenAI outputs
5. Post-process and upload
"""

import argparse
import sys
import os
import pandas as pd
import asyncio
import openai
import google.generativeai as genai
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv
import aiohttp
import random

# Load environment variables from .env file
load_dotenv()

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.tableau_downloader import TableauDownloadCSV
from utils.clean_raw import clean_raw_data
from utils.segment import process_conversations
from utils.json_processor import convert_conversation_to_json
from utils.transparent_processor import create_transparent_view
from config.departments import DEPARTMENTS
from config.settings import MODELS, DATA_PROCESSING, PATHS
from prompts.base import PromptRegistry

def filter_agent_messages_from_conversation(conversation_text: str) -> str:
    """
    Filter out agent messages from conversation text, keeping only bot and consumer messages.
    Works with XML formatted conversations.
    """
    if not conversation_text or not isinstance(conversation_text, str):
        return conversation_text
    
    # For XML format conversations
    if '<conversation>' in conversation_text:
        lines = conversation_text.split('\n')
        filtered_lines = []
        skip_until_next_message = False
        
        for line in lines:
            # Check if this is an agent message start
            if line.strip().startswith('Agent') and ':' in line:
                skip_until_next_message = True
                continue
            
            # Check if this is a new message start (Bot or Consumer)
            if (line.strip().startswith('Bot:') or 
                line.strip().startswith('Consumer:') or
                line.strip().startswith('<') or
                not line.strip()):
                skip_until_next_message = False
            
            # Include line if we're not skipping
            if not skip_until_next_message:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    # For other formats, return as-is for now
    return conversation_text

class LLMProcessor:
    """Handles LLM processing for both OpenAI and Gemini"""
    
    def __init__(self, model="gpt-4o"):
        self.model = model
        self.model_config = MODELS.get(model, MODELS["gpt-4o"])
        self.provider = self.model_config["provider"]
        
        # Token tracking per department
        self.token_usage = {
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_tokens': 0,
            'conversations_processed': 0
        }
        
        # Initialize appropriate client based on provider
        if self.provider == "openai":
            self.client = openai.AsyncOpenAI()
        elif self.provider == "gemini":
            # Configure Gemini
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            self.gemini_model = genai.GenerativeModel(model)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    async def fetch_system_prompt_for_chat(self, chat_id):
        """Fetch the actual system prompt used for a specific chat from the API"""
        try:
            url = f"https://erpbackendpro.maids.cc/chatai/gptopenairequest/evaluatedPrompt/{chat_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'Accept': 'application/json'}) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Try multiple possible response structures
                        # Structure 1: Original format with 'system' array
                        if 'system' in data and len(data['system']) > 0 and 'text' in data['system'][0]:
                            return data['system'][0]['text']
                        
                        # Structure 2: New format with 'systemInstruction.parts'
                        elif 'systemInstruction' in data and 'parts' in data['systemInstruction']:
                            parts = data['systemInstruction']['parts']
                            if isinstance(parts, list) and len(parts) > 0 and 'text' in parts[0]:
                                return parts[0]['text']
                        
                        # Structure 3: Direct systemInstruction text
                        elif 'systemInstruction' in data and isinstance(data['systemInstruction'], str):
                            return data['systemInstruction']
                        
                        # Structure 4: Try to find any 'text' key in the response
                        elif 'text' in data:
                            return data['text']
                        
                        # If none of the structures match, log the actual structure for debugging
                        else:
                            print(f"⚠️  Invalid response structure for chat {chat_id}")
                            # Optionally log the keys to help debug structure issues
                            if data:
                                print(f"    Available keys: {list(data.keys())[:5]}")  # Show first 5 keys
                            return None
                    else:
                        print(f"⚠️  API status {response.status} for chat {chat_id}")
                        return None
        except Exception as e:
            print(f"❌ System prompt fetch failed for {chat_id}: {str(e)}")
            return None
    
    def get_max_tokens(self, retry_multiplier=1):
        """Calculate dynamic token limits based on model type
        
        Args:
            retry_multiplier: Multiply token limit by this factor (e.g., 2 for retries)
        """
        base_tokens = 16000  # Default
        
        if self.provider == "openai":
            # OpenAI: o4/o3 series get 30k, others get 16k
            if "o4" in self.model or "o3" in self.model:
                base_tokens = 30000
            else:
                base_tokens = 16000
        elif self.provider == "gemini":
            # Gemini: Always 20k
            base_tokens = 20000
        
        # Apply retry multiplier
        return base_tokens * retry_multiplier
        
    def clean_datetime_columns_df(self, df):
        """Clean datetime columns by removing invisible Unicode characters - NON-DESTRUCTIVE"""
        try:
            # Create a copy to avoid modifying the original DataFrame
            cleaned_df = df.copy()
            
            # Clean 'Message Sent Time' and 'Tool Creation Date' columns
            datetime_columns = ['Message Sent Time', 'Tool Creation Date']
            
            for col in datetime_columns:
                if col in cleaned_df.columns:
                    cleaned_df[col] = cleaned_df[col].apply(lambda x: self.fix_datetime_format(x) if pd.notna(x) else x)
            
            print(f"✅ Cleaned datetime columns (non-destructive)")
            return cleaned_df
            
        except Exception as e:
            print(f"❌ Error cleaning datetime columns: {str(e)}")
            return df  # Return original if cleaning fails
    
    def fix_datetime_format(self, datetime_str):
        """Fix datetime format by removing 3rd, 4th, 5th to last chars and adding space ONLY if needed"""
        if not datetime_str or isinstance(datetime_str, type(None)):
            return datetime_str
        
        # Convert to string if not already
        datetime_str = str(datetime_str)
        
        # First, try to parse the datetime as-is to see if it's already valid
        try:
            pd.to_datetime(datetime_str)
            # If parsing succeeds, the datetime is already valid - return unchanged
            return datetime_str
        except:
            # If parsing fails, then apply the cleaning logic
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
        
    async def analyze_conversation(self, conversation, prompt, semaphore, chat_id=None):
        """Analyze a single conversation using OpenAI or Gemini"""
        async with semaphore:
            try:
                # Handle system prompt replacement if needed
                final_prompt = str(prompt)
                if "@Prompt@" in final_prompt and chat_id:
                    system_prompt = await self.fetch_system_prompt_for_chat(chat_id)
                    if system_prompt:
                        final_prompt = final_prompt.replace("@Prompt@", system_prompt)
                    else:
                        print(f"⚠️  No system prompt for chat {chat_id}, skipping conversation")
                        return {"skip_conversation": True, "reason": "no_system_prompt"}
                
                if self.provider == "openai":
                    return await self._analyze_with_openai_with_retry(conversation, final_prompt, chat_id)
                elif self.provider == "gemini":
                    return await self._analyze_with_gemini_with_retry(conversation, final_prompt, chat_id)
                else:
                    return {"llm_output": "", "error": f"Unsupported provider: {self.provider}"}
                    
            except Exception as e:
                print(f"🚨 LLM Error for conversation: {str(e)[:100]}...")
                return {"llm_output": "", "error": f"{self.provider} error: {str(e)}"}
    
    async def _analyze_with_openai_with_retry(self, conversation, prompt, chat_id=None):
        """Wrapper for OpenAI API calls with retry logic and doubled tokens on retry"""
        max_retries = 3
        base_delay = 1.0
        max_delay = 30.0
        timeout_seconds = 60.0
        
        chat_id_display = chat_id[-8:] if chat_id and len(chat_id) > 8 else chat_id or "unknown"
        
        for attempt in range(max_retries):
            try:
                # Use asyncio timeout for each attempt
                async with asyncio.timeout(timeout_seconds):
                    # Double tokens on retry (attempt 0 = normal, attempt 1+ = doubled)
                    token_multiplier = 2 if attempt > 0 else 1
                    
                    if attempt > 0:
                        print(f"🔄 Retry {attempt}/{max_retries - 1} with {token_multiplier}x tokens ({self.get_max_tokens(token_multiplier):,} tokens)")
                    
                    result = await self._analyze_with_openai(conversation, prompt, retry_attempt=attempt)
                    
                # If successful, return the result
                if result and not result.get("error"):
                    return result
                    
                # If empty response but no error, still consider it a success
                if result and result.get("llm_output") == "(empty)":
                    return result
                    
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    # Calculate exponential backoff with jitter
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    print(f"⏱️  Timeout for {chat_id_display} (attempt {attempt + 1}/{max_retries}). Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    print(f"❌ Timeout for {chat_id_display} after {max_retries} attempts")
                    return {"llm_output": "", "error": f"Timeout after {max_retries} attempts"}
                    
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a rate limit error
                is_rate_limit = any(phrase in error_msg.lower() for phrase in [
                    "rate limit", "rate_limit", "429", "too many requests", "insufficient_quota"
                ])
                
                # Check if it's a server error that might be transient
                is_server_error = any(phrase in error_msg.lower() for phrase in [
                    "500", "502", "503", "504", "server_error", "internal server error"
                ])
                
                if attempt < max_retries - 1 and (is_rate_limit or is_server_error):
                    # Calculate exponential backoff with jitter
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    
                    # For rate limits, use a longer delay
                    if is_rate_limit:
                        delay = max(delay, 5.0)  # At least 5 seconds for rate limits
                    
                    print(f"⚠️  OpenAI error for {chat_id_display}: {error_msg[:100]}...")
                    print(f"🔄 Retrying (attempt {attempt + 1}/{max_retries}) in {delay:.1f}s...")
                    
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed or non-retryable error
                    print(f"❌ OpenAI error for {chat_id_display} after {attempt + 1} attempts: {error_msg[:100]}...")
                    return {"llm_output": "", "error": f"OpenAI error after {attempt + 1} attempts: {error_msg}"}
        
        # Should not reach here, but just in case
        return {"llm_output": "", "error": f"Failed after {max_retries} attempts"}
    
    async def _analyze_with_openai(self, conversation, prompt, retry_attempt=0):
        """Analyze conversation using OpenAI"""
        # Match working message structure exactly
        messages = [
            {"role": "system", "content": str(prompt)},
            {"role": "user", "content": str(conversation)}
        ]
        
        # Use appropriate token parameter based on model type
        # Double tokens on retry (attempt 0 = normal, attempt 1+ = doubled)
        token_multiplier = 2 if retry_attempt > 0 else 1
        max_tokens = self.get_max_tokens(token_multiplier)
        
        if "o4-mini" in self.model or "o3" in self.model:
            # o-series models require max_completion_tokens
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=max_tokens
            )
        else:
            # Standard models use max_tokens
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=self.model_config.get("temperature", 0.0)
            )
        
        result = response.choices[0].message.content
        if result:
            result = result.strip()
        else:
            result = ""
        
        # Track token usage for OpenAI
        if hasattr(response, 'usage') and response.usage:
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            
            # Accumulate tokens
            self.token_usage['total_input_tokens'] += input_tokens
            self.token_usage['total_output_tokens'] += output_tokens
            self.token_usage['total_tokens'] += total_tokens
            self.token_usage['conversations_processed'] += 1
        
        # Return raw result like working version
        if not result:
            print(f"⚠️  Empty response from {self.provider} model {self.model}")
            return {"llm_output": "(empty)", "error": "Empty response from LLM"}
        
        return {"llm_output": result}
    
    async def _analyze_with_gemini_with_retry(self, conversation, prompt, chat_id=None):
        """Wrapper for Gemini API calls with retry logic and doubled tokens on retry"""
        max_retries = 3
        base_delay = 1.0
        max_delay = 30.0
        timeout_seconds = 60.0
        
        chat_id_display = chat_id[-8:] if chat_id and len(chat_id) > 8 else chat_id or "unknown"
        
        for attempt in range(max_retries):
            try:
                # Use asyncio timeout for each attempt
                async with asyncio.timeout(timeout_seconds):
                    # Double tokens on retry (attempt 0 = normal, attempt 1+ = doubled)
                    token_multiplier = 2 if attempt > 0 else 1
                    
                    if attempt > 0:
                        print(f"🔄 Retry {attempt}/{max_retries - 1} with {token_multiplier}x tokens ({self.get_max_tokens(token_multiplier):,} tokens)")
                    
                    result = await self._analyze_with_gemini(conversation, prompt, chat_id, retry_attempt=attempt)
                    
                # If successful, return the result
                if result and not result.get("error"):
                    return result
                    
                # If empty response but no error, still consider it a success
                if result and result.get("llm_output") == "(empty)":
                    return result
                    
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    # Calculate exponential backoff with jitter
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    print(f"⏱️  Timeout for {chat_id_display} (attempt {attempt + 1}/{max_retries}). Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    print(f"❌ Timeout for {chat_id_display} after {max_retries} attempts")
                    return {"llm_output": "", "error": f"Timeout after {max_retries} attempts"}
                    
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a rate limit or quota error
                is_rate_limit = any(phrase in error_msg.lower() for phrase in [
                    "rate limit", "quota", "resource exhausted", "429", "too many requests"
                ])
                
                # Check if it's a server error that might be transient
                is_server_error = any(phrase in error_msg.lower() for phrase in [
                    "500", "502", "503", "504", "server error", "service unavailable"
                ])
                
                if attempt < max_retries - 1 and (is_rate_limit or is_server_error):
                    # Calculate exponential backoff with jitter
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    
                    # For rate limits, use a longer delay
                    if is_rate_limit:
                        delay = max(delay, 5.0)  # At least 5 seconds for rate limits
                    
                    print(f"⚠️  Gemini error for {chat_id_display}: {error_msg[:100]}...")
                    print(f"🔄 Retrying (attempt {attempt + 1}/{max_retries}) in {delay:.1f}s...")
                    
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed or non-retryable error
                    print(f"❌ Gemini error for {chat_id_display} after {attempt + 1} attempts: {error_msg[:100]}...")
                    return {"llm_output": "", "error": f"Gemini error after {attempt + 1} attempts: {error_msg}"}
        
        # Should not reach here, but just in case
        return {"llm_output": "", "error": f"Failed after {max_retries} attempts"}
    
    async def _analyze_with_gemini(self, conversation, prompt, chat_id=None, retry_attempt=0):
        """Analyze conversation using Gemini"""
        # Combine system prompt and user message for Gemini
        full_prompt = f"{prompt}\n\nUser conversation:\n{conversation}"
        
        # Gemini doesn't have native async support, so we'll run in thread pool
        import asyncio
        loop = asyncio.get_event_loop()
        
        def _generate_content():
            # Build generation config with advanced parameters
            # Double tokens on retry (attempt 0 = normal, attempt 1+ = doubled)
            token_multiplier = 2 if retry_attempt > 0 else 1
            gen_config = genai.types.GenerationConfig(
                max_output_tokens=self.get_max_tokens(token_multiplier),
                temperature=self.model_config.get("temperature", 0.0)
            )
            
            # Add advanced parameters if specified in model config
            if "top_p" in self.model_config:
                gen_config.top_p = self.model_config["top_p"]
            if "top_k" in self.model_config:
                gen_config.top_k = self.model_config["top_k"]
            
            # Handle thinking mode using the exact parameters from user's example
            if self.model_config.get("enable_thinking", True) == False:
                # Following user's exact specification:
                # gemini_thinking_config = {"include_thoughts": False, "thinking_budget": 0}
                
                # Create generation config with thinking parameters included
                gen_config_dict = {
                    "max_output_tokens": self.get_max_tokens(token_multiplier),
                    "temperature": self.model_config.get("temperature", 0.0),
                    "include_thoughts": False,
                    "thinking_budget": 0
                }
                
                # Add other parameters
                if "top_p" in self.model_config:
                    gen_config_dict["top_p"] = self.model_config["top_p"]
                if "top_k" in self.model_config:
                    gen_config_dict["top_k"] = self.model_config["top_k"]
                
                # Try multiple approaches to pass thinking config
                try:
                    # Method 1: Pass as part of generation config
                    response = self.gemini_model.generate_content(
                        full_prompt,
                        generation_config=gen_config_dict
                    )
                except Exception as e1:
                    try:
                        # Method 2: Try with model_settings approach
                        response = self.gemini_model.generate_content(
                            full_prompt,
                            generation_config=gen_config,
                            model_settings={
                                "gemini_thinking_config": {
                                    "include_thoughts": False,
                                    "thinking_budget": 0
                                }
                            }
                        )
                    except Exception as e2:
                        # Method 3: Standard config as fallback
                        response = self.gemini_model.generate_content(
                            full_prompt,
                            generation_config=gen_config
                        )
            else:
                response = self.gemini_model.generate_content(
                    full_prompt,
                    generation_config=gen_config
                )
            return response
        
        response = await loop.run_in_executor(None, _generate_content)
        
        # Extract result and usage info
        result = response.text if response.text else ""
        
        # Track and log Gemini token usage
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            from datetime import datetime
            timestamp = datetime.now().strftime('%H:%M:%S')
            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
            total_tokens = getattr(response.usage_metadata, 'total_token_count', input_tokens + output_tokens)
            
            # Accumulate tokens
            self.token_usage['total_input_tokens'] += input_tokens
            self.token_usage['total_output_tokens'] += output_tokens
            self.token_usage['total_tokens'] += total_tokens
            self.token_usage['conversations_processed'] += 1
            
            chat_id_display = chat_id[-8:] if chat_id and len(chat_id) > 8 else chat_id or "unknown"
            print(f"🤖 {timestamp} {chat_id_display}: {total_tokens}t ({input_tokens}→{output_tokens})")
        
        if result:
            result = result.strip()
        else:
            result = ""
        
        # Return raw result
        if not result:
            chat_id_display = chat_id[-8:] if chat_id and len(chat_id) > 8 else chat_id or "unknown"
            print(f"⚠️  Empty response from Gemini for {chat_id_display}")
            return {"llm_output": "(empty)", "error": "Empty response from LLM"}
        
        return {"llm_output": result}
        
    async def process_conversations(self, conversations: List[Dict], prompt_text: str) -> List[Dict]:
        """Process conversations through LLM with concurrency control"""
        # Create semaphore for concurrency control
        # Reduced from 40 to 30 when running multiple concurrent pipelines
        semaphore = asyncio.Semaphore(30)
        
        results = []
        tasks = []
        conversation_data = []
        
        for conv in conversations:
            # Format conversation for prompt
            if isinstance(conv, dict) and 'Messages' in conv:
                # Segmented format
                conversation_text = conv['Messages']
                chat_id = conv.get('Conversation ID', 'unknown')
                customer_name = conv.get('Customer Name', 'unknown')
            elif isinstance(conv, dict) and 'conversation' in conv:
                # JSON format
                conversation_text = str(conv)
                chat_id = conv.get('chat_id', 'unknown')
                customer_name = conv.get('customer_name', 'unknown')
            elif isinstance(conv, dict) and 'conversation_record' in conv:
                # JSON format with conversation_record structure
                conversation_text = str(conv)
                # Extract chat_id from first conversation record
                if conv['conversation_record'] and len(conv['conversation_record']) > 0:
                    chat_id = conv['conversation_record'][0].get('chat_id', 'unknown')
                else:
                    chat_id = 'unknown'
                customer_name = conv.get('customer_name', 'unknown')
            elif isinstance(conv, dict) and 'content_xml_view' in conv:
                # XML or XML3D format
                conversation_text = conv['content_xml_view']
                chat_id = conv.get('conversation_id', conv.get('customer_name', 'unknown'))
                customer_name = conv.get('customer_name', 'unknown')
            else:
                # Transparent format or other
                conversation_text = str(conv)
                chat_id = conv.get('conversation ID', conv.get('Conversation ID', 'unknown'))
                customer_name = 'unknown'
            
            # Create async task for this conversation
            task = self.analyze_conversation(conversation_text, prompt_text, semaphore, chat_id)
            tasks.append(task)
            conversation_data.append((chat_id, customer_name, conversation_text))
        
        print(f"🤖 Processing {len(tasks)} conversations through {self.model} ({self.provider})...")
        print(f"🔧 Using {self.get_max_tokens():,} token limit for {self.model} (doubles on retry)")
        
        # Wait for all conversations to be processed
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and track skipped conversations
        skipped_count = 0
        skipped_reasons = {}
        
        for i, (result, (chat_id, customer_name, conversation_text)) in enumerate(zip(task_results, conversation_data)):
            if isinstance(result, Exception):
                results.append({
                    'conversation_id': chat_id,
                    'conversation': conversation_text,
                    'llm_output': ''
                })
            elif isinstance(result, dict):
                # Check if conversation should be skipped
                if result.get('skip_conversation', False):
                    reason = result.get('reason', 'unknown')
                    skipped_count += 1
                    skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1
                    continue  # Skip adding to results
                
                llm_output = result.get('llm_output', '')
                
                results.append({
                    'conversation_id': chat_id,
                    'conversation': conversation_text,
                    'llm_output': str(llm_output)
                })
            else:
                results.append({
                    'conversation_id': chat_id,
                    'conversation': conversation_text,
                    'llm_output': str(result)
                })
            
            if (i + 1) % 100 == 0:
                print(f"⚡ Processed {i + 1}/{len(task_results)} conversations...")
        
        # Report processing statistics
        total_processed = len(results)
        total_attempted = len(task_results)
        
        if skipped_count > 0:
            print(f"📊 Processing Summary:")
            print(f"   Total conversations: {total_attempted}")
            print(f"   Successfully processed: {total_processed}")
            print(f"   Skipped: {skipped_count}")
            for reason, count in skipped_reasons.items():
                if reason == 'no_system_prompt':
                    print(f"     - No system prompt: {count}")
                else:
                    print(f"     - {reason}: {count}")
        else:
            print(f"✅ Processed {len(results)} conversations")
            
        return results
    
    def get_token_summary(self, department_name: str = ""):
        """Get a formatted summary of token usage"""
        if self.token_usage['conversations_processed'] == 0:
            return f"📊 {department_name} Token Usage: No conversations processed"
        
        return (f"📊 {department_name} Token Usage: "
                f"{self.token_usage['total_tokens']:,} total tokens "
                f"({self.token_usage['total_input_tokens']:,}→{self.token_usage['total_output_tokens']:,}) "
                f"for {self.token_usage['conversations_processed']} conversations")

def download_tableau_data(department: str, days_lookback: int = 1, target_date: datetime = None) -> str:
    """Download data from Tableau for a department with caching and view sharing"""
    dept_config = DEPARTMENTS[department]
    tableau_view = dept_config['tableau_view']
    
    # Use target_date if provided, otherwise use yesterday's date
    if target_date is None:
        target_date = datetime.now() - timedelta(days=1)
    start_date = target_date - timedelta(days=days_lookback-1)
    target_date_str = target_date.strftime('%Y%m%d')
    
    # Check for shared views (African, Ethiopian, Filipina all use "Applicants")
    view_sharing_map = {
        "Applicants": ["African", "Ethiopian", "Filipina"]
    }
    
    # Determine the canonical department for shared views
    canonical_dept = department
    if tableau_view in view_sharing_map:
        # Use the first department in the list as canonical
        canonical_dept = view_sharing_map[tableau_view][0]
    
    # Check cache first
    cache_filename = f"{canonical_dept}_{target_date_str}.csv"
    date_folder = target_date.strftime('%Y-%m-%d')
    cache_filepath = f"outputs/tableau_exports/{date_folder}/{cache_filename}"
    
    if os.path.exists(cache_filepath):
        print(f"📋 Using cached data for {department} (view: {tableau_view}): {cache_filepath}")
        return cache_filepath
    
    print(f"📥 Downloading Tableau data for {canonical_dept} (view: {tableau_view})...")
    
    # Download from Tableau
    downloader = TableauDownloadCSV()
    required_headers = DATA_PROCESSING['required_headers']
    
    filepath = downloader.download_csv(
        workbook_name="8 Department wise tables for chats & calls",
        view_name=tableau_view,
        from_date=start_date.strftime('%Y-%m-%d'),
        to_date=target_date.strftime('%Y-%m-%d'),
        output=cache_filename,
        required_headers=required_headers
    )
    
    print(f"✅ Downloaded: {filepath}")
    
    # If downloading for a shared view, notify about sharing
    if tableau_view in view_sharing_map and department != canonical_dept:
        shared_depts = [d for d in view_sharing_map[tableau_view] if d != canonical_dept]
        print(f"🔗 Data will be shared with: {', '.join(shared_depts)}")
    
    return filepath

def preprocess_data(raw_file: str, department: str, format_type: str, filter_agent_messages: bool = False, target_date: datetime = None, include_all_skills: bool = False) -> str:
    """Preprocess raw data based on format type
    
    Args:
        raw_file: Path to raw CSV file
        department: Department name
        format_type: Format type (json, xml, segmented, transparent)
        filter_agent_messages: If True, removes all agent messages from the data
        target_date: Target date for processing, defaults to yesterday
    """
    
    # Check if preprocessing output already exists (caching)
    if check_preprocessed_output_exists(department, format_type, target_date):
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        date_folder = target_date.strftime('%Y-%m-%d')
        
        # Generate expected filename and return cached path
        if format_type == "segmented":
            filename = f"{department}_segmented.csv"
        elif format_type == "json":
            filename = f"{department}_json.jsonl"
        elif format_type == "transparent":
            filename = f"{department}_transparent.csv"
        elif format_type == "xml":
            filename = f"{department}_xml.csv"
        elif format_type == "xml3d":
            filename = f"{department}_xml3d.csv"
        
        return f"outputs/preprocessing_output/{date_folder}/{filename}"
    
    print(f"🔄 Preprocessing data for {department} in {format_type} format...")
    
    dept_config = DEPARTMENTS[department]
    target_skills = dept_config['skills'] if not include_all_skills else None
    
    # Clean datetime columns first (non-destructive)
    df = pd.read_csv(raw_file)
    processor = LLMProcessor()
    cleaned_df = processor.clean_datetime_columns_df(df)
    
    # Create temporary cleaned file for processing
    temp_cleaned_path = raw_file.replace('.csv', '_temp_cleaned.csv')
    cleaned_df.to_csv(temp_cleaned_path, index=False)
    
    try:
        # Create date-based subfolder for preprocessing output
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        date_folder = target_date.strftime('%Y-%m-%d')
        preprocessing_dir = f"outputs/preprocessing_output/{date_folder}"
        os.makedirs(preprocessing_dir, exist_ok=True)
        
        # Clean raw data 
        cleaned_file = f"{preprocessing_dir}/{department}_cleaned.csv"
        clean_raw_data(temp_cleaned_path, cleaned_file, filter_agent_messages)
        
        # Process based on format
        if format_type == "segmented":
            processed_df = process_conversations(cleaned_file, target_skills)
            output_file = f"{preprocessing_dir}/{department}_segmented.csv"
            processed_df.to_csv(output_file, index=False)
            
        elif format_type == "json":
            conversations = convert_conversation_to_json(cleaned_file, target_skills)
            output_file = f"{preprocessing_dir}/{department}_json.jsonl"
            
            import json
            with open(output_file, 'w') as f:
                for conv in conversations:
                    f.write(json.dumps(conv) + '\n')
                    
        elif format_type == "transparent":
            output_file = f"{preprocessing_dir}/{department}_transparent.csv"
            create_transparent_view(cleaned_file, output_file)
            
        elif format_type == "xml":
            from utils.xml_processor import create_xml_view
            output_file = f"{preprocessing_dir}/{department}_xml.csv"
            create_xml_view(cleaned_file, output_file, target_skills)
            
        elif format_type == "xml3d":
            from utils.xml3d_processor import create_xml3d_view
            output_file = f"{preprocessing_dir}/{department}_xml3d.csv"
            create_xml3d_view(department, target_skills)
            
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        print(f"✅ Preprocessed data saved: {output_file}")
        return output_file
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_cleaned_path):
            os.remove(temp_cleaned_path)

def load_preprocessed_data(file_path: str, format_type: str) -> List[Dict]:
    """Load preprocessed data for LLM processing"""
    if format_type == "json":
        import json
        conversations = []
        with open(file_path, 'r') as f:
            for line in f:
                conversations.append(json.loads(line.strip()))
        return conversations
    elif format_type == "xml":
        # XML format has specific structure: conversation_id, content_xml_view, last_skill
        df = pd.read_csv(file_path)
        conversations = []
        for _, row in df.iterrows():
            conversations.append({
                'conversation_id': row['conversation_id'],
                'content_xml_view': row['content_xml_view'], 
                'unique_skills': row['unique_skills']
            })
        return conversations
    elif format_type == "xml3d":
        # XML3D format has structure: customer_name, content_xml_view
        df = pd.read_csv(file_path)
        conversations = []
        for _, row in df.iterrows():
            conversations.append({
                'customer_name': row['customer_name'],
                'content_xml_view': row['content_xml_view']
            })
        return conversations
    else:
        # CSV formats (segmented, transparent)
        df = pd.read_csv(file_path)
        return df.to_dict('records')

async def run_llm_processing(conversations: List[Dict], prompt_text: str, model: str) -> tuple[List[Dict], LLMProcessor]:
    """Run conversations through LLM and return results with processor for token tracking"""
    processor = LLMProcessor(model)
    results = await processor.process_conversations(conversations, prompt_text)
    return results, processor

def check_llm_output_exists(department: str, prompt_type: str, target_date: datetime = None) -> bool:
    """Check if LLM output already exists for a department and date"""
    if target_date is None:
        target_date = datetime.now() - timedelta(days=1)
    date_folder = target_date.strftime('%Y-%m-%d')
    date_str = target_date.strftime('%m_%d')
    dept_name = department.lower().replace(' ', '_')
    
    if prompt_type == "sentiment_analysis":
        filename = f"saprompt_{dept_name}_{date_str}.csv"
    elif prompt_type == "rule_breaking":
        filename = f"rule_breaking_{dept_name}_{date_str}.csv"
    elif prompt_type == "ftr":
        filename = f"ftr_{dept_name}_{date_str}.csv"
    elif prompt_type == "category_docs":
        filename = f"category_docs_{dept_name}_{date_str}.csv"
    else:
        filename = f"{prompt_type}_{dept_name}_{date_str}.csv"
    
    output_path = f"outputs/LLM_outputs/{date_folder}/{filename}"
    
    if os.path.exists(output_path):
        # Check if file has content (not just headers)
        try:
            df = pd.read_csv(output_path)
            if len(df) > 0:
                print(f"📋 Using cached LLM outputs for {department}: {output_path}")
                print(f"   Found {len(df)} existing results")
                return True
        except:
            pass
    
    return False

def check_preprocessed_output_exists(department: str, format_type: str, target_date: datetime = None) -> bool:
    """Check if preprocessed output already exists for a department and date"""
    if target_date is None:
        target_date = datetime.now() - timedelta(days=1)
    date_folder = target_date.strftime('%Y-%m-%d')
    
    # Generate expected filename based on format
    if format_type == "segmented":
        filename = f"{department}_segmented.csv"
    elif format_type == "json":
        filename = f"{department}_json.jsonl"
    elif format_type == "transparent":
        filename = f"{department}_transparent.csv"
    elif format_type == "xml":
        filename = f"{department}_xml.csv"
    elif format_type == "xml3d":
        filename = f"{department}_xml3d.csv"
    else:
        return False
    
    output_path = f"outputs/preprocessing_output/{date_folder}/{filename}"
    
    if os.path.exists(output_path):
        # Check if file has content
        try:
            if format_type == "json":
                # For JSON files, check line count
                with open(output_path, 'r') as f:
                    line_count = sum(1 for _ in f)
                if line_count > 0:
                    print(f"📋 Using cached preprocessing for {department} ({format_type}): {output_path}")
                    print(f"   Found {line_count} existing records")
                    return True
            else:
                # For CSV files, check DataFrame length
                df = pd.read_csv(output_path)
                if len(df) > 0:
                    print(f"📋 Using cached preprocessing for {department} ({format_type}): {output_path}")
                    print(f"   Found {len(df)} existing records")
                    return True
        except:
            pass
    
    return False

def save_llm_outputs(results: List[Dict], department: str, prompt_type: str, target_date: datetime = None) -> str:
    """Save LLM outputs to expected location"""
    import json
    
    # Generate output filename
    if target_date is None:
        target_date = datetime.now() - timedelta(days=1)
    date_str = target_date.strftime('%m_%d')
    dept_name = department.lower().replace(' ', '_')
    
    if prompt_type == "sentiment_analysis":
        filename = f"saprompt_{dept_name}_{date_str}.csv"
    elif prompt_type == "rule_breaking":
        filename = f"rule_breaking_{dept_name}_{date_str}.csv"
    elif prompt_type == "ftr":
        filename = f"ftr_{dept_name}_{date_str}.csv"
    elif prompt_type == "category_docs":
        filename = f"category_docs_{dept_name}_{date_str}.csv"
    else:
        filename = f"{prompt_type}_{dept_name}_{date_str}.csv"
    
    # Create date-based subfolder 
    date_folder = target_date.strftime('%Y-%m-%d')
    output_dir = f"outputs/LLM_outputs/{date_folder}"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, filename)
    
    # For rule breaking, format the JSON beautifully
    if prompt_type == "rule_breaking":
        formatted_results = []
        for result in results:
            formatted_result = result.copy()
            llm_output = formatted_result.get('llm_output', '')
            
            # Try to parse and format the JSON beautifully
            try:
                if llm_output and llm_output.strip():
                    parsed_json = json.loads(llm_output)
                    formatted_result['llm_output'] = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                else:
                    formatted_result['llm_output'] = llm_output
            except (json.JSONDecodeError, TypeError):
                # If it's not valid JSON, keep as is
                formatted_result['llm_output'] = llm_output
            
            formatted_results.append(formatted_result)
        
        # Save as CSV
        df = pd.DataFrame(formatted_results)
    else:
        # For other prompt types, use original behavior
        df = pd.DataFrame(results)
    
    df.to_csv(output_path, index=False)
    
    print(f"💾 Saved LLM outputs: {output_path}")
    return output_path

def run_sentiment_analysis(departments, model, format_type, with_upload=False, dry_run=False, target_date=None):
    """Run complete sentiment analysis pipeline"""
    print(f"📊 Running Sentiment Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full SA pipeline")
        return True
    
    try:
        # Get prompt
        prompt_registry = PromptRegistry()
        sa_prompt = prompt_registry.get_prompt("sentiment_analysis")
        prompt_text = sa_prompt.get_prompt_text()
        
        # Determine departments to process
        if departments == "all":
            dept_list = list(DEPARTMENTS.keys())
        else:
            dept_list = [d.strip() for d in departments.split(',')]
        
        print(f"🎯 Processing departments: {dept_list}")
        
        for department in dept_list:
            print(f"\n🏢 Processing {department}...")
            
            try:
                # Check if LLM outputs already exist (caching)
                if check_llm_output_exists(department, "sentiment_analysis", target_date):
                    print(f"⚡ Skipping LLM processing for {department} - using cached results")
                    continue
                
                # Step 1: Download from Tableau
                raw_file = download_tableau_data(department, days_lookback=1, target_date=target_date)
                
                # Step 2: Preprocess data
                processed_file = preprocess_data(raw_file, department, format_type, target_date=target_date)
                
                # Step 3: Load preprocessed data
                conversations = load_preprocessed_data(processed_file, format_type)
                
                if not conversations:
                    print(f"⚠️  No conversations found for {department}")
                    continue
                
                # Step 4: Process through LLM
                results, processor = asyncio.run(run_llm_processing(conversations, prompt_text, model))
                
                # Step 5: Save outputs
                save_llm_outputs(results, department, "sentiment_analysis", target_date)
                
                # Display token usage
                print(processor.get_token_summary(department))
                print(f"✅ Completed {department}")
                
            except Exception as e:
                print(f"❌ Failed processing {department}: {str(e)}")
                continue
        
        # Step 6: Post-processing and upload
        if with_upload:
            print(f"\n📤 Running post-processing and upload for: {', '.join(dept_list)}...")
            from post_processors.sa_post_processing import SAPreprocessor
            from post_processors.upload_sa_sheets import SaprompUploader
            
            # Only process the departments that were specified
            processor = SAPreprocessor()
            print(f"🚀 Starting SA preprocessing for: {', '.join(dept_list)}")
            
            results = {}
            success_count = 0
            
            for department in dept_list:
                nps = processor.update_department_nps(department)
                if nps is not None:
                    results[department] = nps
                    success_count += 1
                else:
                    results[department] = None
            
            # Print summary for requested departments only
            print(f"\n📈 Summary: Processed {success_count}/{len(dept_list)} departments")
            print("\n📊 NPS Results:")
            for dept, nps in results.items():
                if nps is not None:
                    print(f"  {dept}: {nps:.2f}")
                else:
                    print(f"  {dept}: Failed")
            
            # Upload files (this will only upload files that exist)
            uploader = SaprompUploader(target_date=target_date)
            uploader.process_all_files()
        
        print("🎉 Sentiment Analysis pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ SA Pipeline failed: {str(e)}")
        return False

def run_rule_breaking(departments, model, format_type, with_upload=False, dry_run=False, target_date=None):
    """Run complete rule breaking analysis pipeline"""
    print(f"🚨 Running Rule Breaking Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full Rule Breaking pipeline")
        return True
    
    try:
        # Get prompt
        prompt_registry = PromptRegistry()
        rb_prompt = prompt_registry.get_prompt("rule_breaking")
        
        # Determine departments to process
        if departments == "all":
            # Rule breaking typically only works for specific departments
            dept_list = ["Doctors", "CC Sales", "MV Resolvers", "MV Sales"]
        else:
            dept_list = [d.strip() for d in departments.split(',')]
        
        print(f"🎯 Processing departments: {dept_list}")
        
        for department in dept_list:
            print(f"\n🏢 Processing {department}...")
            
            try:
                # Check if LLM outputs already exist (caching)
                if check_llm_output_exists(department, "rule_breaking", target_date):
                    print(f"⚡ Skipping LLM processing for {department} - using cached results")
                    continue
                
                # Get department-specific prompt
                prompt_text = rb_prompt.get_prompt_text(department)
                
                # Step 1: Download from Tableau
                raw_file = download_tableau_data(department, days_lookback=1, target_date=target_date)
                
                # Step 2: Preprocess data
                processed_file = preprocess_data(raw_file, department, format_type, target_date=target_date)
                
                # Step 3: Load preprocessed data
                conversations = load_preprocessed_data(processed_file, format_type)
                
                if not conversations:
                    print(f"⚠️  No conversations found for {department}")
                    continue
                
                # Step 3.5: Filter automated sales messages for MV Sales and CC Sales
                if department.lower() in ['mv sales', 'cc sales'] and format_type == 'json':
                    from utils.sales_message_filter import filter_sales_conversations
                    print(f"🔧 Filtering automated sales messages for {department}...")
                    original_count = len(conversations)
                    # Use 70% similarity threshold for flexible matching
                    conversations = filter_sales_conversations(conversations, [department], similarity_threshold=0.7)
                    filtered_count = len(conversations)
                    if original_count > filtered_count:
                        print(f"   Conversations after filtering: {filtered_count} (from {original_count})")
                
                # Step 4: Process through LLM
                results, processor = asyncio.run(run_llm_processing(conversations, prompt_text, model))
                
                # Step 5: Save outputs
                save_llm_outputs(results, department, "rule_breaking", target_date)
                
                # Display token usage
                print(processor.get_token_summary(department))
                print(f"✅ Completed {department}")
                
            except Exception as e:
                print(f"❌ Failed processing {department}: {str(e)}")
                continue
        
        # Step 6: Post-processing and upload
        if with_upload:
            print(f"\n📤 Running post-processing and upload for: {', '.join(dept_list)}...")
            from post_processors.rulebreaking_postprocessing import RuleBreakingProcessor
            from post_processors.upload_rulebreaking_sheets import RuleBreakingUploader
            
            # Only process the departments that were specified
            processor = RuleBreakingProcessor()
            print(f"🚀 Starting Rule Breaking post-processing for: {', '.join(dept_list)}")
            
            # Find rule breaking files for the specified departments only
            all_files = processor.find_rule_breaking_files()
            
            # Filter files to only include requested departments
            filtered_files = []
            for filepath, dept_key, filename in all_files:
                # Convert dept_key to proper department name to match dept_list
                dept_name = dept_key.replace('_', ' ').title()
                
                # Handle specific mappings
                if dept_name == 'Cc Sales':
                    dept_name = 'CC Sales'
                elif dept_name == 'Cc Resolvers':
                    dept_name = 'CC Resolvers'
                elif dept_name == 'Mv Resolvers':
                    dept_name = 'MV Resolvers'
                elif dept_name == 'Mv Sales':
                    dept_name = 'MV Sales'
                
                if dept_name in dept_list:
                    filtered_files.append((filepath, dept_key, filename))
                    print(f"📁 Will process: {filename} -> {dept_name}")
                else:
                    print(f"⏭️  Skipping: {filename} -> {dept_name} (not in requested departments)")
            
            # Process only the filtered files
            success_count = 0
            for filepath, dept_key, filename in filtered_files:
                try:
                    print(f"\n📊 Processing {filename}...")
                    
                    # Analyze the data
                    analysis_results = processor.analyze_rule_breaking_data(filepath)
                    if not analysis_results:
                        continue
                    
                    # Create proper department name (same logic as in original code)
                    dept_name = dept_key.replace('_', ' ').title()
                    
                    # Map prompt prefixes and standard cases
                    if dept_name == 'Mvr Mv Resolvers':
                        dept_name = 'MV Resolvers'
                    elif dept_name == 'Ccs Cc Sales':
                        dept_name = 'CC Sales'
                    elif dept_name == 'Mvs Mv Sales':
                        dept_name = 'MV Sales'
                    elif dept_name == 'Doc Doctors':
                        dept_name = 'Doctors'
                    elif dept_name == 'Cc Sales':
                        dept_name = 'CC Sales'
                    elif dept_name == 'Cc Resolvers':
                        dept_name = 'CC Resolvers'
                    elif dept_name == 'Mv Resolvers':
                        dept_name = 'MV Resolvers'
                    elif dept_name == 'Mv Sales':
                        dept_name = 'MV Sales'
                    
                    # Create summary report
                    output_filename = f"{processor.rule_breaking_dir}/{dept_name}_Rule_Breaking_Summary.csv"
                    percentage_ge_1 = processor.create_summary_report(analysis_results, dept_name, output_filename)
                    
                    if percentage_ge_1 is not None:
                        # Upload to Google Sheets
                        if processor.upload_to_google_sheets(dept_name, percentage_ge_1):
                            success_count += 1
                        
                except Exception as e:
                    print(f"❌ Error processing {filename}: {str(e)}")
            
            # Print summary for requested departments only
            print(f"\n📈 Processing Summary:")
            print(f"✅ Successfully processed and uploaded: {success_count}/{len(filtered_files)} departments")
            
            # Upload files (this will only upload files that exist for requested departments)
            uploader = RuleBreakingUploader()
            uploader.process_all_files()
        
        print("🎉 Rule Breaking Analysis pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Rule Breaking Pipeline failed: {str(e)}")
        return False

def run_ftr_analysis(departments, model, format_type, with_upload=False, dry_run=False):
    """Run complete FTR analysis pipeline"""
    print(f"📈 Running FTR Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full FTR pipeline")
        return True
    
    try:
        # Get prompt
        prompt_registry = PromptRegistry()
        ftr_prompt = prompt_registry.get_prompt("ftr")
        prompt_text = ftr_prompt.get_prompt_text()
        
        # Determine departments to process
        if departments == "all":
            dept_list = list(DEPARTMENTS.keys())
        else:
            dept_list = [d.strip() for d in departments.split(',')]
        
        print(f"🎯 Processing departments: {dept_list}")
        
        for department in dept_list:
            print(f"\n🏢 Processing {department}...")
            
            try:
                # Check if LLM outputs already exist (caching)
                if check_llm_output_exists(department, "ftr"):
                    print(f"⚡ Skipping LLM processing for {department} - using cached results")
                    continue
                
                # Step 1: Download from Tableau (3-day lookback for FTR)
                raw_file = download_tableau_data(department, days_lookback=3)
                
                # Step 2: Preprocess data
                processed_file = preprocess_data(raw_file, department, format_type)
                
                # Step 3: Load preprocessed data
                conversations = load_preprocessed_data(processed_file, format_type)
                
                if not conversations:
                    print(f"⚠️  No conversations found for {department}")
                    continue
                
                # Step 4: Process through LLM
                results, processor = asyncio.run(run_llm_processing(conversations, prompt_text, model))
                
                # Step 5: Save outputs
                save_llm_outputs(results, department, "ftr")
                
                # Display token usage
                print(processor.get_token_summary(department))
                print(f"✅ Completed {department}")
                
            except Exception as e:
                print(f"❌ Failed processing {department}: {str(e)}")
                continue
        
        # Post-processing step (always run for FTR since it generates essential metrics)
        print(f"\n📊 Starting FTR post-processing...")
        try:
            from post_processors.ftr_postprocessing import FTRProcessor
            processor = FTRProcessor()
            processor.process_all_files()
            
            # Upload to Google Sheets if requested
            if with_upload:
                print(f"\n📤 Uploading FTR results to Google Sheets...")
                try:
                    from post_processors.upload_ftr_sheets import FTRUploader
                    uploader = FTRUploader()
                    uploader.process_all_files()
                except Exception as e:
                    print(f"❌ Error during Google Sheets upload: {str(e)}")
                    
        except Exception as e:
            print(f"❌ FTR post-processing failed: {str(e)}")
        
        print("🎉 FTR Analysis pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ FTR Pipeline failed: {str(e)}")
        return False

def run_false_promises_analysis(departments, model, format_type, with_upload=False, dry_run=False):
    """Run complete False Promises analysis pipeline"""
    print(f"🔍 Running False Promises Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full False Promises pipeline")
        return True
    
    try:
        # Get prompt
        prompt_registry = PromptRegistry()
        false_promises_prompt = prompt_registry.get_prompt("false_promises")
        prompt_text = false_promises_prompt.get_prompt_text()
        
        # Determine departments to process
        if departments == "all":
            dept_list = list(DEPARTMENTS.keys())
        else:
            dept_list = [d.strip() for d in departments.split(',')]
        
        print(f"🎯 Processing departments: {dept_list}")
        
        for department in dept_list:
            print(f"\n🏢 Processing {department}...")
            
            try:
                # Check if LLM outputs already exist (caching)
                if check_llm_output_exists(department, "false_promises"):
                    print(f"⚡ Skipping LLM processing for {department} - using cached results")
                    continue
                
                # Step 1: Download from Tableau
                raw_file = download_tableau_data(department)
                
                # Step 2: Preprocess data
                processed_file = preprocess_data(raw_file, department, format_type)
                
                # Step 3: Load preprocessed data
                conversations = load_preprocessed_data(processed_file, format_type)
                
                if not conversations:
                    print(f"⚠️  No conversations found for {department}")
                    continue
                
                # Step 4: Process through LLM (system prompts will be fetched automatically)
                results, processor = asyncio.run(run_llm_processing(conversations, prompt_text, model))
                
                # Step 5: Save outputs
                save_llm_outputs(results, department, "false_promises")
                
                # Display token usage
                print(processor.get_token_summary(department))
                print(f"✅ Completed {department}")
                
            except Exception as e:
                print(f"❌ Failed processing {department}: {str(e)}")
                continue
        
        # Upload to Google Sheets
        if with_upload:
            print(f"\n📤 Uploading false promises results to Google Sheets...")
            try:
                from post_processors.upload_false_promises_sheets import FalsePromisesUploader
                uploader = FalsePromisesUploader()
                uploader.process_all_files()
            except Exception as e:
                print(f"❌ Error during Google Sheets upload: {str(e)}")
        
        print("🎉 False Promises Analysis pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ False Promises Pipeline failed: {str(e)}")
        return False

def run_categorizing_analysis(departments, model, format_type, with_upload=False, dry_run=False):
    """Run complete Categorizing analysis pipeline with department-specific logic"""
    print(f"📂 Running Categorizing Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full Categorizing pipeline")
        return True
    
    try:
        prompt_registry = PromptRegistry()
        
        # Determine departments to process
        if departments == "all":
            dept_list = list(DEPARTMENTS.keys())
        else:
            dept_list = [d.strip() for d in departments.split(',')]
        
        print(f"🎯 Processing departments: {dept_list}")
        
        # Separate departments by their processing type
        doctors_depts = [d for d in dept_list if d.lower() == "doctors"]
        other_depts = [d for d in dept_list if d.lower() != "doctors"]
        
        # Process Doctors department with category_docs prompt
        if doctors_depts:
            print(f"\n🏥 Processing Doctors department with category_docs prompt...")
            category_docs_prompt = prompt_registry.get_prompt("category_docs")
            prompt_text = category_docs_prompt.get_prompt_text()
            
            for department in doctors_depts:
                print(f"\n🏢 Processing {department}...")
                
                try:
                    # Check if LLM outputs already exist - use category_docs as key
                    if check_llm_output_exists(department, "category_docs"):
                        print(f"⚡ Skipping LLM processing for {department} - using cached results")
                        continue
                    
                    # Step 1: Download from Tableau
                    raw_file = download_tableau_data(department)
                    
                    # Step 2: Preprocess data
                    processed_file = preprocess_data(raw_file, department, format_type)
                    
                    # Step 3: Load preprocessed data
                    conversations = load_preprocessed_data(processed_file, format_type)
                    
                    if not conversations:
                        print(f"⚠️  No conversations found for {department}")
                        continue
                    
                    # Step 4: Use gemini-2.5-flash for Doctors
                    dept_model = "gemini-2.5-flash"
                    print(f"🤖 Using gemini-2.5-flash for {department} (Temp: 0.2, TopP: 1.0, TopK: 40, Think: OFF)")
                    
                    # Step 5: Process through LLM
                    results, processor = asyncio.run(run_llm_processing(conversations, prompt_text, dept_model))
                    
                    # Step 6: Save outputs - use category_docs as key
                    save_llm_outputs(results, department, "category_docs")
                    
                    # Display token usage
                    print(processor.get_token_summary(department))
                    print(f"✅ Completed {department}")
                    
                except Exception as e:
                    print(f"❌ Failed processing {department}: {str(e)}")
                    continue
        
        # Process other departments with categorizing prompt
        if other_depts:
            print(f"\n🏢 Processing other departments with categorizing prompt...")
            categorizing_prompt = prompt_registry.get_prompt("categorizing")
            prompt_text = categorizing_prompt.get_prompt_text()
            
            for department in other_depts:
                print(f"\n🏢 Processing {department}...")
                
                try:
                    # Check if LLM outputs already exist - use categorizing as key
                    if check_llm_output_exists(department, "categorizing"):
                        print(f"⚡ Skipping LLM processing for {department} - using cached results")
                        continue
                    
                    # Step 1: Download from Tableau
                    raw_file = download_tableau_data(department)
                    
                    # Step 2: Preprocess data
                    processed_file = preprocess_data(raw_file, department, format_type)
                    
                    # Step 3: Load preprocessed data
                    conversations = load_preprocessed_data(processed_file, format_type)
                    
                    if not conversations:
                        print(f"⚠️  No conversations found for {department}")
                        continue
                    
                    # Step 4: Use specified model for other departments
                    dept_model = model
                    
                    # Step 5: Process through LLM
                    results, processor = asyncio.run(run_llm_processing(conversations, prompt_text, dept_model))
                    
                    # Step 6: Save outputs - use categorizing as key
                    save_llm_outputs(results, department, "categorizing")
                    
                    # Display token usage
                    print(processor.get_token_summary(department))
                    print(f"✅ Completed {department}")
                    
                except Exception as e:
                    print(f"❌ Failed processing {department}: {str(e)}")
                    continue
        
        # Post-processing and upload
        if with_upload:
            # Process and upload category_docs results for Doctors
            if doctors_depts:
                print(f"\n📊 Starting Category Docs post-processing for Doctors...")
                try:
                    from post_processors.category_docs_postprocessing import CategoryDocsProcessor
                    processor = CategoryDocsProcessor()
                    processor.process_all_departments()
                except Exception as e:
                    print(f"❌ Error during category docs post-processing: {str(e)}")
                
                print(f"\n📤 Uploading category docs raw results for Doctors...")
                try:
                    from post_processors.upload_category_docs_sheets import CategoryDocsUploader
                    uploader = CategoryDocsUploader()
                    uploader.process_all_files()
                except Exception as e:
                    print(f"❌ Error during category docs upload: {str(e)}")
                
                print(f"\n📤 Uploading category docs summary results for Doctors...")
                try:
                    from post_processors.upload_category_docs_summary_sheets import CategoryDocsSummaryUploader
                    summary_uploader = CategoryDocsSummaryUploader()
                    summary_uploader.process_all_files()
                except Exception as e:
                    print(f"❌ Error during category docs summary upload: {str(e)}")
            
            # Post-process and upload categorizing results for other departments
            if other_depts:
                print(f"\n📊 Starting Categorizing post-processing for other departments...")
                try:
                    from post_processors.categorizing_postprocessing import CategorizingProcessor
                    processor = CategorizingProcessor()
                    processor.process_all_departments()
                    
                    print(f"\n📤 Uploading categorizing results...")
                    from post_processors.upload_categorizing_sheets import CategorizingUploader
                    uploader = CategorizingUploader()
                    uploader.process_all_files()
                except Exception as e:
                    print(f"❌ Error during categorizing post-processing/upload: {str(e)}")
        
        print("🎉 Categorizing Analysis pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Categorizing Pipeline failed: {str(e)}")
        return False

def run_policy_escalation_analysis(departments, model, format_type, with_upload=False, dry_run=False, target_date=None):
    """Run complete Policy Escalation analysis pipeline"""
    print(f"⚖️ Running Policy Escalation Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full Policy Escalation pipeline")
        return True
    
    try:
        # Get prompt
        prompt_registry = PromptRegistry()
        policy_escalation_prompt = prompt_registry.get_prompt("policy_escalation")
        prompt_text = policy_escalation_prompt.get_prompt_text()
        
        # Determine departments to process
        if departments == "all":
            dept_list = list(DEPARTMENTS.keys())
        else:
            dept_list = [d.strip() for d in departments.split(',')]
        
        print(f"🎯 Processing departments: {dept_list}")
        
        for department in dept_list:
            print(f"\n🏢 Processing {department}...")
            
            try:
                # Check if LLM outputs already exist (caching)
                if check_llm_output_exists(department, "policy_escalation", target_date):
                    print(f"⚡ Skipping LLM processing for {department} - using cached results")
                    continue
                
                # Step 1: Download from Tableau
                raw_file = download_tableau_data(department, target_date=target_date)
                
                # Step 2: Preprocess data
                processed_file = preprocess_data(raw_file, department, format_type, target_date=target_date)
                
                # Step 3: Load preprocessed data
                conversations = load_preprocessed_data(processed_file, format_type)
                
                if not conversations:
                    print(f"⚠️  No conversations found for {department}")
                    continue
                
                # Step 4: Process through LLM (system prompts will be fetched automatically)
                results, processor = asyncio.run(run_llm_processing(conversations, prompt_text, model))
                
                # Step 5: Save outputs
                save_llm_outputs(results, department, "policy_escalation", target_date)
                
                # Display token usage
                print(processor.get_token_summary(department))
                print(f"✅ Completed {department}")
                
            except Exception as e:
                print(f"❌ Failed processing {department}: {str(e)}")
                continue
        
        # Post-processing step
        if with_upload:
            print(f"\n📊 Starting Policy Escalation post-processing...")
            try:
                from post_processors.policy_escalation_postprocessing import PolicyEscalationProcessor
                processor = PolicyEscalationProcessor()
                processor.process_all_files()
                
                # Upload to Google Sheets
                print(f"\n📤 Uploading Policy Escalation results to Google Sheets...")
                try:
                    from post_processors.upload_policy_escalation_sheets import PolicyEscalationUploader
                    uploader = PolicyEscalationUploader()
                    uploader.process_all_files()
                except Exception as e:
                    print(f"❌ Error during Google Sheets upload: {str(e)}")
                
                # Run policy frequency analysis
                print(f"\n📊 Running Policy Frequency Analysis...")
                try:
                    from scripts.analyze_policy_frequency import find_policy_escalation_files, analyze_policy_frequency, save_analysis_results
                    
                    # Find and analyze policy files
                    policy_files = find_policy_escalation_files()
                    
                    for filepath, filename, date_folder in policy_files:
                        result = analyze_policy_frequency(filepath)
                        if result:
                            frequency_df, stats = result
                            
                            # Extract department name
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
                            
                            # Save analysis
                            output_dir = f"outputs/policy_escalation/{date_folder}"
                            os.makedirs(output_dir, exist_ok=True)
                            output_filename = f"{output_dir}/{dept_name}_Policy_Frequency_Analysis.csv"
                            save_analysis_results(frequency_df, stats, output_filename)
                    
                    # The frequency analysis will be uploaded automatically by the PolicyEscalationUploader
                    print(f"✅ Policy frequency analysis files generated")
                        
                except Exception as e:
                    print(f"❌ Policy frequency analysis failed: {str(e)}")
                    
            except Exception as e:
                print(f"❌ Policy Escalation post-processing failed: {str(e)}")
        else:
            print(f"\n💾 Raw results are available in LLM_outputs directory")
        
        print("🎉 Policy Escalation Analysis pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Policy Escalation Pipeline failed: {str(e)}")
        return False

def run_client_suspecting_ai_analysis(departments, model, format_type, with_upload=False, dry_run=False):
    """Run complete Client Suspecting AI analysis pipeline"""
    print(f"🤖 Running Client Suspecting AI Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full Client Suspecting AI pipeline")
        return True
    
    try:
        # Get prompt
        prompt_registry = PromptRegistry()
        client_suspecting_ai_prompt = prompt_registry.get_prompt("client_suspecting_ai")
        prompt_text = client_suspecting_ai_prompt.get_prompt_text()
        
        # Determine departments to process
        if departments == "all":
            dept_list = list(DEPARTMENTS.keys())
        else:
            dept_list = [d.strip() for d in departments.split(',')]
        
        print(f"🎯 Processing departments: {dept_list}")
        
        for department in dept_list:
            print(f"\n🏢 Processing {department}...")
            
            try:
                # Check if LLM outputs already exist (caching)
                if check_llm_output_exists(department, "client_suspecting_ai"):
                    print(f"⚡ Skipping LLM processing for {department} - using cached results")
                    continue
                
                # Step 1: Download from Tableau
                raw_file = download_tableau_data(department)
                
                # Step 2: Preprocess data
                processed_file = preprocess_data(raw_file, department, format_type)
                
                # Step 3: Load preprocessed data
                conversations = load_preprocessed_data(processed_file, format_type)
                
                if not conversations:
                    print(f"⚠️  No conversations found for {department}")
                    continue
                
                # Step 4: Process through LLM
                results, processor = asyncio.run(run_llm_processing(conversations, prompt_text, model))
                
                # Step 5: Save outputs
                save_llm_outputs(results, department, "client_suspecting_ai")
                
                # Display token usage
                print(processor.get_token_summary(department))
                print(f"✅ Completed {department}")
                
            except Exception as e:
                print(f"❌ Failed processing {department}: {str(e)}")
                continue
        
        # Post-processing and upload
        if with_upload:
            print(f"\n📊 Starting Client Suspecting AI post-processing...")
            try:
                from post_processors.client_suspecting_ai_postprocessing import ClientSuspectingAiProcessor
                processor = ClientSuspectingAiProcessor()
                processor.process_all_files()
                
                print(f"\n📤 Uploading client suspecting AI results to Google Sheets...")
                from post_processors.upload_client_suspecting_ai_sheets import ClientSuspectingAiUploader
                uploader = ClientSuspectingAiUploader()
                uploader.process_all_files()
                
            except Exception as e:
                print(f"❌ Error during post-processing/upload: {str(e)}")
        
        print("🎉 Client Suspecting AI Analysis pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Client Suspecting AI Pipeline failed: {str(e)}")
        return False

def run_clarity_score_analysis(departments, model, format_type, with_upload=False, dry_run=False):
    """Run complete Clarity Score analysis pipeline"""
    print(f"🔍 Running Clarity Score Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full Clarity Score pipeline")
        return True
    
    try:
        # Get prompt
        prompt_registry = PromptRegistry()
        clarity_score_prompt = prompt_registry.get_prompt("clarity_score")
        prompt_text = clarity_score_prompt.get_prompt_text()
        
        # Determine departments to process
        if departments == "all":
            dept_list = list(DEPARTMENTS.keys())
        else:
            dept_list = [d.strip() for d in departments.split(',')]
        
        print(f"🎯 Processing departments: {dept_list}")
        
        for department in dept_list:
            print(f"\n🏢 Processing {department}...")
            
            try:
                # Check if LLM outputs already exist (caching)
                if check_llm_output_exists(department, "clarity_score"):
                    print(f"⚡ Skipping LLM processing for {department} - using cached results")
                    continue
                
                # Step 1: Download from Tableau
                raw_file = download_tableau_data(department)
                
                # Step 2: Preprocess data
                processed_file = preprocess_data(raw_file, department, format_type)
                
                # Step 3: Load preprocessed data
                conversations = load_preprocessed_data(processed_file, format_type)
                
                if not conversations:
                    print(f"⚠️  No conversations found for {department}")
                    continue
                
                # Step 4: Process through LLM
                results, processor = asyncio.run(run_llm_processing(conversations, prompt_text, model))
                
                # Step 5: Save outputs
                save_llm_outputs(results, department, "clarity_score")
                
                # Display token usage
                print(processor.get_token_summary(department))
                print(f"✅ Completed {department}")
                
            except Exception as e:
                print(f"❌ Failed processing {department}: {str(e)}")
                continue
        
        # Post-processing and upload
        if with_upload:
            print(f"\n📊 Starting Clarity Score post-processing...")
            try:
                from post_processors.clarity_score_postprocessing import ClarityScoreProcessor
                processor = ClarityScoreProcessor()
                processor.process_all_files()
                
                print(f"\n📤 Uploading clarity score results to Google Sheets...")
                from post_processors.upload_clarity_score_sheets import ClarityScoreUploader
                uploader = ClarityScoreUploader()
                uploader.process_all_files()
                
            except Exception as e:
                print(f"❌ Error during post-processing/upload: {str(e)}")
        
        print("🎉 Clarity Score Analysis pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Clarity Score Pipeline failed: {str(e)}")
        return False

def run_legal_alignment_analysis(departments, model, format_type, with_upload=False, dry_run=False):
    """Run complete Legal Alignment analysis pipeline"""
    print(f"⚖️ Running Legal Alignment Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full Legal Alignment pipeline")
        return True
    
    try:
        # Get prompt
        prompt_registry = PromptRegistry()
        legal_alignment_prompt = prompt_registry.get_prompt("legal_alignment")
        prompt_text = legal_alignment_prompt.get_prompt_text()
        
        # Determine departments to process
        if departments == "all":
            dept_list = list(DEPARTMENTS.keys())
        else:
            dept_list = [d.strip() for d in departments.split(',')]
        
        print(f"🎯 Processing departments: {dept_list}")
        
        for department in dept_list:
            print(f"\n🏢 Processing {department}...")
            
            try:
                # Check if LLM outputs already exist (caching)
                if check_llm_output_exists(department, "legal_alignment"):
                    print(f"⚡ Skipping LLM processing for {department} - using cached results")
                    continue
                
                # Step 1: Download from Tableau
                raw_file = download_tableau_data(department)
                
                # Step 2: Preprocess data
                processed_file = preprocess_data(raw_file, department, format_type)
                
                # Step 3: Load preprocessed data
                conversations = load_preprocessed_data(processed_file, format_type)
                
                if not conversations:
                    print(f"⚠️  No conversations found for {department}")
                    continue
                
                # Step 4: Process through LLM
                results, processor = asyncio.run(run_llm_processing(conversations, prompt_text, model))
                
                # Step 5: Save outputs
                save_llm_outputs(results, department, "legal_alignment")
                
                # Display token usage
                print(processor.get_token_summary(department))
                print(f"✅ Completed {department}")
                
            except Exception as e:
                print(f"❌ Failed processing {department}: {str(e)}")
                continue
        
        # Post-processing and upload
        if with_upload:
            print(f"\n📊 Starting Legal Alignment post-processing...")
            try:
                from post_processors.legal_alignment_postprocessing import LegalAlignmentProcessor
                processor = LegalAlignmentProcessor()
                processor.process_all_files()
                
                print(f"\n📤 Uploading legal alignment results to Google Sheets...")
                from post_processors.upload_legal_alignment_sheets import LegalAlignmentUploader
                uploader = LegalAlignmentUploader()
                uploader.process_all_files()
                
            except Exception as e:
                print(f"❌ Error during post-processing/upload: {str(e)}")
        
        print("🎉 Legal Alignment Analysis pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Legal Alignment Pipeline failed: {str(e)}")
        return False

def run_call_request_analysis(departments, model, format_type, with_upload=False, dry_run=False):
    """Run complete Call Request analysis pipeline"""
    print(f"📞 Running Call Request Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full Call Request pipeline")
        return True
    
    try:
        # Get prompt
        prompt_registry = PromptRegistry()
        call_request_prompt = prompt_registry.get_prompt("call_request")
        prompt_text = call_request_prompt.get_prompt_text()
        
        # Determine departments to process
        if departments == "all":
            dept_list = list(DEPARTMENTS.keys())
        else:
            dept_list = [d.strip() for d in departments.split(',')]
        
        print(f"🎯 Processing departments: {dept_list}")
        
        for department in dept_list:
            print(f"\n🏢 Processing {department}...")
            
            try:
                # Check if LLM outputs already exist (caching)
                if check_llm_output_exists(department, "call_request"):
                    print(f"⚡ Skipping LLM processing for {department} - using cached results")
                    continue
                
                # Step 1: Download from Tableau
                raw_file = download_tableau_data(department)
                
                # Step 2: Preprocess data
                processed_file = preprocess_data(raw_file, department, format_type)
                
                # Step 3: Load preprocessed data
                conversations = load_preprocessed_data(processed_file, format_type)
                
                if not conversations:
                    print(f"⚠️  No conversations found for {department}")
                    continue
                
                # Step 4: Process through LLM
                results, processor = asyncio.run(run_llm_processing(conversations, prompt_text, model))
                
                # Step 5: Save outputs
                save_llm_outputs(results, department, "call_request")
                
                # Display token usage
                print(processor.get_token_summary(department))
                print(f"✅ Completed {department}")
                
            except Exception as e:
                print(f"❌ Failed processing {department}: {str(e)}")
                continue
        
        # Post-processing and upload
        if with_upload:
            print(f"\n📊 Starting Call Request post-processing...")
            try:
                from post_processors.call_request_postprocessing import CallRequestProcessor
                processor = CallRequestProcessor()
                processor.process_all_files()
                
                print(f"\n📤 Uploading call request results to Google Sheets...")
                from post_processors.upload_call_request_sheets import CallRequestUploader
                uploader = CallRequestUploader()
                uploader.process_all_files()
                
            except Exception as e:
                print(f"❌ Error during post-processing/upload: {str(e)}")
        
        print("🎉 Call Request Analysis pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Call Request Pipeline failed: {str(e)}")
        return False

def run_misprescription_analysis(departments, model, format_type, with_upload=False, dry_run=False):
    """
    Run misprescription analysis pipeline with dependency on category_docs
    
    This analysis only runs on conversations where category_docs identified 
    "OTC Medication Advice" = "Yes"
    
    Args:
        departments: Comma-separated list of departments or 'all'
        model: LLM model to use 
        format_type: Data format ('xml', 'json', 'segmented', 'transparent')
        with_upload: Whether to upload results to Google Sheets
        dry_run: Whether to run in dry-run mode
    """
    from prompts.base import PromptRegistry
    import json
    import ast
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full Misprescription pipeline")
        return

    print(f"\n📂 Running Misprescription Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")

    # Get yesterday's date
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    
    # Parse departments
    if departments == "all":
        dept_list = list(DEPARTMENTS.keys())
    else:
        dept_list = [d.strip() for d in departments.split(',')]
    
    # Get the prompt
    prompt_registry = PromptRegistry()
    misprescription_prompt = prompt_registry.get_prompt("misprescription")
    if not misprescription_prompt:
        print("❌ Misprescription prompt not found in registry")
        return
    
    prompt_text = misprescription_prompt.get_prompt_text()
    
    total_conversations_analyzed = 0
    
    for department in dept_list:
        print(f"\n🏢 Processing {department}...")
        
        # Step 1: Check if category_docs output exists for this department
        category_docs_file = f"outputs/LLM_outputs/{yesterday_str}/category_docs_{department.lower().replace(' ', '_')}_{yesterday.strftime('%m_%d')}.csv"
        
        if not os.path.exists(category_docs_file):
            print(f"⚠️ Category docs file not found: {category_docs_file}")
            print(f"   Please run categorizing analysis first for {department}")
            continue
            
        print(f"📋 Found category docs file: {category_docs_file}")
        
        # Step 2: Read category_docs output and filter for OTC Medication Advice = Yes
        try:
            category_df = pd.read_csv(category_docs_file)
            print(f"📊 Read {len(category_df)} rows from category docs")
            
            # Filter for conversations with OTC Medication Advice
            otc_conversations = []
            
            for _, row in category_df.iterrows():
                try:
                    # Parse the llm_output JSON
                    llm_output = row['llm_output']
                    
                    # Handle different JSON formats
                    if isinstance(llm_output, str):
                        # Strip markdown code blocks if present
                        if llm_output.strip().startswith('```json'):
                            # Extract JSON from markdown code block
                            lines = llm_output.strip().split('\n')
                            json_lines = []
                            in_json = False
                            for line in lines:
                                if line.strip() == '```json':
                                    in_json = True
                                    continue
                                elif line.strip() == '```':
                                    in_json = False
                                    break
                                elif in_json:
                                    json_lines.append(line)
                            llm_output = '\n'.join(json_lines)
                        
                        # Try to parse as JSON
                        try:
                            output_data = json.loads(llm_output)
                        except json.JSONDecodeError:
                            # Try to evaluate as Python literal
                            try:
                                output_data = ast.literal_eval(llm_output)
                            except:
                                print(f"⚠️ Could not parse llm_output: {llm_output}")
                                continue
                    else:
                        output_data = llm_output
                    
                    # Check if OTC Medication Advice is Yes
                    if output_data.get("OTC Medication Advice") == "Yes":
                        # Filter agent messages from the conversation
                        filtered_conversation = filter_agent_messages_from_conversation(row['conversation'])
                        otc_conversations.append({
                            'conversation_id': row['conversation_id'],
                            'conversation': filtered_conversation,
                            'chat_id': row['conversation_id']  # Add chat_id for proper token tracking
                        })
                        
                except Exception as e:
                    print(f"⚠️ Error processing row: {e}")
                    continue
            
            print(f"🔍 Found {len(otc_conversations)} conversations with OTC Medication Advice")
            
            if len(otc_conversations) == 0:
                print(f"   No conversations to analyze for {department}")
                continue
                
        except Exception as e:
            print(f"❌ Error reading category docs file: {e}")
            continue
        
        # Step 3: Check if misprescription output already exists
        if check_llm_output_exists(department, "misprescription"):
            print(f"   ✅ Misprescription output already exists for {department}")
            continue
        
        # Step 4: Process through LLM
        print(f"   🤖 Processing {len(otc_conversations)} conversations through {model}...")
        results, processor = asyncio.run(run_llm_processing(otc_conversations, prompt_text, model))
        
        total_conversations_analyzed += len(results)
        
        # Step 5: Save results
        output_file = save_llm_outputs(results, department, "misprescription")
        print(f"   💾 Saved results to: {output_file}")
        
        # Display token usage
        token_summary = processor.get_token_summary(department)
        print(f"   🎯 Token Usage: {token_summary}")

    # Step 6: Post-processing and upload to Google Sheets
    if with_upload:
        print(f"\n📊 Starting Misprescription post-processing...")
        try:
            from post_processors.misprescription_postprocessing import MisprescriptionProcessor
            processor = MisprescriptionProcessor()
            processor.process_all_files()
        except Exception as e:
            print(f"❌ Error during post-processing: {str(e)}")
        
        print(f"\n📤 Uploading misprescription results to Google Sheets...")
        try:
            from post_processors.upload_misprescription_sheets import MisprescriptionUploader
            uploader = MisprescriptionUploader()
            uploader.process_all_files()
        except Exception as e:
            print(f"❌ Error during upload: {str(e)}")

    print(f"\n✅ Misprescription Analysis Complete!")
    print(f"📊 Total conversations analyzed: {total_conversations_analyzed}")

def run_unnecessary_clinic_rec_analysis(departments, model, format_type, with_upload=False, dry_run=False):
    """
    Run unnecessary clinic rec analysis pipeline with dependency on category_docs
    
    This analysis only runs on conversations where category_docs identified 
    "Clinic Recommendation" = "Yes"
    
    Args:
        departments: Comma-separated list of departments or 'all'
        model: LLM model to use 
        format_type: Data format ('xml', 'json', 'segmented', 'transparent')
        with_upload: Whether to upload results to Google Sheets
        dry_run: Whether to run in dry-run mode
    """
    from prompts.base import PromptRegistry
    import json
    import ast
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full Unnecessary Clinic Rec pipeline")
        return

    print(f"\n📂 Running Unnecessary Clinic Rec Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")

    # Get yesterday's date
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    
    # Parse departments
    if departments == "all":
        dept_list = list(DEPARTMENTS.keys())
    else:
        dept_list = [d.strip() for d in departments.split(',')]
    
    # Get the prompt
    prompt_registry = PromptRegistry()
    unnecessary_clinic_rec_prompt = prompt_registry.get_prompt("unnecessary_clinic_rec")
    if not unnecessary_clinic_rec_prompt:
        print("❌ Unnecessary clinic rec prompt not found in registry")
        return
    
    prompt_text = unnecessary_clinic_rec_prompt.get_prompt_text()
    
    total_conversations_analyzed = 0
    
    for department in dept_list:
        print(f"\n🏢 Processing {department}...")
        
        # Step 1: Check if category_docs output exists for this department
        category_docs_file = f"outputs/LLM_outputs/{yesterday_str}/category_docs_{department.lower().replace(' ', '_')}_{yesterday.strftime('%m_%d')}.csv"
        
        if not os.path.exists(category_docs_file):
            print(f"⚠️ Category docs file not found: {category_docs_file}")
            print(f"   Please run categorizing analysis first for {department}")
            continue
            
        print(f"📋 Found category docs file: {category_docs_file}")
        
        # Step 2: Read category_docs output and filter for Clinic Recommendation = Yes
        try:
            category_df = pd.read_csv(category_docs_file)
            print(f"📊 Read {len(category_df)} rows from category docs")
            
            # Filter for conversations with Clinic Recommendation
            clinic_conversations = []
            
            for _, row in category_df.iterrows():
                try:
                    # Parse the llm_output JSON
                    llm_output = row['llm_output']
                    
                    # Handle different JSON formats
                    if isinstance(llm_output, str):
                        # Strip markdown code blocks if present
                        if llm_output.strip().startswith('```json'):
                            # Extract JSON from markdown code block
                            lines = llm_output.strip().split('\n')
                            json_lines = []
                            in_json = False
                            for line in lines:
                                if line.strip() == '```json':
                                    in_json = True
                                    continue
                                elif line.strip() == '```':
                                    in_json = False
                                    break
                                elif in_json:
                                    json_lines.append(line)
                            llm_output = '\n'.join(json_lines)
                        
                        # Try to parse as JSON
                        try:
                            output_data = json.loads(llm_output)
                        except json.JSONDecodeError:
                            # Try to evaluate as Python literal
                            try:
                                output_data = ast.literal_eval(llm_output)
                            except:
                                print(f"⚠️ Could not parse llm_output: {llm_output}")
                                continue
                    else:
                        output_data = llm_output
                    
                    # Check if Clinic Recommendation is Yes
                    if output_data.get("Clinic Recommendation") == "Yes":
                        # Filter agent messages from the conversation
                        filtered_conversation = filter_agent_messages_from_conversation(row['conversation'])
                        clinic_conversations.append({
                            'conversation_id': row['conversation_id'],
                            'conversation': filtered_conversation,
                            'chat_id': row['conversation_id']  # Add chat_id for proper token tracking
                        })
                        
                except Exception as e:
                    print(f"⚠️ Error processing row: {e}")
                    continue
            
            print(f"🔍 Found {len(clinic_conversations)} conversations with Clinic Recommendation")
            
            if len(clinic_conversations) == 0:
                print(f"   No conversations to analyze for {department}")
                continue
                
        except Exception as e:
            print(f"❌ Error reading category docs file: {e}")
            continue
        
        # Step 3: Check if unnecessary_clinic_rec output already exists
        if check_llm_output_exists(department, "unnecessary_clinic_rec"):
            print(f"   ✅ Unnecessary clinic rec output already exists for {department}")
            continue
        
        # Step 4: Process through LLM
        print(f"   🤖 Processing {len(clinic_conversations)} conversations through {model}...")
        results, processor = asyncio.run(run_llm_processing(clinic_conversations, prompt_text, model))
        
        total_conversations_analyzed += len(results)
        
        # Step 5: Save results
        output_file = save_llm_outputs(results, department, "unnecessary_clinic_rec")
        print(f"   💾 Saved results to: {output_file}")
        
        # Display token usage
        token_summary = processor.get_token_summary(department)
        print(f"   🎯 Token Usage: {token_summary}")

    # Step 6: Post-processing and upload to Google Sheets
    if with_upload:
        print(f"\n📊 Starting Unnecessary Clinic Rec post-processing...")
        try:
            from post_processors.unnecessary_clinic_rec_postprocessing import UnnecessaryClinicRecProcessor
            processor = UnnecessaryClinicRecProcessor()
            processor.process_all_files()
        except Exception as e:
            print(f"❌ Error during post-processing: {str(e)}")
        
        print(f"\n📤 Uploading unnecessary clinic rec results to Google Sheets...")
        try:
            from post_processors.upload_unnecessary_clinic_rec_sheets import UnnecessaryClinicRecUploader
            uploader = UnnecessaryClinicRecUploader()
            uploader.process_all_files()
        except Exception as e:
            print(f"❌ Error during upload: {str(e)}")

    print(f"\n✅ Unnecessary Clinic Rec Analysis Complete!")
    print(f"📊 Total conversations analyzed: {total_conversations_analyzed}")

def run_threatening_analysis(departments, model, format_type, with_upload=False, dry_run=False):
    """Run complete Threatening analysis pipeline"""
    print(f"⚠️ Running Threatening Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full Threatening pipeline")
        return True
    
    try:
        # Get prompt
        prompt_registry = PromptRegistry()
        threatening_prompt = prompt_registry.get_prompt("threatening")
        prompt_text = threatening_prompt.get_prompt_text()
        
        # Determine departments to process
        if departments == "all":
            dept_list = list(DEPARTMENTS.keys())
        else:
            dept_list = [d.strip() for d in departments.split(',')]
        
        print(f"🎯 Processing departments: {dept_list}")
        
        for department in dept_list:
            print(f"\n🏢 Processing {department}...")
            
            try:
                # Check if LLM outputs already exist (caching)
                if check_llm_output_exists(department, "threatening"):
                    print(f"⚡ Skipping LLM processing for {department} - using cached results")
                    continue
                
                # Step 1: Download from Tableau
                raw_file = download_tableau_data(department)
                
                # Step 2: Preprocess data
                processed_file = preprocess_data(raw_file, department, format_type)
                
                # Step 3: Load preprocessed data
                conversations = load_preprocessed_data(processed_file, format_type)
                
                if not conversations:
                    print(f"⚠️  No conversations found for {department}")
                    continue
                
                # Step 4: Process through LLM
                results, processor = asyncio.run(run_llm_processing(conversations, prompt_text, model))
                
                # Step 5: Save outputs
                save_llm_outputs(results, department, "threatening")
                
                # Display token usage
                print(processor.get_token_summary(department))
                print(f"✅ Completed {department}")
                
            except Exception as e:
                print(f"❌ Failed processing {department}: {str(e)}")
                continue
        
        # Post-processing and upload
        if with_upload:
            print(f"\n📊 Starting Threatening post-processing...")
            try:
                from post_processors.threatening_postprocessing import ThreateningProcessor
                processor = ThreateningProcessor()
                processor.process_all_files()
                
                print(f"\n📤 Uploading threatening results to Google Sheets...")
                from post_processors.upload_threatening_sheets import ThreateningUploader
                uploader = ThreateningUploader()
                uploader.process_all_files()
                
            except Exception as e:
                print(f"❌ Error during post-processing/upload: {str(e)}")
        
        print("🎉 Threatening Analysis pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Threatening Pipeline failed: {str(e)}")
        return False

def run_loss_of_interest(departments, model, format_type, with_upload=False, dry_run=False, target_date=None):
    """
    Run Loss of Interest analysis pipeline
    
    This analysis uses dynamic prompts based on the department and unique skills in the conversation.
    Only processes conversations that contain skills for which we have specific prompts.
    Different prompts are applied based on the department and application stage where the applicant dropped off.
    
    Args:
        departments: Comma-separated list of departments or 'all'
        model: LLM model to use
        format_type: Must be 'xml' to access unique_skills field
        with_upload: Whether to upload results to Google Sheets
        dry_run: Whether to run in dry-run mode
        target_date: Target date for analysis (defaults to yesterday)
    """
    print(f"📊 Running Loss of Interest Analysis Pipeline")
    print(f"   Departments: {departments}")
    print(f"   Model: {model}")
    print(f"   Format: {format_type}")
    
    if dry_run:
        print("🔍 DRY RUN - Would execute full Loss of Interest pipeline")
        return True
    
    # Force XML format for this analysis
    if format_type != "xml":
        print("⚠️  Switching to XML format (required for skill-based analysis)")
        format_type = "xml"
    
    try:
        # Get prompt
        prompt_registry = PromptRegistry()
        loss_of_interest_prompt = prompt_registry.get_prompt("loss_of_interest")
        if not loss_of_interest_prompt:
            print("❌ Loss of Interest prompt not found in registry")
            return False
        
        # Determine departments to process
        if departments == "all":
            # For now, only Filipina is configured
            dept_list = ["Filipina"]
            print("ℹ️  Loss of Interest analysis currently configured for: Filipina")
        else:
            dept_list = [d.strip() for d in departments.split(',')]
        
        print(f"🎯 Processing departments: {dept_list}")
        
        for department in dept_list:
            print(f"\n🏢 Processing {department}...")
            
            try:
                # Check cache
                if check_llm_output_exists(department, "loss_of_interest", target_date):
                    print(f"⚡ Skipping LLM processing for {department} - using cached results")
                    continue
                
                # Download and preprocess (include all skills for loss_of_interest)
                raw_file = download_tableau_data(department, days_lookback=1, target_date=target_date)
                processed_file = preprocess_data(raw_file, department, format_type, target_date=target_date, include_all_skills=True)
                
                # Load preprocessed data
                conversations = load_preprocessed_data(processed_file, format_type)
                
                if not conversations:
                    print(f"⚠️  No conversations found for {department}")
                    continue
                
                # Process through LLM with skill-aware logic
                processor = LLMProcessor(model)
                results = []
                tasks = []
                
                # Create semaphore for concurrency control
                semaphore = asyncio.Semaphore(30)
                
                # Filter and prepare tasks only for conversations with matching prompts
                skipped_count = 0
                filtered_conversations = []
                for conv in conversations:
                    # Add department to conversation data for prompt selection
                    conv_with_dept = dict(conv)
                    conv_with_dept['department'] = department
                    
                    # Check if conversation has any matching prompts
                    if not loss_of_interest_prompt.has_matching_prompt(conv_with_dept):
                        skipped_count += 1
                        continue
                    
                    # Get conversation-specific prompt based on department and unique_skills
                    prompt_text = loss_of_interest_prompt.get_prompt_text(conv_with_dept)
                    
                    if prompt_text is None:
                        skipped_count += 1
                        continue
                    
                    # Create task with conversation-specific prompt
                    task = processor.analyze_conversation(
                        conv.get('content_xml_view', ''), 
                        prompt_text, 
                        semaphore,
                        conv.get('conversation_id', 'unknown')
                    )
                    tasks.append(task)
                    filtered_conversations.append(conv)
                
                if skipped_count > 0:
                    print(f"ℹ️  Skipped {skipped_count} conversations without matching skill prompts")
                
                print(f"🤖 Processing {len(tasks)} conversations through {model}...")
                print(f"🔧 Using dynamic prompts based on unique skills in conversations")
                
                # Process conversations asynchronously
                async def process_all():
                    return await asyncio.gather(*tasks, return_exceptions=True)
                
                # Wait for all conversations to be processed
                task_results = asyncio.run(process_all())
                
                # Process results
                for i, (result, conv) in enumerate(zip(task_results, filtered_conversations)):
                    if isinstance(result, Exception):
                        results.append({
                            'conversation_id': conv.get('conversation_id', ''),
                            'conversation': conv.get('content_xml_view', ''),
                            'unique_skills': conv.get('unique_skills', ''),
                            'llm_output': f'Error: {str(result)}'
                        })
                    elif isinstance(result, dict):
                        # Check if conversation should be skipped
                        if result.get('skip_conversation', False):
                            continue  # Skip adding to results
                        
                        results.append({
                            'conversation_id': conv.get('conversation_id', ''),
                            'conversation': conv.get('content_xml_view', ''),
                            'unique_skills': conv.get('unique_skills', ''),
                            'llm_output': result.get('llm_output', '')
                        })
                    else:
                        results.append({
                            'conversation_id': conv.get('conversation_id', ''),
                            'conversation': conv.get('content_xml_view', ''),
                            'unique_skills': conv.get('unique_skills', ''),
                            'llm_output': str(result)
                        })
                    
                    if (i + 1) % 100 == 0:
                        print(f"⚡ Processed {i + 1}/{len(task_results)} conversations...")
                
                # Save outputs
                output_file = save_llm_outputs(results, department, "loss_of_interest", target_date=target_date)
                
                # Display token usage
                print(processor.get_token_summary(department))
                print(f"✅ Completed {department}")
                
                # Print skill distribution summary
                print(f"\n📊 Skill Distribution Summary:")
                skill_counts = {}
                for result in results:
                    skill = result.get('unique_skills', 'Unknown')
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1
                
                for skill, count in sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"   {skill}: {count} conversations")
                
            except Exception as e:
                print(f"❌ Failed processing {department}: {str(e)}")
                continue
        
        # Post-processing and upload
        if with_upload:
            print(f"\n📤 Uploading Loss of Interest results to Google Sheets...")
            try:
                from post_processors.upload_loss_of_interest_sheets import LossOfInterestUploader
                uploader = LossOfInterestUploader(target_date=target_date)
                uploader.process_all_files()
            except Exception as e:
                print(f"⚠️  Upload failed: {str(e)}")
        
        print("🎉 Loss of Interest Analysis pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Loss of Interest Pipeline failed: {str(e)}")
        return False

def parse_date(date_str: str) -> datetime:
    """Parse a date string in YYYY-MM-DD format"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Please use YYYY-MM-DD format.")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='LLM-as-a-Judge Pipeline')
    parser.add_argument('--prompt', required=True, 
                       choices=['sentiment_analysis', 'rule_breaking', 'ftr', 'false_promises', 'categorizing', 'policy_escalation', 'client_suspecting_ai', 'clarity_score', 'legal_alignment', 'call_request', 'threatening', 'misprescription', 'unnecessary_clinic_rec', 'loss_of_interest'],
                       help='Type of analysis to run')
    parser.add_argument('--departments', default='all', 
                       help='Departments to process (comma-separated or "all")')
    parser.add_argument('--format', default='segmented',
                       help='Data format to use')
    parser.add_argument('--model', default='gpt-4o',
                       help='Model to use for analysis')
    parser.add_argument('--with-upload', action='store_true',
                       help='Include post-processing and upload')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would run without executing')
    parser.add_argument('--date', default=None,
                       help='Target date for analysis in YYYY-MM-DD format (defaults to yesterday)')
    
    args = parser.parse_args()
    
    # Parse target date if provided
    target_date = None
    if args.date:
        try:
            target_date = parse_date(args.date)
            print(f"🗓️  Using target date: {target_date.strftime('%Y-%m-%d')}")
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)
    
    # Set default format for specific prompts if not explicitly specified
    if args.prompt in ['categorizing', 'false_promises', 'policy_escalation', 'clarity_score', 'legal_alignment', 'call_request', 'misprescription', 'unnecessary_clinic_rec'] and args.format == 'segmented':
        # Check if format was explicitly set by user
        import sys
        if '--format' not in sys.argv:
            args.format = 'xml'
            print(f"🔧 Auto-setting format to XML for {args.prompt} analysis")
    elif args.prompt == 'client_suspecting_ai' and args.format == 'segmented':
        # Check if format was explicitly set by user
        import sys
        if '--format' not in sys.argv:
            args.format = 'json'
            print(f"🔧 Auto-setting format to JSON for {args.prompt} analysis")
    # Note: threatening uses default segmented format
    
    # Set default model to gemini-2.5-pro for specific prompts if not explicitly specified
    if args.prompt in ['false_promises', 'policy_escalation', 'client_suspecting_ai', 'clarity_score', 'legal_alignment', 'call_request', 'threatening'] and args.model == 'gpt-4o':
        # Check if model was explicitly set by user
        import sys
        if '--model' not in sys.argv:
            args.model = 'gemini-2.5-pro'
            print(f"🔧 Auto-setting model to gemini-2.5-pro for {args.prompt} analysis")
    # Set default model to gemini-2.5-flash for misprescription and unnecessary_clinic_rec
    elif args.prompt in ['misprescription', 'unnecessary_clinic_rec'] and args.model == 'gpt-4o':
        # Check if model was explicitly set by user
        import sys
        if '--model' not in sys.argv:
            args.model = 'gemini-2.5-flash'
            print(f"🔧 Auto-setting model to gemini-2.5-flash for {args.prompt} analysis")
    # Note: categorizing now uses gpt-4o as default
    
    print(f"🚀 Starting {args.prompt} pipeline...")
    print(f"📋 Arguments: {vars(args)}")
    print()
    
    # Route to appropriate handler
    if args.prompt == 'sentiment_analysis':
        success = run_sentiment_analysis(
            args.departments, args.model, args.format, 
            args.with_upload, args.dry_run, target_date
        )
    elif args.prompt == 'rule_breaking':
        success = run_rule_breaking(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run, target_date
        )
    elif args.prompt == 'ftr':
        success = run_ftr_analysis(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run
        )
    elif args.prompt == 'false_promises':
        success = run_false_promises_analysis(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run
        )
    elif args.prompt == 'categorizing':
        success = run_categorizing_analysis(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run
        )
    elif args.prompt == 'policy_escalation':
        success = run_policy_escalation_analysis(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run, target_date
        )
    elif args.prompt == 'client_suspecting_ai':
        success = run_client_suspecting_ai_analysis(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run
        )
    elif args.prompt == 'clarity_score':
        success = run_clarity_score_analysis(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run
        )
    elif args.prompt == 'legal_alignment':
        success = run_legal_alignment_analysis(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run
        )
    elif args.prompt == 'call_request':
        success = run_call_request_analysis(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run
        )
    elif args.prompt == 'threatening':
        success = run_threatening_analysis(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run
        )
    elif args.prompt == 'misprescription':
        success = run_misprescription_analysis(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run
        )
    elif args.prompt == 'unnecessary_clinic_rec':
        success = run_unnecessary_clinic_rec_analysis(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run
        )
    elif args.prompt == 'loss_of_interest':
        success = run_loss_of_interest(
            args.departments, args.model, args.format,
            args.with_upload, args.dry_run, target_date
        )
    else:
        print(f"❌ Unknown prompt type: {args.prompt}")
        success = False
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 