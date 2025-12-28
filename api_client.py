import requests  # type: ignore[reportMissingImports]
import base64
import os
import time
from typing import Dict, Optional

from dotenv import load_dotenv  # type: ignore[reportMissingImports]

try:
    from PIL import Image  # type: ignore[reportMissingImports]
    from transformers import (  # type: ignore[reportMissingImports]
        BlipProcessor,
        BlipForConditionalGeneration,
    )
    _BLIP_AVAILABLE = True
except Exception:
    _BLIP_AVAILABLE = False

load_dotenv()


class ImageRecognitionAPI:
    def __init__(self):
        self._blip_processor = None
        self._blip_model = None
    
    def recognize_image(self, image_path: str) -> Dict:
        """Распознавание изображения"""
        try:
            return self._recognize_local_blip(image_path)
        except Exception as e:
            return {'error': f'Ошибка: {str(e)}'}

    def _ensure_blip_loaded(self) -> Optional[str]:
        if not _BLIP_AVAILABLE:
            return "Локальная модель BLIP недоступна. Установите пакеты: transformers, torch, pillow."

        try:
            if self._blip_processor is None:
                self._blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            if self._blip_model is None:
                self._blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
            return None
        except Exception as e:
            return f"Ошибка загрузки локальной модели BLIP: {str(e)}"

    def _recognize_local_blip(self, image_path: str) -> Dict:
        """Распознавание изображения локальной моделью BLIP"""
        error = self._ensure_blip_loaded()
        if error:
            return {"error": error}

        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            return {"error": f"Не удалось прочитать файл: {str(e)}"}

        try:
            inputs = self._blip_processor(images=image, return_tensors="pt")
            output = self._blip_model.generate(**inputs, max_length=50, num_beams=3)
            caption_en = self._blip_processor.decode(output[0], skip_special_tokens=True).strip()
            if not caption_en:
                return {"error": "Модель не смогла сгенерировать подпись к изображению"}
            
            caption_en = self._clean_caption(caption_en)
            caption_ru = self._translate_to_ru(caption_en)
            return {"caption": caption_ru or caption_en}
        except Exception as e:
            return {"error": f"Ошибка работы локальной модели BLIP: {str(e)}"}
    
    def _clean_caption(self, text: str) -> str:
        """Очистка подписи от повторяющихся слов"""
        if not text:
            return ""
        
        words = text.split()
        if len(words) <= 2:
            return text
        
        word_count = {}
        for word in words:
            word_count[word] = word_count.get(word, 0) + 1
        
        cleaned = []
        seen_repeated = set()
        
        for word in words:
            count = word_count.get(word, 0)
            if count > 3:
                if word not in seen_repeated:
                    cleaned.append(word)
                    seen_repeated.add(word)
            elif count >= 2:
                if not cleaned or cleaned[-1] != word:
                    cleaned.append(word)
            else:
                cleaned.append(word)
        
        result = " ".join(cleaned)
        
        unique_words = set(result.split())
        if len(unique_words) == 1 and len(words) > 3:
            original_unique = []
            seen = set()
            for word in words:
                if word not in seen:
                    original_unique.append(word)
                    seen.add(word)
                    if len(original_unique) >= 3:
                        break
            if len(original_unique) > 1:
                return " ".join(original_unique)
        
        return result
    
    def _translate_to_ru(self, text: str) -> str:
        if not text:
            return ""
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "en",
                "tl": "ru",
                "dt": "t",
                "q": text,
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                return ""
            data = resp.json()
            return str(data[0][0][0]).strip()
        except Exception:
            return ""

