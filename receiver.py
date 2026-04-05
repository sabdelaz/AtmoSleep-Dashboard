import socket
import os
import requests
import base64


HOST = "0.0.0.0"   # listen on all network interfaces
PORT = 5001        # must match DASHBOARD_PORT on ESP32
SAVE_DIR = r"/Users/seifabdelazim/Dropbox/Mac/Desktop/atmosleep-dashboard/data/history"

# github info
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = "sabdelaz"
GITHUB_REPO = "atmosleep-dashboard"
GITHUB_BRANCH = "main"

os.makedirs(SAVE_DIR, exist_ok=True)


def recv_line(conn):
    """
    Read one line ending in \n from the socket.
    Returns the line without trailing \r or \n.
    """
    data = bytearray()
    while True:
        ch = conn.recv(1)
        if not ch:
            raise ConnectionError("Socket closed while reading line")
        if ch == b"\n":
            break
        data.extend(ch)
    return data.rstrip(b"\r").decode("utf-8")


def recv_exact(conn, nbytes):
    """
    Read exactly nbytes from the socket.
    """
    data = bytearray()
    while len(data) < nbytes:
        chunk = conn.recv(min(4096, nbytes - len(data)))
        if not chunk:
            raise ConnectionError("Socket closed before receiving full file")
        data.extend(chunk)
    return bytes(data)


def upload_to_github(filename, file_data):
    """
    Upload the received CSV to GitHub inside data/history/
    If the file already exists, this updates it.
    """
    if not GITHUB_TOKEN:
        print("GitHub token not found. Skipping GitHub upload.")
        return

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/data/history/{filename}"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    content_b64 = base64.b64encode(file_data).decode("utf-8")

    # first check if file already exists
    get_res = requests.get(url, headers=headers, params={"ref": GITHUB_BRANCH})

    payload = {
        "message": f"Upload sleep file {filename}",
        "content": content_b64,
        "branch": GITHUB_BRANCH,
    }

    # if file exists already, github needs the sha to update it
    if get_res.status_code == 200:
        payload["sha"] = get_res.json()["sha"]

    put_res = requests.put(url, headers=headers, json=payload)

    if put_res.status_code in [200, 201]:
        print(f"Uploaded {filename} to GitHub")
    else:
        print(f"GitHub upload failed: {put_res.status_code}")
        print(put_res.text)


def handle_client(conn, addr):
    print(f"\nConnected by {addr}")

    try:
        start_marker = recv_line(conn)
        if start_marker != "START":
            print(f"Invalid start marker: {start_marker!r}")
            return

        filename = recv_line(conn)
        filesize_str = recv_line(conn)

        try:
            filesize = int(filesize_str)
        except ValueError:
            print(f"Invalid file size: {filesize_str!r}")
            return

        print(f"Receiving file: {filename}")
        print(f"Expected size: {filesize} bytes")

        file_data = recv_exact(conn, filesize)

        # after file bytes, sender sends:
        # client.println();
        # client.println("END");
        # so there may be one blank line before END
        next_line = recv_line(conn)
        if next_line == "":
            end_marker = recv_line(conn)
        else:
            end_marker = next_line

        if end_marker != "END":
            print(f"Warning: expected END, got {end_marker!r}")

        # save locally too
        save_path = os.path.join(SAVE_DIR, filename)
        with open(save_path, "wb") as f:
            f.write(file_data)

        print(f"Saved file to: {save_path}")

        # also upload to github
        upload_to_github(filename, file_data)

    except Exception as e:
        print(f"Error while handling client {addr}: {e}")

    finally:
        conn.close()
        print(f"Connection closed: {addr}")


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)

    print(f"Listening on {HOST}:{PORT}")
    print(f"Files will be saved in ./{SAVE_DIR}")

    try:
        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)
    except KeyboardInterrupt:
        print("\nServer shutting down.")
    finally:
        server.close()


if __name__ == "__main__":
    main()
