# Validation and known limits

Local release validation on Windows 11 x64, Python 3.13:

- 137 non-GUI tests passed; one upstream recording-dependent test skipped.
- Two GUI tests passed in separate processes: sample rendering and progress/library behaviour.
- Portable EXE smoke test: GUI, portrait sample preview, SVG/PNG/PDF export and Windows Bluetooth scanning passed.
- The Pages and Transfer layouts were visually inspected using synthetic ink.
- The six combinations of oldest/all/newest and deletion on/off were simulated with a multi-page device queue.
- Tests cover CRC rejection, storage failure, cancellation, missing replies, disconnects, notification framing, bytes/rate/idle calculations and save-before-delete ordering.

The user reported that prior builds worked with their Slate. A stored raw/decoded page pair and a matching Windows-paired Slate were observed during development. No new destructive hardware test was performed for the final selection controls. These observations do not prove every device/firmware combination or recovery scenario.

GUI tests run in separate processes because repeated Tk initialisation in one process showed intermittent local failures. Automated release checks simulate Bluetooth replies; they are not a substitute for testing a physical Slate. The GitHub workflow's result should be checked separately; local success does not establish that hosted CI passed.

Outstanding: extensive physical tests across Slate sizes/firmware/adapters; sleep/reconnect and long transfers; real multi-monitor DPI transitions; printing/physical-size accuracy; ARM64 and other Windows versions. Binaries are unsigned. No byte-for-byte reproducibility claim is made.

Start with Get oldest and deletion unchecked. Keep the device copy until you have reviewed the downloaded drawing and exported files. Maintain a separate backup of the local library.
