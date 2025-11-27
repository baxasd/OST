import argparse
from src.run import run_system


def menu():
    """Interactive CLI menu."""
    while True:
        print("\n===== 3D Pose Tracking Menu =====")
        print("1. Run normally (no smoothing)")
        print("2. Run with Kalman filter")
        print("3. Exit")

        choice = input("Select an option: ").strip()

        if choice == "1":
            return run_system(use_kalman=False, model=1)

        elif choice == "2":
            return run_system(use_kalman=True, model=1)

        elif choice == "3":
            print("Goodbye.")
            return

        else:
            print("Invalid option. Try again.")

def main():
    parser = argparse.ArgumentParser(
        description="3D Pose Tracking with Intel RealSense + MediaPipe"
    )
    parser.add_argument("--kalman", action="store_true")
    parser.add_argument("--model", type=int, choices=[0, 1, 2], default=1)

    args = parser.parse_args()

    # If the user gave no arguments → show menu
    no_args = not (args.kalman)

    if no_args:
        return menu()

    # Otherwise run normally
    run_system(
        use_kalman=args.use_kalman,
        model=args.model
    )
