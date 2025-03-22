@echo off

REM Check if the --clear flag is provided
if "%1"=="--clear" (
    echo Clearing CANVAS_API_KEY and CANVAS_COURSE_URL environment variables...
    setx CANVAS_API_KEY ""
    setx CANVAS_COURSE_URL ""
    echo Variables cleared.  You may need to restart your terminal/command prompt.
    exit /b 0
)

:get_api_key
set /p "api_key=Enter your Canvas API key: "
if "%api_key%"=="" (
    echo API key cannot be empty.
    goto get_api_key
)

:get_course_url
set /p "course_url=Enter your Canvas course URL (e.g., https://canvas.example.com/courses/12345): "
if "%course_url%"=="" (
    echo Course URL cannot be empty.
    goto get_course_url
)

echo Setting environment variables...

REM Use setx to set the variables *persistently*
setx CANVAS_API_KEY "%api_key%"
setx CANVAS_COURSE_URL "%course_url%"

echo Environment variables set successfully.
echo You may need to restart your terminal or command prompt for the changes to take effect.

exit /b 0