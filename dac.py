import tkinter as tk
from tkinter import scrolledtext
import threading
import speech_recognition as sr
import google.generativeai as genai

# =======================================================
# CONFIGURAÇÃO DA IA (GEMINI)
# =======================================================
# Lembre-se de colocar sua chave real aqui
genai.configure(api_key="cahve sua aqui ")
# Atualizado para a versão estável mais recente aceita pelo servidor
modelo = genai.GenerativeModel('gemini-2.5-flash')

# =======================================================
# APLICAÇÃO DESKTOP (TKINTER)
# =======================================================
class AssistenteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Assistente de IA")
        self.geometry("550x450")
        self.configure(padx=20, pady=20)
        
        self.recognizer = sr.Recognizer()
        self.chat_ia = None  # Guardará o histórico da conversa (essencial para o "explicar de outra forma")
        self.escutando_wake_word = True 
        
        self.frame_atual = None
        
        # Inicia o aplicativo na tela de espera
        self.mostrar_tela_espera()
        
        # Inicia a Thread que ouve o gatilho em segundo plano
        t = threading.Thread(target=self.loop_wake_word, daemon=True)
        t.start()

    def trocar_frame(self, construtor_frame):
        """Remove o frame antigo e desenha o novo com segurança."""
        if self.frame_atual:
            self.frame_atual.destroy()
        self.frame_atual = construtor_frame()
        self.frame_atual.pack(fill="both", expand=True)

    # =======================================================
    # TELA 1: ESPERA (STANDBY / MINIMIZADO)
    # =======================================================
    def mostrar_tela_espera(self):
        def construir():
            frame = tk.Frame(self)
            lbl = tk.Label(frame, text="Assistente em Standby...\nDiga 'Google me ajuda' para ativar.", 
                           font=("Arial", 14), fg="gray")
            lbl.pack(expand=True)
            return frame
        self.trocar_frame(construir)

    def loop_wake_word(self):
        """Fica ouvindo em segundo plano enquanto o app está minimizado."""
        while True:
            if not self.escutando_wake_word:
                import time
                time.sleep(1)
                continue
                
            with sr.Microphone() as source:
                # Ajuste rápido de ruído para ouvir de imediato
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                try:
                    # Captura rápida
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=4)
                    texto = self.recognizer.recognize_google(audio, language="pt-BR").lower()
                    print(f"[Debug] Ouvido em standby: {texto}")
                    
                    if "google me ajuda" in texto:
                        print("[Debug] Gatilho ativado! Restaurando janela...")
                        self.escutando_wake_word = False
                        self.chat_ia = modelo.start_chat(history=[])
                        
                        #  Força a janela a restaurar e subir para a tela do usuário
                        self.after(0, self.restaurar_janela_sistema)
                        
                except Exception:
                    pass

    def restaurar_janela_sistema(self):
        """Traz o aplicativo de volta para o primeiro plano na tela do usuário."""
        self.deiconify()  # Desminimiza a janela caso esteja minimizada
        self.update()
        self.attributes("-topmost", True)  # Força a ficar em cima de todas as outras janelas
        self.attributes("-topmost", False) # Libera para o usuário mexer normalmente depois
        self.focus_force()                 # Dá foco para a janela do app
        self.mostrar_tela_botao()          # Muda para a tela de ação

    # =======================================================
    # TELA 2: BOTÃO PARA FAZER A PERGUNTA
    # =======================================================
    def mostrar_tela_botao(self):
        def construir():
            frame = tk.Frame(self)
            lbl = tk.Label(frame, text="Estou ouvindo! Clique no botão abaixo e fale sua dúvida.", font=("Arial", 12))
            lbl.pack(pady=20)
            
            btn = tk.Button(frame, text="🎙️ Falar Problema / Dúvida", font=("Arial", 12, "bold"),
                            bg="#4CAF50", fg="white", command=self.ouvir_duvida_usuario)
            btn.pack(ipadx=20, ipady=10, expand=True)
            return frame
        self.trocar_frame(construir)

    # =======================================================
    # Ouvir e Confirmar
    # =======================================================
    def ouvir_duvida_usuario(self):
        """Apenas escuta o áudio do usuário e envia para validação textual."""
        self.mostrar_tela_carregando("Ouvindo sua dúvida...")
        
        def thread_ouvir():
            #  Reduzido o tempo de silêncio para não esperar 3 segundos
            self.recognizer.pause_threshold = 1.0 
            
            with sr.Microphone() as source:
                try:
                    audio = self.recognizer.listen(source)
                    texto_ouvido = self.recognizer.recognize_google(audio, language="pt-BR")
                    # Em vez de mandar direto para a IA, manda para a tela de CONFIRMAÇÃO
                    self.after(0, self.mostrar_tela_confirmacao, texto_ouvido)
                except Exception as e:
                    self.after(0, self.mostrar_tela_resposta, "Erro ao ouvir", f"Não entendi o áudio.\nDetalhe: {e}")
                    
        threading.Thread(target=thread_ouvir, daemon=True).start()

    def mostrar_tela_confirmacao(self, texto_entendido):
        """Modificação Item 1: Tela intermediária para confirmar o que foi falado."""
        def construir():
            frame = tk.Frame(self)
            lbl_titulo = tk.Label(frame, text="Eu entendi isso da sua fala:", font=("Arial", 12, "bold"))
            lbl_titulo.pack(pady=10)
            
            # Caixa de texto editável para caso o usuário queira corrigir digitando
            txt_confirmar = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Arial", 11), height=5)
            txt_confirmar.insert(tk.END, texto_entendido)
            txt_confirmar.pack(fill="x", padx=10, pady=10)
            
            frame_botoes = tk.Frame(frame)
            frame_botoes.pack(fill="x", pady=20)
            
            # Botão Confirmar -> Envia o texto da caixa para a IA
            btn_sim = tk.Button(frame_botoes, text="✔️ Confirmar e Enviar", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
                                command=lambda: self.enviar_para_ia(txt_confirmar.get("1.0", tk.END).strip()))
            btn_sim.pack(side="left", expand=True, ipadx=10, ipady=5)
            
            # Botão Corrigir -> Descarta e deixa o usuário falar novamente
            btn_nao = tk.Button(frame_botoes, text="❌ Falar Novamente", bg="#f44336", fg="white", font=("Arial", 10, "bold"),
                                command=self.mostrar_tela_botao)
            btn_nao.pack(side="right", expand=True, ipadx=10, ipady=5)
            
            return frame
        self.trocar_frame(construir)

    def enviar_para_ia(self, texto_final):
        """Envia o texto confirmado para os servidores do Gemini."""
        self.mostrar_tela_carregando("Pensando... (Chamando IA)")
        
        def thread_ia():
            try:
                resposta = self.chat_ia.send_message(texto_final)
                self.after(0, self.mostrar_tela_resposta, texto_final, resposta.text)
            except Exception as e:
                self.after(0, self.mostrar_tela_resposta, "Erro na IA", f"Problema de conexão.\nDetalhe: {e}")
                
        threading.Thread(target=thread_ia, daemon=True).start()

    # =======================================================
    # TELA DE CARREGAMENTO (FEEDBACK VISUAL)
    # =======================================================
    def mostrar_tela_carregando(self, mensagem):
        def construir():
            frame = tk.Frame(self)
            lbl = tk.Label(frame, text=mensagem, font=("Arial", 12, "italic"), fg="#2196F3")
            lbl.pack(expand=True)
            return frame
        self.trocar_frame(construir)

    # =======================================================
    # TELA 3: EXIBIÇÃO DA RESPOSTA DA IA
    # =======================================================
    def mostrar_tela_resposta(self, pergunta, resposta_ia):
        def construir():
            frame = tk.Frame(self)
            
            lbl = tk.Label(frame, text="Resultado do Auxílio:", font=("Arial", 12, "bold"))
            lbl.pack(anchor="w", pady=(0, 5))
            
            txt = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Arial", 10))
            txt.insert(tk.END, f"VOCÊ:\n{pergunta}\n\n")
            txt.insert(tk.END, "-"*40 + "\n\n")
            txt.insert(tk.END, f"IA:\n{resposta_ia}")
            txt.config(state=tk.DISABLED)
            txt.pack(fill="both", expand=True, pady=(0, 15))
            
            frame_botoes = tk.Frame(frame)
            frame_botoes.pack(fill="x")
            
            # Botão "Ainda com dúvida" para pedir outra explicação
            btn_duvida = tk.Button(frame_botoes, text="🤔 Não entendi, mude a explicação", 
                                   command=self.pedir_outra_explicacao, bg="#FF9800", fg="white", font=("Arial", 9, "bold"))
            btn_duvida.pack(side="left", ipadx=5, ipady=5)
            
            # Continuar -> Mantém a conversa atual aberta
            btn_continuar = tk.Button(frame_botoes, text="Continuar", 
                                      command=self.mostrar_tela_botao, bg="#2196F3", fg="white")
            btn_continuar.pack(side="left", padx=10, ipadx=10)
            
            # Finalizar -> Minimiza e volta pro standby do Wake Word
            btn_finalizar = tk.Button(frame_botoes, text="Finalizar", 
                                      command=self.encerrar_fluxo, bg="#f44336", fg="white")
            btn_finalizar.pack(side="right", ipadx=10)
            
            return frame
        self.trocar_frame(construir)

    def pedir_outra_explicacao(self):
        """Modificação Item 2: Envia um comando oculto no chat pedindo outra abordagem."""
        comando_oculto = "Não entendi a resposta anterior. Poderia me explicar de outra maneira mais simples ou usando termos diferentes?"
        self.enviar_para_ia(comando_oculto)

    def encerrar_fluxo(self):
        """Fecha o chat atual, limpa dados e joga a aplicação de volta para standby minimizada."""
        print("[Debug] Fluxo encerrado. Retornando a standby oculto...")
        self.chat_ia = None
        self.escutando_wake_word = True
        self.mostrar_tela_espera()
        self.iconify()  # Minimiza a janela automaticamente ao terminar

# =======================================================
# EXECUÇÃO DO PROGRAMA
# =======================================================
if __name__ == "__main__":
    app = AssistenteApp()
    app.mainloop()