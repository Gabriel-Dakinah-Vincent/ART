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
set "ICON_NAME="
set "ICON_PATH="
set "ICON_AUTO_SELECTED="
set "APP_NAME_OVERRIDE="
set "PYTHON_LABEL="
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

:args_done
if defined LIST_ICONS goto list_icons

if exist "%VENV_PYTHON%" (
  set "PYTHON_LABEL=%VENV_PYTHON%"
) else (
  set "PYTHON_LABEL=py -3.13"
)

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

if defined DRY_RUN (
  echo [DRY-RUN] Resolved build command:
  call :print_command
  goto success
)

if not exist "%VENV_PYTHON%" (
  py -3.13 -c "import sys" >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python 3.13 was not found.
    echo         Create build_env or install Python 3.13 and ensure the py launcher is available.
    goto fail
  )
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

call :prepare_icon_arg
if errorlevel 1 goto fail

echo [INFO] Starting PyInstaller build...
call :run_build
if errorlevel 1 goto fail

if not exist "%OUTPUT_FILE%" (
  echo [ERROR] PyInstaller completed without producing "%OUTPUT_FILE%".
  goto fail
)

echo [INFO] Build complete. Output: "%OUTPUT_FILE%"
goto success

:check_pyinstaller
if exist "%VENV_PYTHON%" (
  "%VENV_PYTHON%" -m PyInstaller --version >nul 2>&1
) else (
  py -3.13 -m PyInstaller --version >nul 2>&1
)

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

if exist "%VENV_PYTHON%" (
  "%VENV_PYTHON%" -m pip install -r "%REQUIREMENTS_FILE%"
) else (
  py -3.13 -m pip install -r "%REQUIREMENTS_FILE%"
)

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

if exist "%APP_NAME%.spec" (
  echo [INFO] Removing stale spec file: "%APP_NAME%.spec"
  del /f /q "%APP_NAME%.spec" >nul 2>&1
)

exit /b 0

:run_build
if exist "%VENV_PYTHON%" (
  "%VENV_PYTHON%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --noconsole ^
    --name "%APP_NAME%" ^
    --distpath "%DIST_DIR%" ^
    --workpath "%WORK_DIR%" ^
    --specpath "%SPEC_DIR%" ^
    --add-data "%DATA_DIR_PATH%;%DATA_DIR%" ^
    %ICON_CLI_ARG% ^
    --hidden-import pythoncom ^
    --hidden-import pywintypes ^
    --hidden-import win32timezone ^
    --hidden-import win32com ^
    --hidden-import win32com.client ^
    --collect-submodules win32com ^
    --collect-binaries pywin32_system32 ^
    "%ENTRY_SCRIPT_PATH%"
) else (
  py -3.13 -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --noconsole ^
    --name "%APP_NAME%" ^
    --distpath "%DIST_DIR%" ^
    --workpath "%WORK_DIR%" ^
    --specpath "%SPEC_DIR%" ^
    --add-data "%DATA_DIR_PATH%;%DATA_DIR%" ^
    %ICON_CLI_ARG% ^
    --hidden-import pythoncom ^
    --hidden-import pywintypes ^
    --hidden-import win32timezone ^
    --hidden-import win32com ^
    --hidden-import win32com.client ^
    --collect-submodules win32com ^
    --collect-binaries pywin32_system32 ^
    "%ENTRY_SCRIPT_PATH%"
)
exit /b %errorlevel%

:print_command
call :prepare_icon_arg
if exist "%VENV_PYTHON%" (
  echo   "%VENV_PYTHON%" -m PyInstaller --noconfirm --clean --onefile --noconsole --name "%APP_NAME%" --distpath "%DIST_DIR%" --workpath "%WORK_DIR%" --specpath "%SPEC_DIR%" --add-data "%DATA_DIR_PATH%;%DATA_DIR%" %ICON_PRINT_ARG% --hidden-import pythoncom --hidden-import pywintypes --hidden-import win32timezone --hidden-import win32com --hidden-import win32com.client --collect-submodules win32com --collect-binaries pywin32_system32 "%ENTRY_SCRIPT_PATH%"
) else (
  echo   py -3.13 -m PyInstaller --noconfirm --clean --onefile --noconsole --name "%APP_NAME%" --distpath "%DIST_DIR%" --workpath "%WORK_DIR%" --specpath "%SPEC_DIR%" --add-data "%DATA_DIR_PATH%;%DATA_DIR%" %ICON_PRINT_ARG% --hidden-import pythoncom --hidden-import pywintypes --hidden-import win32timezone --hidden-import win32com --hidden-import win32com.client --collect-submodules win32com --collect-binaries pywin32_system32 "%ENTRY_SCRIPT_PATH%"
)
exit /b 0

:prepare_icon_arg
set "ICON_CLI_ARG="
set "ICON_PRINT_ARG="
if defined ICON_PATH (
  set "ICON_CLI_ARG=--icon "%ICON_PATH%""
  set "ICON_PRINT_ARG=--icon "%ICON_PATH%""
)
exit /b 0

:show_help
echo Usage: build.bat [clean] [dry-run] [bootstrap] [--icon file.ico] [--name output-name] [--list-icons] [pause]
echo.
echo   clean      Remove the existing build directory before compiling.
echo   dry-run    Print the resolved PyInstaller command without building.
echo   bootstrap  Install dependencies from requirements.txt if PyInstaller is missing.
echo   --icon     Use an .ico file from the icons folder for the EXE icon.
echo   --name     Override the EXE filename. Defaults to the selected icon name.
echo   --list-icons  Show available .ico files in the icons folder.
echo   pause      Pause before exit.
goto success

:show_help_error
echo Usage: build.bat [clean] [dry-run] [bootstrap] [--icon file.ico] [--name output-name] [--list-icons] [pause]
echo.
echo   clean      Remove the existing build directory before compiling.
echo   dry-run    Print the resolved PyInstaller command without building.
echo   bootstrap  Install dependencies from requirements.txt if PyInstaller is missing.
echo   --icon     Use an .ico file from the icons folder for the EXE icon.
echo   --name     Override the EXE filename. Defaults to the selected icon name.
echo   --list-icons  Show available .ico files in the icons folder.
echo   pause      Pause before exit.
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
