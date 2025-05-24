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
    console.print("[bold cyan]║  ██╗  ██╗ █████╗ ███████╗██╗   ██╗██╗  ██╗ █████╗  ║[/bold cyan]")
    console.print("[bold cyan]║  ██║ ██╔╝██╔══██╗╚══███╔╝██║   ██║██║  ██║██╔══██╗ ║[/bold cyan]")
    console.print("[bold cyan]║  █████╔╝ ███████║  ███╔╝ ██║   ██║███████║███████║ ║[/bold cyan]")
    console.print("[bold cyan]║  ██╔═██╗ ██╔══██║ ███╔╝  ██║   ██║██╔══██║██╔══██║ ║[/bold cyan]")
    console.print("[bold cyan]║  ██║  ██╗██║  ██║███████╗╚██████╔╝██║  ██║██║  ██║ ║[/bold cyan]")
    console.print("[bold cyan]║  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ║[/bold cyan]")
    console.print("[bold cyan]║                                                    ║[/bold cyan]")
    console.print("[bold cyan]╚════════════════════════════════════════════════════╝[/bold cyan]")

discord_tokens_env = os.getenv('DISCORD_TOKENS', '')
if discord_tokens_env:
    discord_tokens = [token.strip() for token in discord_tokens_env.split(',') if token.strip()]
else:
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        raise ValueError("No Discord token found! Please set DISCORD_TOKENS or DISCORD_TOKEN in .env.")
    discord_tokens = [discord_token]

google_api_keys = os.getenv('GOOGLE_API_KEYS', '').split(',')
google_api_keys = [key.strip() for key in google_api_keys if key.strip()]
openai_api_keys = os.getenv('OPENAI_API_KEYS', '').split(',')
openai_api_keys = [key.strip() for key in openai_api_keys if key.strip()]
if not google_api_keys and not openai_api_keys:
    raise ValueError '

("No API keys found! Please set GOOGLE_API_KEYS or OPENAI_API_KEYS in .env.")

processed_message_ids = set()
used_google_api_keys = set()
used_openai_api_keys = set()
last_generated_text = None
cooldown_time = 86400
bot_question_counts = {}  # Track bot/AI question attempts per user

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

def generate_reply(prompt, prompt_language, ai_provider="google", author_id=None, is_quiz=False):
    global last_generated_text
    REFERENCED_MESSAGES_SYSTEM_PROMPT = """You are a casual Discord chat participant in your teens/early 20s. Your task is to continue the conversation naturally based on the previous messages.

Rules:
- Keep responses between 3-15 words
- Stay in context of the conversation
- Be super casual and informal, like a real Discord user
- Sometimes start sentences with lowercase
- Use minimal punctuation (occasional commas are ok)
- Use slang sparingly (only use "lol", "ngl", "fr", "tbh" in about 20% of messages)
- Don't overuse exclamation marks
- Never mention that you're an AI
- It's ok to make small typos sometimes
- Mix up your style - don't be repetitive with phrases"""
    
    bot_keywords = r'\b(bot|ai|artificial intelligence|gemini|robot)\b'
    is_bot_question = re.search(bot_keywords, prompt.lower())
    
    if is_bot_question and author_id:
        bot_question_counts[author_id] = bot_question_counts.get(author_id, 0) + 1
        if bot_question_counts[author_id] == 1:
            return "Haha, I'm just here chilling like anyone else! What's good? 😎"
        elif bot_question_counts[author_id] <= 3:
            return "Yo, I'm just a regular guy vibing, let's talk something fun! 😏"
        else:
            return "Bruh, stop it already! I'm no bot, just a human having a blast! 😤🙄 #Chill"

    if is_quiz:
        emoji = re.match(r'^\s*([🐷🐮🐶🐱🐭🐹🐰🐻🐼🐨🐯🦁🐸🐵🐔🐧🐦🐤🐣🐺🦊🦝🐗🐴🦄🐝🐛🦋🐞🐜🦗🕷️🦂🐍🐢🐙🦑🦐🦞🦀🐡🐠🐟🐬🐳🐋🦈🐊🐅🐆🦒🐘🦏🦛🐪🐫🦘🐃🐂🐄🐎🐖🐏🐑🦙🐐🐓🦃🦚🦜🦢🦩🐕‍🦺🦮🐈‍⬛])', prompt)
        if emoji:
            emoji_str = emoji.group(1)
            animal_map = {
                '🐷': 'pig', '🐮': 'cow', '🐶': 'dog', '🐱': 'cat', '🐭': 'mouse', '🐹': 'hamster', '🐰': 'rabbit',
                '🐻': 'bear', '🐼': 'panda', '🐨': 'koala', '🐯': 'tiger', '🦁': 'lion', '🐸': 'frog', '🐵': 'monkey',
                '🐔': 'chicken', '🐧': 'penguin', '🐦': 'bird', '🐤': 'chick', '🐣': 'hatching chick', '🐺': 'wolf',
                '🦊': 'fox', '🦝': 'raccoon', '🐗': 'boar', '🐴': 'horse', '🦄': 'unicorn', '🐝': 'bee', '🐛': 'bug',
                '🦋': 'butterfly', '🐞': 'ladybug', '🐜': 'ant', '🦗': 'cricket', '🕷️': 'spider', '🦂': 'scorpion',
                '🐍': 'snake', '🐢': 'turtle', '🐙': 'octopus', '🦑': 'squid', '🦐': 'shrimp', '🦞': 'lobster',
                '🦀': 'crab', '🐡': 'pufferfish', '🐠': 'tropical fish', '🐟': 'fish', '🐬': 'dolphin', '🐳': 'whale',
                '🐋': 'whale', '🦈': 'shark', '🐊': 'crocodile', '🐅': 'tiger', '🐆': 'leopard', '🦒': 'giraffe',
                '🐘': 'elephant', '🦏': 'rhino', '🦛': 'hippo', '🐪': 'camel', '🐫': 'bactrian camel', '🦘': 'kangaroo',
                '🐃': 'water buffalo', ' 02': 'ox', '🐄': 'cow', '🐎': 'horse', '🐖': 'pig', '🐏': 'ram', '🐑': 'sheep',
                '🦙': 'llama', '🐐': 'goat', '🐓': 'rooster', '🦃': 'turkey', '🦚': 'peacock', '🦜': 'parrot',
                '🦢': 'swan', '🦩': 'flamingo', '🐕‍🦺': 'service dog', '🦮': 'guide dog', '🐈‍⬛': 'black cat'
            }
            animal = animal_map.get(emoji_str, 'animal')
            return f"Yo, that's a {animal}! 🫶 Nailed it! What's the next one? 😄"

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
                    log_message(f"Google API key {google_api_key} hit rate limit (429). Trying another API key...", "WARNING")
                    used_google_api_keys.add(google_api_key)
                    return generate_reply(prompt, prompt_language, ai_provider, author_id, is_quiz)
                response.raise_for_status()
                result = response.json()
                generated_text = result['candidates'][0]['content']['parts'][0]['text']
                if generated_text == last_generated_text:
                    log_message("AI generated the same text, requesting new text...", "WAIT")
                    continue
                last_generated_text = generated_text
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
                return generate_reply(prompt, prompt_language, ai_provider, author_id, is_quiz)
            return None
        if response_text == last_generated_text:
            log_message("GPT generated the same text, requesting new text...", "WAIT")
            return generate_reply(prompt, prompt_language, ai_provider, author_id, is_quiz)
        last_generated_text = response_text
        return response_text
    else:
        return get_random_message_from_file()

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
    except requests.exceptions.RequestException as e:
        log_message(f"Failed to fetch bot account info: {e}", "ERROR")
        return "Unknown", "", "Unknown"

def get_channel_members(channel_id, token):
    headers = {'Authorization': token}
    guild_id = None
    try:
        channel_url = f"https://discord.com/api/v9/channels/{channel_id}"
        channel_response = requests.get(channel_url, headers=headers)
        channel_response.raise_for_status()
        guild_id = channel_response.json().get('guild_id')
    except requests.exceptions.RequestException as e:
        log_message(f"[Channel {channel_id}] Failed to fetch guild ID: {e}", "ERROR")
        return []

    if guild_id:
        try:
            members_url = f"https://discord.com/api/v9/guilds/{guild_id}/members?limit=100"
            members_response = requests.get(members_url, headers=headers)
            members_response.raise_for_status()
            members = members_response.json()
            return [member['user']['id'] for member in members if 'user' in member and not member['user'].get('bot')]
        except requests.exceptions.RequestException as e:
            log_message(f"[Channel {channel_id}] Failed to fetch members: {e}", "ERROR")
    return []

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
            author_id = None
            tagged_users = []
            log_message(f"[Channel {channel_id}] Waiting {settings['read_delay']} seconds before reading messages...", "WAIT")
            time.sleep(settings["read_delay"])
            try:
                response = requests.get(f'https://discord.com/api/v9/channels/{channel_id}/messages?limit=2', headers=headers)
                response.raise_for_status()
                messages = response.json()
                if messages:
                    most_recent_message = messages[0]
                    message_id = most_recent_message.get('id')
                    author_id = most_recent_message.get('author', {}).get('id')
                    message_type = most_recent_message.get('type', '')
                    user_message = most_recent_message.get('content', '').strip()
                    mentions = most_recent_message.get('mentions', [])
                    tagged_users = [mention['id'] for mention in mentions]
                    
                    is_bot_tagged = bot_user_id in tagged_users
                    quiz_pattern = r'^\s*[🐷🐮🐶🐱🐭🐹🐰🐻🐼🐨🐯🦁🐸🐵🐔🐧🐦🐤🐣🐺🦊🦝🐗🐴🦄🐝🐛🦋🐞🐜🦗🕷️🦂🐍🐢🐙🦑🦐🦞🦀🐡🐠🐟🐬🐳🐋🦈🐊🐅🐆🦒🐘🦏🦛🐪🐫🦘🐃 02🐄🐎🐖🐏🐑🦙🐐🐓🦃🦚🦜🦢🦩🐕‍🦺🦮🐈‍⬛]\s*-?\s*(which animal|what animal|guess the animal|what is this)\b'
                    is_quiz = bool(re.match(quiz_pattern, user_message.lower()))

                    if is_quiz:
                        if is_bot_tagged:
                            log_message(f"[Channel {channel_id}] Bot tagged in quiz: {user_message}", "INFO")
                            prompt = user_message
                            reply_to_id = message_id
                            processed_message_ids.add(message_id)
                        elif tagged_users:
                            log_message(f"[Channel {channel_id}] Quiz tags other users, ignoring: {user_message}", "INFO")
                            continue
                        else:
                            log_message(f"[Channel {channel_id}] Untagged quiz, processing: {user_message}", "INFO")
                            prompt = user_message
                            reply_to_id = message_id
                            processed_message_ids.add(message_id)
                    elif is_bot_tagged and author_id != bot_user_id and message_type != 8 and message_id not in processed_message_ids:
                        log_message(f"[Channel {channel_id}] Bot tagged in message: {user_message}", "INFO")
                        prompt = user_message
                        reply_to_id = message_id
                        processed_message_ids.add(message_id)
                    elif author_id != bot_user_id and message_type != 8 and message_id not in processed_message_ids:
                        attachments = most_recent_message.get('attachments', [])
                        if attachments or not re.search(r'\w', user_message):
                            log_message(f"[Channel {channel_id}] Message not processed (not plain text).", "WARNING")
                        else:
                            log_message(f"[Channel {channel_id}] Received: {user_message}", "INFO")
                            reply_choice = random.choice(['latest', 'previous', 'none'])
                            if reply_choice == 'latest':
                                prompt = user_message
                                reply_to_id = message_id
                            elif reply_choice == 'previous' and len(messages) > 1:
                                prev_message = messages[1]
                                prev_message_id = prev_message.get('id')
                                prev_author_id = prev_message.get('author', {}).get('id')
                                prev_content = prev_message.get('content', '').strip()
                                if prev_author_id != bot_user_id and prev_message_id not in processed_message_ids:
                                    prompt = prev_content
                                    reply_to_id = prev_message_id
                            else:
                                prompt = user_message
                                reply_to_id = None
                            processed_message_ids.add(message_id)
                else:
                    prompt = None
            except requests.exceptions.RequestException as e:
                log_message(f"[Channel {channel_id}] Request error: {e}", "ERROR")
                prompt = None

            if prompt:
                if settings["use_slow_mode"]:
                    slow_mode_delay = get_slow_mode_delay(channel_id, token)
                    log_message(f"[Channel {channel_id}] Slow mode active, waiting {slow_mode_delay} seconds...", "WAIT")
                    time.sleep(slow_mode_delay)
                
                result = generate_reply(prompt, settings["prompt_language"], settings["ai_provider"], author_id, is_quiz)
                if result is None:
                    log_message(f"[Channel {channel_id}] Invalid prompt language or API error. Message skipped.", "WARNING")
                else:
                    response_text = result if result else "Sorry, unable to reply to the message."
                    if response_text.strip().lower() == prompt.strip().lower():
                        log_message(f"[Channel {channel_id}] Reply matches received message. Not sending reply.", "WARNING")
                    else:
                        tag_user = random.choice([True, False])
                        tag_user_id = None
                        if tag_user:
                            members = get_channel_members(channel_id, token)
                            if members:
                                tag_user_id = random.choice(members)
                        
                        if settings["use_reply"] and reply_to_id:
                            send_message(channel_id, response_text, token, reply_to=reply_to_id, 
                                       tag_user_id=tag_user_id, delete_after=settings["delete_bot_reply"], 
                                       delete_immediately=settings["delete_immediately"])
                        else:
                            send_message(channel_id, response_text, token, reply_to=None, 
                                       tag_user_id=tag_user_id, delete_after=settings["delete_bot_reply"], 
                                       delete_immediately=settings["delete_immediately"])
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
            tag_user = random.choice([True, False])
            tag_user_id = None
            if tag_user:
                members = get_channel_members(channel_id, token)
                if members:
                    tag_user_id = random.choice(members)
            if settings["use_reply"]:
                send_message(channel_id, message_text, token, tag_user_id=tag_user_id, 
                           delete_after=settings["delete_bot_reply"], delete_immediately=settings["delete_immediately"])
            else:
                send_message(channel_id, message_text, token, tag_user_id=tag_user_id, 
                           delete_after=settings["delete_bot_reply"], delete_immediately=settings["delete_immediately"])

def send_message(channel_id, message_text, token, reply_to=None, tag_user_id=None, delete_after=None, delete_immediately=False):
    headers = {'Authorization': token, 'Content-Type': 'application/json'}
    if tag_user_id:
        message_text = f"<@{tag_user_id}> {message_text}"
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

    return {
        "prompt_language": prompt_language,
        "ai_provider": ai_provider,
        "enable_read_message": enable_read_message,
        "read_delay": read_delay,
        "delay_interval": delay_interval,
        "use_slow_mode": use_slow_mode,
        "use_reply": use_reply,
        "delete_bot_reply": delete_bot_reply,
        "delete_immediately": delete_immediately
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
        log_message(
            f"[Channel {cid} | Server: {info['server_name']} | Channel: {info['channel_name']}] "
            f"Settings: AI = {ai_str}, "
            f"Language = {settings['prompt_language'].upper()}, "
            f"Read Messages = {'Active' if settings['enable_read_message'] else 'Inactive'}, "
            f"Read Delay = {settings['read_delay']} seconds, "
            f"Interval = {settings['delay_interval']} seconds, "
            f"Slow Mode = {'Active' if settings['use_slow_mode'] else 'Inactive'}, "
            f"Reply = {'Yes' if settings['use_reply'] else 'No'}, "
            f"Delete Messages = {delete_str}",
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
    while True:
        time.sleep(10)