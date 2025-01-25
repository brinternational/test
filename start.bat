@echo off
echo Starting Bitcoin Education App Setup...

REM Set PyOpenCL compiler output
set PYOPENCL_COMPILER_OUTPUT=1

REM Remove old directory if it exists
if exist test (
    echo Removing old test directory...
    rmdir /s /q test
)

REM Clone the repository
echo Cloning repository...
git clone https://github.com/brinternational/test.git
if errorlevel 1 (
    echo Failed to clone repository
    pause
    exit /b 1
)

REM Change to the project directory
cd test

REM Install required package
echo Installing required packages...
pip install python-bitcoinrpc
if errorlevel 1 (
    echo Failed to install packages
    pause
    exit /b 1
)

REM Run the application
echo Starting application...
python main.py
if errorlevel 1 (
    echo Failed to start application
    pause
    exit /b 1
)

pause