# Upstream provenance and attribution

SlateDesk is derived in part from [Tuhi](https://github.com/tuhiproject/tuhi), the Linux Wacom SmartPad application. Tuhi contributors developed the protocol implementation and stroke decoder reused here. This Windows application is maintained independently and is not endorsed by Tuhi or Wacom.

Upstream revision: [`aea086fa321a9e6d93ebd013eb6743c175843acf`](https://github.com/tuhiproject/tuhi/tree/aea086fa321a9e6d93ebd013eb6743c175843acf). GitHub HEAD matched this revision when inspected on 23 November 2026.

Checksums use the exact canonical Git blobs from the upstream revision (LF line endings), independent of Windows checkout settings.

## Unmodified upstream files

| SlateDesk path | Upstream path | SHA-256 |
|---|---|---|
| `tuhi/protocol.py` | [tuhi/protocol.py](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/tuhi/protocol.py) | `cf659469231960e5249984998d03561883c89d3bfd5ce912629e3032b76105db` |
| `tuhi/util.py` | [tuhi/util.py](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/tuhi/util.py) | `dfef3b526b51ad20fdfcd70b1281750e7c6e8547c0e95419581f14086c64449f` |
| `tuhi/__init__.py` | [tuhi/__init__.py](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/tuhi/__init__.py) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `tests/test_messages.py` | [test/test_messages.py](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/test/test_messages.py) | `c4e0f2cf4d6a9fb4f75185a0cf29e2761e5af766670c6631f7b2412aff4cc01a` |
| `tests/test_strokes.py` | [test/test_strokes.py](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/test/test_strokes.py) | `e1292fe1d5e36eef27c9c6700c4209b907445a185e39ad1009158d529bf205fe` |

## New Windows implementation

`core.py` adapts the operation sequences in Tuhi `wacom.py` to Windows Bluetooth using Bleak/WinRT. `devices.py`, `progress.py`, `app.py`, `theme.py` and `exporters.py` implement Windows discovery, progress tracking, the desktop UI and exports. They are distributed under GPL-2.0-or-later. The Linux BlueZ/D-Bus/GTK/UHID layers are not bundled or claimed to work on Windows.

## License

Tuhi file headers allow GNU GPL version 2 or any later version. Its COPYING text is retained as LICENSE. The copied tests retain their original Red Hat copyright notices. The project-level GPL-2.0-or-later designation does not relicense third-party dependencies; their licenses remain in THIRD-PARTY-NOTICES.txt and the runtime notices.

This is a separate repository with explicit attribution, not a GitHub fork relationship. No claim is made that this is the entire Tuhi application ported to Windows. For Linux, use the upstream Tuhi project. For Windows issues, use this repository.
