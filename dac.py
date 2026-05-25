import tkinter as tk
from tkinter import scrolledtext
import threading
import speech_recognition as sr
import google.generativeai as genai
import re
from gtts import gTTS
import pygame
import os  

# =======================================================
# CONFIGURAÇÃO DA IA (GEMINI)
# =======================================================
genai.configure(api_key="AIzaSyDcSKptO9oDOsgOAKQwF4cpZvMqqDHN9-E")
modelo = genai.GenerativeModel('gemini-2.5-flash')

# =======================================================
# APLICAÇÃO DESKTOP (TKINTER)
# =======================================================
class AssistenteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Assistente de IA Inclusivo")
        self.geometry("750x650") 
        self.configure(padx=25, pady=25)
        
        self.recognizer = sr.Recognizer()
        self.chat_ia = None  
        self.escutando_wake_word = True 
        self.frame_atual = None
        pygame.mixer.init() # Inicializa o sistema de som
        
        # --- VARIÁVEIS DE ACESSIBILIDADE ---
        self.tamanho_fonte = 14
        self.alto_contraste = False
        self.parar_audio = False  # Flag para cortar a voz do robô
        
        self.mostrar_tela_espera()
        
        t = threading.Thread(target=self.loop_wake_word, daemon=True)
        t.start()

    # =======================================================
    # GESTOR DE TEMAS (ALTO CONTRASTE)
    # =======================================================
    def get_cores(self):
        if self.alto_contraste:
            return {
                "bg": "#121212",          
                "fg": "#FFFF00",          
                "bg_caixa": "#2A2A2A",    
                "fg_caixa": "#FFFFFF",    
                "titulo": "#4CAF50"
            }
        else:
            return {
                "bg": "#F0F0F0",          
                "fg": "#000000",          
                "bg_caixa": "#FFFFFF",
                "fg_caixa": "#000000",
                "titulo": "#000000"
            }

    def trocar_frame(self, construtor_frame):
        cores = self.get_cores()
        self.configure(bg=cores["bg"]) 
        
        if self.frame_atual:
            self.frame_atual.destroy()
        self.frame_atual = construtor_frame()
        self.frame_atual.pack(fill="both", expand=True)

    # =======================================================
    # FUNÇÕES DE ACESSIBILIDADE (AÇÕES)
    # =======================================================
    def mudar_fonte(self, delta):
        nova_fonte = self.tamanho_fonte + delta
        if 10 <= nova_fonte <= 24:
            self.tamanho_fonte = nova_fonte
            if hasattr(self, 'ultima_pergunta') and hasattr(self, 'ultima_resposta'):
                self.mostrar_tela_resposta(self.ultima_pergunta, self.ultima_resposta)

    def mudar_contraste(self):
        self.alto_contraste = not self.alto_contraste
        if hasattr(self, 'ultima_pergunta') and hasattr(self, 'ultima_resposta'):
            self.mostrar_tela_resposta(self.ultima_pergunta, self.ultima_resposta)

    def ler_em_voz_alta(self, texto):
        """Lê o texto usando a voz natural do Google (gTTS) com correção de velocidade."""
        self.parar_audio = False 
        
        def thread_ler():
            import time
            import random 
            import os
            from gtts import gTTS
            import pygame
            
            texto_limpo = re.sub(r'\*\*', '', texto)
            texto_limpo = texto_limpo.replace('* ', '')
            texto_limpo = texto_limpo.replace('• ', '')
            
            try:
                # 1. Garante que o pygame está ligado e limpo
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                else:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()

                # 2. Gera um nome de arquivo único
                id_unico = int(time.time()) + random.randint(1, 1000)
                arquivo_audio = f"v_ia_{id_unico}.mp3"
                
                # 3. Baixa e salva o áudio do Google
                tts = gTTS(text=texto_limpo, lang='pt', tld='com.br')
                tts.save(arquivo_audio)
                
                # Pausa para o HD do Windows terminar de salvar o arquivo
                time.sleep(0.5) 
                
                # 4. Carrega, define volume e TOCA
                pygame.mixer.music.load(arquivo_audio)
                pygame.mixer.music.set_volume(1.0)
                pygame.mixer.music.play()
                
                # ---> A MÁGICA ESTÁ AQUI <---
                # Pausa de 0.2 segundos para a placa de som "engatar" o áudio 
                # antes do programa verificar se está tocando.
                time.sleep(0.5)
                
                # 5. Monitora a execução e o botão de parar
                while pygame.mixer.music.get_busy():
                    if self.parar_audio:
                        pygame.mixer.music.stop()
                        break
                    pygame.time.Clock().tick(10)
                    
                # 6. Limpa o áudio da memória
                pygame.mixer.music.unload()
                
                # Tenta apagar o arquivo para manter sua pasta limpa
                try:
                    os.remove(arquivo_audio)
                except:
                    pass
                    
            except Exception as e:
                print(f"Erro ao tentar falar: {e}")
                
        threading.Thread(target=thread_ler, daemon=True).start()

    # =======================================================
    # TELA 1: ESPERA
    # =======================================================
    def mostrar_tela_espera(self):
        cores = self.get_cores()
        def construir():
            frame = tk.Frame(self, bg=cores["bg"])
            lbl = tk.Label(frame, text="Assistente em Standby...\nDiga 'Google me ajuda' para ativar.", 
                           font=("Arial", self.tamanho_fonte), fg=cores["fg"], bg=cores["bg"])
            lbl.pack(expand=True)
            return frame
        self.trocar_frame(construir)

    def loop_wake_word(self):
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
                    
                    if "google me ajuda" in texto:
                        self.escutando_wake_word = False
                        self.chat_ia = modelo.start_chat(history=[])
                        self.after(0, self.restaurar_janela_sistema)
                except Exception:
                    pass

    def restaurar_janela_sistema(self):
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
        self.parar_audio = True # Para o áudio caso o usuário tenha clicado em "Continuar"
        cores = self.get_cores()
        
        def construir():
            frame = tk.Frame(self, bg=cores["bg"])
            lbl = tk.Label(frame, text="Estou ouvindo! Clique no botão abaixo e fale sua dúvida.", 
                           font=("Arial", self.tamanho_fonte), fg=cores["fg"], bg=cores["bg"])
            lbl.pack(pady=30)
            
            btn = tk.Button(frame, text="🎙️ Falar Problema / Dúvida", font=("Arial", 14, "bold"),
                            bg="#4CAF50", fg="white", command=self.ouvir_duvida_usuario)
            btn.pack(ipadx=30, ipady=15, expand=True)
            return frame
        self.trocar_frame(construir)

    def ouvir_duvida_usuario(self):
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
    # TELA DE CONFIRMAÇÃO
    # =======================================================
    def mostrar_tela_confirmacao(self, texto_entendido):
        cores = self.get_cores()
        def construir():
            frame = tk.Frame(self, bg=cores["bg"])
            lbl_titulo = tk.Label(frame, text="Eu entendi isso da sua fala:", font=("Arial", self.tamanho_fonte, "bold"), fg=cores["fg"], bg=cores["bg"]) 
            lbl_titulo.pack(pady=15)
            
            txt_confirmar = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Arial", self.tamanho_fonte), 
                                                      bg=cores["bg_caixa"], fg=cores["fg_caixa"], height=6) 
            txt_confirmar.insert(tk.END, texto_entendido)
            txt_confirmar.pack(fill="x", padx=15, pady=15)
            
            frame_botoes = tk.Frame(frame, bg=cores["bg"])
            frame_botoes.pack(fill="x", pady=25) 
            
            btn_sim = tk.Button(frame_botoes, text="✔️ Confirmar e Enviar", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                                command=lambda: self.enviar_para_ia(txt_confirmar.get("1.0", tk.END).strip()))
            btn_sim.pack(side="left", expand=True, ipadx=15, ipady=10)
            
            btn_nao = tk.Button(frame_botoes, text="❌ Falar Novamente", bg="#f44336", fg="white", font=("Arial", 12, "bold"),
                                command=self.mostrar_tela_botao)
            btn_nao.pack(side="right", expand=True, ipadx=15, ipady=10)
            
            return frame
        self.trocar_frame(construir)

    def enviar_para_ia(self, texto_final):
        self.mostrar_tela_carregando("Pensando... (Chamando IA)")
        def thread_ia():
            try:
                resposta = self.chat_ia.send_message(texto_final)
                self.after(0, self.mostrar_tela_resposta, texto_final, resposta.text)
            except Exception as e:
                self.after(0, self.mostrar_tela_resposta, "Erro na IA", f"Problema de conexão.\nDetalhe: {e}")
        threading.Thread(target=thread_ia, daemon=True).start()

    def mostrar_tela_carregando(self, mensagem):
        cores = self.get_cores()
        def construir():
            frame = tk.Frame(self, bg=cores["bg"])
            lbl = tk.Label(frame, text=mensagem, font=("Arial", self.tamanho_fonte, "italic"), fg="#2196F3", bg=cores["bg"])
            lbl.pack(expand=True)
            return frame
        self.trocar_frame(construir)

    # =======================================================
    # TELA 3: RESPOSTA DA IA (COM BARRA DE ACESSIBILIDADE)
    # =======================================================
    def mostrar_tela_resposta(self, pergunta, resposta_ia):
        self.ultima_pergunta = pergunta
        self.ultima_resposta = resposta_ia
        cores = self.get_cores()
        
        def construir():
            frame = tk.Frame(self, bg=cores["bg"])
            
            frame_aces = tk.Frame(frame, bg=cores["bg"])
            frame_aces.pack(fill="x", pady=(0, 15))
            
            lbl_aces = tk.Label(frame_aces, text="Ferramentas:", font=("Arial", 12, "bold"), bg=cores["bg"], fg=cores["fg"])
            lbl_aces.pack(side="left", padx=(0, 10))
            
            btn_a_menos = tk.Button(frame_aces, text=" A- ", font=("Arial", 11, "bold"), command=lambda: self.mudar_fonte(-2))
            btn_a_menos.pack(side="left", padx=2)
            
            btn_a_mais = tk.Button(frame_aces, text=" A+ ", font=("Arial", 11, "bold"), command=lambda: self.mudar_fonte(2))
            btn_a_mais.pack(side="left", padx=2)
            
            btn_contraste = tk.Button(frame_aces, text="🌓 Contraste", font=("Arial", 11, "bold"), command=self.mudar_contraste)
            btn_contraste.pack(side="left", padx=10)
            
            btn_ouvir = tk.Button(frame_aces, text="🔊 Ler Resposta", font=("Arial", 11, "bold"), bg="#9C27B0", fg="white", command=lambda: self.ler_em_voz_alta(resposta_ia))
            btn_ouvir.pack(side="right")
            
            lbl = tk.Label(frame, text="Resultado do Auxílio:", font=("Arial", self.tamanho_fonte, "bold"), bg=cores["bg"], fg=cores["titulo"]) 
            lbl.pack(anchor="w", pady=(0, 10))
            
            frame_botoes = tk.Frame(frame, bg=cores["bg"])
            frame_botoes.pack(side="bottom", fill="x", pady=(10, 0))
            
            btn_duvida = tk.Button(frame_botoes, text="🤔 Não entendi, mude a explicação", 
                                   command=self.pedir_outra_explicacao, bg="#FF9800", fg="white", font=("Arial", 11, "bold"))
            btn_duvida.pack(side="left", ipadx=10, ipady=8)
            
            btn_continuar = tk.Button(frame_botoes, text="Continuar", 
                                      command=self.mostrar_tela_botao, bg="#2196F3", fg="white", font=("Arial", 11, "bold"))
            btn_continuar.pack(side="left", padx=15, ipadx=15, ipady=8)
            
            btn_finalizar = tk.Button(frame_botoes, text="Finalizar", 
                                      command=self.encerrar_fluxo, bg="#f44336", fg="white", font=("Arial", 11, "bold"))
            btn_finalizar.pack(side="right", ipadx=15, ipady=8)

            txt = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Arial", self.tamanho_fonte), 
                                            bg=cores["bg_caixa"], fg=cores["fg_caixa"]) 
            
            txt.tag_configure("bold", font=("Arial", self.tamanho_fonte, "bold"))
            txt.tag_configure("normal", font=("Arial", self.tamanho_fonte))
            
            partes_do_texto = re.split(r'(\*\*.*?\*\*)', resposta_ia)
            for parte in partes_do_texto:
                if parte.startswith('**') and parte.endswith('**'):
                    texto_negrito = parte[2:-2]
                    txt.insert(tk.END, texto_negrito, "bold")
                else:
                    texto_normal = parte.replace("* ", "• ")
                    txt.insert(tk.END, texto_normal, "normal")
            
            txt.config(state=tk.DISABLED) 
            txt.pack(fill="both", expand=True)
            
            return frame
        self.trocar_frame(construir)

    def pedir_outra_explicacao(self):
        self.parar_audio = True # Para o áudio imediatamente
        comando_oculto = "Não entendi a resposta anterior. Poderia me explicar de outra maneira mais simples, direta e usando termos menos técnicos?"
        self.enviar_para_ia(comando_oculto)

    def encerrar_fluxo(self):
        self.parar_audio = True # Para o áudio imediatamente
        self.chat_ia = None
        self.escutando_wake_word = True
        self.mostrar_tela_espera()
        self.iconify()  

if __name__ == "__main__":
    app = AssistenteApp()
    app.mainloop()