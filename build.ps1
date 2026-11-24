$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -3.13 -m venv .venv
if ($LASTEXITCODE) { throw 'Python 3.13 x64 is required.' }
& .venv/Scripts/python -m pip install -r requirements-lock.txt
if ($LASTEXITCODE) { throw 'Dependency installation failed.' }
& .venv/Scripts/python -m pytest tests -q -k "not test_gui"
if ($LASTEXITCODE) { throw 'Tests failed.' }
& .venv/Scripts/python -m pytest tests/test_app.py::test_gui -q
if ($LASTEXITCODE) { throw 'GUI test failed.' }
& .venv/Scripts/python -m pytest tests/test_progress.py::test_gui_progress_refresh_and_library_completion -q
if ($LASTEXITCODE) { throw 'Progress GUI test failed.' }
& .venv/Scripts/python -m PyInstaller --noconfirm --clean --windowed --onedir --name SlateDesk --collect-all bleak --collect-all winrt --copy-metadata bleak --add-data 'LICENSE;.' app.py
if ($LASTEXITCODE) { throw 'Build failed.' }
Copy-Item LICENSE,README.md,UPSTREAM.md,CHANGELOG.md,THIRD-PARTY-NOTICES.txt,PYTHON-LICENSE.txt,TK-LICENSE.txt -Destination dist/SlateDesk
Copy-Item docs -Destination dist/SlateDesk/docs -Recurse -Force
Write-Host 'Built dist/SlateDesk/SlateDesk.exe. Keep the entire folder together.'
