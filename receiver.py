import socket
from datetime import datetime
from pathlib import Path


PORT = 5005
OUTFILE = Path("/Users/seifabdelazim/Dropbox/Mac/Desktop/atmosleep-dashboard/data/live/live.csv")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", PORT))  # listen on all network interfaces


print(f"Listening for UDP on port {PORT}...")
print(f"Saving to: {OUTFILE}")
print("Press Ctrl+C to stop.\n")


with open(OUTFILE, "a", buffering=1, encoding="utf-8") as f:
    while True:
        data, addr = sock.recvfrom(65535)
        line = data.decode("utf-8", errors="replace").strip()


        # Print for debugging
        print(f"{datetime.now().strftime('%H:%M:%S')}  {addr[0]}:{addr[1]}  {line}")


        # Append to CSV
        f.write(line + "\n")



