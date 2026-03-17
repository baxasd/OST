import zmq
import streamlit_authenticator as stauth

server_public, server_secret = zmq.curve_keypair()
client_public, client_secret = zmq.curve_keypair()
studio_pass = input("Enter Password for OSTStudio: ")

print("\n--- Paste this into your settings.ini ---\n")
print("-----------------------------------------")
print("[Security]")
print(f"server_public = {server_public.decode('ascii')}")
print(f"server_secret = {server_secret.decode('ascii')}")
print(f"client_public = {client_public.decode('ascii')}")
print(f"client_secret = {client_secret.decode('ascii')}")
print(f"studio_password = {studio_pass}")
print("-----------------------------------------")