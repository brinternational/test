@echo off
echo Starting Bitcoin Education App Setup...

REM Set PyOpenCL compiler output
set PYOPENCL_COMPILER_OUTPUT=1
set PYOPENCL_CTX=0

REM Set OpenCL paths for cache
set PYOPENCL_NO_CACHE=1
set ADRENO_CACHE_PATH=%LOCALAPPDATA%\AdrenalineCache

REM Set Python Scripts path
set PATH=%PATH%;C:\Users\bmorr\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts

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

REM Install required packages
echo Installing required packages...
pip install python-bitcoinrpc flask numpy psutil pyopencl
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