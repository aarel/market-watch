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

REM Run tests and capture output
python -m unittest discover -s tests -p "test_*.py" -v > "%LOG_FILE%" 2>&1

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

REM Count results from log
findstr /R "^test_" "%LOG_FILE%" > nul 2>&1
for /f %%a in ('findstr /R "^test_" "%LOG_FILE%" ^| find /c /v ""') do set TOTAL_TESTS=%%a
for /f %%a in ('findstr /C:" ok" "%LOG_FILE%" ^| find /c /v ""') do set PASSED=%%a
for /f %%a in ('findstr /C:"FAIL" "%LOG_FILE%" ^| find /c /v ""') do set FAILED=%%a
for /f %%a in ('findstr /C:"ERROR" "%LOG_FILE%" ^| find /c /v ""') do set ERRORS=%%a

REM Write summary to file
echo Market-Watch Test Suite Summary > "%SUMMARY_FILE%"
echo Generated: %date% %time% >> "%SUMMARY_FILE%"
echo Log file: %LOG_FILE% >> "%SUMMARY_FILE%"
echo. >> "%SUMMARY_FILE%"
echo Results: >> "%SUMMARY_FILE%"
echo -------- >> "%SUMMARY_FILE%"
echo Total Tests: %TOTAL_TESTS% >> "%SUMMARY_FILE%"
echo Passed:      %PASSED% >> "%SUMMARY_FILE%"
echo Failed:      %FAILED% >> "%SUMMARY_FILE%"
echo Errors:      %ERRORS% >> "%SUMMARY_FILE%"
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
