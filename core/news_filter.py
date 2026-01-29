"""
╔══════════════════════════════════════════════════════════════════════════╗
║          ECONOMIC NEWS FILTER - Filtro de Noticias v1.0                 ║
║                                                                          ║
║  Pausa el trading durante noticias económicas de alto impacto           ║
║  - Buffer de 15 min antes y después de eventos                          ║
║  - Actualización automática cada 12 horas                               ║
║  - Previene pérdidas por volatilidad extrema                            ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
from datetime import datetime, timedelta


class EconomicNewsFilter:
    """
    Filtro de noticias económicas de alto impacto
    
    Pausa el trading automáticamente durante ventanas de riesgo
    alrededor de eventos económicos importantes (NFP, CPI, FOMC, etc.)
    """
    
    def __init__(self, data_dir="bot_data", logger=None):
        self.data_dir = data_dir
        self.logger = logger
        self.news_file = os.path.join(data_dir, "economic_calendar.json")
        
        # Crear directorio si no existe
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Configuración
        self.buffer_minutes_before = 15  # Pausar 15 min antes del evento
        self.buffer_minutes_after = 15   # Pausar 15 min después del evento
        self.update_interval_hours = 12  # Actualizar calendario cada 12 horas
        
        # Eventos de alto impacto
        self.high_impact_events = []
        self.last_update = None
        
        # Cargar eventos cacheados
        self.load_cached_events()
    
    def send_log(self, message):
        """Envía log si hay logger"""
        if self.logger:
            self.logger.info(message)
    
    def load_cached_events(self):
        """Carga eventos del cache"""
        if os.path.exists(self.news_file):
            try:
                with open(self.news_file, 'r') as f:
                    data = json.load(f)
                    
                    # Convertir strings a datetime
                    events = data.get('events', [])
                    self.high_impact_events = []
                    
                    for event in events:
                        event_copy = event.copy()
                        event_copy['time'] = datetime.fromisoformat(event['time'])
                        self.high_impact_events.append(event_copy)
                    
                    last_update_str = data.get('last_update')
                    if last_update_str:
                        self.last_update = datetime.fromisoformat(last_update_str)
                
                # Limpiar eventos pasados
                now = datetime.now()
                self.high_impact_events = [
                    e for e in self.high_impact_events 
                    if e['time'] > (now - timedelta(hours=2))
                ]
                
                if self.high_impact_events:
                    self.send_log(f"📰 Calendario cargado: {len(self.high_impact_events)} eventos")
                
                return True
            except Exception as e:
                self.send_log(f"⚠️ Error cargando calendario: {e}")
                return False
        return False
    
    def save_cached_events(self):
        """Guarda eventos en cache"""
        try:
            # Convertir datetime a string
            events_serializable = []
            for event in self.high_impact_events:
                event_copy = event.copy()
                event_copy['time'] = event['time'].isoformat()
                events_serializable.append(event_copy)
            
            data = {
                'events': events_serializable,
                'last_update': self.last_update.isoformat() if self.last_update else datetime.now().isoformat()
            }
            
            with open(self.news_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.send_log(f"⚠️ Error guardando calendario: {e}")
    
    def needs_update(self):
        """Verifica si necesita actualizar calendario"""
        if not self.last_update:
            return True
        
        hours_since_update = (datetime.now() - self.last_update).total_seconds() / 3600
        return hours_since_update >= self.update_interval_hours
    
    def update_calendar(self):
        """
        Actualiza calendario económico
        
        NOTA: Implementación simplificada
        Para producción, usar API como:
        - https://nfs.faireconomy.media/ff_calendar_thisweek.json
        - https://www.investing.com/economic-calendar/
        - https://www.forexfactory.com/calendar
        """
        try:
            # Por ahora, crear eventos de ejemplo
            # En producción, hacer request a API real
            
            self.send_log("📰 Actualizando calendario económico...")
            
            # Eventos ejemplo (reemplazar con API real)
            now = datetime.now()
            
            self.high_impact_events = [
                {
                    'name': 'US Non-Farm Payrolls (NFP)',
                    'time': now.replace(hour=13, minute=30) + timedelta(days=3),
                    'impact': 'high',
                    'currency': 'USD'
                },
                {
                    'name': 'US CPI (Inflation)',
                    'time': now.replace(hour=13, minute=30) + timedelta(days=7),
                    'impact': 'high',
                    'currency': 'USD'
                },
                {
                    'name': 'Fed Interest Rate Decision',
                    'time': now.replace(hour=19, minute=0) + timedelta(days=14),
                    'impact': 'high',
                    'currency': 'USD'
                },
                {
                    'name': 'ECB Interest Rate Decision',
                    'time': now.replace(hour=12, minute=45) + timedelta(days=10),
                    'impact': 'high',
                    'currency': 'EUR'
                }
            ]
            
            self.last_update = datetime.now()
            self.save_cached_events()
            
            self.send_log(f"✅ Calendario actualizado: {len(self.high_impact_events)} eventos")
            
        except Exception as e:
            self.send_log(f"⚠️ Error actualizando calendario: {e}")
    
    def is_safe_to_trade(self):
        """
        Verifica si es seguro operar (no hay noticias cercanas)
        
        Returns:
            tuple: (is_safe: bool, reason: str)
        """
        # Actualizar si es necesario
        if self.needs_update():
            self.update_calendar()
        elif not self.high_impact_events:
            self.load_cached_events()
        
        now = datetime.now()
        
        for event in self.high_impact_events:
            event_time = event['time']
            
            # Calcular diferencia en minutos
            time_diff_seconds = (event_time - now).total_seconds()
            time_diff_minutes = time_diff_seconds / 60
            
            # Verificar si estamos en ventana de riesgo
            if -self.buffer_minutes_after <= time_diff_minutes <= self.buffer_minutes_before:
                return False, f"⏰ Noticia cercana: {event['name']} en {abs(time_diff_minutes):.0f} min"
        
        return True, "✅ Sin noticias cercanas"
    
    def get_upcoming_events(self, hours_ahead=24):
        """
        Retorna eventos próximos en las siguientes N horas
        
        Args:
            hours_ahead: Horas hacia adelante a buscar
        
        Returns:
            list: Lista de eventos próximos
        """
        if self.needs_update():
            self.update_calendar()
        
        now = datetime.now()
        cutoff = now + timedelta(hours=hours_ahead)
        
        upcoming = [
            e for e in self.high_impact_events
            if now <= e['time'] <= cutoff
        ]
        
        # Ordenar por tiempo
        upcoming.sort(key=lambda x: x['time'])
        
        return upcoming
    
    def get_stats(self):
        """Retorna estadísticas del filtro"""
        return {
            'total_events': len(self.high_impact_events),
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'buffer_minutes_before': self.buffer_minutes_before,
            'buffer_minutes_after': self.buffer_minutes_after
        }
    
    def update_config(self, buffer_before=None, buffer_after=None):
        """Actualiza configuración del filtro"""
        if buffer_before is not None:
            self.buffer_minutes_before = buffer_before
        
        if buffer_after is not None:
            self.buffer_minutes_after = buffer_after
        
        self.send_log(f"⚙️ News Filter: buffer_before={self.buffer_minutes_before}min, "
                     f"buffer_after={self.buffer_minutes_after}min")