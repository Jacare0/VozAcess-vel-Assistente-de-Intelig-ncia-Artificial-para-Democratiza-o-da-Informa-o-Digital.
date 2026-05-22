import tkinter as tk
from tkinter import scrolledtext
import threading
import speech_recognition as sr
import google.generativeai as genai

# =======================================================
# CONFIGURAÇÃO DA IA (GEMINI)
# =======================================================
genai.configure(api_key="SUA_CHAVE_AQUI")
modelo = genai.GenerativeModel('gemini-1.5-flash')

# =======================================================
# APLICAÇÃO DESKTOP (TKINTER)
# =======================================================
class AssistenteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Assistente de IA")
        self.geometry("500x400")
        self.configure(padx=20, pady=20)
        
        self.recognizer = sr.Recognizer()
        self.chat_ia = None  # Guardará o histórico da conversa atual
        self.escutando_wake_word = True # Flag de controle
        
        # Variável para controlar o Frame (tela) visível no momento
        self.frame_atual = None
        
        # Inicia a tela aguardando o gatilho
        self.mostrar_tela_espera()
        
        # Inicia a Thread que fica ouvindo o gatilho em segundo plano
        t = threading.Thread(target=self.loop_wake_word, daemon=True)
        t.start()

    def trocar_frame(self, construtor_de_frame):
        """Destrói a tela atual e carrega a nova para limpar o visual"""
        if self.frame_atual is not None:
            self.frame_atual.destroy()
        self.frame_atual = construtor_de_frame()
        self.frame_atual.pack(fill="both", expand=True)

    # ---------------------------------------------------
    # TELA 0: AGUARDANDO GATILHO (WAKE WORD)
    # ---------------------------------------------------
    def mostrar_tela_espera(self):
        def construir():
            frame = tk.Frame(self)
            lbl = tk.Label(frame, text="Zzz...", font=("Arial", 24))
            lbl.pack(pady=(50, 10))
            lbl_desc = tk.Label(frame, text="Aguardando você dizer:\n'Google me ajuda'", fg="gray")
            lbl_desc.pack()
            return frame
        self.trocar_frame(construir)
        self.escutando_wake_word = True

    def loop_wake_word(self):
        """Roda eternamente na thread de fundo, escutando o ambiente."""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while True:
                # Se o usuário já ativou, pausa essa escuta para não cruzar áudios
                if not self.escutando_wake_word:
                    import time
                    time.sleep(1)
                    continue
                try:
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=4)
                    texto = self.recognizer.recognize_google(audio, language="pt-BR").lower()
                    print(f"[Debug] Escutou no fundo: {texto}")
                    
                    if "google me ajuda" in texto:
                        print("[Debug] Gatilho ativado!")
                        self.escutando_wake_word = False # Trava o wake word
                        
                        # Inicia uma sessão nova com a IA (histórico limpo)
                        self.chat_ia = modelo.start_chat(history=[])
                        
                        # Usa .after(0, ...) para mandar a Thread Principal desenhar a próxima tela
                        self.after(0, self.mostrar_tela_botao)
                        
                except Exception:
                    # Ignora ruídos, timeouts e não reconhecimentos
                    pass

    # ---------------------------------------------------
    # TELA 1: BOTÃO PARA FALAR
    # ---------------------------------------------------
    def mostrar_tela_botao(self):
        def construir():
            frame = tk.Frame(self)
            lbl = tk.Label(frame, text="Como posso ajudar?", font=("Arial", 16))
            lbl.pack(pady=(40, 20))
            
            btn = tk.Button(frame, text="🎤 Falar Problema", font=("Arial", 14), 
                            bg="#4CAF50", fg="white", command=self.iniciar_gravacao)
            btn.pack(ipady=10, ipadx=20)
            return frame
        self.trocar_frame(construir)

    def iniciar_gravacao(self):
        """Muda a UI para carregamento e dispara a thread de gravação"""
        self.mostrar_tela_carregando("Ouvindo...\n(Pare de falar por 3s para enviar)")
        # Inicia a Thread para não travar o botão e a tela
        threading.Thread(target=self.processar_problema, daemon=True).start()

    def mostrar_tela_carregando(self, mensagem):
        def construir():
            frame = tk.Frame(self)
            lbl = tk.Label(frame, text=mensagem, font=("Arial", 14), fg="blue")
            lbl.pack(pady=80)
            return frame
        self.trocar_frame(construir)

    def processar_problema(self):
        """Thread de fundo que grava os 3s, chama a API e atualiza a UI"""
        self.recognizer.pause_threshold = 3.0
        with sr.Microphone() as source:
            try:
                audio = self.recognizer.listen(source)
                
                # Atualiza a UI para avisar que está processando
                self.after(0, lambda: self.mostrar_tela_carregando("Convertendo áudio..."))
                texto_problema = self.recognizer.recognize_google(audio, language="pt-BR")
                
                self.after(0, lambda: self.mostrar_tela_carregando("Pensando... (Chamando IA)"))
                resposta = self.chat_ia.send_message(texto_problema)
                
                # Manda o resultado para a tela final
                self.after(0, lambda: self.mostrar_tela_resposta(texto_problema, resposta.text))
                
            except Exception as e:
                self.after(0, lambda: self.mostrar_tela_resposta("Erro", f"Não foi possível processar.\nDetalhe: {e}"))


    # ---------------------------------------------------
    # TELA 2: RESPOSTA E BOTÕES FINAIS
    # ---------------------------------------------------
    def mostrar_tela_resposta(self, pergunta, resposta_ia):
        def construir():
            frame = tk.Frame(self)
            
            # Caixa de texto com barra de rolagem para ler tudo
            txt = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Arial", 10))
            txt.insert(tk.END, f"VOCÊ:\n{pergunta}\n\n")
            txt.insert(tk.END, "-"*40 + "\n\n")
            txt.insert(tk.END, f"IA:\n{resposta_ia}")
            txt.config(state=tk.DISABLED) # Bloqueia edição pelo usuário
            txt.pack(fill="both", expand=True, pady=(0, 15))
            
            # Botões inferiores
            frame_botoes = tk.Frame(frame)
            frame_botoes.pack(fill="x")
            
            # Continuar -> Volta pro botão de falar (mantém chat_ia vivo)
            btn_continuar = tk.Button(frame_botoes, text="Continuar", 
                                      command=self.mostrar_tela_botao, bg="#2196F3", fg="white")
            btn_continuar.pack(side="left", ipadx=10)
            
            # Finalizar -> Zera tudo e volta pro wake word
            btn_finalizar = tk.Button(frame_botoes, text="Finalizar", 
                                      command=self.encerrar_fluxo, bg="#f44336", fg="white")
            btn_finalizar.pack(side="right", ipadx=10)
            
            return frame
        self.trocar_frame(construir)

    def encerrar_fluxo(self):
        """Limpa a memória do chat e volta a escutar o ambiente"""
        self.chat_ia = None 
        self.mostrar_tela_espera()

# Inicia a aplicação
if __name__ == "__main__":
    app = AssistenteApp()
    app.mainloop() # Este é o loop principal que trava o código, por isso usamos Threads