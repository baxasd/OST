import zmq

server_public, server_secret = zmq.curve_keypair()
client_public, client_secret = zmq.curve_keypair()

print("\n--- Paste this into your settings.ini ---")
print("[Security]")
print(f"server_public = {server_public.decode('ascii')}")
print(f"server_secret = {server_secret.decode('ascii')}")
print(f"client_public = {client_public.decode('ascii')}")
print(f"client_secret = {client_secret.decode('ascii')}")
print("-----------------------------------------")