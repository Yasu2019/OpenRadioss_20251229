@echo off
echo Running OpenRadioss Simulation...
echo Input: ASSY_OpenRadioss_PM7T1C_20260102_0000.rad
echo User Path: D:\OpenRadioss

set "RAD_DIR=D:\OpenRadioss"

:: Add common exec paths
set "PATH=%RAD_DIR%\exec;%RAD_DIR%\bin;%RAD_DIR%;%PATH%"

:: Try generic commands
echo Trying global PATH...
OpenRadioss -i ASSY_OpenRadioss_PM7T1C_20260102_0000.rad -np 4
if %errorlevel% equ 0 goto end

echo Trying specific executables in %RAD_DIR%...

:: Method 1: exec/starter_win64.exe (Common)
if exist "%RAD_DIR%\exec\starter_win64.exe" (
    "%RAD_DIR%\exec\starter_win64.exe" -i ASSY_OpenRadioss_PM7T1C_20260102_0000.rad
    if %errorlevel% equ 0 (
        echo Starter finished. Running Engine...
        "%RAD_DIR%\exec\engine_win64.exe" -i ASSY_OpenRadioss_PM7T1C_20260102_0001.rad -nt 4
        goto end
    )
)

:: Method 2: win64_starter.exe (Altair naming)
if exist "%RAD_DIR%\exec\win64_starter.exe" (
    "%RAD_DIR%\exec\win64_starter.exe" -i ASSY_OpenRadioss_PM7T1C_20260102_0000.rad
    if %errorlevel% equ 0 (
        echo Starter finished. Running Engine...
        "%RAD_DIR%\exec\win64_engine.exe" -i ASSY_OpenRadioss_PM7T1C_20260102_0001.rad -nt 4
        goto end
    )
)

:: Method 3: MPI version often has long name
if exist "%RAD_DIR%\exec\starter_win64_sp_dp_ompi.exe" (
    "%RAD_DIR%\exec\starter_win64_sp_dp_ompi.exe" -i ASSY_OpenRadioss_PM7T1C_20260102_0000.rad
    if %errorlevel% equ 0 (
        echo Starter finished. Running Engine...
        "%RAD_DIR%\exec\engine_win64_sp_dp_ompi.exe" -i ASSY_OpenRadioss_PM7T1C_20260102_0001.rad -nt 4
        goto end
    )
)


echo.
echo Error: Could not find OpenRadioss executables in D:\OpenRadioss.
echo Checked: exec\starter_win64.exe, exec\win64_starter.exe
pause
exit /b 1

:end
echo Simulation commands executed.
pause
