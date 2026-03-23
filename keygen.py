import zmq
import configparser
import os

def run():
    # Generate ZeroMQ Curve keys
    server_public, server_secret = zmq.curve_keypair()
    client_public, client_secret = zmq.curve_keypair()

    # Ask password for Studio
    print("\n*******************************")
    print("*** OST SUITE SETUP & KEYGEN ***")
    print("*******************************")
    studio_pass = input("Enter a new password for OST Studio: ")

    config = configparser.ConfigParser()
    settings_file = 'settings.ini'

    # 1. Define all default settings
    defaults = {
        'Hardware': {'radar_cfg_file': 'core/radar/config.cfg', 'cli_port': 'auto', 'data_port': 'auto'},
        'Network': {'zmq_radar_port': '5555', 'zmq_camera_port': '5556'},
        'Recording': {'chunk_size': '50'},
        'Viewer': {'default_ip': '127.0.0.1', 'max_range_m': '5.0', 'cmap': 'inferno', 'low_pct': '40.0', 'high_pct': '99.5', 'smooth_grid_size': '250'},
        'Camera': {'width': '640', 'height': '480', 'fps': '30', 'model_complexity': '1', 'jpeg_quality': '80', 'auto_exposure': 'False', 'exposure': '450'}
    }

    # 2. Load defaults into the parser
    config.read_dict(defaults)

    # 3. Read existing file to preserve any custom tweaks the user made
    if os.path.exists(settings_file):
        config.read(settings_file)

    # 4. Force update the Security section with new keys
    if 'Security' not in config:
        config.add_section('Security')
        
    config['Security']['server_public'] = server_public.decode('ascii')
    config['Security']['server_secret'] = server_secret.decode('ascii')
    config['Security']['client_public'] = client_public.decode('ascii')
    config['Security']['client_secret'] = client_secret.decode('ascii')
    config['Security']['studio_password'] = studio_pass

    # 5. Write the clean configuration
    with open(settings_file, 'w') as f:
        config.write(f)

    print(f"\n[OK] Clean configuration and keys successfully generated at: {settings_file}")

# Allow standalone execution
if __name__ == "__main__":
    run()
    input("\nPress Enter to exit...")