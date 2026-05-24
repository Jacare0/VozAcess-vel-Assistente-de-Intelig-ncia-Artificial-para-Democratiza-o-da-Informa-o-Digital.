import tkinter as tk
from tkinter import scrolledtext
import threading
import speech_recognition as sr
import google.generativeai as genai

# =======================================================
# CONFIGURAÇÃO DA IA (GEMINI)
# =======================================================
# Lembre-se de colocar sua chave real aqui antes de rodar
genai.configure(api_key="AIzaSyAcFR8jR9I3Dt6I7xdDVYm00vuhkIlZPos")
modelo = genai.GenerativeModel('gemini-2.5-flash')

# =======================================================
# APLICAÇÃO DESKTOP (TKINTER)
# =======================================================
class AssistenteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Assistente de IA")
        
        # MODIFICAÇÃO 1: Aumentado o tamanho padrão da tela para caber tudo sem rolar/ajustar manual
        self.geometry("750x600") 
        self.configure(padx=25, pady=25)
        
        self.recognizer = sr.Recognizer()
        self.chat_ia = None  
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
                           font=("Arial", 16), fg="gray") # Fonte aumentada para 16
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
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                try:
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=4)
                    texto = self.recognizer.recognize_google(audio, language="pt-BR").lower()
                    print(f"[Debug] Ouvido em standby: {texto}")
                    
                    if "google me ajuda" in texto:
                        print("[Debug] Gatilho ativado! Restaurando janela...")
                        self.escutando_wake_word = False
                        self.chat_ia = modelo.start_chat(history=[])
                        self.after(0, self.restaurar_janela_sistema)
                        
                except Exception:
                    pass

    def restaurar_janela_sistema(self):
        """Traz o aplicativo de volta para o primeiro plano na tela do usuário."""
        self.deiconify()  
        self.update()
        self.attributes("-topmost", True)  
        self.attributes("-topmost", False) 
        self.focus_force()                 
        self.mostrar_tela_botao()          

    # =======================================================
    # TELA 2: BOTÃO PARA FAZER A PERGUNTA
    # =======================================================
    def mostrar_tela_botao(self):
        def construir():
            frame = tk.Frame(self)
            lbl = tk.Label(frame, text="Estou ouvindo! Clique no botão abaixo e fale sua dúvida.", font=("Arial", 14)) # Aumentado para 14
            lbl.pack(pady=30)
            
            btn = tk.Button(frame, text="🎙️ Falar Problema / Dúvida", font=("Arial", 14, "bold"), # Aumentado para 14
                            bg="#4CAF50", fg="white", command=self.ouvir_duvida_usuario)
            btn.pack(ipadx=30, ipady=15, expand=True)
            return frame
        self.trocar_frame(construir)

    # =======================================================
    # FLUXO DE CAPTURA DO ÁUDIO
    # =======================================================
    def ouvir_duvida_usuario(self):
        """Apenas escuta o áudio do usuário e envia para validação textual."""
        self.mostrar_tela_carregando("Ouvindo sua dúvida...")
        
        def thread_ouvir():
            self.recognizer.pause_threshold = 1.0 
            with sr.Microphone() as source:
                try:
                    audio = self.recognizer.listen(source)
                    texto_ouvido = self.recognizer.recognize_google(audio, language="pt-BR")
                    self.after(0, self.mostrar_tela_confirmacao, texto_ouvido)
                except Exception as e:
                    self.after(0, self.mostrar_tela_resposta, "Erro ao ouvir", f"Não entendi o áudio.\nDetalhe: {e}")
                    
        threading.Thread(target=thread_ouvir, daemon=True).start()

    # =======================================================
    # TELA DE CONFIRMAÇÃO (COM FONTE AMPLIADA)
    # =======================================================
    def mostrar_tela_confirmacao(self, texto_entendido):
        """Tela intermediária para confirmar o que foi falado."""
        def construir():
            frame = tk.Frame(self)
            lbl_titulo = tk.Label(frame, text="Eu entendi isso da sua fala:", font=("Arial", 14, "bold")) # MODIFICAÇÃO 2: Fonte 14
            lbl_titulo.pack(pady=15)
            
            # MODIFICAÇÃO 2: Caixa de confirmação com Letra Grande (Font 14) para idosos lerem com facilidade
            txt_confirmar = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Arial", 14), height=6) 
            txt_confirmar.insert(tk.END, texto_entendido)
            txt_confirmar.pack(fill="x", padx=15, pady=15)
            
            frame_botoes = tk.Frame(frame)
            frame_botoes.pack(fill="x", pady=25) # Correção do bug da barra invertida feita aqui
            
            # Botões com fontes maiores e mais espaçados
            btn_sim = tk.Button(frame_botoes, text="✔️ Confirmar e Enviar", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                                command=lambda: self.enviar_para_ia(txt_confirmar.get("1.0", tk.END).strip()))
            btn_sim.pack(side="left", expand=True, ipadx=15, ipady=10)
            
            btn_nao = tk.Button(frame_botoes, text="❌ Falar Novamente", bg="#f44336", fg="white", font=("Arial", 12, "bold"),
                                command=self.mostrar_tela_botao)
            btn_nao.pack(side="right", expand=True, ipadx=15, ipady=10)
            
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
            lbl = tk.Label(frame, text=mensagem, font=("Arial", 14, "italic"), fg="#2196F3") # Fonte 14
            lbl.pack(expand=True)
            return frame
        self.trocar_frame(construir)

    # =======================================================
    # TELA 3: RESPOSTA DA IA (LIMPA E AMPLIADA)
    # =======================================================
    def mostrar_tela_resposta(self, pergunta, resposta_ia):
        def construir():
            frame = tk.Frame(self)
            
            lbl = tk.Label(frame, text="Resultado do Auxílio:", font=("Arial", 14, "bold")) 
            lbl.pack(anchor="w", pady=(0, 10))
            
            # CORREÇÃO DE LAYOUT: Colamos a barra de botões no FUNDO da tela primeiro (side="bottom")
            frame_botoes = tk.Frame(frame)
            frame_botoes.pack(side="bottom", fill="x", pady=(10, 0))
            
            # Criamos os botões dentro desse frame que está preso no fundo
            btn_duvida = tk.Button(frame_botoes, text="🤔 Não entendi, mude a explicação", 
                                   command=self.pedir_outra_explicacao, bg="#FF9800", fg="white", font=("Arial", 11, "bold"))
            btn_duvida.pack(side="left", ipadx=10, ipady=8)
            
            btn_continuar = tk.Button(frame_botoes, text="Continuar", 
                                      command=self.mostrar_tela_botao, bg="#2196F3", fg="white", font=("Arial", 11, "bold"))
            btn_continuar.pack(side="left", padx=15, ipadx=15, ipady=8)
            
            btn_finalizar = tk.Button(frame_botoes, text="Finalizar", 
                                      command=self.encerrar_fluxo, bg="#f44336", fg="white", font=("Arial", 11, "bold"))
            btn_finalizar.pack(side="right", ipadx=15, ipady=8)

            # AGORA desenhamos a caixa de texto. Como ela tem expand=True, 
            # ela vai preencher apenas o recheio entre o título e os botões!
            txt = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Arial", 14)) 
            txt.insert(tk.END, resposta_ia) 
            txt.config(state=tk.DISABLED) 
            txt.pack(fill="both", expand=True)
            
            return frame
        self.trocar_frame(construir)

    def pedir_outra_explicacao(self):
        """Envia um comando oculto no chat pedindo outra abordagem mais acessível."""
        comando_oculto = "Não entendi a resposta anterior. Poderia me explicar de outra maneira mais simples, direta e usando termos menos técnicos?"
        self.enviar_para_ia(comando_oculto)

    def encerrar_fluxo(self):
        """Fecha o chat atual, limpa dados e joga a aplicação de volta para standby minimizada."""
        print("[Debug] Fluxo encerrado. Retornando a standby oculto...")
        self.chat_ia = None
        self.escutando_wake_word = True
        self.mostrar_tela_espera()
        self.iconify()  # Minimiza a janela automaticamente na barra de tarefas

# =======================================================
# EXECUÇÃO DO PROGRAMA
# =======================================================
if __name__ == "__main__":
    app = AssistenteApp()
    app.mainloop()