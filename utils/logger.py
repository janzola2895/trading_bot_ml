"""
╔══════════════════════════════════════════════════════════════════════════╗
║                        SISTEMA DE LOGS v5.2                              ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime
import os
from config import LOG_TO_FILE, LOG_FILE_PATH, DATA_DIR


class BotLogger:
    """Sistema de logs para el bot"""
    
    def __init__(self, gui_queue=None):
        self.gui_queue = gui_queue
        self.log_to_file = LOG_TO_FILE
        
        if self.log_to_file:
            if not os.path.exists(DATA_DIR):
                os.makedirs(DATA_DIR)
            
            self.log_file = LOG_FILE_PATH
    
    def log(self, message, level="INFO"):
        """
        Envía mensaje al log
        
        Args:
            message: Mensaje a loggear
            level: Nivel (INFO, WARNING, ERROR, DEBUG)
        """
        # 🆕 FILTRO: No loggear mensajes de MTF detallados
        if any(filter_text in message for filter_text in [
            "TIMEFRAMES SUPERIORES",
            "TIMEFRAMES INFERIORES",
            "ANÁLISIS MULTI-TIMEFRAME",
            "Votos:",
            "Req:"
        ]):
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Enviar a GUI
        if self.gui_queue:
            self.gui_queue.put({'type': 'log', 'message': message})
        else:
            print(formatted_message)
        
        # Guardar en archivo si está habilitado
        if self.log_to_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{formatted_message}\n")
            except Exception as e:
                print(f"Error escribiendo log: {e}")
    
    def info(self, message):
        """Log de información"""
        self.log(message, "INFO")
    
    def warning(self, message):
        """Log de advertencia"""
        self.log(f"⚠️ {message}", "WARNING")
    
    def error(self, message):
        """Log de error"""
        self.log(f"❌ {message}", "ERROR")
    
    def success(self, message):
        """Log de éxito"""
        self.log(f"✅ {message}", "SUCCESS")
    
    def debug(self, message):
        """Log de debug"""
        self.log(f"🔍 {message}", "DEBUG")