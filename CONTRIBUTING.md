# Contributing

Open an issue describing the problem before undertaking a substantial feature change. Pull requests should explain the user-visible behaviour, validation and any hardware limitations.

Use Python 3.13 x64 on Windows and install `requirements-lock.txt` in a virtual environment. Run tests in these groups because multiple Tk interpreter initialisations in one process have shown intermittent failures:

```powershell
python -m pytest tests -q -k "not test_gui"
python -m pytest tests/test_app.py::test_gui -q
python -m pytest tests/test_progress.py::test_gui_progress_refresh_and_library_completion -q
```

Do not weaken the CRC, durable backup, read-back verification or save-before-delete safeguards. Any transfer change needs simulated failure/cancellation coverage and an explicit statement of physical-device testing. Never add an automatic erase-all or delete-before-save path.

Keep user drawings, registration tokens, Bluetooth addresses, logs and credentials out of commits. Screenshots and test fixtures should use synthetic data. Preserve Tuhi's original notices and document changes to vendored files in UPSTREAM.md. Contributions are made under GPL-2.0-or-later.
