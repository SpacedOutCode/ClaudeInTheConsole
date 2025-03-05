# Claude In The Console

A terminal-based interface for interacting with Claude AI models.

![Claude In The Console](https://i.imgur.com/placeholder.png)

## Features

- Interactive conversations with Claude AI through a command-line interface
- Support for multiple Claude models (claude-3-7-sonnet-20250219, claude-3-5-haiku-latest)
- Web scraping capability to provide Claude with website content
- File reading support to ask questions about local files
- Code execution capability for Python scripts
- Conversation memory with save/load functionality
- Customizable system prompts and response speeds
- Automatic code extraction and execution from Claude's responses
- Robust error handling and retry mechanisms for API overload scenarios

## Requirements

- Python 3.7+
- Anthropic API key (set as environment variable)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/spacedoucode/claudeintheconsole.git
   cd claude-console
   ```

2. Install required packages:
   ```
   pip install anthropic requests beautifulsoup4
   ```

3. Set up your Anthropic API key as an environment variable:
   ```
   # For Linux/Mac
   export ANTHROPIC_API_KEY="your-api-key"

   # For Windows
   setx ANTHROPIC_API_KEY=your-api-key
   ```

## Usage

Run the application:
```
py claude.py
```

### Commands

- `scrape [url]` - Retrieve information from a website
- `settings` or `config` - Change application settings
- `clear` or `cls` - Clear the screen
- `cd` - View the current directory
- `menu`, `help`, or `cmd` - Show the command menu
- `read [filename] "question"` - Read a file and ask a question about it
- `save [filename]` - Save the conversation
- `load [filename]` - Load a saved conversation
- `memory` or `mem` - View message memory size
- `reset` - Clear message memory
- `test` - Create and run a test Python script
- `exit`, `quit`, or `bye` - Exit the application

### Configuration

Use the `settings` or `config` command to configure:
- `(m)odel` - Select which Claude model to use
- `(p)rompt` - Change the system prompt
- `(s)peed` - Adjust the response display speed

Configuration is automatically saved between sessions.

## Example Usage

```
User>> Hello, Claude!
Claude>> Hello! How can I assist you today?

User>> scrape wikipedia.org
Claude>> [Information about Wikipedia...]

User>> read
System>> Enter the filename: mycode.py
User>> What does this code do?
Claude>> [Explanation of the code...]

User>> save my_conversation
System>> Conversation saved to my_conversation.json
```

## License

MIT License

## Acknowledgments

- [Anthropic](https://www.anthropic.com/) for the Claude AI API
- BeautifulSoup4 for web scraping capabilities
