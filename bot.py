import json
import threading
import time
import os
import random
import re
import requests
from dotenv import load_dotenv
from datetime import datetime
from colorama import init, Fore, Style
from rich.console import Console
from openai import OpenAI
import httpx
from urllib.parse import quote

init(autoreset=True)
load_dotenv()

console = Console()

def print_banner():
    console.print("[bold cyan]╔════════════════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║          DISCORD AI AUTO REPLIER BOT 🤖            ║[/bold cyan]")
    console.print("[bold cyan]║     Automate replies using Google AI, GPT & Discord║[/bold cyan]")
    console.print("[bold cyan]║    Developed by: https://t.me/Offical_Im_kazuha    ║[/bold cyan]")
    console.print("[bold cyan]║    GitHub: https://github.com/Kazuha787            ║[/bold cyan]")
    console.print("[bold cyan]╠════════════════════════════════════════════════════╣[/bold cyan]")
    console.print("[bold cyan]║                                                    ║[/bold cyan]")
    console.print("[bold cyan]║  ██╗  ██╗ █████╗ ███████╗██╗   ██║██╗  ██╗ █████╗  ║[/bold cyan]")
    console.print("[bold cyan]║  ██║ ██╔╝██╔══██╗╚══███╔╝██║   ██║██║  ██║██╔══██╗ ║[/bold cyan]")
    console.print("[bold cyan]║  █████╔╝ ███████║  ███╔╝ ██║   ██║███████║███████║ ║[/bold cyan]")
    console.print("[bold cyan]║  ██╔═██╗ ██╔══██║ ███╔╝  ██║   ██║██╔══██║██╔══██║ ║[/bold cyan]")
    console.print("[bold cyan]║  ██║  ██╗██║  ██║███████╗╚██████╔╝██║  ██║██║  ██║ ║[/bold cyan]")
    console.print("[bold cyan]║  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ║[/bold cyan]")
    console.print("[bold cyan]║                                                    ║[/bold cyan]")
    console.print("[bold cyan]╚════════════════════════════════════════════════════╝[/bold cyan]")

# Load Discord tokens with debug logging
discord_tokens_env = os.getenv('DISCORD_TOKENS', '')
print(f"DEBUG: DISCORD_TOKENS from .env: {discord_tokens_env[:4] + '...' if discord_tokens_env else 'None'}")
if discord_tokens_env:
    discord_tokens = [token.strip() for token in discord_tokens_env.split(',') if token.strip()]
else:
    discord_token = os.getenv('DISCORD_TOKEN')
    print(f"DEBUG: DISCORD_TOKEN from .env: {discord_token[:4] + '...' if discord_token else 'None'}")
    if not discord_token:
        raise ValueError("No Discord token found! Please set DISCORD_TOKENS or DISCORD_TOKEN in .env with a valid token.")
    discord_tokens = [discord_token]
print(f"DEBUG: Loaded tokens: {[token[:4] + '...' for token in discord_tokens]}")

# Load API keys
google_api_keys = os.getenv('GOOGLE_API_KEYS', '').split(',')
google_api_keys = [key.strip() for key in google_api_keys if key.strip()]
openai_api_keys = os.getenv('OPENAI_API_KEYS', '').split(',')
openai_api_keys = [key.strip() for key in openai_api_keys if key.strip()]
if not google_api_keys and not openai_api_keys:
    raise ValueError("No API keys found! Please set GOOGLE_API_KEYS or OPENAI_API_KEYS in .env.")

processed_message_ids = set()
used_google_api_keys = set()
used_openai_api_keys = set()
last_generated_text = None
cooldown_time = 86400

def log_message(message, level="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if level.upper() == "SUCCESS":
        color, icon = Fore.GREEN, "✅"
    elif level.upper() == "ERROR":
        color, icon = Fore.RED, "🚨"
    elif level.upper() == "WARNING":
        color, icon = Fore.YELLOW, "⚠️"
    elif level.upper() == "WAIT":
        color, icon = Fore.CYAN, "⌛"
    else:
        color, icon = Fore.WHITE, "ℹ️"
    border = f"{Fore.MAGENTA}{'=' * 80}{Style.RESET_ALL}"
    formatted_message = f"{color}[{timestamp}] {icon} {message}{Style.RESET_ALL}"
    print(border)
    print(formatted_message)
    print(border)

def get_random_api_key(api_type):
    if api_type == "google":
        available_keys = [key for key in google_api_keys if key not in used_google_api_keys]
        used_set = used_google_api_keys
    else:  # openai
        available_keys = [key for key in openai_api_keys if key not in used_openai_api_keys]
        used_set = used_openai_api_keys
    if not available_keys:
        log_message(f"All {api_type} API keys hit 429 error. Waiting 24 hours before retrying...", "ERROR")
        time.sleep(cooldown_time)
        used_set.clear()
        return get_random_api_key(api_type)
    return random.choice(available_keys)

def get_random_message_from_file():
    try:
        with open("messages.txt", "r", encoding="utf-8") as file:
            messages = [line.strip() for line in file.readlines() if line.strip()]
            return random.choice(messages) if messages else "No messages available in file."
    except FileNotFoundError:
        return "File messages.txt not found!"

def ask_chatgpt(api_key, user_message, prompt, proxy=""):
    if proxy:
        log_message(f"Using proxy: {proxy} for ChatGPT", "INFO")
        if not proxy.startswith(("http://", "https://")):
            proxy = f"http://{proxy}"
        http_client = httpx.Client(proxy=proxy)
        client = OpenAI(api_key=api_key, http_client=http_client)
    else:
        client = OpenAI(api_key=api_key)
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": user_message}]
    try:
        response = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
        response_text = response.choices[0].message.content
        if "Rate limit reached" in response_text:
            raise Exception("GPT rate limit reached, please try again later.")
        if "You exceeded your current quota" in response_text:
            raise Exception("Your ChatGPT API key has no balance.")
        return True, response_text
    except Exception as e:
        if "Rate limit reached" in str(e):
            return False, "GPT rate limit reached, please try again later."
        if "You exceeded your current quota" in str(e):
            return False, "Your ChatGPT API key has no balance."
        return False, f"GPT Error occurred: {str(e)}"

def generate_language_specific_prompt(user_message, prompt_language):
    if prompt_language == 'in':
        return f"Reply to the following message in Indian English: {user_message}"
    elif prompt_language == 'en':
        return f"Reply to the following message in English: {user_message}"
    else:
        log_message(f"Prompt language '{prompt_language}' is invalid. Message skipped.", "WARNING")
        return None

def clean_response(text):
    """Ensure response is 3-15 words, casual, and human-like."""
    # Filter out formal or bot-like phrases
    bot_like_patterns = r'\b(here are|options for|depending on|following options|select one|multiple replies)\b'
    if re.search(bot_like_patterns, text.lower()):
        log_message("Detected bot-like phrase in response, using fallback.", "WARNING")
        return random.choice(["yo what's good", "haha what's up", "lol same"])

    # Split into lines and take the first non-empty line
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return random.choice(["yo what's good", "haha what's up", "lol same"])
    text = lines[0]

    # Split into words
    words = text.split()
    # Truncate to 15 words max
    if len(words) > 15:
        words = words[:15]
    # Ensure at least 3 words
    if len(words) < 3:
        words.extend(["lol", "what's", "up"])
    # Remove excessive punctuation
    text = ' '.join(words).rstrip('.,!?') + ('.' if random.random() < 0.3 else '')
    # Ensure lowercase start for casual tone (50% chance)
    if random.random() < 0.5:
        text = text[0].lower() + text[1:] if text else text
    return text

def generate_reply(prompt, prompt_language, ai_provider="google"):
    global last_generated_text
    REFERENCED_MESSAGES_SYSTEM_PROMPT = """

Rules:

- """ 

    if ai_provider == "google":
        google_api_key = get_random_api_key("google")
        lang_prompt = generate_language_specific_prompt(prompt, prompt_language)
        if lang_prompt is None:
            return None
        ai_prompt = f"{lang_prompt}\n\n{REFERENCED_MESSAGES_SYSTEM_PROMPT}"
        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={google_api_key}'
        headers = {'Content-Type': 'application/json'}
        data = {'contents': [{'parts': [{'text': ai_prompt}]}]}
        while True:
            try:
                response = requests.post(url, headers=headers, json=data)
                if response.status_code == 429:
                    log_message(f"Google API key {google_api_key[:4]}... hit rate limit (429). Trying another API key...", "WARNING")
                    used_google_api_keys.add(google_api_key)
                    return generate_reply(prompt, prompt_language, ai_provider)
                response.raise_for_status()
                result = response.json()
                generated_text = result['candidates'][0]['content']['parts'][0]['text']
                log_message(f"Raw AI output: {generated_text}", "INFO")
                return generated_text
            except requests.exceptions.RequestException as e:
                log_message(f"Request failed: {e}", "ERROR")
                time.sleep(2)
    elif ai_provider == "gpt":
        openai_api_key = get_random_api_key("openai")
        lang_prompt = generate_language_specific_prompt(prompt, prompt_language)
        if lang_prompt is None:
            return None
        ai_prompt = f"{lang_prompt}\n\n{REFERENCED_MESSAGES_SYSTEM_PROMPT}"
        success, response_text = ask_chatgpt(openai_api_key, prompt, ai_prompt)
        if not success:
            log_message(response_text, "ERROR")
            if "rate limit" in response_text.lower():
                used_openai_api_keys.add(openai_api_key)
                return generate_reply(prompt, prompt_language, ai_provider)
            return None
        log_message(f"Raw GPT output: {response_text}", "INFO")
        return response_text
    else:
        return get_random_message_from_file()

def press_reaction(channel_id, message_id, emoji, token, attempts=3, pause_between_attempts=(5, 10), reaction_delay=(1, 5)):
    headers = {
        'sec-ch-ua-platform': '"Windows"',
        'Authorization': token,
        'Referer': f'https://discord.com/channels/{channel_id}/{channel_id}',
        'X-Debug-Options': 'bugReporterEnabled',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'X-Discord-Timezone': 'Etc/GMT-2',
        'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6InJ1IiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEzMy4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTMzLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiJodHRwczovL2Rpc2NvcmQuY29tLyIsInJlZmVycmluZ19kb21haW4iOiJkaXNjb3JkLmNvbSIsInJlZmVycmVyX2N1cnJlbnQiOiIiLCJyZWZlcnJpbmdfZG9tYWluX2N1cnJlbnQiOiIiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJclient_build_number":374679,"client_event_source":null,"has_client_mods":false}',
        'X-Discord-Locale': 'en-US',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    }
    params = {
        'location': 'Message Context Menu',
        'type': '0',
    }
    for attempt in range(attempts):
        try:
            if emoji.get('id') is not None:
                emoji_name = emoji['name']
                url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}/reactions/{emoji_name}%3A{emoji['id']}/%40me"
            else:
                emoji_name = quote(emoji['name'])
                url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}/reactions/{emoji_name}/%40me"
            response = requests.put(url, headers=headers, params=params)
            if 'Unauthorized' in response.text:
                log_message(f"[Channel {channel_id}] Incorrect Discord token or account blocked.", "ERROR")
                return None
            if response.status_code == 204:
                log_message(f"[Channel {channel_id}] Successfully reacted with {emoji['name']} to message {message_id}", "SUCCESS")
                delay = random.randint(reaction_delay[0], reaction_delay[1])
                log_message(f"[Channel {channel_id}] Waiting {delay} seconds after reaction...", "WAIT")
                time.sleep(delay)
                return True
            else:
                log_message(f"[Channel {channel_id}] Failed to react: {response.status_code} {response.text}", "ERROR")
        except requests.exceptions.RequestException as e:
            log_message(f"[Channel {channel_id}] Error reacting: {e}", "ERROR")
        random_sleep = random.randint(pause_between_attempts[0], pause_between_attempts[1])
        log_message(f"[Channel {channel_id}] Retrying reaction in {random_sleep} seconds...", "WAIT")
        time.sleep(random_sleep)
    return False

def detect_emoji_usage(channel_id, token):
    """Check if recent messages contain emojis."""
    headers = {'Authorization': token}
    try:
        response = requests.get(f'https://discord.com/api/v9/channels/{channel_id}/messages?limit=10', headers=headers)
        response.raise_for_status()
        messages = response.json()
        emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF]')
        emoji_count = 0
        total_messages = len(messages)
        for message in messages:
            content = message.get('content', '')
            if emoji_pattern.search(content):
                emoji_count += 1
        emoji_usage = emoji_count / total_messages > 0.5 if total_messages > 0 else False
        log_message(f"[Channel {channel_id}] Emoji usage detected: {emoji_usage} ({emoji_count}/{total_messages} messages)", "INFO")
        return emoji_usage
    except requests.exceptions.RequestException as e:
        log_message(f"[Channel {channel_id}] Error checking emoji usage: {e}", "ERROR")
        return False

def get_channel_info(channel_id, token):
    headers = {'Authorization': token}
    channel_url = f"https://discord.com/api/v9/channels/{channel_id}"
    try:
        channel_response = requests.get(channel_url, headers=headers)
        channel_response.raise_for_status()
        channel_data = channel_response.json()
        channel_name = channel_data.get('name', 'Unknown Channel')
        guild_id = channel_data.get('guild_id')
        server_name = "Direct Message"
        if guild_id:
            guild_url = f"https://discord.com/api/v9/guilds/{guild_id}"
            guild_response = requests.get(guild_url, headers=headers)
            guild_response.raise_for_status()
            guild_data = guild_response.json()
            server_name = guild_data.get('name', 'Unknown Server')
        return server_name, channel_name
    except requests.exceptions.RequestException as e:
        log_message(f"Error fetching channel info: {e}", "ERROR")
        return "Unknown Server", "Unknown Channel"

def get_bot_info(token):
    headers = {'Authorization': token}
    try:
        response = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
        response.raise_for_status()
        data = response.json()
        username = data.get("username", "Unknown")
        discriminator = data.get("discriminator", "")
        bot_id = data.get("id", "Unknown")
        return username, discriminator, bot_id
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            log_message(f"Invalid Discord token: {token[:4]}... Please update DISCORD_TOKEN or DISCORD_TOKENS in .env.", "ERROR")
            exit(1)  # Stop the script
        log_message(f"Failed to fetch bot account info: {e}", "ERROR")
        return "Unknown", "", "Unknown"
    except requests.exceptions.RequestException as e:
        log_message(f"Network error fetching bot account info: {e}", "ERROR")
        return "Unknown", "", "Unknown"

def auto_reply(channel_id, settings, token):
    headers = {'Authorization': token}
    if settings["ai_provider"] in ["google", "gpt"]:
        try:
            bot_info_response = requests.get('https://discord.com/api/v9/users/@me', headers=headers)
            bot_info_response.raise_for_status()
            bot_user_id = bot_info_response.json().get('id')
        except requests.exceptions.RequestException as e:
            log_message(f"[Channel {channel_id}] Failed to fetch bot info: {e}", "ERROR")
            return

        while True:
            prompt = None
            reply_to_id = None
            log_message(f"[Channel {channel_id}] Waiting {settings['read_delay']} seconds before reading messages...", "WAIT")
            time.sleep(settings["read_delay"])
            try:
                response = requests.get(f'https://discord.com/api/v9/channels/{channel_id}/messages', headers=headers)
                response.raise_for_status()
                messages = response.json()
                if messages:
                    most_recent_message = messages[0]
                    message_id = most_recent_message.get('id')
                    author_id = most_recent_message.get('author', {}).get('id')
                    message_type = most_recent_message.get('type', '')
                    if author_id != bot_user_id and message_type != 8 and message_id not in processed_message_ids:
                        user_message = most_recent_message.get('content', '').strip()
                        attachments = most_recent_message.get('attachments', [])
                        if attachments or not re.search(r'\w', user_message):
                            log_message(f"[Channel {channel_id}] Message not processed (not plain text).", "WARNING")
                        else:
                            log_message(f"[Channel {channel_id}] Received: {user_message}", "INFO")
                            if settings["use_slow_mode"]:
                                slow_mode_delay = get_slow_mode_delay(channel_id, token)
                                log_message(f"[Channel {channel_id}] Slow mode active, waiting {slow_mode_delay} seconds...", "WAIT")
                                time.sleep(slow_mode_delay)
                            prompt = user_message
                            reply_to_id = message_id
                            processed_message_ids.add(message_id)
                            # Press reaction if enabled
                            if settings["use_reactions"]:
                                emoji = random.choice(settings["emojis"])
                                press_reaction(channel_id, message_id, emoji, token, 
                                              reaction_delay=(settings["reaction_delay_min"], settings["reaction_delay_max"]))
                else:
                    prompt = None
            except requests.exceptions.RequestException as e:
                log_message(f"[Channel {channel_id}] Request error: {e}", "ERROR")
                prompt = None

            if prompt:
                result = generate_reply(prompt, settings["prompt_language"], settings["ai_provider"])
                if result is None:
                    log_message(f"[Channel {channel_id}] Invalid prompt language or API error. Message skipped.", "WARNING")
                else:
                    response_text = clean_response(result) if settings["use_clean_response"] else result
                    log_message(f"{'Cleaned' if settings['use_clean_response'] else 'Raw'} response: {response_text}", "INFO")
                    if response_text.strip().lower() == prompt.strip().lower():
                        log_message(f"[Channel {channel_id}] Reply matches received message. Not sending reply.", "WARNING")
                    else:
                        # Append emoji to reply if emoji usage is common in channel
                        if settings["use_reactions"] and detect_emoji_usage(channel_id, token):
                            emoji = random.choice(settings["emojis"])["name"]
                            response_text = f"{response_text} {emoji}"
                        if settings["use_reply"]:
                            send_message(channel_id, response_text, token, reply_to=reply_to_id, 
                                         delete_after=settings["delete_bot_reply"], delete_immediately=settings["delete_immediately"])
                        else:
                            send_message(channel_id, response_text, token, 
                                         delete_after=settings["delete_bot_reply"], delete_immediately=settings["delete_immediately"])
            else:
                log_message(f"[Channel {channel_id}] No new messages or invalid message.", "INFO")

            log_message(f"[Channel {channel_id}] Waiting {settings['delay_interval']} seconds before next iteration...", "WAIT")
            time.sleep(settings["delay_interval"])
    else:
        while True:
            delay = settings["delay_interval"]
            log_message(f"[Channel {channel_id}] Waiting {delay} seconds before sending message from file...", "WAIT")
            time.sleep(delay)
            message_text = generate_reply("", settings["prompt_language"], ai_provider="file")
            if settings["use_clean_response"]:
                message_text = clean_response(message_text)
                log_message(f"Cleaned response: {message_text}", "INFO")
            if settings["use_reactions"] and detect_emoji_usage(channel_id, token):
                emoji = random.choice(settings["emojis"])["name"]
                message_text = f"{message_text} {emoji}"
            if settings["use_reply"]:
                send_message(channel_id, message_text, token, delete_after=settings["delete_bot_reply"], delete_immediately=settings["delete_immediately"])
            else:
                send_message(channel_id, message_text, token, delete_after=settings["delete_bot_reply"], delete_immediately=settings["delete_immediately"])

def send_message(channel_id, message_text, token, reply_to=None, delete_after=None, delete_immediately=False):
    headers = {'Authorization': token, 'Content-Type': 'application/json'}
    payload = {'content': message_text}
    if reply_to:
        payload["message_reference"] = {"message_id": reply_to}
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        if response.status_code in [200, 201]:
            data = response.json()
            message_id = data.get("id")
            log_message(f"[Channel {channel_id}] Message sent: \"{message_text}\" (ID: {message_id})", "SUCCESS")
            if delete_after is not None:
                if delete_immediately:
                    log_message(f"[Channel {channel_id}] Deleting message immediately without delay...", "WAIT")
                    threading.Thread(target=delete_message, args=(channel_id, message_id, token), daemon=True).start()
                elif delete_after > 0:
                    log_message(f"[Channel {channel_id}] Message will be deleted in {delete_after} seconds...", "WAIT")
                    threading.Thread(target=delayed_delete, args=(channel_id, message_id, delete_after, token), daemon=True).start()
        else:
            log_message(f"[Channel {channel_id}] Failed to send message. Status: {response.status_code}", "ERROR")
            log_message(f"[Channel {channel_id}] API response: {response.text}", "ERROR")
    except requests.exceptions.RequestException as e:
        log_message(f"[Channel {channel_id}] Error sending message: {e}", "ERROR")

def delayed_delete(channel_id, message_id, delay, token):
    time.sleep(delay)
    delete_message(channel_id, message_id, token)

def delete_message(channel_id, message_id, token):
    headers = {'Authorization': token, 'Content-Type': 'application/json'}
    url = f'https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}'
    try:
        response = requests.delete(url, headers=headers)
        if response.status_code == 204:
            log_message(f"[Channel {channel_id}] Message with ID {message_id} successfully deleted.", "SUCCESS")
        else:
            log_message(f"[Channel {channel_id}] Failed to delete message. Status: {response.status_code}", "ERROR")
            log_message(f"[Channel {channel_id}] API response: {response.text}", "ERROR")
    except requests.exceptions.RequestException as e:
        log_message(f"[Channel {channel_id}] Error deleting message: {e}", "ERROR")

def get_slow_mode_delay(channel_id, token):
    headers = {'Authorization': token, 'Accept': 'application/json'}
    url = f"https://discord.com/api/v9/channels/{channel_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        slow_mode_delay = data.get("rate_limit_per_user", 0)
        log_message(f"[Channel {channel_id}] Slow mode delay: {slow_mode_delay} seconds", "INFO")
        return slow_mode_delay
    except requests.exceptions.RequestException as e:
        log_message(f"[Channel {channel_id}] Failed to fetch slow mode info: {e}", "ERROR")
        return 5

def get_server_settings(channel_id, channel_name):
    print(f"\nEnter settings for channel {channel_id} (Channel Name: {channel_name}):")
    print("  Choose AI provider:")
    print("    1. Google Gemini AI")
    print("    2. OpenAI GPT")
    print("    3. Messages from file")
    ai_choice = input("  Enter choice (1/2/3): ").strip()
    if ai_choice == "1":
        if not google_api_keys:
            print("  No Google API keys found. Defaulting to file-based messages.")
            ai_provider = "file"
        else:
            ai_provider = "google"
    elif ai_choice == "2":
        if not openai_api_keys:
            print("  No OpenAI API keys found. Defaulting to file-based messages.")
            ai_provider = "file"
        else:
            ai_provider = "gpt"
    else:
        ai_provider = "file"

    if ai_provider in ["google", "gpt"]:
        prompt_language = input("  Choose prompt language (en/in): ").strip().lower()
        if prompt_language not in ["en", "in"]:
            print("  Invalid input. Defaulting to 'in'.")
            prompt_language = "in"
        enable_read_message = True
        read_delay = int(input("  Enter message read delay (seconds): "))
        delay_interval = int(input("  Enter interval (seconds) for each auto reply iteration: "))
        use_slow_mode = input("  Use slow mode? (y/n): ").strip().lower() == 'y'
    else:
        prompt_language = input("  Choose message language from file (en/in): ").strip().lower()
        if prompt_language not in ["en", "in"]:
            print("  Invalid input. Defaulting to 'in'.")
            prompt_language = "in"
        enable_read_message = False
        read_delay = 0
        delay_interval = int(input("  Enter delay (seconds) for sending messages from file: "))
        use_slow_mode = False

    use_reply = input("  Send messages as replies? (y/n): ").strip().lower() == 'y'
    delete_reply = input("  Delete bot replies after some seconds? (y/n): ").strip().lower() == 'y'
    if delete_reply:
        delete_bot_reply = int(input("  After how many seconds should replies be deleted? (0 for no deletion, or enter delay): "))
        delete_immediately = input("  Delete messages immediately without delay? (y/n): ").strip().lower() == 'y'
    else:
        delete_bot_reply = None
        delete_immediately = False

    use_reactions = input("  Add reactions to messages? (y/n): ").strip().lower() == 'y'
    emojis = [{"name": "😎", "id": None}, {"name": "👍", "id": None}, {"name": "🔥", "id": None}]
    reaction_delay_min = 1
    reaction_delay_max = 5
    if use_reactions:
        custom_emojis = input("  Enter emojis (e.g., 😎,👍,🔥 or leave blank for default): ").strip()
        if custom_emojis:
            emojis = [{"name": emoji.strip(), "id": None} for emoji in custom_emojis.split(",")]
        reaction_delay_min = int(input("  Enter minimum reaction delay (seconds): "))
        reaction_delay_max = int(input("  Enter maximum reaction delay (seconds): "))
        if reaction_delay_max < reaction_delay_min:
            print("  Max delay must be >= min delay. Defaulting to 1-5 seconds.")
            reaction_delay_min, reaction_delay_max = 1, 5

    use_clean_response = input("  Clean AI responses to be 3-15 words and casual? (y/n): ").strip().lower() == 'y'

    return {
        "prompt_language": prompt_language,
        "ai_provider": ai_provider,
        "enable_read_message": enable_read_message,
        "read_delay": read_delay,
        "delay_interval": delay_interval,
        "use_slow_mode": use_slow_mode,
        "use_reply": use_reply,
        "delete_bot_reply": delete_bot_reply,
        "delete_immediately": delete_immediately,
        "use_reactions": use_reactions,
        "emojis": emojis,
        "reaction_delay_min": reaction_delay_min,
        "reaction_delay_max": reaction_delay_max,
        "use_clean_response": use_clean_response
    }

if __name__ == "__main__":
    print_banner()

    bot_accounts = {}
    for token in discord_tokens:
        username, discriminator, bot_id = get_bot_info(token)
        bot_accounts[token] = {"username": username, "discriminator": discriminator, "bot_id": bot_id}
        log_message(f"Bot Account: {username}#{discriminator} (ID: {bot_id})", "SUCCESS")

    channel_ids = [cid.strip() for cid in input("Enter channel IDs (separate with commas if multiple): ").split(",") if cid.strip()]

    token = discord_tokens[0]
    channel_infos = {}
    for channel_id in channel_ids:
        server_name, channel_name = get_channel_info(channel_id, token)
        channel_infos[channel_id] = {"server_name": server_name, "channel_name": channel_name}
        log_message(f"[Channel {channel_id}] Connected to server: {server_name} | Channel Name: {channel_name}", "SUCCESS")

    server_settings = {}
    for channel_id in channel_ids:
        channel_name = channel_infos.get(channel_id, {}).get("channel_name", "Unknown Channel")
        server_settings[channel_id] = get_server_settings(channel_id, channel_name)

    for cid, settings in server_settings.items():
        info = channel_infos.get(cid, {"server_name": "Unknown Server", "channel_name": "Unknown Channel"})
        delete_str = ("Immediately" if settings['delete_immediately'] else 
                      (f"In {settings['delete_bot_reply']} seconds" if settings['delete_bot_reply'] and settings['delete_bot_reply'] > 0 else "No"))
        ai_str = {"google": "Google Gemini AI", "gpt": "OpenAI GPT", "file": "File-based"}.get(settings['ai_provider'], "Unknown")
        emojis_str = ", ".join([emoji['name'] for emoji in settings['emojis']]) if settings['use_reactions'] else "No"
        reaction_delay_str = f"{settings['reaction_delay_min']}-{settings['reaction_delay_max']} seconds" if settings['use_reactions'] else "N/A"
        log_message(
            f"[Channel {cid} | Server: {info['server_name']} | Channel: {info['channel_name']}] "
            f"Settings: AI = {ai_str}, "
            f"Language = {settings['prompt_language'].upper()}, "
            f"Read Messages = {'Active' if settings['enable_read_message'] else 'Inactive'}, "
            f"Read Delay = {settings['read_delay']} seconds, "
            f"Interval = {settings['delay_interval']} seconds, "
            f"Slow Mode = {'Active' if settings['use_slow_mode'] else 'Inactive'}, "
            f"Reply = {'Yes' if settings['use_reply'] else 'No'}, "
            f"Delete Messages = {delete_str}, "
            f"Reactions = {'Yes' if settings['use_reactions'] else 'No'} ({emojis_str}), "
            f"Reaction Delay = {reaction_delay_str}, "
            f"Clean Response = {'Yes' if settings['use_clean_response'] else 'No'}",
            "INFO"
        )

    token_index = 0
    for channel_id in channel_ids:
        token = discord_tokens[token_index % len(discord_tokens)]
        token_index += 1
        bot_info = bot_accounts.get(token, {"username": "Unknown", "discriminator": "", "bot_id": "Unknown"})
        thread = threading.Thread(
            target=auto_reply,
            args=(channel_id, server_settings[channel_id], token)
        )
        thread.daemon = True
        thread.start()
        log_message(f"[Channel {channel_id}] Bot active: {bot_info['username']}#{bot_info['discriminator']} (Token: {token[:4]}{'...' if len(token) > 4 else token})", "SUCCESS")

    log_message("Bot is running on multiple servers... Press CTRL+C to stop.", "INFO")
    log_message("SECURITY REMINDER: Never share Discord tokens or API keys publicly!", "WARNING")
    while True:
        time.sleep(10)