# One Page Rules — Discord Matchmaking Bot

A Discord bot for the game **One Page Rules** that handles player matchmaking based on faction choice.

## Features

- **Slash Commands** via `discord.py` app_commands
- **Faction-based matchmaking** (AOF / GDF)
- **Persistent storage** using a local JSON file
- **Admin reset** command for manual clearing

## Commands

| Command | Description |
|---------|-------------|
| `/matchmaking action:Join faction:[AOF/GDF]` | Join the queue or get matched |
| `/matchmaking action:Show` | Display all active matches and waiting players |
| `/matchmaking action:Leave` | Leave the queue (if not yet matched) |
| `/matchmaking_reset` | Clear all data (Admin only) |

## Setup

### Prerequisites

- Python 3.10+
- A Discord Bot Token from the [Discord Developer Portal](https://discord.com/developers/applications)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd DiscordMatchmakingOPR
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your bot token**
   ```bash
   export DISCORD_TOKEN="your-bot-token-here"
   ```

4. **Run the bot**
   ```bash
   python bot.py
   ```

## Project Structure

```
├── bot.py                 # Main entry point
├── matchmaking_cog.py     # Matchmaking commands & logic
├── storage.py             # JSON persistence layer
├── requirements.txt       # Python dependencies
├── .gitignore
└── README.md
```

## License

MIT
