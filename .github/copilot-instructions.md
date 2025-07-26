# Copilot Instructions for DetectorBox

## Overview
DetectorBox is a modular Python system for quality control in beverage production lines, using computer vision and protocol abstraction for industrial device communication.

## Architecture
- **core/**: Contains protocol implementations (e.g., `SerialProtocol.py`, `ModbusTCPProtocol.py`) and device logic (e.g., `camera.py`).
- **models/**: Contains abstract base classes and data models (e.g., `camera_model.py`, `box_model.py`).
- **main.py**: Entry point for the application.

### Protocol Abstraction
- Protocols (Serial, Modbus/RTU, Modbus/TCP) are implemented as classes, typically inheriting from a shared abstract base (see `core/`).
- New protocols should follow the interface pattern established in `core/` and `models/`.
- Devices (e.g., `Camera`) receive protocol objects as parameters, enabling flexible integration.

### Computer Vision
- Uses OpenCV (`cv2`) for image capture and processing.
- `Camera` classes operate on `cv2.VideoCapture` objects and return `numpy.ndarray` images.

## Developer Workflows
- **Install dependencies:** `pip install -r requirements.txt`
- **Run the application:** `python main.py`
- **Add a new protocol:** Implement a class in `core/` following the abstract base pattern, then integrate with device classes as needed.

## Project Conventions
- Abstract base classes are defined in `models/` and use Python generics for type safety.
- Device and protocol classes are separated for modularity and extensibility.
- Use type hints throughout for clarity.
- Prefer composition (injecting protocol objects) over inheritance for device/protocol integration.

## Integration Points
- External dependencies: OpenCV (`cv2`), NumPy
- Protocol classes may interface with hardware or network devices; mock or stub as needed for tests.

## Example Pattern
```python
from core.SerialProtocol import SerialProtocol
from models.camera_model import Camera

serial = SerialProtocol(port='COM1', baudrate=9600)
camera = Camera(name='Cam1', id=1, capture_device=serial)
```

## Key Files
- `core/camera.py`, `core/SerialProtocol.py`, `core/ModbusTCPProtocol.py`
- `models/camera_model.py`, `models/box_model.py`
- `main.py`

---
For questions about architecture or patterns, review the README.md or the abstract base classes in `models/`.
