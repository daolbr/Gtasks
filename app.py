import os
import sys
import tkinter as tk
from tkinter import ttk
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/tasks']

def get_token_path():
    """Gera um caminho seguro na pasta APPDATA para não ter erros de permissão."""
    app_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'GoogleTasksWidget')
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, 'token.json')

def get_tasks_service():
    creds = None
    token_path = get_token_path()

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return build('tasks', 'v1', credentials=creds)

def fetch_pending_tasks():
    try:
        service = get_tasks_service()
        results = service.tasks().list(tasklist='@default', showCompleted=False).execute()
        items = results.get('items', [])
        return [{'id': task['id'], 'title': task['title']} for task in items if 'title' in task and task['title'].strip()]
    except Exception as e:
        return [{'id': None, 'title': f"Erro ao carregar: {e}"}]

def add_new_task(title):
    try:
        service = get_tasks_service()
        service.tasks().insert(tasklist='@default', body={'title': title}).execute()
        return True
    except Exception as e:
        print(f"Erro ao criar tarefa: {e}")
        return False

def complete_task(task_id):
    try:
        service = get_tasks_service()
        service.tasks().patch(tasklist='@default', task=task_id, body={'status': 'completed'}).execute()
        return True
    except Exception as e:
        print(f"Erro ao concluir tarefa: {e}")
        return False

class FloatingWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("Google Tasks")
        
        self.root.geometry("300x420+100+100")
        self.root.overrideredirect(True)
        
        # AJUSTE PARA FICAR ATRÁS DE OUTRAS JANELAS:
        self.root.wm_attributes("-topmost", False)  # Desativa ficar no topo
        self.root.lower()                           # Manda para a camada do fundo
        self.root.bind("<FocusOut>", lambda e: self.root.lower()) # Se perder foco, volta pro fundo

        self.root.attributes("-alpha", 0.95)
        self.root.configure(bg="#1e1e2e")

        self._x = 0
        self._y = 0

        # Header
        self.header = tk.Frame(root, bg="#11111b", height=30)
        self.header.pack(fill="x", side="top")
        
        self.title_label = tk.Label(self.header, text="📌 Google Tasks", fg="#cdd6f4", bg="#11111b", font=("Segoe UI", 9, "bold"))
        self.title_label.pack(side="left", padx=10, pady=5)

        self.close_btn = tk.Label(self.header, text="✕", fg="#f38ba8", bg="#11111b", font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.close_btn.pack(side="right", padx=10)
        self.close_btn.bind("<Button-1>", lambda e: root.destroy())

        self.refresh_btn = tk.Label(self.header, text="🔄", fg="#a6e3a1", bg="#11111b", font=("Segoe UI", 9), cursor="hand2")
        self.refresh_btn.pack(side="right", padx=5)
        self.refresh_btn.bind("<Button-1>", lambda e: self.load_tasks())

        self.header.bind("<Button-1>", self.start_move)
        self.header.bind("<B1-Motion>", self.do_move)
        self.title_label.bind("<Button-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)

        # Adicionar tarefa
        self.add_frame = tk.Frame(root, bg="#1e1e2e")
        self.add_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.task_entry = tk.Entry(self.add_frame, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4", font=("Segoe UI", 9), relief="flat")
        self.task_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 5))
        self.task_entry.bind("<Return>", lambda e: self.handle_add_task())

        self.add_btn = tk.Button(self.add_frame, text="+", bg="#89b4fa", fg="#11111b", font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", command=self.handle_add_task)
        self.add_btn.pack(side="right", ipadx=6)

        # Lista
        self.container = tk.Frame(root, bg="#1e1e2e")
        self.container.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.canvas = tk.Canvas(self.container, bg="#1e1e2e", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#1e1e2e")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.load_tasks()

    def start_move(self, event):
        self._x = event.x
        self._y = event.y

    def do_move(self, event):
        x = self.root.winfo_pointerx() - self._x
        y = self.root.winfo_pointery() - self._y
        self.root.geometry(f"+{x}+{y}")

    def handle_add_task(self):
        title = self.task_entry.get().strip()
        if title:
            self.task_entry.delete(0, tk.END)
            add_new_task(title)
            self.load_tasks()

    def handle_complete_task(self, task_id):
        if task_id:
            complete_task(task_id)
            self.load_tasks()

    def load_tasks(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        loading_label = tk.Label(self.scrollable_frame, text="Carregando...", fg="#a6adc8", bg="#1e1e2e", font=("Segoe UI", 9, "italic"))
        loading_label.pack(anchor="w", pady=5)
        self.root.update()

        tasks = fetch_pending_tasks()
        loading_label.destroy()

        if not tasks:
            no_tasks_label = tk.Label(self.scrollable_frame, text="Nenhuma tarefa pendente! 🎉", fg="#a6e3a1", bg="#1e1e2e", font=("Segoe UI", 9))
            no_tasks_label.pack(anchor="w", pady=5)
            return

        for task in tasks:
            task_frame = tk.Frame(self.scrollable_frame, bg="#313244", padx=8, pady=6)
            task_frame.pack(fill="x", expand=True, pady=3)

            if task['id']:
                check_btn = tk.Label(task_frame, text="☐", fg="#89b4fa", bg="#313244", font=("Segoe UI", 11, "bold"), cursor="hand2")
                check_btn.pack(side="left", anchor="n", padx=(0, 5))
                t_id = task['id']
                check_btn.bind("<Button-1>", lambda e, tid=t_id: self.handle_complete_task(tid))

            label = tk.Label(
                task_frame, 
                text=task['title'], 
                fg="#cdd6f4", 
                bg="#313244", 
                font=("Segoe UI", 9), 
                wraplength=200, 
                justify="left"
            )
            label.pack(side="left", padx=5, fill="x", expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = FloatingWidget(root)
    root.mainloop()
