"""
Audio Recorder - Moduł nagrywania dźwięku
=========================================

Moduł obsługujący nagrywanie audio z mikrofonu:
- Nagrywanie w czasie rzeczywistym
- Zapis do formatu WAV
- Pauza i wznawianie nagrywania
- Monitorowanie poziomu dźwięku
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
from loguru import logger
import queue
import threading


class AudioRecorder:
    """
    Klasa do nagrywania audio z mikrofonu.
    
    Attributes:
        sample_rate (int): Częstotliwość próbkowania (Hz)
        channels (int): Liczba kanałów (1=mono, 2=stereo)
        is_recording (bool): Czy trwa nagrywanie
        is_paused (bool): Czy nagrywanie jest wstrzymane
    """
    
    def __init__(self, sample_rate: int = 44100, channels: int = 1):
        """
        Inicjalizacja nagrywarki audio.
        
        Args:
            sample_rate: Częstotliwość próbkowania (domyślnie 44100 Hz)
            channels: Liczba kanałów (domyślnie 1 - mono)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.is_paused = False
        
        # Kolejka do przechowywania bloków audio
        self.audio_queue = queue.Queue()
        
        # Lista wszystkich nagranych bloków
        self.recorded_frames = []
        
        # Stream audio
        self.stream: Optional[sd.InputStream] = None
        
        # Callback dla poziomu głośności
        self.level_callback: Optional[Callable[[float], None]] = None
        
        logger.info(f"AudioRecorder initialized: {sample_rate}Hz, {channels} channel(s)")
    
    def set_level_callback(self, callback: Callable[[float], None]):
        """
        Ustaw callback wywoływany przy każdym bloku audio z poziomem głośności.
        
        Args:
            callback: Funkcja przyjmująca float (0.0-1.0) reprezentujący poziom głośności
        """
        self.level_callback = callback
    
    def _audio_callback(self, indata, frames, time_info, status):
        """
        Callback wywoływany przez sounddevice dla każdego bloku audio.
        
        Args:
            indata: Dane audio
            frames: Liczba ramek
            time_info: Informacje o czasie
            status: Status strumienia
        """
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        # Jeśli nie jesteśmy w pauzie, dodaj dane do kolejki
        if not self.is_paused:
            self.audio_queue.put(indata.copy())
            
            # Oblicz poziom głośności (RMS)
            if self.level_callback:
                volume_norm = np.linalg.norm(indata) * 10
                volume_level = min(1.0, volume_norm)  # Normalizuj do 0.0-1.0
                self.level_callback(volume_level)
    
    def start_recording(self, output_path: Optional[Path] = None) -> Path:
        """
        Rozpocznij nagrywanie.
        
        Args:
            output_path: Ścieżka do pliku wyjściowego (opcjonalnie)
            
        Returns:
            Path: Ścieżka do pliku, w którym zostanie zapisane nagranie
            
        Raises:
            RuntimeError: Jeśli nagrywanie już trwa
        """
        if self.is_recording:
            raise RuntimeError("Recording already in progress")
        
        # Jeśli nie podano ścieżki, utwórz domyślną
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"recording_{timestamp}.wav")
        
        self.output_path = output_path
        self.is_recording = True
        self.is_paused = False
        self.recorded_frames = []
        
        # Wyczyść kolejkę
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        # Uruchom stream audio
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback
            )
            self.stream.start()
            
            # Uruchom wątek przetwarzający kolejkę
            self._processing_thread = threading.Thread(target=self._process_queue, daemon=True)
            self._processing_thread.start()
            
            logger.info(f"Recording started: {output_path}")
            
        except Exception as e:
            self.is_recording = False
            logger.error(f"Failed to start recording: {e}")
            raise
        
        return self.output_path
    
    def _process_queue(self):
        """
        Wątek przetwarzający kolejkę audio i dodający ramki do listy.
        """
        while self.is_recording:
            try:
                # Pobierz blok z kolejki (timeout 0.1s)
                block = self.audio_queue.get(timeout=0.1)
                self.recorded_frames.append(block)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing audio queue: {e}")
    
    def pause_recording(self):
        """
        Wstrzymaj nagrywanie (można wznowić za pomocą resume_recording).
        
        Raises:
            RuntimeError: Jeśli nagrywanie nie jest w trakcie
        """
        if not self.is_recording:
            raise RuntimeError("No recording in progress")
        
        self.is_paused = True
        logger.info("Recording paused")
    
    def resume_recording(self):
        """
        Wznów wstrzymane nagrywanie.
        
        Raises:
            RuntimeError: Jeśli nagrywanie nie jest w trakcie lub nie jest wstrzymane
        """
        if not self.is_recording:
            raise RuntimeError("No recording in progress")
        
        if not self.is_paused:
            raise RuntimeError("Recording is not paused")
        
        self.is_paused = False
        logger.info("Recording resumed")
    
    def stop_recording(self) -> Path:
        """
        Zatrzymaj nagrywanie i zapisz do pliku.
        
        Returns:
            Path: Ścieżka do zapisanego pliku
            
        Raises:
            RuntimeError: Jeśli nagrywanie nie jest w trakcie
        """
        if not self.is_recording:
            raise RuntimeError("No recording in progress")
        
        self.is_recording = False
        self.is_paused = False
        
        # Zatrzymaj stream
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        # Poczekaj na zakończenie wątku przetwarzającego
        if hasattr(self, '_processing_thread'):
            self._processing_thread.join(timeout=1.0)
        
        # Połącz wszystkie ramki
        if self.recorded_frames:
            recording = np.concatenate(self.recorded_frames, axis=0)
            
            # Zapisz do pliku
            try:
                # Upewnij się, że katalog istnieje
                self.output_path.parent.mkdir(parents=True, exist_ok=True)
                
                sf.write(
                    str(self.output_path),
                    recording,
                    self.sample_rate
                )
                logger.info(f"Recording saved: {self.output_path} ({len(recording)} frames)")
                
            except Exception as e:
                logger.error(f"Failed to save recording: {e}")
                raise
        else:
            logger.warning("No audio data recorded")
        
        return self.output_path
    
    def get_duration(self) -> float:
        """
        Pobierz aktualny czas trwania nagrania w sekundach.
        
        Returns:
            float: Czas trwania w sekundach
        """
        if not self.recorded_frames:
            return 0.0
        
        total_frames = sum(len(block) for block in self.recorded_frames)
        return total_frames / self.sample_rate
    
    def cancel_recording(self):
        """
        Anuluj nagrywanie bez zapisywania.
        """
        if not self.is_recording:
            return
        
        self.is_recording = False
        self.is_paused = False
        
        # Zatrzymaj stream
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        # Wyczyść dane
        self.recorded_frames = []
        
        logger.info("Recording cancelled")
    
    @staticmethod
    def get_available_devices() -> list:
        """
        Pobierz listę dostępnych urządzeń audio.
        
        Returns:
            list: Lista słowników z informacjami o urządzeniach
        """
        try:
            devices = sd.query_devices()
            return [
                {
                    'index': i,
                    'name': dev['name'],
                    'channels': dev['max_input_channels'],
                    'sample_rate': dev['default_samplerate']
                }
                for i, dev in enumerate(devices)
                if dev['max_input_channels'] > 0  # Tylko urządzenia wejściowe
            ]
        except Exception as e:
            logger.error(f"Failed to query audio devices: {e}")
            return []
    
    @staticmethod
    def get_default_device() -> Optional[dict]:
        """
        Pobierz domyślne urządzenie wejściowe.
        
        Returns:
            dict: Informacje o domyślnym urządzeniu lub None
        """
        try:
            device = sd.query_devices(kind='input')
            return {
                'name': device['name'],
                'channels': device['max_input_channels'],
                'sample_rate': device['default_samplerate']
            }
        except Exception as e:
            logger.error(f"Failed to query default device: {e}")
            return None
