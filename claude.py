import asyncio
import time
import os
import random
import subprocess
import requests
from bs4 import BeautifulSoup
from anthropic import AsyncAnthropic
from typing import List, Dict, Any, Optional
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='claude_console.log'
)

# ANSI color codes
ORANGE = '\033[38;2;255;165;0m'
BLUE = '\033[38;2;0;165;255m'
RED = '\033[38;2;255;0;0m'
GREEN = '\033[38;2;0;255;0m'
RESET = '\033[0m'

# Create an async Anthropic client
client = AsyncAnthropic()

# Message memory to store conversation history
msgMemory = []

# Models available
models = [
    "claude-3-7-sonnet-20250219",
    "claude-3-5-haiku-latest"
]

# Model to use
model = 0

# System prompt to guide Claude's responses
prompt = "You are the best artificial Intelligence Model. You are to provide short concise responses to users questions in the best way possible to the following user request: "

# Response speed
speed = 0.05

# Retry configuration
MAX_RETRIES = 5
BASE_DELAY = 1  # seconds

# Config file path
CONFIG_FILE = "claude_config.json"

def save_config() -> None:
    """Save current configuration to a file"""
    config_data = {
        "model_index": model,
        "prompt": prompt,
        "speed": speed
    }

    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f)
        print(f"{BLUE}System>> {RESET}Configuration saved.")
    except Exception as e:
        print(f"{RED}System>> Error saving configuration: {str(e)}{RESET}")
        logging.error(f"Error saving configuration: {str(e)}")

def load_config() -> None:
    """Load configuration from file if it exists"""
    global model, prompt, speed

    if not os.path.exists(CONFIG_FILE):
        return

    try:
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)

        model = config_data.get("model_index", 0)
        prompt = config_data.get("prompt", prompt)
        speed = config_data.get("speed", 0.05)
        print(f"{BLUE}System>> {RESET}Configuration loaded.")
    except Exception as e:
        print(f"{RED}System>> Error loading configuration: {str(e)}{RESET}")
        logging.error(f"Error loading configuration: {str(e)}")

async def stream_with_retry(messages: List[Dict[str, str]], model: str) -> str:
    """Stream responses from Claude with retry logic"""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            async with client.messages.stream(
                max_tokens=4096,
                messages=messages,
                model=model,
                system=prompt
            ) as stream:
                print(f"{ORANGE}Claude>> {RESET}", end="", flush=True)
                message_text = ""
                async for event in stream:
                    if event.type == "text":
                        time.sleep(speed)  # Reduced a bit for better responsiveness
                        print(event.text, end="", flush=True)
                        message_text += event.text
                    elif event.type == "content_block_stop":
                        print()
                        return message_text
        except Exception as e:
            if "overloaded_error" in str(e) and retries < MAX_RETRIES - 1:
                # Calculate backoff time with jitter
                delay = (BASE_DELAY * (2 ** retries)) + (random.random() * 0.5)
                retries += 1
                print(f"\n{RED}API overloaded. Retrying in {delay:.2f} seconds... (Attempt {retries}/{MAX_RETRIES}){RESET}")
                logging.warning(f"API overloaded. Retrying (Attempt {retries}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
            else:
                print(f"\n{RED}Error: {e}{RESET}")
                logging.error(f"Stream error: {str(e)}")
                return f"Sorry, I encountered an error: {e}"

    logging.error("Failed to get a response after multiple retries")
    return "Failed to get a response after multiple retries. Please try again later."

def normalize_url(url: str) -> str:
    """Normalize URL by adding https:// if not present"""
    if not url.startswith("https://") and not url.startswith("http://"):
        return "https://" + url
    return url

def scrape_website(url: str) -> str:
    """Scrapes content from a website URL"""
    url = normalize_url(url)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "header", "footer", "nav"]):
            script.extract()

        # Extract text content
        text = soup.get_text(separator='\n')

        # Clean up the text (remove extra whitespace)
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        # Truncate if too long
        if len(text) > 18000:
            text = text[:8000] + "... [content truncated]"

        return text
    except Exception as e:
        logging.error(f"Error scraping website: {str(e)}")
        return f"Error scraping website: {str(e)}"

def extract_code_from_response(response_text: str) -> Optional[list]:
    """Extract code from a response containing markdown code blocks"""
    if "```" not in response_text:
        return None

    # Extract code between first pair of ``` markers
    parts = response_text.split("```", 2)
    if len(parts) < 3:
        return None

    code_block = parts[1]

    # Handle language identifier if present (e.g., ```python)
    if "\n" in code_block:
        lines = code_block.split("\n", 1)
        if len(lines) > 1 and lines[0].strip():
            language = lines[0].strip()  # Check if first line has content (language identifier)
            return [lines[1], language]
        return [code_block, ""]

    return [code_block, ""]

def determine_file_extension(language: str) -> str:
    """Determine file extension based on language identifier"""
    language = language.lower().strip()

    extensions = {
        "python": ".py",
        "py": ".py",
        "javascript": ".js",
        "js": ".js",
        "typescript": ".ts",
        "ts": ".ts",
        "html": ".html",
        "css": ".css",
        "java": ".java",
        "c": ".c",
        "cpp": ".cpp",
        "c++": ".cpp",
        "csharp": ".cs",
        "cs": ".cs",
        "php": ".php",
        "ruby": ".rb",
        "rb": ".rb",
        "go": ".go",
        "rust": ".rs",
        "swift": ".swift",
        "kotlin": ".kt",
        "sql": ".sql",
        "sh": ".sh",
        "bash": ".sh",
        "shell": ".sh",
        "json": ".json",
        "xml": ".xml",
        "yaml": ".yml",
        "yml": ".yml",
        "markdown": ".md",
        "md": ".md",
    }

    return extensions.get(language, ".txt")

def save_conversation(filename: str = None) -> None:
    """Save the current conversation to a file"""
    if not msgMemory:
        print(f"{BLUE}System>> {RESET}No conversation to save.")
        return

    if not filename:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"conversation_{timestamp}.json"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(msgMemory, f, indent=2)
        print(f"{GREEN}System>> {RESET}Conversation saved to {filename}")
    except Exception as e:
        print(f"{RED}System>> Error saving conversation: {str(e)}{RESET}")
        logging.error(f"Error saving conversation: {str(e)}")

def load_conversation(filename: str) -> None:
    """Load a conversation from a file"""
    global msgMemory

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            loaded_memory = json.load(f)

        msgMemory = loaded_memory
        print(f"{GREEN}System>> {RESET}Loaded conversation with {len(msgMemory)} messages from {filename}")
    except Exception as e:
        print(f"{RED}System>> Error loading conversation: {str(e)}{RESET}")
        logging.error(f"Error loading conversation: {str(e)}")

def runPyFile(filename: str) -> str:
    """Run a Python file and return its output"""
    try:
        result = subprocess.run(['python', filename], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Python execution error: {e.stderr}")
        return f"{RED}Error: {e.stderr}{RESET}"
    except Exception as e:
        logging.error(f"Execution error: {str(e)}")
        return f"{RED}Execution error: {str(e)}{RESET}"

def config(type: str) -> None:
    """Handle configuration changes"""
    global model, models, prompt, speed

    if type.lower() == "m":
        print(f"{BLUE}System>> {RESET}Current models:")
        for i, m in enumerate(models):
            print(f"{BLUE}System>> {RESET}\t{i}: {m}")
        print(f"{BLUE}System>> {RESET}Current model in use: {models[model]}")

        try:
            new_model = int(input("Config>> Enter the model number to use: "))
            if 0 <= new_model < len(models):
                model = new_model
                print(f"{BLUE}System>> {RESET}Model changed to: {models[model]}")
                save_config()
            else:
                print(f"{RED}Invalid model number. Please choose between 0 and {len(models)-1}{RESET}")
        except ValueError:
            print(f"{RED}Please enter a valid number{RESET}")

    elif type.lower() == "p":
        print(f"{BLUE}System>> {RESET}Current prompt: {prompt}")
        prompt = input("Config>> Enter a new prompt: ")
        print(f"{BLUE}System>> {RESET}Prompt changed to: {prompt}")
        save_config()

    elif type.lower() == "s":
        print(f"{BLUE}System>> {RESET}Current speed: {speed}")
        try:
            speed = float(input("Config>> Enter a new speed (in seconds): "))
            print(f"{BLUE}System>> {RESET}Speed changed to: {speed}")
            save_config()
        except ValueError:
            print(f"{RED}Please enter a valid number{RESET}")

    elif type.lower() == "e":
        print(f"{BLUE}System>> {RESET}Exiting configuration...")
    else:
        print(f"{RED}Unknown configuration option. Choose (m)odel, (p)rompt, (s)peed, or (e)xit{RESET}")

def clear_screen() -> None:
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def menu() -> None:
    """Display the main menu"""
    clear_screen()

    # Get terminal width (fallback to 80 if can't determine)
    try:
        terminal_width = os.get_terminal_size().columns
    except:
        terminal_width = 80

    print(f"{ORANGE}" + "=" * terminal_width)
    print("Claude In The Console".center(terminal_width))
    print("=" * terminal_width + RESET)

    # Center "Commands:"
    print("Commands:".center(terminal_width))

    commands = [
        "- 'scrape [url]' to retrieve information from a website",
        "- 'read [filename] [question]' to read a file and ask about it",
        "- 'save [filename]' to save the conversation",
        "- 'load [filename]' to load a saved conversation",
        "- 'settings' or 'config' to change model, prompt or speed",
        "- 'memory' or 'mem' to view message memory size",
        "- 'reset' to clear message memory",
        "- 'test' or 'testfile' to create and analyze a file",
        "- 'clear' or 'cls' to clear the screen",
        "- 'cd' to view the current directory",
        "- 'menu', 'help', or 'cmd' to show this menu",
        "- 'exit', 'quit', or 'bye' to exit"
    ]

    # Calculate left padding to center the commands
    max_command_length = max(len(cmd) for cmd in commands)
    left_padding = (terminal_width - max_command_length) // 2

    for cmd in commands:
        print(" " * left_padding + cmd)

    print(f"{ORANGE}" + "=" * terminal_width + RESET)

async def handle_read_file(filename=None, question=None) -> None:
    """Handle the read file command with optional parameters"""
    if not filename:
        filename = input(f"{BLUE}System>> {RESET}Enter the filename: ")

    if not os.path.exists(filename):
        print(f"{RED}System>> File not found: {filename}{RESET}")
        return

    try:
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()
        print(f"{BLUE}System>> {RESET}File read successfully.")

        if not question:
            question = input("User>> ")

        # Add the user message to memory
        msgMemory.append({
            "role": "user",
            "content": question + "\nUSER PROVIDED FILE '" + filename + "' CONTENTS:\n" + text
        })

        # Stream the response with retry logic
        response_text = await stream_with_retry(
            messages=msgMemory,
            model=models[model]
        )

        # Add Claude's response to memory
        if response_text:
            msgMemory.append({
                "role": "assistant",
                "content": response_text
            })

            # Check for code blocks in response
            if "```" in response_text:
                write_choice = input(f"{BLUE}System>> {RESET}Detected code block in response. Do you want to write it to a file? (y/n): ")

                if write_choice.lower() == "y":
                    new_filename = input(f"{BLUE}System>> {RESET}What would you like to name the file? (default is a py file if no extension): ")

                    if os.path.splitext(new_filename)[1] == "":
                        new_filename += ".py"  # Add .py extension only if no extension exists

                    code = extract_code_from_response(response_text)
                    if code:
                        with open(new_filename, "w", encoding="utf-8") as f:
                            f.write(code)
                        print(f"{BLUE}System>> {RESET}{new_filename} created.")

                        # Ask about running the file
                        if new_filename.endswith(".py"):
                            run_choice = input(f"{BLUE}System>> {RESET}Would you like to run {new_filename}? (y/n): ")
                            if run_choice.lower() == "y":
                                print(f"{BLUE}System>> {RESET}Running {new_filename}...")
                                output = runPyFile(new_filename)
                                print(output)
                                print(f"{BLUE}System>> {RESET}{new_filename} execution completed.")
                    else:
                        print(f"{RED}System>> Could not extract code properly from the response.{RESET}")
    except Exception as e:
        print(f"{RED}System>> Error reading file: {str(e)}{RESET}")
        logging.error(f"Error reading file: {str(e)}")

async def main() -> None:
    """Main application function"""
    menu()
    load_config()
    done = False

    while not done:
        question = input("User>> ")

        # Split command and arguments
        parts = question.strip().split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if command in ["exit", "quit", "bye"]:
            save_choice = input(f"{BLUE}System>> {RESET}Do you want to save this conversation before exiting? (y/n): ")
            if save_choice.lower() == "y":
                filename = input(f"{BLUE}System>> {RESET}Enter filename (or press Enter for default): ")
                save_conversation(filename if filename else None)
            print(f"{BLUE}System>> {RESET}Goodbye!")
            done = True
        elif command in ["menu", "help", "cmd"]:
            menu()
        elif command in ["clear", "cls"]:
            clear_screen()
            menu()
        elif command == "cd":
            print(f"{BLUE}System>> {RESET}Current directory: {os.getcwd()}")
        elif command in ["settings", "config"]:
            config_choice = input(f"{BLUE}System>> {RESET}What would you like to change? (m)odel, (p)rompt, (s)peed, or (e)xit: ").lower()
            config(config_choice)
        elif command in ["memory", "mem"]:
            print(f"{BLUE}System>> {RESET}Message memory size: {len(msgMemory)}")
        elif command in ["reset"]:
            msgMemory.clear()
            print(f"{BLUE}System>> {RESET}Message memory cleared.")
        elif command in ["test", "testfile"]:
            await handle_read_file()
        elif command == "read":
            if args:
                # Parse the multi-parameter command: read filename [question]
                file_parts = args.split(maxsplit=1)
                filename = file_parts[0]
                question = file_parts[1] if len(file_parts) > 1 else None
                await handle_read_file(filename, question)
            else:
                await handle_read_file()
        elif command == "save":
            save_conversation(args if args else None)
        elif command == "load":
            if args:
                load_conversation(args)
            else:
                print(f"{RED}System>> Please specify a filename to load.{RESET}")
        elif command == "scrape":
            if args:
                url = args
                text = scrape_website(url)

                # Add the user message to memory
                msgMemory.append({
                    "role": "user",
                    "content": f"I want to learn about this website: {url}. Here is the content: {text}"
                })

                # Stream the response with retry logic
                response_text = await stream_with_retry(
                    messages=msgMemory,
                    model=models[model]
                )

                # Add Claude's response to memory
                if response_text:
                    msgMemory.append({
                        "role": "assistant",
                        "content": response_text
                    })
            else:
                print(f"{RED}System>> Please specify a URL to scrape.{RESET}")
        elif question.strip():
            # Add the user message to memory
            msgMemory.append({
                "role": "user",
                "content": question
            })

            # Stream the response with retry logic
            response_text = await stream_with_retry(
                messages=msgMemory,
                model=models[model]
            )

            # Add Claude's response to memory
            if response_text:
                msgMemory.append({
                    "role": "assistant",
                    "content": response_text
                })

                # Check for code blocks and offer to save them
                if "`" + "``" in response_text:
                    code_data = extract_code_from_response(response_text)
                    if code_data:
                        write_choice = input(f"{BLUE}System>> {RESET}Detected code block in response. Do you want to write it to a file? (y/n): ")
                
                        if write_choice.lower() == "y":
                            # Determine file extension
                            code_content, language = code_data
                            file_extension = determine_file_extension(language)
                            default_filename = f"new_file{file_extension}"
                
                            print(f"{BLUE}System>> {RESET}Default filename: {default_filename}")
                            rename_choice = input(f"{BLUE}System>> {RESET}Do you want to rename the file? (y/n): ")
                
                            if rename_choice.lower() == "y":
                                custom_filename = input(f"{BLUE}System>> {RESET}Enter new filename (without extension): ")
                                # Ensure the extension stays the same
                                new_filename = f"{custom_filename}{file_extension}"
                            else:
                                new_filename = default_filename
                
                            with open(new_filename, "w", encoding="utf-8") as f:
                                f.write(code_content)
                            print(f"{BLUE}System>> {RESET}{new_filename} created.")
                
                            # Ask about running the file if it's a Python file
                            if file_extension == ".py":
                                run_choice = input(f"{BLUE}System>> {RESET}Would you like to run {new_filename}? (y/n): ")
                                if run_choice.lower() == "y":
                                    print(f"{BLUE}System>> {RESET}Running {new_filename}...")
                                    output = runPyFile(new_filename)
                                    print(output)
                                    print(f"{BLUE}System>> {RESET}{new_filename} execution completed.")
if __name__ == "__main__":
    asyncio.run(main())
