@echo off
rem ---------------------------------------------------------------------------
rem AgentCubicle 一键构建脚本（Windows）
rem AgentCubicle one-shot build script (Windows)
rem
rem 用法 / Usage:
rem   scripts\build.bat          # 构建 sdist + wheel
rem   scripts\build.bat clean    # 清理构建产物
rem   scripts\build.bat test     # 运行测试
rem ---------------------------------------------------------------------------
setlocal enabledelayedexpansion

pushd "%~dp0.."

set PYTHON_BIN=python
where py >nul 2>nul
if %ERRORLEVEL%==0 set PYTHON_BIN=py

if "%1"=="clean" goto :clean
if "%1"=="test" goto :test

echo [build] using interpreter:
%PYTHON_BIN% --version

if exist dist rmdir /s /q dist

echo [build] running tests before packaging...
%PYTHON_BIN% tests\run_tests.py
if errorlevel 1 (
  echo [build] tests failed, aborting.
  popd
  exit /b 1
)

echo [build] building sdist + wheel...
%PYTHON_BIN% -m build --sdist --wheel
if errorlevel 1 (
  echo [build] PEP 517 build unavailable, falling back to setuptools...
  %PYTHON_BIN% setup.py sdist bdist_wheel
)

echo [build] artifacts:
dir /b dist 2>nul
echo [build] build finished.
popd
exit /b 0

:clean
echo [build] cleaning build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
echo [build] done.
popd
exit /b 0

:test
echo [build] running the standard-library test suite...
%PYTHON_BIN% tests\run_tests.py
popd
exit /b %ERRORLEVEL%
