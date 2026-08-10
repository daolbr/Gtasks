import os
import tkinter as tk
from tkinter import ttk
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/tasks.readonly']

def get_tasks_service():
    """Autentica com o Google e retorna o serviço da API."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('tasks', 'v1', credentials=creds)

def fetch_pending_tasks():
    """Busca tarefas pendentes na lista padrão."""
    try:
        service = get_tasks_service()
        results = service.tasks().list(tasklist='@default', showCompleted=False).execute()
        items = results.get('items', [])
        return [task['title'] for task in items if 'title' in task and task['title'].strip()]
    except Exception as e:
        return [f"Erro ao carregar: {e}"]

class FloatingWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("Google Tasks")
        
        # Configuração da Janela
        self.root.geometry("280x380+100+100")
        self.root.overrideredirect(True)       # Remove bordas/barra de título padrão
        self.root.wm_attributes("-topmost", True) # Mantém sempre no topo
        self.root.attributes("-alpha", 0.92)    # Transparência leve (92%)
        self.root.configure(bg="#1e1e2e")      # Estilo Dark Mode

        # Variáveis de arraste
        self._x = 0
        self._y = 0

        # Barra de título personalizada (Drag Bar)
        self.header = tk.Frame(root, bg="#11111b", height=30)
        self.header.pack(fill="x", side="top")
        
        self.title_label = tk.Label(self.header, text="📌 Tarefas Pendentes", fg="#cdd6f4", bg="#11111b", font=("Segoe UI", 9, "bold"))
        self.title_label.pack(side="left", padx=10, py=5)

        # Botão Fechar
        self.close_btn = tk.Label(self.header, text="✕", fg="#f38ba8", bg="#11111b", font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.close_btn.pack(side="right", padx=10)
        self.close_btn.bind("<Button-1>", lambda e: root.destroy())

        # Botão Recarregar
        self.refresh_btn = tk.Label(self.header, text="🔄", fg="#a6e3a1", bg="#11111b", font=("Segoe UI", 9), cursor="hand2")
        self.refresh_btn.pack(side="right", padx=5)
        self.refresh_btn.bind("<Button-1>", lambda e: self.load_tasks())

        # Eventos para arrastar a janela
        self.header.bind("<Button-1>", self.start_move)
        self.header.bind("<B1-Motion>", self.do_move)
        self.title_label.bind("<Button-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)

        # Container das Tarefas
        self.container = tk.Frame(root, bg="#1e1e2e")
        self.container.pack(fill="both", expand=True, padx=10, py=10)

        # Lista com Scroll
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

        # Carregar tarefas iniciais
        self.load_tasks()

    def start_move(self, event):
        self._x = event.x
        self._y = event.y

    def do_move(self, event):
        x = self.root.winfo_pointerx() - self._x
        y = self.root.winfo_pointery() - self._y
        self.root.geometry(f"+{x}+{y}")

    def load_tasks(self):
        # Limpa tarefas anteriores da tela
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        loading_label = tk.Label(self.scrollable_frame, text="Carregando...", fg="#a6adc8", bg="#1e1e2e", font=("Segoe UI", 9, "italic"))
        loading_label.pack(anchor="w", py=5)
        self.root.update()

        tasks = fetch_pending_tasks()
        loading_label.destroy()

        if not tasks:
            no_tasks_label = tk.Label(self.scrollable_frame, text="Nenhuma tarefa pendente! 🎉", fg="#a6e3a1", bg="#1e1e2e", font=("Segoe UI", 9))
            no_tasks_label.pack(anchor="w", py=5)
            return

        for task in tasks:
            task_frame = tk.Frame(self.scrollable_frame, bg="#313244", padx=8, pady=6)
            task_frame.pack(fill="x", expand=True, pady=3)

            bullet = tk.Label(task_frame, text="•", fg="#89b4fa", bg="#313244", font=("Segoe UI", 10, "bold"))
            bullet.pack(side="left", anchor="n")

            label = tk.Label(
                task_frame, 
                text=task, 
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
