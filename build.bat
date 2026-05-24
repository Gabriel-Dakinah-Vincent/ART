@echo off
REM Advanced PyInstaller build script for ART project.
REM Uses build_env\Scripts\python.exe when available; otherwise falls back to py -3.13.

setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
pushd "%SCRIPT_DIR%" >nul || (
  echo [ERROR] Failed to enter project directory: "%SCRIPT_DIR%"
  exit /b 1
)

set "ENTRY_SCRIPT=agent_template.py"
set "DATA_DIR=agent_logs"
set "BUILD_DIR=build"
set "DIST_DIR=%BUILD_DIR%"
set "WORK_DIR=%BUILD_DIR%\pyinstaller_work"
set "SPEC_DIR=%BUILD_DIR%"
set "DEFAULT_APP_NAME=agent"
set "APP_NAME=%DEFAULT_APP_NAME%"
set "ICONS_DIR=icons"
set "DEFAULT_ICON_NAME=Windows Defender.ico"
set "OUTPUT_NAME=%APP_NAME%.exe"
set "OUTPUT_FILE=%DIST_DIR%\%OUTPUT_NAME%"
set "VENV_PYTHON=build_env\Scripts\python.exe"
set "REQUIREMENTS_FILE=requirements.txt"
set "ENTRY_SCRIPT_PATH=%SCRIPT_DIR%\%ENTRY_SCRIPT%"
set "DATA_DIR_PATH=%SCRIPT_DIR%\%DATA_DIR%"
set "ICONS_DIR_PATH=%SCRIPT_DIR%\%ICONS_DIR%"

set "DO_CLEAN="
set "DRY_RUN="
set "BOOTSTRAP="
set "LIST_ICONS="
set "PAUSE_ON_EXIT="
set "SMOKE_TEST="
set "ARCHIVE_BUILD="
set "ICON_NAME="
set "ICON_PATH="
set "ICON_AUTO_SELECTED="
set "APP_NAME_OVERRIDE="
set "OUTPUT_DIR_OVERRIDE="
set "PYTHON_OVERRIDE="
set "PYTHON_EXE="
set "PYTHON_EXTRA_ARGS="
set "PYTHON_LABEL="
set "WINDOW_MODE=windowed"
set "LOG_LEVEL="
set "VERSION_VALUE="
set "COMPANY_NAME="
set "PRODUCT_NAME="
set "MANIFEST_LEVEL="
set "MANIFEST_SPECIFIED="
set "SIGN_SCRIPT_COMMAND="
set "ICON_CLI_ARG="
set "ICON_PRINT_ARG="
set "WINDOW_MODE_CLI_ARG="
set "WINDOW_MODE_PRINT_ARG="
set "LOG_LEVEL_CLI_ARG="
set "LOG_LEVEL_PRINT_ARG="
set "VERSION_CLI_ARG="
set "VERSION_PRINT_ARG="
set "VERSION_FILE="
set "MANIFEST_CLI_ARG="
set "MANIFEST_PRINT_ARG="
set "MANIFEST_FILE="
set "HASH_FILE="
set "ARCHIVE_FILE="
set "EXIT_CODE=0"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="clean" set "DO_CLEAN=1" & shift & goto parse_args
if /I "%~1"=="--clean" set "DO_CLEAN=1" & shift & goto parse_args
if /I "%~1"=="dry-run" set "DRY_RUN=1" & shift & goto parse_args
if /I "%~1"=="--dry-run" set "DRY_RUN=1" & shift & goto parse_args
if /I "%~1"=="bootstrap" set "BOOTSTRAP=1" & shift & goto parse_args
if /I "%~1"=="--bootstrap" set "BOOTSTRAP=1" & shift & goto parse_args
if /I "%~1"=="list-icons" set "LIST_ICONS=1" & shift & goto parse_args
if /I "%~1"=="--list-icons" set "LIST_ICONS=1" & shift & goto parse_args
if /I "%~1"=="icon" goto parse_icon
if /I "%~1"=="--icon" goto parse_icon
if /I "%~1"=="name" goto parse_name
if /I "%~1"=="--name" goto parse_name
if /I "%~1"=="python" goto parse_python
if /I "%~1"=="--python" goto parse_python
if /I "%~1"=="console" set "WINDOW_MODE=console" & shift & goto parse_args
if /I "%~1"=="--console" set "WINDOW_MODE=console" & shift & goto parse_args
if /I "%~1"=="windowed" set "WINDOW_MODE=windowed" & shift & goto parse_args
if /I "%~1"=="--windowed" set "WINDOW_MODE=windowed" & shift & goto parse_args
if /I "%~1"=="debug" set "LOG_LEVEL=DEBUG" & shift & goto parse_args
if /I "%~1"=="--debug" set "LOG_LEVEL=DEBUG" & shift & goto parse_args
if /I "%~1"=="log-level" goto parse_log_level
if /I "%~1"=="--log-level" goto parse_log_level
if /I "%~1"=="smoke-test" set "SMOKE_TEST=1" & shift & goto parse_args
if /I "%~1"=="--smoke-test" set "SMOKE_TEST=1" & shift & goto parse_args
if /I "%~1"=="version" goto parse_version
if /I "%~1"=="--version" goto parse_version
if /I "%~1"=="company" goto parse_company
if /I "%~1"=="--company" goto parse_company
if /I "%~1"=="product" goto parse_product
if /I "%~1"=="--product" goto parse_product
if /I "%~1"=="manifest" goto parse_manifest
if /I "%~1"=="--manifest" goto parse_manifest
if /I "%~1"=="requirements" goto parse_requirements
if /I "%~1"=="--requirements" goto parse_requirements
if /I "%~1"=="output-dir" goto parse_output_dir
if /I "%~1"=="--output-dir" goto parse_output_dir
if /I "%~1"=="archive" set "ARCHIVE_BUILD=1" & shift & goto parse_args
if /I "%~1"=="--archive" set "ARCHIVE_BUILD=1" & shift & goto parse_args
if /I "%~1"=="sign-script" goto parse_sign_script
if /I "%~1"=="--sign-script" goto parse_sign_script
if /I "%~1"=="pause" set "PAUSE_ON_EXIT=1" & shift & goto parse_args
if /I "%~1"=="--pause" set "PAUSE_ON_EXIT=1" & shift & goto parse_args
if /I "%~1"=="help" goto show_help
if /I "%~1"=="--help" goto show_help
echo [ERROR] Unknown option: %~1
goto show_help_error

:parse_icon
shift
if "%~1"=="" (
  echo [ERROR] Missing icon filename after --icon.
  goto show_help_error
)
set "ICON_NAME=%~1"
shift
goto parse_args

:parse_name
shift
if "%~1"=="" (
  echo [ERROR] Missing output name after --name.
  goto show_help_error
)
set "APP_NAME_OVERRIDE=%~1"
shift
goto parse_args

:parse_python
shift
if "%~1"=="" (
  echo [ERROR] Missing interpreter path or version after --python.
  goto show_help_error
)
set "PYTHON_OVERRIDE=%~1"
shift
goto parse_args

:parse_log_level
shift
if "%~1"=="" (
  echo [ERROR] Missing log level after --log-level.
  goto show_help_error
)
set "LOG_LEVEL=%~1"
shift
goto parse_args

:parse_version
shift
if "%~1"=="" (
  echo [ERROR] Missing version value after --version.
  goto show_help_error
)
set "VERSION_VALUE=%~1"
shift
goto parse_args

:parse_company
shift
if "%~1"=="" (
  echo [ERROR] Missing company value after --company.
  goto show_help_error
)
set "COMPANY_NAME=%~1"
shift
goto parse_args

:parse_product
shift
if "%~1"=="" (
  echo [ERROR] Missing product value after --product.
  goto show_help_error
)
set "PRODUCT_NAME=%~1"
shift
goto parse_args

:parse_manifest
shift
if "%~1"=="" (
  echo [ERROR] Missing manifest level after --manifest.
  goto show_help_error
)
set "MANIFEST_LEVEL=%~1"
set "MANIFEST_SPECIFIED=1"
shift
goto parse_args

:parse_requirements
shift
if "%~1"=="" (
  echo [ERROR] Missing requirements file after --requirements.
  goto show_help_error
)
set "REQUIREMENTS_FILE=%~1"
shift
goto parse_args

:parse_output_dir
shift
if "%~1"=="" (
  echo [ERROR] Missing directory after --output-dir.
  goto show_help_error
)
set "OUTPUT_DIR_OVERRIDE=%~1"
shift
goto parse_args

:parse_sign_script
shift
if "%~1"=="" (
  echo [ERROR] Missing command after --sign-script.
  goto show_help_error
)
set "SIGN_SCRIPT_COMMAND=%~1"
shift
goto parse_args

:args_done
if defined LIST_ICONS goto list_icons

if defined OUTPUT_DIR_OVERRIDE set "DIST_DIR=%OUTPUT_DIR_OVERRIDE%"

call :resolve_python_runner
if errorlevel 1 goto fail

if not exist "%ENTRY_SCRIPT%" (
  echo [ERROR] Missing entry script: "%ENTRY_SCRIPT%"
  goto fail
)

if not exist "%DATA_DIR%" (
  echo [ERROR] Missing data directory: "%DATA_DIR%"
  goto fail
)

if defined ICON_NAME (
  call :resolve_icon
) else (
  call :apply_default_icon
)
if errorlevel 1 goto fail

call :resolve_app_name
if errorlevel 1 goto fail

echo [INFO] Project directory: "%SCRIPT_DIR%"
echo [INFO] Python runner: %PYTHON_LABEL%
echo [INFO] App name: "%APP_NAME%"
echo [INFO] Output file: "%OUTPUT_FILE%"
if defined ICON_AUTO_SELECTED echo [INFO] Default icon selected: "%ICON_NAME%"
if defined ICON_PATH echo [INFO] Icon file: "%ICON_PATH%"
if defined OUTPUT_DIR_OVERRIDE echo [INFO] Output directory override: "%DIST_DIR%"
if defined SIGN_SCRIPT_COMMAND echo [INFO] Post-build sign hook: %SIGN_SCRIPT_COMMAND%

if defined DRY_RUN (
  call :prepare_build_args
  if errorlevel 1 goto fail
  echo [DRY-RUN] Resolved build command:
  call :print_command
  goto success
)

call :run_python -c "import sys"
if errorlevel 1 (
  echo [ERROR] The selected Python runner is not available: %PYTHON_LABEL%
  goto fail
)

if defined BOOTSTRAP (
  echo [INFO] Bootstrapping build dependencies from "%REQUIREMENTS_FILE%"...
  call :install_build_deps
  if errorlevel 1 goto fail
)

call :check_pyinstaller
if errorlevel 1 goto fail

if defined DO_CLEAN call :clean_output
if errorlevel 1 goto fail

call :prepare_build_args
if errorlevel 1 goto fail

echo [INFO] Starting PyInstaller build...
call :run_build
if errorlevel 1 goto fail

if not exist "%OUTPUT_FILE%" (
  echo [ERROR] PyInstaller completed without producing "%OUTPUT_FILE%".
  goto fail
)

if defined SIGN_SCRIPT_COMMAND (
  call :run_sign_script
  if errorlevel 1 goto fail
)

if defined SMOKE_TEST (
  call :run_smoke_test
  if errorlevel 1 goto fail
)

if defined ARCHIVE_BUILD (
  call :archive_output
  if errorlevel 1 goto fail
)

echo [INFO] Build complete. Output: "%OUTPUT_FILE%"
goto success

:resolve_python_runner
set "PYTHON_EXE="
set "PYTHON_EXTRA_ARGS="
set "PYTHON_LABEL="

if defined PYTHON_OVERRIDE (
  if exist "%PYTHON_OVERRIDE%" (
    set "PYTHON_EXE=%PYTHON_OVERRIDE%"
    set "PYTHON_LABEL=%PYTHON_OVERRIDE%"
    exit /b 0
  )
  if exist "%SCRIPT_DIR%\%PYTHON_OVERRIDE%" (
    set "PYTHON_EXE=%SCRIPT_DIR%\%PYTHON_OVERRIDE%"
    set "PYTHON_LABEL=%SCRIPT_DIR%\%PYTHON_OVERRIDE%"
    exit /b 0
  )
  call :set_python_launcher_override "%PYTHON_OVERRIDE%"
  exit /b %errorlevel%
)

if exist "%VENV_PYTHON%" (
  set "PYTHON_EXE=%VENV_PYTHON%"
  set "PYTHON_LABEL=%VENV_PYTHON%"
) else (
  set "PYTHON_EXE=py"
  set "PYTHON_EXTRA_ARGS=-3.13"
  set "PYTHON_LABEL=py -3.13"
)
exit /b 0

:set_python_launcher_override
set "PYTHON_LAUNCHER_ARG=%~1"
if /I "%PYTHON_LAUNCHER_ARG%"=="py" (
  set "PYTHON_EXE=py"
  set "PYTHON_EXTRA_ARGS="
  set "PYTHON_LABEL=py"
  exit /b 0
)
if /I "%PYTHON_LAUNCHER_ARG:~0,3%"=="py " (
  set "PYTHON_EXE=py"
  set "PYTHON_EXTRA_ARGS=%PYTHON_LAUNCHER_ARG:~3%"
  set "PYTHON_LABEL=py %PYTHON_EXTRA_ARGS%"
  exit /b 0
)
if "%PYTHON_LAUNCHER_ARG:~0,1%"=="-" (
  set "PYTHON_EXE=py"
  set "PYTHON_EXTRA_ARGS=%PYTHON_LAUNCHER_ARG%"
  set "PYTHON_LABEL=py %PYTHON_EXTRA_ARGS%"
  exit /b 0
)
set "PYTHON_EXE=py"
set "PYTHON_EXTRA_ARGS=-%PYTHON_LAUNCHER_ARG%"
set "PYTHON_LABEL=py %PYTHON_EXTRA_ARGS%"
exit /b 0

:run_python
if /I "%PYTHON_EXE%"=="py" (
  if defined PYTHON_EXTRA_ARGS (
    py %PYTHON_EXTRA_ARGS% %*
  ) else (
    py %*
  )
) else (
  "%PYTHON_EXE%" %*
)
exit /b %errorlevel%

:check_pyinstaller
call :run_python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] PyInstaller is not installed for %PYTHON_LABEL%.
  echo         Re-run with --bootstrap to install build dependencies automatically.
  exit /b 1
)
exit /b 0

:install_build_deps
if not exist "%REQUIREMENTS_FILE%" (
  echo [ERROR] Missing requirements file: "%REQUIREMENTS_FILE%"
  exit /b 1
)

call :run_python -m pip install -r "%REQUIREMENTS_FILE%"
if errorlevel 1 (
  echo [ERROR] Failed to install build dependencies from "%REQUIREMENTS_FILE%".
  exit /b 1
)

exit /b 0

:list_icons
if not exist "%ICONS_DIR%" (
  echo [ERROR] Missing icons directory: "%ICONS_DIR%"
  goto fail
)

echo [INFO] Available icons in "%ICONS_DIR%":
dir /b "%ICONS_DIR%\*.ico" 2>nul
if errorlevel 1 (
  echo [INFO] No .ico files found.
)
goto success

:apply_default_icon
if not exist "%ICONS_DIR%" exit /b 0
if "%DEFAULT_ICON_NAME%"=="" exit /b 0
if exist "%ICONS_DIR_PATH%\%DEFAULT_ICON_NAME%" (
  set "ICON_NAME=%DEFAULT_ICON_NAME%"
  set "ICON_AUTO_SELECTED=1"
  call :resolve_icon
  exit /b %errorlevel%
)
exit /b 0

:resolve_icon
if not exist "%ICONS_DIR%" (
  echo [ERROR] Missing icons directory: "%ICONS_DIR%"
  exit /b 1
)

if exist "%ICON_NAME%" (
  set "ICON_PATH=%ICON_NAME%"
) else (
  set "ICON_PATH=%ICONS_DIR_PATH%\%ICON_NAME%"
)

if not exist "%ICON_PATH%" (
  echo [ERROR] Icon file not found: "%ICON_NAME%"
  echo         Place the icon in "%ICONS_DIR%" and rerun with --icon ^<filename.ico^>.
  exit /b 1
)

exit /b 0

:resolve_app_name
set "APP_NAME=%DEFAULT_APP_NAME%"
if defined APP_NAME_OVERRIDE (
  call :set_app_name_from_source "%APP_NAME_OVERRIDE%"
  if errorlevel 1 exit /b 1
) else (
  if defined ICON_NAME (
    call :set_app_name_from_source "%ICON_NAME%"
    if errorlevel 1 exit /b 1
  )
)
call :refresh_output_paths
exit /b 0

:set_app_name_from_source
set "APP_NAME=%~n1"
if "%APP_NAME%"=="" (
  echo [ERROR] Output name could not be resolved.
  exit /b 1
)
exit /b 0

:refresh_output_paths
set "OUTPUT_NAME=%APP_NAME%.exe"
set "OUTPUT_FILE=%DIST_DIR%\%OUTPUT_NAME%"
exit /b 0

:clean_output
if exist "%BUILD_DIR%" (
  echo [INFO] Removing previous build output: "%BUILD_DIR%"
  rmdir /s /q "%BUILD_DIR%"
  if exist "%BUILD_DIR%" (
    echo [ERROR] Failed to remove "%BUILD_DIR%".
    echo         Ensure no previous build is still running and no files are locked.
    exit /b 1
  )
)

if /I not "%DIST_DIR%"=="%BUILD_DIR%" (
  if exist "%DIST_DIR%" (
    echo [INFO] Removing previous dist output: "%DIST_DIR%"
    rmdir /s /q "%DIST_DIR%"
    if exist "%DIST_DIR%" (
      echo [ERROR] Failed to remove "%DIST_DIR%".
      echo         Ensure no previous build output is still running and no files are locked.
      exit /b 1
    )
  )
)

if exist "%SPEC_DIR%\%APP_NAME%.spec" (
  echo [INFO] Removing stale spec file: "%SPEC_DIR%\%APP_NAME%.spec"
  del /f /q "%SPEC_DIR%\%APP_NAME%.spec" >nul 2>&1
)

exit /b 0

:prepare_build_args
call :prepare_icon_arg
if errorlevel 1 exit /b 1
call :prepare_window_mode_arg
if errorlevel 1 exit /b 1
call :prepare_log_level_arg
if errorlevel 1 exit /b 1
call :prepare_version_metadata
if errorlevel 1 exit /b 1
call :prepare_manifest_arg
if errorlevel 1 exit /b 1
exit /b 0

:prepare_icon_arg
set "ICON_CLI_ARG="
set "ICON_PRINT_ARG="
if defined ICON_PATH (
  set "ICON_CLI_ARG=--icon "%ICON_PATH%""
  set "ICON_PRINT_ARG=--icon "%ICON_PATH%""
)
exit /b 0

:prepare_window_mode_arg
set "WINDOW_MODE_CLI_ARG=--noconsole"
set "WINDOW_MODE_PRINT_ARG=--noconsole"
if /I "%WINDOW_MODE%"=="console" (
  set "WINDOW_MODE_CLI_ARG=--console"
  set "WINDOW_MODE_PRINT_ARG=--console"
)
exit /b 0

:prepare_log_level_arg
set "LOG_LEVEL_CLI_ARG="
set "LOG_LEVEL_PRINT_ARG="
if defined LOG_LEVEL (
  set "LOG_LEVEL_CLI_ARG=--log-level %LOG_LEVEL%"
  set "LOG_LEVEL_PRINT_ARG=--log-level %LOG_LEVEL%"
)
exit /b 0

:prepare_version_metadata
set "VERSION_CLI_ARG="
set "VERSION_PRINT_ARG="
set "VERSION_FILE="

if not defined VERSION_VALUE if not defined COMPANY_NAME if not defined PRODUCT_NAME exit /b 0

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%" >nul 2>&1

set "VERSION_INPUT=%VERSION_VALUE%"
if not defined VERSION_INPUT set "VERSION_INPUT=1.0.0.0"
if not defined COMPANY_NAME set "COMPANY_NAME=%APP_NAME%"
if not defined PRODUCT_NAME set "PRODUCT_NAME=%APP_NAME%"

for /f "tokens=1,2 delims=;" %%A in ('powershell -NoProfile -Command "$p=@('%VERSION_INPUT%' -split '\.'); while($p.Count -lt 4){$p += '0'}; $p=$p[0..3]; Write-Output (($p -join ',') + ';' + ($p -join '.'))"') do (
  set "VERSION_COMMAS=%%A"
  set "VERSION_STRING=%%B"
)

if not defined VERSION_COMMAS (
  echo [ERROR] Failed to normalize version value: "%VERSION_INPUT%"
  exit /b 1
)

set "ESCAPED_COMPANY_NAME=%COMPANY_NAME:\=\\%"
set "ESCAPED_COMPANY_NAME=%ESCAPED_COMPANY_NAME:'=\'%"
set "ESCAPED_PRODUCT_NAME=%PRODUCT_NAME:\=\\%"
set "ESCAPED_PRODUCT_NAME=%ESCAPED_PRODUCT_NAME:'=\'%"
set "ESCAPED_APP_NAME=%APP_NAME:\=\\%"
set "ESCAPED_APP_NAME=%ESCAPED_APP_NAME:'=\'%"
set "ESCAPED_OUTPUT_NAME=%OUTPUT_NAME:\=\\%"
set "ESCAPED_OUTPUT_NAME=%ESCAPED_OUTPUT_NAME:'=\'%"

set "VERSION_FILE=%BUILD_DIR%\%APP_NAME%.version.txt"
> "%VERSION_FILE%" echo VSVersionInfo^(
>> "%VERSION_FILE%" echo   ffi=FixedFileInfo^(
>> "%VERSION_FILE%" echo     filevers=^(%VERSION_COMMAS%^),
>> "%VERSION_FILE%" echo     prodvers=^(%VERSION_COMMAS%^),
>> "%VERSION_FILE%" echo     mask=0x3f,
>> "%VERSION_FILE%" echo     flags=0x0,
>> "%VERSION_FILE%" echo     OS=0x40004,
>> "%VERSION_FILE%" echo     fileType=0x1,
>> "%VERSION_FILE%" echo     subtype=0x0,
>> "%VERSION_FILE%" echo     date=^(0, 0^)
>> "%VERSION_FILE%" echo     ^),
>> "%VERSION_FILE%" echo   kids=[
>> "%VERSION_FILE%" echo     StringFileInfo^(
>> "%VERSION_FILE%" echo       [
>> "%VERSION_FILE%" echo       StringTable^(
>> "%VERSION_FILE%" echo         '040904B0',
>> "%VERSION_FILE%" echo         [
>> "%VERSION_FILE%" echo         StringStruct^('CompanyName', '%ESCAPED_COMPANY_NAME%'^),
>> "%VERSION_FILE%" echo         StringStruct^('FileDescription', '%ESCAPED_PRODUCT_NAME%'^),
>> "%VERSION_FILE%" echo         StringStruct^('FileVersion', '%VERSION_STRING%'^),
>> "%VERSION_FILE%" echo         StringStruct^('InternalName', '%ESCAPED_APP_NAME%'^),
>> "%VERSION_FILE%" echo         StringStruct^('OriginalFilename', '%ESCAPED_OUTPUT_NAME%'^),
>> "%VERSION_FILE%" echo         StringStruct^('ProductName', '%ESCAPED_PRODUCT_NAME%'^),
>> "%VERSION_FILE%" echo         StringStruct^('ProductVersion', '%VERSION_STRING%'^)
>> "%VERSION_FILE%" echo         ]^)
>> "%VERSION_FILE%" echo       ]^),
>> "%VERSION_FILE%" echo     VarFileInfo^([VarStruct^('Translation', [1033, 1200]^)^])
>> "%VERSION_FILE%" echo   ]
>> "%VERSION_FILE%" echo ^)

set "VERSION_CLI_ARG=--version-file "%VERSION_FILE%""
set "VERSION_PRINT_ARG=--version-file "%VERSION_FILE%""
exit /b 0

:prepare_manifest_arg
set "MANIFEST_CLI_ARG="
set "MANIFEST_PRINT_ARG="
set "MANIFEST_FILE="

if not defined MANIFEST_SPECIFIED exit /b 0

set "MANIFEST_EXEC_LEVEL=%MANIFEST_LEVEL%"
if /I "%MANIFEST_EXEC_LEVEL%"=="admin" set "MANIFEST_EXEC_LEVEL=requireAdministrator"
if /I "%MANIFEST_EXEC_LEVEL%"=="highest" set "MANIFEST_EXEC_LEVEL=highestAvailable"
if /I "%MANIFEST_EXEC_LEVEL%"=="highestavailable" set "MANIFEST_EXEC_LEVEL=highestAvailable"
if /I "%MANIFEST_EXEC_LEVEL%"=="asinvoker" set "MANIFEST_EXEC_LEVEL=asInvoker"
if /I "%MANIFEST_EXEC_LEVEL%"=="requireadministrator" set "MANIFEST_EXEC_LEVEL=requireAdministrator"

if /I not "%MANIFEST_EXEC_LEVEL%"=="asInvoker" if /I not "%MANIFEST_EXEC_LEVEL%"=="highestAvailable" if /I not "%MANIFEST_EXEC_LEVEL%"=="requireAdministrator" (
  echo [ERROR] Unsupported manifest level: "%MANIFEST_LEVEL%"
  echo         Use asInvoker, highest, or admin.
  exit /b 1
)

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%" >nul 2>&1
set "MANIFEST_FILE=%BUILD_DIR%\%APP_NAME%.manifest"
> "%MANIFEST_FILE%" (
  echo ^<?xml version="1.0" encoding="UTF-8" standalone="yes"?^>
  echo ^<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0"^>
  echo   ^<trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"^>
  echo     ^<security^>
  echo       ^<requestedPrivileges^>
  echo         ^<requestedExecutionLevel level="%MANIFEST_EXEC_LEVEL%" uiAccess="false" /^>
  echo       ^</requestedPrivileges^>
  echo     ^</security^>
  echo   ^</trustInfo^>
  echo ^</assembly^>
)

set "MANIFEST_CLI_ARG=--manifest "%MANIFEST_FILE%""
set "MANIFEST_PRINT_ARG=--manifest "%MANIFEST_FILE%""
exit /b 0

:run_build
call :run_python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  %WINDOW_MODE_CLI_ARG% ^
  --name "%APP_NAME%" ^
  --distpath "%DIST_DIR%" ^
  --workpath "%WORK_DIR%" ^
  --specpath "%SPEC_DIR%" ^
  --add-data "%DATA_DIR_PATH%;%DATA_DIR%" ^
  %ICON_CLI_ARG% ^
  %LOG_LEVEL_CLI_ARG% ^
  %VERSION_CLI_ARG% ^
  %MANIFEST_CLI_ARG% ^
  --hidden-import pythoncom ^
  --hidden-import pywintypes ^
  --hidden-import win32timezone ^
  --hidden-import win32com ^
  --hidden-import win32com.client ^
  --hidden-import Crypto ^
  --hidden-import Crypto.Cipher ^
  --hidden-import Crypto.Cipher.AES ^
  --exclude-module Crypto.SelfTest ^
  --collect-submodules win32com ^
  --collect-all Crypto ^
  --collect-binaries pywin32_system32 ^
  "%ENTRY_SCRIPT_PATH%"
exit /b %errorlevel%

:print_command
echo   %PYTHON_LABEL% -m PyInstaller --noconfirm --clean --onefile %WINDOW_MODE_PRINT_ARG% --name "%APP_NAME%" --distpath "%DIST_DIR%" --workpath "%WORK_DIR%" --specpath "%SPEC_DIR%" --add-data "%DATA_DIR_PATH%;%DATA_DIR%" %ICON_PRINT_ARG% %LOG_LEVEL_PRINT_ARG% %VERSION_PRINT_ARG% %MANIFEST_PRINT_ARG% --hidden-import pythoncom --hidden-import pywintypes --hidden-import win32timezone --hidden-import win32com --hidden-import win32com.client --hidden-import Crypto --hidden-import Crypto.Cipher --hidden-import Crypto.Cipher.AES --exclude-module Crypto.SelfTest --collect-submodules win32com --collect-all Crypto --collect-binaries pywin32_system32 "%ENTRY_SCRIPT_PATH%"
exit /b 0

:run_sign_script
echo [INFO] Running sign script hook...
set "SIGN_SCRIPT_CALL=%SIGN_SCRIPT_COMMAND% "%OUTPUT_FILE%""
cmd /d /s /c "%SIGN_SCRIPT_CALL%"
if errorlevel 1 (
  echo [ERROR] Sign script failed for "%OUTPUT_FILE%".
  exit /b 1
)
exit /b 0

:run_smoke_test
echo [INFO] Running smoke test...
if not exist "%OUTPUT_FILE%" (
  echo [ERROR] Smoke test could not find output file: "%OUTPUT_FILE%"
  exit /b 1
)

for %%I in ("%OUTPUT_FILE%") do set "OUTPUT_SIZE=%%~zI"
echo [INFO] Output size: %OUTPUT_SIZE% bytes

call :generate_checksum
if errorlevel 1 exit /b 1

echo [INFO] SHA256 written to "%HASH_FILE%"
exit /b 0

:generate_checksum
set "HASH_FILE=%OUTPUT_FILE%.sha256"
powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 '%OUTPUT_FILE%').Hash | Set-Content -Path '%HASH_FILE%' -Encoding ASCII"
if errorlevel 1 (
  echo [ERROR] Failed to generate SHA256 checksum for "%OUTPUT_FILE%".
  exit /b 1
)
exit /b 0

:archive_output
if not defined HASH_FILE (
  call :generate_checksum
  if errorlevel 1 exit /b 1
)

set "ARCHIVE_FILE=%DIST_DIR%\%APP_NAME%_release.zip"
echo [INFO] Creating release archive: "%ARCHIVE_FILE%"
powershell -NoProfile -Command "$paths=@('%OUTPUT_FILE%','%HASH_FILE%'); if (Test-Path '%SCRIPT_DIR%\RELEASE_NOTES.md') {$paths += '%SCRIPT_DIR%\RELEASE_NOTES.md'}; if (Test-Path '%SCRIPT_DIR%\CHANGELOG.md') {$paths += '%SCRIPT_DIR%\CHANGELOG.md'}; Compress-Archive -Path $paths -DestinationPath '%ARCHIVE_FILE%' -Force"
if errorlevel 1 (
  echo [ERROR] Failed to create archive "%ARCHIVE_FILE%".
  exit /b 1
)

echo [INFO] Release archive ready: "%ARCHIVE_FILE%"
exit /b 0

:show_help
echo Usage: build.bat [clean] [dry-run] [bootstrap] [--icon file.ico] [--name output-name] [--python 3.13^|path\python.exe] [--console^|--windowed] [--debug] [--log-level level] [--smoke-test] [--version x.y.z.w] [--company name] [--product name] [--manifest asInvoker^|highest^|admin] [--requirements file.txt] [--output-dir path] [--archive] [--sign-script "command"] [--list-icons] [pause]
echo.
echo   clean          Remove the existing build directory before compiling.
echo   dry-run        Print the resolved PyInstaller command without building.
echo   bootstrap      Install dependencies from the selected requirements file.
echo   --icon         Use an .ico file from the icons folder for the EXE icon.
echo   --name         Override the EXE filename. Defaults to the selected icon name.
echo   --python       Use a specific python.exe path or a py launcher version like 3.13.
echo   --console      Build a console-visible executable for debugging.
echo   --windowed     Build without a console window. This is the default.
echo   --debug        Shortcut for --log-level DEBUG.
echo   --log-level    Pass a PyInstaller log level such as INFO, WARN, or DEBUG.
echo   --smoke-test   Print output size and generate a SHA256 checksum after build.
echo   --version      Set the Windows file/product version metadata.
echo   --company      Set CompanyName in the EXE version metadata.
echo   --product      Set ProductName and FileDescription in the EXE version metadata.
echo   --manifest     Set the requested execution level: asInvoker, highest, or admin.
echo   --requirements Use an alternate requirements file during bootstrap.
echo   --output-dir   Place the built EXE in a different directory.
echo   --archive      Create a release zip with the EXE, checksum, and release notes if present.
echo   --sign-script  Run a post-build command and append the EXE path as the final argument.
echo   --list-icons   Show available .ico files in the icons folder.
echo   pause          Pause before exit.
goto success

:show_help_error
echo Usage: build.bat [clean] [dry-run] [bootstrap] [--icon file.ico] [--name output-name] [--python 3.13^|path\python.exe] [--console^|--windowed] [--debug] [--log-level level] [--smoke-test] [--version x.y.z.w] [--company name] [--product name] [--manifest asInvoker^|highest^|admin] [--requirements file.txt] [--output-dir path] [--archive] [--sign-script "command"] [--list-icons] [pause]
echo.
echo   clean          Remove the existing build directory before compiling.
echo   dry-run        Print the resolved PyInstaller command without building.
echo   bootstrap      Install dependencies from the selected requirements file.
echo   --icon         Use an .ico file from the icons folder for the EXE icon.
echo   --name         Override the EXE filename. Defaults to the selected icon name.
echo   --python       Use a specific python.exe path or a py launcher version like 3.13.
echo   --console      Build a console-visible executable for debugging.
echo   --windowed     Build without a console window. This is the default.
echo   --debug        Shortcut for --log-level DEBUG.
echo   --log-level    Pass a PyInstaller log level such as INFO, WARN, or DEBUG.
echo   --smoke-test   Print output size and generate a SHA256 checksum after build.
echo   --version      Set the Windows file/product version metadata.
echo   --company      Set CompanyName in the EXE version metadata.
echo   --product      Set ProductName and FileDescription in the EXE version metadata.
echo   --manifest     Set the requested execution level: asInvoker, highest, or admin.
echo   --requirements Use an alternate requirements file during bootstrap.
echo   --output-dir   Place the built EXE in a different directory.
echo   --archive      Create a release zip with the EXE, checksum, and release notes if present.
echo   --sign-script  Run a post-build command and append the EXE path as the final argument.
echo   --list-icons   Show available .ico files in the icons folder.
echo   pause          Pause before exit.
set "EXIT_CODE=1"
goto end

:success
set "EXIT_CODE=0"
goto end

:fail
set "EXIT_CODE=1"
echo [ERROR] Build failed.
goto end

:end
popd >nul
if defined PAUSE_ON_EXIT pause
endlocal & exit /b %EXIT_CODE%
