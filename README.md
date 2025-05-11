# Revmedical Chatbot

## Two Bot Options

1. **OpenAI Bot** (Default)

   - Uses gpt-4o for conversation
   - Requires OpenAI API key

## Quick Start

### First, start the bot server:

1. Navigate to the server directory:
   ```bash
   cd server
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy env.example to .env and configure:
   - Add your API keys
   - Choose your bot implementation:
     ```ini
     BOT_IMPLEMENTATION=      # Options: 'openai' (default) or 'gemini'
     ```
5. Start the server:
   ```bash
   python server.py
   ```

## Important Note

The bot server must be running for any of the client implementations to work. Start the server first before trying the client app.

## Requirements

- Python 3.10+
- Node.js 16+ (for JavaScript and React implementations)
- Daily API key
- OpenAI API key (for OpenAI bot)
- ElevenLabs API key
- Modern web browser with WebRTC support

## Project Structure

```
rdvmedical/
├── server/              # Bot server implementation
│   ├── bot-openai.py    # OpenAI bot implementation
│   ├── runner.py        # Server runner utilities
│   ├── server.py        # FastAPI server
│   ├── gcalendar.py     # Google calendar api management
│   └── requirements.txt
└── client/              # Client implementations
    └── react/           # Pipecat React client
```
