@echo off
REM Default build is portable — delegate to build.bat
cd /d "%~dp0"
call "%~dp0build.bat" %*
