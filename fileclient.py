import socket
import threading
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import webbrowser
import subprocess
import sys

PORT = 5050
CHUNKSIZE = 4096
SEPARATOR = '<SEPARATOR>'

class FileClientApp:
    def __init__(self, master):
        self.master = master
        master.title('Client-Server File Transfer - Client')

        frame = ttk.Frame(master)
        frame.pack(padx=10, pady=5)
        ttk.Label(frame, text='Server IP:').grid(row=0, column=0)
        self.ip_entry = ttk.Entry(frame)
        self.ip_entry.insert(0, socket.gethostbyname(socket.gethostname()))
        self.ip_entry.grid(row=0, column=1, padx=5)
        ttk.Label(frame, text='Port:').grid(row=0, column=2)
        self.port_entry = ttk.Entry(frame, width=6)
        self.port_entry.insert(0, str(PORT))
        self.port_entry.grid(row=0, column=3, padx=5)

        send_frame = ttk.LabelFrame(master, text='Send File to Server')
        send_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(send_frame, text='Choose File', command=self.choose_file).pack(side='left', padx=5)
        self.file_label = ttk.Label(send_frame, text='No file selected')
        self.file_label.pack(side='left', padx=5)
        ttk.Button(send_frame, text='Send', command=self.gui_send).pack(side='left', padx=5)

        recv_frame = ttk.LabelFrame(master, text='Request File from Server')
        recv_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(recv_frame, text='Refresh File List', command=self.refresh_list).pack(side='left', padx=5)
        self.file_combo = ttk.Combobox(recv_frame)
        self.file_combo.pack(side='left', padx=5)
        ttk.Button(recv_frame, text='Receive', command=self.gui_receive).pack(side='left', padx=5)

        self.progress = ttk.Progressbar(master, length=300)
        self.progress.pack(pady=10)
        self.status = ttk.Label(master, text='')
        self.status.pack()

        self.filename = None

    def choose_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.filename = path
            self.file_label.config(text=os.path.basename(path))

    def gui_send(self):
        addr = (self.ip_entry.get(), int(self.port_entry.get()))
        threading.Thread(target=self.send_file, args=(addr, self.filename), daemon=True).start()

    def send_file(self, addr, filepath):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(addr)
                s.send(b'SEND')
                if s.recv(1024).decode().strip() == 'OK':
                    fname = os.path.basename(filepath)
                    size = os.path.getsize(filepath)
                    s.send(fname.encode())
                    s.send(f"{fname}{SEPARATOR}{size}".encode())
                    sent = 0
                    with open(filepath, 'rb') as f:
                        while chunk := f.read(CHUNKSIZE):
                            s.sendall(chunk)
                            sent += len(chunk)
                            self.progress['value'] = (sent/size)*100
                            self.status.config(text=f"Sent {sent}/{size} bytes")
                    self.status.config(text='File sent successfully')
                    messagebox.showinfo('Success', f'File \"{fname}\" sent successfully.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def refresh_list(self):
        addr = (self.ip_entry.get(), int(self.port_entry.get()))
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(addr)
                s.send(b'LIST')
                data = s.recv(8192).decode()
                files = data.split('|') if data else []
                self.file_combo['values'] = files
                if files:
                    self.file_combo.set(files[0])
        except Exception as e:
            messagebox.showerror('Error', f'Failed to fetch file list: {e}')

    def gui_receive(self):
        addr = (self.ip_entry.get(), int(self.port_entry.get()))
        fname = self.file_combo.get().strip()
        threading.Thread(target=self.receive_file, args=(addr, fname), daemon=True).start()

    def receive_file(self, addr, fname):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(addr)
                s.send(b'RECEIVE')
                if s.recv(1024).decode().strip() == 'OK':
                    s.send(fname.encode())
                    resp = s.recv(1024).decode()
                    if not resp or resp.startswith('ERROR'):
                        messagebox.showerror('Error', resp or 'No response from server')
                        return
                    name, size = resp.split(SEPARATOR)
                    size = int(size)
                    received = 0
                    with open(name, 'wb') as f:
                        while received < size:
                            chunk = s.recv(CHUNKSIZE)
                            if not chunk: break
                            f.write(chunk)
                            received += len(chunk)
                            self.progress['value'] = (received/size)*100
                            self.status.config(text=f"Received {received}/{size} bytes")
                    self.status.config(text='File received successfully')
                    messagebox.showinfo('Success', f'File \"{name}\" received successfully.')
                    self.preview_file(name)
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def preview_file(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext in ('.txt', '.py', '.csv', '.log'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                win = tk.Toplevel(self.master)
                win.title(f"Preview - {filepath}")
                text_widget = tk.Text(win, wrap='word')
                text_widget.insert('1.0', content)
                text_widget.pack(expand=True, fill='both')

            elif ext in ('.png', '.jpg', '.jpeg', '.bmp', '.gif'):
                win = tk.Toplevel(self.master)
                win.title(f"Image Preview - {filepath}")
                img = Image.open(filepath)
                photo = ImageTk.PhotoImage(img)
                label = ttk.Label(win, image=photo)
                label.image = photo
                label.pack()

            elif ext == '.html':
                webbrowser.open(f"file://{os.path.abspath(filepath)}")

            elif ext == '.pdf':
                if sys.platform == 'win32':
                    os.startfile(filepath)
                elif sys.platform == 'darwin':
                    subprocess.call(('open', filepath))
                else:
                    subprocess.call(('xdg-open', filepath))
            else:
                messagebox.showinfo('Preview', 'Preview tidak tersedia untuk file ini.')
        except Exception as e:
            messagebox.showerror('Preview Error', f'Gagal menampilkan preview: {e}')

if __name__ == '__main__':
    root = tk.Tk()
    app = FileClientApp(root)
    root.mainloop()
