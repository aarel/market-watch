@echo off
REM Test runner script with logging for Windows
REM Usage: run_tests.bat

REM Create test_results directory if it doesn't exist
if not exist test_results mkdir test_results

REM Generate timestamp for log file
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%
set LOG_FILE=test_results\test_run_%TIMESTAMP%.log
set SUMMARY_FILE=test_results\latest_summary.txt

echo Running Market-Watch Test Suite...
echo Log file: %LOG_FILE%
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

echo ========================================== > "%LOG_FILE%"
echo Test Run: %DATE% %TIME% >> "%LOG_FILE%"
echo Log file: %LOG_FILE% >> "%LOG_FILE%"
echo Summary file: %SUMMARY_FILE% >> "%LOG_FILE%"
echo Command: python -m pytest tests %PYTEST_ARGS% >> "%LOG_FILE%"
echo Tip: use --verbose for per-test output or --quiet for dots only. >> "%LOG_FILE%"
echo ========================================== >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

REM Run tests and capture output (pytest runs unittest tests too)
python -m pytest tests %PYTEST_ARGS% >> "%LOG_FILE%" 2>&1

REM Capture exit code
set TEST_EXIT_CODE=%ERRORLEVEL%

REM Display output
type "%LOG_FILE%"

REM Generate summary
echo.
echo ==========================================
echo   Test Summary
echo ==========================================
echo.

REM Capture pytest summary line (last matching line)
set SUMMARY_LINE=
for /f "usebackq delims=" %%a in (`"type "%LOG_FILE%" ^| findstr /R /C:\"passed\" /C:\"failed\" /C:\"error\" /C:\"skipped\" /C:\"xfailed\" /C:\"xpassed\""` ) do set SUMMARY_LINE=%%a

REM Write summary to file
echo Market-Watch Test Suite Summary > "%SUMMARY_FILE%"
echo Generated: %date% %time% >> "%SUMMARY_FILE%"
echo Log file: %LOG_FILE% >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo Results: >> "%SUMMARY_FILE%"
echo -------- >> "%SUMMARY_FILE%"
if not "%SUMMARY_LINE%"=="" (
    echo %SUMMARY_LINE% >> "%SUMMARY_FILE%"
) else (
    echo (No pytest summary line found) >> "%SUMMARY_FILE%"
)
echo. >> "%SUMMARY_FILE%"
echo Exit Code: %TEST_EXIT_CODE% >> "%SUMMARY_FILE%"

REM Display summary
type "%SUMMARY_FILE%"
echo.

if %TEST_EXIT_CODE% EQU 0 (
    echo [OK] All tests passed!
) else (
    echo [FAILED] Some tests failed
    echo.
    echo View full log: %LOG_FILE%
    echo To see failures only:
    echo   findstr /C:"FAIL:" %LOG_FILE%
    echo   findstr /C:"ERROR:" %LOG_FILE%
)

echo.
echo Test logs saved to: test_results\

exit /b %TEST_EXIT_CODE%
