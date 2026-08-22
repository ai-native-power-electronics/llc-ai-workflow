@echo off
setlocal EnableExtensions EnableDelayedExpansion
pushd "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -B -m llc_tool doctor >nul
  if errorlevel 1 (
    echo Environment check: FAIL
    echo Python 3.10 or newer is required.
    pause
    popd
    exit /b 2
  )
  echo Environment check: PASS
  echo.
  py -3 -B run_demo.py --human --open-report %*
  set "LLC_DEMO_EXIT=!errorlevel!"
  if not !LLC_DEMO_EXIT!==0 (
    echo.
    echo Demo failed. Review the error above.
    pause
  )
  popd
  exit /b !LLC_DEMO_EXIT!
)

where python >nul 2>nul
if %errorlevel%==0 (
  python -B -m llc_tool doctor >nul
  if errorlevel 1 (
    echo Environment check: FAIL
    echo Python 3.10 or newer is required.
    pause
    popd
    exit /b 2
  )
  echo Environment check: PASS
  echo.
  python -B run_demo.py --human --open-report %*
  set "LLC_DEMO_EXIT=!errorlevel!"
  if not !LLC_DEMO_EXIT!==0 (
    echo.
    echo Demo failed. Review the error above.
    pause
  )
  popd
  exit /b !LLC_DEMO_EXIT!
)

echo Environment check: FAIL
echo Python was not found. Install Python 3.10 or newer, then run this file again.
pause
popd
exit /b 2
