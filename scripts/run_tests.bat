@echo off
REM Test runner script with logging for Windows
REM Usage: run_tests.bat

REM Generate timestamp for log file
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%-%datetime:~8,6%
set RUN_DIR=test_results\full_suite\%TIMESTAMP%
if not exist "%RUN_DIR%" mkdir "%RUN_DIR%"
set STDOUT_FILE=%RUN_DIR%\pytest_stdout.log
set STDERR_FILE=%RUN_DIR%\pytest_stderr.log
set SUMMARY_JSON=%RUN_DIR%\summary.json
set METADATA_JSON=%RUN_DIR%\metadata.json

echo Running Market-Watch Test Suite...
echo Run dir: %RUN_DIR%
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [WARNING] Virtual environment not found
)

echo.
echo ==========================================
echo   Running Tests
echo ==========================================
echo.

REM Build pytest args (allow overrides)
set PYTEST_ARGS=
set HAS_VERBOSITY=0

:parse_args
if "%~1"=="" goto args_done
if "%~1"=="--verbose" (
    set PYTEST_ARGS=%PYTEST_ARGS% -vv
    set HAS_VERBOSITY=1
    shift
    goto parse_args
)
if "%~1"=="--quiet" (
    set PYTEST_ARGS=%PYTEST_ARGS% -q
    set HAS_VERBOSITY=1
    shift
    goto parse_args
)
set PYTEST_ARGS=%PYTEST_ARGS% %1
if "%~1"=="-q" set HAS_VERBOSITY=1
if "%~1"=="-v" set HAS_VERBOSITY=1
if "%~1"=="-vv" set HAS_VERBOSITY=1
shift
goto parse_args

:args_done
if "%HAS_VERBOSITY%"=="0" set PYTEST_ARGS=%PYTEST_ARGS% -q

echo ==========================================
echo Test Run: %DATE% %TIME%
echo Run dir: %RUN_DIR%
echo Stdout: %STDOUT_FILE%
echo Stderr: %STDERR_FILE%
echo Command: python -m pytest tests %PYTEST_ARGS%
echo Tip: use --verbose for per-test output or --quiet for dots only.
echo ==========================================
echo.

REM Run tests and capture output (pytest runs unittest tests too)
python -m pytest tests %PYTEST_ARGS% > "%STDOUT_FILE%" 2> "%STDERR_FILE%"

REM Capture exit code
set TEST_EXIT_CODE=%ERRORLEVEL%

REM Display output
type "%STDOUT_FILE%"
if exist "%STDERR_FILE%" type "%STDERR_FILE%"

REM Generate summary
echo.
echo ==========================================
echo   Test Summary
echo ==========================================
echo.

REM Build combined log for summary parsing
set COMBINED_LOG=%RUN_DIR%\combined.log
copy /b "%STDOUT_FILE%"+"%STDERR_FILE%" "%COMBINED_LOG%" >nul

REM Capture pytest summary line (last matching line)
set SUMMARY_LINE=
for /f "usebackq delims=" %%a in (`"type "%COMBINED_LOG%" ^| findstr /R /C:\"passed\" /C:\"failed\" /C:\"error\" /C:\"skipped\" /C:\"xfailed\" /C:\"xpassed\""` ) do set SUMMARY_LINE=%%a

REM Write summary and metadata JSON
echo { > "%SUMMARY_JSON%"
echo   "suite_name": "full_suite", >> "%SUMMARY_JSON%"
echo   "run_id": "%TIMESTAMP%", >> "%SUMMARY_JSON%"
echo   "generated_at": "%date% %time%", >> "%SUMMARY_JSON%"
echo   "command": "python -m pytest tests %PYTEST_ARGS%", >> "%SUMMARY_JSON%"
echo   "pytest_summary_line": "%SUMMARY_LINE%", >> "%SUMMARY_JSON%"
echo   "exit_code": %TEST_EXIT_CODE%, >> "%SUMMARY_JSON%"
echo   "artifacts": { >> "%SUMMARY_JSON%"
echo     "pytest_stdout": "pytest_stdout.log", >> "%SUMMARY_JSON%"
echo     "pytest_stderr": "pytest_stderr.log", >> "%SUMMARY_JSON%"
echo     "summary": "summary.json", >> "%SUMMARY_JSON%"
echo     "metadata": "metadata.json" >> "%SUMMARY_JSON%"
echo   } >> "%SUMMARY_JSON%"
echo } >> "%SUMMARY_JSON%"

echo { > "%METADATA_JSON%"
echo   "suite_name": "full_suite", >> "%METADATA_JSON%"
echo   "run_id": "%TIMESTAMP%", >> "%METADATA_JSON%"
echo   "generated_at": "%date% %time%", >> "%METADATA_JSON%"
echo   "run_dir": "%RUN_DIR%", >> "%METADATA_JSON%"
echo   "policy": "forward_only_canonical_artifact_schema_v1" >> "%METADATA_JSON%"
echo } >> "%METADATA_JSON%"

REM Display summary
type "%SUMMARY_JSON%"
echo.

if %TEST_EXIT_CODE% EQU 0 (
    echo [OK] All tests passed!
) else (
    echo [FAILED] Some tests failed
    echo.
    echo View stdout log: %STDOUT_FILE%
    echo View stderr log: %STDERR_FILE%
    echo To see failures only:
    echo   findstr /C:"FAIL:" %STDOUT_FILE%
    echo   findstr /C:"ERROR:" %STDOUT_FILE%
)

echo.
echo Test artifacts saved to: %RUN_DIR%

exit /b %TEST_EXIT_CODE%
