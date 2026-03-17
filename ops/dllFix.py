# hook_fix.py
import sys

# Force MediaPipe to load internal libraries immediately
# This locks the correct C++ runtime/protobuf versions before PyQt6 loads
try:
    import mediapipe
    from mediapipe.python import _framework_bindings
    print("HOOK: MediaPipe loaded successfully.")
except ImportError as e:
    print(f"HOOK: Failed to load MediaPipe: {e}")