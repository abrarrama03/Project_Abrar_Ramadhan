import socket
import threading
import os
import tkinter as tk
from tkinter import ttk, messagebox

PORT = 5050
CHUNKSIZE = 4096
SEPARATOR = '<SEPARATOR>'

class FileServerApp:
    def __init__(self, master):
        self.master = master
        master.title('Client-Server File Transfer - Server')

        ttk.Button(master, text='Start Server', command=self.start_server).pack(pady=5)

        self.log = tk.Text(master, height=10)
        self.log.pack(fill='both', expand=True, padx=10, pady=5)

    def log_message(self, msg):
        self.log.insert('end', msg + '\n')
        self.log.see('end')

    def start_server(self):
        threading.Thread(target=self.run_server, daemon=True).start()
        self.log_message(f'[LISTENING] on port {PORT}')

    def run_server(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(('', PORT))
        srv.listen()
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

    def handle_client(self, conn, addr):
        self.log_message(f'[NEW] Connection from {addr}')
        try:
            cmd = conn.recv(1024).decode().strip()
            if cmd == 'SEND':
                conn.send(b'OK')
                fname = conn.recv(1024).decode().strip()
                meta = conn.recv(1024).decode()
                name, size = meta.split(SEPARATOR)
                size = int(size)
                with open(name, 'wb') as f:
                    received = 0
                    while received < size:
                        chunk = conn.recv(CHUNKSIZE)
                        if not chunk: break
                        f.write(chunk)
                        received += len(chunk)
                        self.log_message(f'[RECV] {received}/{size} bytes')
                self.log_message(f'[DONE] Received {name}')

            elif cmd == 'RECEIVE':
                conn.send(b'OK')
                fname = conn.recv(1024).decode().strip()
                if os.path.exists(fname):
                    size = os.path.getsize(fname)
                    conn.send(f"{fname}{SEPARATOR}{size}".encode())
                    with open(fname, 'rb') as f:
                        sent = 0
                        while chunk := f.read(CHUNKSIZE):
                            conn.sendall(chunk)
                            sent += len(chunk)
                            self.log_message(f'[SEND] {sent}/{size} bytes')
                    self.log_message(f'[DONE] Sent {fname}')
                else:
                    conn.send(b'ERROR: File not found')
                    self.log_message(f'[ERROR] {fname} not found')

            elif cmd == 'LIST':
                files = os.listdir('.')
                file_list = '|'.join(files)
                conn.send(file_list.encode())

        except Exception as e:
            self.log_message(f'[EXC] {e}')
        finally:
            conn.close()
            self.log_message(f'[CLOSED] {addr}')

if __name__ == '__main__':
    root = tk.Tk()
    app = FileServerApp(root)
    root.mainloop()
