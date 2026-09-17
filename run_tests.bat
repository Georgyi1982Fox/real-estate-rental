@echo off
echo Running code quality checks...

echo.
echo Checking code style with ruff...
ruff check src tests

if %ERRORLEVEL% NEQ 0 (
    echo Ruff check failed!
    exit /b 1
)

echo.
echo Checking types with mypy...
mypy src --config-file mypy.ini

if %ERRORLEVEL% NEQ 0 (
    echo MyPy check failed!
    exit /b 1
)

echo.
echo Running tests with pytest...
pytest tests -v

if %ERRORLEVEL% NEQ 0 (
    echo Tests failed!
    exit /b 1
)

echo.
echo All checks passed successfully!