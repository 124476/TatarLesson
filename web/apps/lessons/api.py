__all__ = ()

import base64
import logging

from django.conf import settings

import requests

logger = logging.getLogger(__name__)


class TatSoftAPI:
    """Клиент для работы с API TatSoft."""

    TTS_URL = "https://tat-tts.api.translate.tatar/listening/"
    ASR_URL = "https://tat-asr.api.translate.tatar/listening/"
    MT_URL = "https://v2.api.translate.tatar/listening/"
    MORPH_URL = "https://tugantel.tatar/new2022/morph"
    TIMEOUT = 30

    # ===== Синтез речи =====
    @classmethod
    def synthesize(cls, text: str, speaker: str = "alsu") -> bytes | None:
        """
        Синтез татарской речи.
        Возвращает WAV-байты или None при ошибке.
        speaker: 'alsu' или 'almaz'
        """
        try:
            response = requests.get(
                cls.TTS_URL,
                params={"speaker": speaker, "text": text},
                timeout=cls.TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            wav_b64 = data.get("wav_base64")
            if not wav_b64:
                logger.error("TTS: нет поля wav_base64")
                return None
            return base64.b64decode(wav_b64)
        except requests.RequestException as e:
            logger.error("TTS error: %s", e)
            return None

    # ===== Распознавание речи =====
    @classmethod
    def recognize(cls, audio_bytes: bytes, filename: str = "voice.wav") -> str | None:
        """
        Распознавание татарской речи.
        Принимает WAV/MP3 байты, возвращает текст.
        """
        try:
            files = {"file": (filename, audio_bytes, "audio/wav")}
            response = requests.post(
                cls.ASR_URL,
                params={"model": "old_model"},
                files=files,
                timeout=cls.TIMEOUT,
            )
            response.raise_for_status()
            # API возвращает текст или JSON
            try:
                data = response.json()
                if isinstance(data, dict):
                    return data.get("text") or data.get("result")
                return str(data)
            except ValueError:
                return response.text
        except requests.RequestException as e:
            logger.error("ASR error: %s", e)
            return None

    # ===== Перевод =====
    @classmethod
    def translate(cls, text: str, src: str = "ru", dst: str = "tt") -> str | None:
        """
        Перевод между русским и татарским.
        src/dst: 'ru' или 'tt'
        """
        # Формируем lang
        if src == "ru" and dst == "tt":
            lang = "rus2tat"
        elif src == "tt" and dst == "ru":
            lang = "tat2rus"
        else:
            logger.error("Translate: неподдерживаемая пара %s→%s", src, dst)
            return None

        try:
            response = requests.get(
                cls.MT_URL,
                params={"lang": lang, "text": text},
                timeout=cls.TIMEOUT,
            )
            response.raise_for_status()
            # API возвращает строку (возможно в кавычках)
            result = response.text.strip().strip('"')
            return result
        except requests.RequestException as e:
            logger.error("Translate error: %s", e)
            return None

    # ===== Морфоанализатор =====
    @classmethod
    def morphology(cls, text: str) -> list | None:
        """
        Морфологический разбор текста.
        Возвращает список с разметкой.
        """
        try:
            response = requests.post(
                cls.MORPH_URL,
                params={"json": "data"},
                data={"text": text},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=cls.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("Morphology error: %s", e)
            return None