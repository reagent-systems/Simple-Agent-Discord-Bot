# Simple-Agent-Discord-Bot

A Discord bot that integrates with the [Simple Agent WebSocket system](https://github.com/reagent-systems/Simple-Agent-Websocket) to provide AI assistance through Discord slash commands with real-time updates in threads.

## 🎯 Features

- **🤖 Slash Commands**: Use `/simple_agent` to run AI tasks
- **🧵 Thread Creation**: Each task runs in its own Discord thread
- **📊 Real-time Updates**: See agent progress live in Discord
- **🔄 Interactive Sessions**: Respond to agent questions directly in threads
- **⚡ Multiple Sessions**: Support for concurrent user sessions
- **🛠️ Modular Design**: Clean, maintainable code structure
- **📱 Rich Embeds**: Beautiful Discord embeds for all agent events

## 🏗️ Architecture

```
Simple-Agent-Discord-Bot/
├── main.py                          # Entry point
├── requirements.txt                 # Dependencies
├── env.example                      # Environment configuration example
├── bot/                            # Main bot package
│   ├── __init__.py
│   ├── core/                       # Core bot functionality
│   │   ├── __init__.py
│   │   └── bot_client.py           # Main Discord bot client
│   ├── commands/                   # Slash command handlers
│   │   ├── __init__.py
│   │   └── simple_agent_command.py # Main Simple Agent command
│   ├── websocket/                  # WebSocket client for Simple Agent
│   │   ├── __init__.py
│   │   └── client.py               # WebSocket communication
│   ├── discord/                    # Discord-specific functionality
│   │   ├── __init__.py
│   │   ├── thread_manager.py       # Thread creation and management
│   │   └── message_formatter.py    # Discord embed formatting
│   └── utils/                      # Utilities
│       ├── __init__.py
│       ├── config.py               # Configuration management
│       └── logger.py               # Logging setup
└── logs/                           # Log files (auto-created)
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8+
- A Discord bot token
- Simple Agent WebSocket server running ([setup guide](https://github.com/reagent-systems/Simple-Agent-Websocket))

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/your-username/Simple-Agent-Discord-Bot.git
cd Simple-Agent-Discord-Bot

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file based on `env.example`:

```bash
cp env.example .env
```

Edit `.env` with your configuration:

```env
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_discord_guild_id_here  # Optional: for faster command sync

# Simple Agent WebSocket Server Configuration
WEBSOCKET_SERVER_URL=http://localhost:5000
WEBSOCKET_TIMEOUT=300

# Bot Configuration
BOT_PREFIX=/
DEFAULT_MAX_STEPS=20
DEFAULT_AUTO_STEPS=10
MAX_THREAD_MESSAGES=50

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/discord_bot.log
```

### 4. Discord Bot Setup

1. **Create a Discord Application:**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Go to the "Bot" tab and click "Add Bot"
   - Copy the bot token to your `.env` file

2. **Set Bot Permissions:**
   Required permissions:
   - Send Messages
   - Use Slash Commands
   - Create Public Threads
   - Send Messages in Threads
   - Add Reactions
   - Read Message History

3. **Invite Bot to Server:**
   - Go to the "OAuth2" > "URL Generator" tab
   - Select "bot" and "applications.commands" scopes
   - Select the required permissions
   - Use the generated URL to invite the bot

### 5. Start the Bot

```bash
python main.py
```

## 🎮 Usage

### Available Commands

#### `/simple_agent`
Run a Simple Agent task with real-time updates.

**Parameters:**
- `prompt` (required): The task or instruction for the AI agent
- `max_steps` (optional): Maximum number of steps to execute (default: 20, max: 100)
- `auto_steps` (optional): Number of steps to auto-continue without confirmation (default: 10)

**Example:**
```
/simple_agent prompt:Write a Python script to calculate fibonacci numbers max_steps:15 auto_steps:5
```

#### `/stop_agent`
Stop your active Simple Agent session.

#### `/agent_status`
Check the status of your active Simple Agent session.

### How It Works

1. **Command Execution**: Use `/simple_agent` with your prompt
2. **Thread Creation**: Bot creates a dedicated thread for your session
3. **Real-time Updates**: See each step of agent execution in the thread:
   - 🚀 Agent started
   - 🔄 Step progress
   - 🧠 Assistant responses
   - 🔧 Tool executions
   - 📝 Step summaries
   - ⏳ Waiting for user input
   - ✅ Task completion
4. **Interactive**: Respond to agent questions directly in the thread
5. **Automatic Cleanup**: Thread is archived when session completes

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token | Required |
| `DISCORD_GUILD_ID` | Guild ID for faster command sync | Optional |
| `WEBSOCKET_SERVER_URL` | Simple Agent WebSocket server URL | `http://localhost:5000` |
| `WEBSOCKET_TIMEOUT` | WebSocket connection timeout (seconds) | `300` |
| `DEFAULT_MAX_STEPS` | Default maximum steps for agent | `20` |
| `DEFAULT_AUTO_STEPS` | Default auto-continue steps | `10` |
| `MAX_THREAD_MESSAGES` | Maximum messages per thread | `50` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FILE` | Log file path | `logs/discord_bot.log` |

### Advanced Configuration

The modular design allows for easy customization:

- **Custom Commands**: Add new commands in `bot/commands/`
- **Custom Formatters**: Modify `bot/discord/message_formatter.py`
- **Event Handlers**: Extend `bot/websocket/client.py`
- **Thread Behavior**: Customize `bot/discord/thread_manager.py`

## 🔒 Security & Permissions

### Required Discord Permissions

- **Send Messages**: Send responses and updates
- **Use Slash Commands**: Register and use slash commands
- **Create Public Threads**: Create threads for agent sessions
- **Send Messages in Threads**: Send updates to threads
- **Add Reactions**: Acknowledge user input
- **Read Message History**: Check thread message limits

### Security Considerations

- Bot token should be kept secret
- Consider rate limiting for production use
- Thread archiving preserves conversation history
- Sessions are isolated per user
- WebSocket connections are managed securely

## 🧪 Development

### Project Structure Benefits

- **🔧 Maintainability**: Each component has a single responsibility
- **🧪 Testability**: Modular design allows for easy testing
- **📈 Scalability**: Easy to add new features
- **🔍 Debuggability**: Clear separation of concerns
- **👥 Team Development**: Multiple developers can work on different modules

### Adding Features

1. **New Commands**: Create new command files in `bot/commands/`
2. **Event Handlers**: Extend WebSocket event handling in `bot/websocket/client.py`
3. **Message Types**: Add new embed types in `bot/discord/message_formatter.py`
4. **Configuration**: Add new config options in `bot/utils/config.py`

### Logging

Comprehensive logging is built-in:
- Rotating log files
- Configurable log levels
- Separate logs for different components
- Error tracking with stack traces

## 🤝 Integration with Simple Agent

This bot is designed to work seamlessly with the [Simple Agent WebSocket system](https://github.com/reagent-systems/Simple-Agent-Websocket). It:

- Connects to the WebSocket server
- Handles all WebSocket events
- Provides real-time updates
- Manages user input flow
- Maintains session state

### WebSocket Events Handled

- `connected` - Connection established
- `agent_started` - Agent execution began
- `step_start` - New step started
- `assistant_message` - AI assistant response
- `tool_call` - Tool/function execution
- `step_summary` - Step completion summary
- `waiting_for_input` - Agent waiting for user input
- `task_completed` - Task finished successfully
- `agent_finished` - Agent execution completed
- `agent_error` - Error occurred

## 📝 Examples

### Basic Task
```
/simple_agent prompt:Explain how Python list comprehensions work
```

### Complex Task with Custom Parameters
```
/simple_agent prompt:Create a REST API for a todo app with FastAPI max_steps:25 auto_steps:15
```

### Interactive Task
```
/simple_agent prompt:Help me debug this Python code [paste code] max_steps:10 auto_steps:3
```

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding to commands**
   - Check bot permissions
   - Verify bot token
   - Ensure commands are synced (check logs)

2. **Cannot create threads**
   - Check "Create Public Threads" permission
   - Ensure channel supports threads

3. **WebSocket connection fails**
   - Verify Simple Agent server is running
   - Check `WEBSOCKET_SERVER_URL` configuration
   - Check firewall/network connectivity

4. **Commands not appearing**
   - Set `DISCORD_GUILD_ID` for faster sync
   - Wait a few minutes for global sync
   - Check bot permissions

### Debug Mode

Enable debug logging:
```env
LOG_LEVEL=DEBUG
```

## 📄 License

This project follows the same license as the Simple Agent Core.

## 🙏 Acknowledgments

- Built for integration with [Simple Agent WebSocket](https://github.com/reagent-systems/Simple-Agent-Websocket)
- Uses discord.py for Discord integration
- Uses python-socketio for WebSocket communication

---

**🤖 Ready to bring AI assistance to your Discord server!**
