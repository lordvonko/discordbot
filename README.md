# 🚀 Musashi BOT

<div align="center">
  <h3>Turn up the volume and keep your server in tune! 🎶🔨</h3>
  <p>A multi-purpose Discord bot for music vibes, moderation muscle, and handy utilities. Built with love for servers that rock. 😎</p>
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Stars](https://img.shields.io/github/stars/lordvonko/discordbot?style=social)](https://github.com/lordvonko/discordbot)
  
  <br/>
  <em>Dive in – we've got beats, bans, and beyond waiting for you! 🎧</em>
</div>

# Don't want to host? Just invite Musashi 
# [Click here to invite](https://discord.com/oauth2/authorize?client_id=1392570482502668410)
---

## 🌈 Why Musashi? Because Your Server Deserves the Best
Tired of juggling multiple bots? Musashi is your all-in-one jam: queue up tunes, kick out trolls, and sprinkle some fun – all in a sleek, easy-to-use package. 

- **Music Magic**: Stream from YouTube or Spotify without breaking a sweat. 🎵
- **Moderation Mastery**: Keep things civil with powerful tools. 🛡️
- **Extra Sparkle**: Utilities that make server life a breeze. ✨

---

## 🛠️ Features That'll Make You Groove and not pay for Spotify again...
Musashi packs a punch with commands for every mood. Here's the lineup, served up in handy tables for quick scanning:

### 🎶 Music Commands
Queue up, skip, pause – we've got your playlist covered!

| Command | Description | Example Usage |
|---------|-------------|---------------|
| **/play** | Plays a song or adds it to the queue (YouTube/Spotify URLs supported). | `/play {url} or music name` |
| **/stop** | Stops the music and clears the queue. | `/stop` |
| **/skip** | Skips to the next song. | `/skip` |
| **/pause** | Pauses the current track. | `/pause` |
| **/resume** | Resumes paused music. | `/resume` |
| **/queue** | Shows the current queue. | `/queue` |
| **/leave** | Disconnects the bot from voice channel. | `/leave` |

### 🔨 Moderation Commands
Keep your server safe and sound – no drama allowed!

| Command | Description | Example Usage |
|---------|-------------|---------------|
| **/ban** | Bans a user permanently. | `/ban @user reason: Spamming` |
| **/kick** | Kicks a user out. | `/kick @user` |
| **/tempban** | Bans a user for a set time. | `/tempban @user 1d reason: Timeout` |
| **/clear** | Deletes messages in bulk. | `/clear 50` |
| **/lock** | Locks a channel from messaging. | `/lock #general` |
| **/nickname** | Changes a user's nickname. | `/nickname @user NewNick` |

### ✨ Other Commands
The fun extras that tie it all together.

| Command | Description | Example Usage |
|---------|-------------|---------------|
| **/announce** | Sends a message to a channel. | `/announce #news Hello world!` |
| **/avatar** | Displays a user's avatar. | `/avatar @user` |
| **/help** | Lists all commands. | `/help` |
| **/sync** | Syncs slash commands (owner only). | `/sync` |

<details>
<summary>Pro Tip: Want more details? Click here! 🤫</summary>
  
All commands are slash-based for that modern Discord feel. Customize permissions in your server settings for ultimate control. 🚀
  
</details>
---

## 📚 Installation & Setup – Easy as 1-2-3
Hosting Musashi on your VPS? No sweat! Follow these chill steps, and you'll be online in minutes.

Choose your deployment method:

## 🐳 Docker Deployment (Recommended)
The easiest and most reliable way to run Musashi!

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) 🐳
- [Docker Compose](https://docs.docker.com/compose/install/) 📦
- [Git](https://git-scm.com/downloads) 📦

### Quick Docker Setup
1. **Clone the Repo**:
   ```bash
   git clone https://github.com/lordvonko/discordbot
   cd discordbot
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   nano .env  # Add your tokens
   ```

3. **Launch with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

4. **Check Status**:
   ```bash
   docker-compose logs -f discordbot
   ```

**That's it! 🎉 Musashi is now running in a secure container with automatic restarts.**

---

## 🐍 Manual Python Setup
For those who prefer the traditional approach.

### Prerequisites
- [Python 3.8+](https://www.python.org/downloads/) 🐍
- [Git](https://git-scm.com/downloads) 📦

### Step-by-Step Guide
1. **Clone the Repo**:
   ```bash
   git clone https://github.com/lordvonko/discordbot
   cd discordbot
   ```

2. **Set Up Virtual Env & Install Deps**:
   Create a virtual environment (highly recommended!):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
   Then install the goodies:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Your .env File**:
   Open `.env` and plug in your secrets:
   ```env
   DISCORD_TOKEN=YOUR_DISCORD_TOKEN_HERE
   SPOTIFY_CLIENT_ID=YOUR_SPOTIFY_CLIENT_ID_HERE
   SPOTIFY_CLIENT_SECRET=YOUR_SPOTIFY_CLIENT_SECRET_HERE
   ```
   (Pro tip: Keep this file safe – it's your bot's lifeline! 🔑)

4. **Launch the Bot**:
   ```bash
   python main.py
   ```
   Watch Musashi come alive in your console. 🎉

---

## 🔧 Docker Management Commands
Useful commands for managing your Dockerized Musashi:

```bash
# View logs
docker-compose logs -f discordbot

# Restart the bot
docker-compose restart discordbot

# Stop the bot
docker-compose down

# Update and restart (after git pull)
docker-compose build --no-cache
docker-compose up -d

# Check container status
docker-compose ps

# Access container shell (for debugging)
docker-compose exec discordbot /bin/bash
```

---

## 🛠️ Troubleshooting
Having issues? Here are common solutions:

### Docker Issues:
- **Bot won't start**: Check `docker-compose logs discordbot` for errors
- **Permission denied**: Ensure `.env` file has correct permissions
- **Build fails**: Run `docker system prune` and rebuild

### General Issues:
- **Invalid token**: Double-check your `DISCORD_TOKEN` in `.env`
- **Music not working**: Ensure FFmpeg is installed (automatic in Docker)
- **Commands not showing**: Use `/sync` command (bot owner only)

<div align="center">
  <p><strong>Still stuck?</strong> Check our issues page or create a new one – we're here to help! 🛠️</p>
</div>

---

## 🤝 Contributions – Let's Build Together!
Love Musashi? Want to make it even better? Contributions are super welcome! Whether it's bug fixes, new features, or just ideas – jump in.

<details>
<summary>Contributor Shoutouts 🏆</summary>
  
- @you – For checking this out! 🎉

</details>

---

## ❓ FAQ – Quick Answers to Common Questions
Got queries? We've got relaxed replies.

- **Q: Does Musashi support playlists?**  
  A: Yep! Just drop a Spotify or YouTube playlist URL in `/play`. 📜

- **Q: How do I get my Discord token?**  
  A: Head to the [Discord Developer Portal](https://discord.com/developers/applications), create an app, and grab the bot token. Easy peasy! 🔑

- **Q: Can I run this on Heroku or other hosts?**  
  A: Absolutely, but VPS is recommended for stability. Docker deployment works great on most platforms! ☁️

- **Q: Should I use Docker or Python directly?**  
  A: Docker is recommended! It's easier to set up, more secure, and handles dependencies automatically. 🐳

---

## 📝 License
Musashi is under the MIT License – free to use, modify, and share. Just give credit where it's due! ⭐

<div align="center">
  <p>Made with ❤️ by LORD Vonko. Thanks for vibing with us and READING this entire README!</p>

--- 

<div align="center">
  <a href="#top">Back to Top ⬆️</a>
</div>
