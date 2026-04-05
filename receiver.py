import socket
import os


HOST = "0.0.0.0"   # listen on all network interfaces
PORT = 5001        # must match DASHBOARD_PORT on ESP32
SAVE_DIR = r"/Users/seifabdelazim/Dropbox/Mac/Desktop/atmosleep-dashboard/data/history"


os.makedirs(SAVE_DIR, exist_ok=True)




def recv_line(conn):
    """
    Read one line ending in \\n from the socket.
    Returns the line without trailing \\r or \\n.
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


        # After file bytes, sender sends:
        #   client.println();
        #   client.println("END");
        #
        # So there may be one blank line before END.
        next_line = recv_line(conn)
        if next_line == "":
            end_marker = recv_line(conn)
        else:
            end_marker = next_line


        if end_marker != "END":
            print(f"Warning: expected END, got {end_marker!r}")


        save_path = os.path.join(SAVE_DIR, filename)
        with open(save_path, "wb") as f:
            f.write(file_data)


        print(f"Saved file to: {save_path}")


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

