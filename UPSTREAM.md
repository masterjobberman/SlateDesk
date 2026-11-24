# Upstream provenance and attribution

SlateDesk is derived in part from [Tuhi](https://github.com/tuhiproject/tuhi), the Linux Wacom SmartPad application. Tuhi contributors developed the protocol implementation and stroke decoder reused here. This Windows application is maintained independently and is not endorsed by Tuhi or Wacom.

Upstream revision: [`aea086fa321a9e6d93ebd013eb6743c175843acf`](https://github.com/tuhiproject/tuhi/tree/aea086fa321a9e6d93ebd013eb6743c175843acf). GitHub HEAD matched this revision when inspected on 23 November 2026.

## Unmodified upstream files

| SlateDesk path | Upstream path | SHA-256 |
|---|---|---|
| `tuhi/protocol.py` | [tuhi/protocol.py](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/tuhi/protocol.py) | `aab116e2cba1bb276c16c96a45d3e663dba4a863bdf0f3b2b0b68674e9977f95` |
| `tuhi/util.py` | [tuhi/util.py](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/tuhi/util.py) | `999167472bac54bd0ac2d1ef6ef29e5196fa4f03e9cfe6a6dd2bb42f9e44dffd` |
| `tuhi/__init__.py` | [tuhi/__init__.py](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/tuhi/__init__.py) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `tests/test_messages.py` | [test/test_messages.py](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/test/test_messages.py) | `f2597a91b457a66567506a79211e0828785bd4db7a145866442f5d590992b5dc` |
| `tests/test_strokes.py` | [test/test_strokes.py](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/test/test_strokes.py) | `d827bbcf75ce2bda8cf8890335c07907e0239b9a5ade9cc56983bd03a8d08a7f` |

## New Windows implementation

`core.py` adapts the operation sequences in Tuhi `wacom.py` to Windows Bluetooth using Bleak/WinRT. `devices.py`, `progress.py`, `app.py`, `theme.py` and `exporters.py` implement Windows discovery, progress tracking, the desktop UI and exports. They are distributed under GPL-2.0-or-later. The Linux BlueZ/D-Bus/GTK/UHID layers are not bundled or claimed to work on Windows.

## License

Tuhi file headers allow GNU GPL version 2 or any later version. Its COPYING text is retained as LICENSE. The copied tests retain their original Red Hat copyright notices. The project-level GPL-2.0-or-later designation does not relicense third-party dependencies; their licenses remain in THIRD-PARTY-NOTICES.txt and the runtime notices.

This is a separate repository with explicit attribution, not a GitHub fork relationship. No claim is made that this is the entire Tuhi application ported to Windows. For Linux, use the upstream Tuhi project. For Windows issues, use this repository.
