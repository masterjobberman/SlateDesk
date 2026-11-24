# Tuhi feature comparison

SlateDesk is a Windows app based on Tuhi's protocol, not a complete port of the Linux application. Audit source: [Tuhi revision aea086fa](https://github.com/tuhiproject/tuhi/tree/aea086fa321a9e6d93ebd013eb6743c175843acf).

| Capability | Tuhi | SlateDesk 1.6 |
|---|---|---|
| Supported platform | Linux GTK/BlueZ/D-Bus | Windows 11 x64, native desktop widgets and WinRT Bluetooth |
| Devices | README lists Spark, Slate and Intuos Pro Paper as tested | Bamboo Slate only |
| Persistent registration | Yes | Yes; existing saved identities and Windows paired-device listing |
| Stored ink download | Oldest-first, delete to advance | Same protocol, with explicit Get all/oldest/newest and deletion checkbox |
| Automatic listening for new drawings | Yes | No; manual transfers |
| Live pen input | Linux UHID and live-mode tools | No Windows pen driver or live drawing mode |
| Preview | Gallery, zoom and rotation | Large fit-to-window portrait preview; no manual zoom or rotation |
| Page orientation | Four orientations and rotation controls | Automatic clockwise landscape-to-portrait conversion for preview/export |
| Local page deletion/undo | Yes | No app-level delete/undo |
| Export | SVG and PNG | SVG, PNG and vector PDF; approximate pressure width |
| Device state | Battery, connection, listening | Connection and last-read battery |
| Transfer feedback | Activity and logging | Bytes, speed, elapsed time, page counts, stages and packet-idle warning |
| Service/command-line API | D-Bus and Kete | No equivalent service API |

Owning sources: [drawing UI](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/tuhi/gui/drawing.py), [gallery/listening](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/tuhi/gui/drawingperspective.py), [service API](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/DBusInterface.md), [export](https://github.com/tuhiproject/tuhi/blob/aea086fa321a9e6d93ebd013eb6743c175843acf/tuhi/export.py).
