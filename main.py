"""
Простое мобильное приложение для распознавания изображений
"""

from kivymd.app import MDApp  # type: ignore[reportMissingImports]
from kivymd.uix.button import MDRaisedButton  # type: ignore[reportMissingImports]
from kivymd.uix.label import MDLabel  # type: ignore[reportMissingImports]
from kivymd.uix.boxlayout import MDBoxLayout  # type: ignore[reportMissingImports]
from kivymd.uix.card import MDCard  # type: ignore[reportMissingImports]
from kivy.uix.screenmanager import Screen  # type: ignore[reportMissingImports]
from kivy.uix.scrollview import ScrollView  # type: ignore[reportMissingImports]
from kivy.uix.image import Image as KivyImage  # type: ignore[reportMissingImports]
from kivy.uix.filechooser import FileChooserIconView  # type: ignore[reportMissingImports]
from kivy.core.window import Window  # type: ignore[reportMissingImports]
from kivy.clock import Clock  # type: ignore[reportMissingImports]
from kivy.utils import get_color_from_hex, platform  # type: ignore[reportMissingImports]
from kivy.uix.popup import Popup  # type: ignore[reportMissingImports]
from kivy.uix.boxlayout import BoxLayout  # type: ignore[reportMissingImports]

from api_client import ImageRecognitionAPI


class ImageRecognitionScreen(Screen):
    """Главный экран приложения"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_client = ImageRecognitionAPI()
        self.current_image_path = None
        self.build_ui()

        # На мобильных устройствах сразу открываем выбор изображения (галерею/файлы)
        if platform in ("android", "ios"):
            Clock.schedule_once(lambda dt: self.select_image(None), 0.5)
    
    def build_ui(self):
        """Построение интерфейса"""
        main = MDBoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Заголовок
        title = MDLabel(
            text="Image Recognize",
            theme_text_color="Custom",
            text_color=get_color_from_hex("#ffffff"),
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=50,
        )
        main.add_widget(title)
        
        # Кнопка выбора
        self.select_btn = MDRaisedButton(
            text="Выбрать изображение",
            size_hint_y=None,
            height=50,
            on_release=self.select_image
        )
        main.add_widget(self.select_btn)
        
        # Превью изображения
        self.image_container = MDBoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            padding=10,
        )
        self.image_label = MDLabel(
            text="Изображение не выбрано",
            halign="center",
            size_hint_y=None,
            height=220,
        )
        self.image_container.add_widget(self.image_label)

        image_card = MDCard(
            orientation='vertical',
            size_hint=(1, None),
            height=340,
            pos_hint={"center_x": 0.5},
            padding=10,
            radius=[16, 16, 16, 16],
        )
        image_card.add_widget(self.image_container)
        main.add_widget(image_card)
        
        # Кнопка распознавания
        self.recognize_btn = MDRaisedButton(
            text="Распознать",
            size_hint=(1, None),
            height=50,
            disabled=True,
            on_release=self.recognize_image,
        )
        main.add_widget(self.recognize_btn)
        
        # Область результатов
        scroll = ScrollView(size_hint=(1, 1))
        self.results_layout = MDBoxLayout(
            orientation='vertical',
            spacing=10,
            size_hint_y=None,
            adaptive_height=True
        )
        scroll.add_widget(self.results_layout)
        results_card = MDCard(
            orientation='vertical',
            padding=15,
            size_hint=(1, 1),
            radius=[16, 16, 0, 0],
        )
        results_card.add_widget(scroll)
        main.add_widget(results_card)
        
        self.add_widget(main)
    
    def select_image(self, instance):
        """Выбор изображения"""
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        filechooser = FileChooserIconView(filters=['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp'])
        content.add_widget(filechooser)
        
        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_cancel = MDRaisedButton(text="Отмена", on_release=lambda x: popup.dismiss())
        btn_select = MDRaisedButton(
            text="Выбрать",
            on_release=lambda x: self.on_file_selected(filechooser.selection, popup)
        )
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_select)
        content.add_widget(btn_layout)
        
        popup = Popup(title="Выберите изображение", content=content, size_hint=(0.9, 0.9))
        popup.open()
    
    def on_file_selected(self, selection, popup):
        """Обработка выбранного файла"""
        if selection:
            self.current_image_path = selection[0]
            self.image_container.clear_widgets()
            try:
                img = KivyImage(
                    source=self.current_image_path,
                    size_hint=(1, 1),
                    allow_stretch=True,
                    keep_ratio=True
                )
                # Открытие изображения во весь экран
                img.bind(on_touch_down=self.open_fullscreen_image)
                self.image_container.add_widget(img)
                self.recognize_btn.disabled = False
            except Exception as e:
                error_label = MDLabel(
                    text=f"Ошибка загрузки: {str(e)}",
                    halign="center",
                    theme_text_color="Error"
                )
                self.image_container.add_widget(error_label)
            popup.dismiss()
    
    def recognize_image(self, instance):
        """Распознавание изображения"""
        if not self.current_image_path:
            return
        
        self.recognize_btn.disabled = True
        self.recognize_btn.text = "Генерация описания..."
        self.results_layout.clear_widgets()
        
        loading = MDLabel(
            text="Подождите, модель обрабатывает изображение (первый запуск может занять несколько минут)...",
            halign="center",
            size_hint_y=None,
            height=70
        )
        self.results_layout.add_widget(loading)
        
        Clock.schedule_once(lambda dt: self.process_recognition(), 0.1)

    def open_fullscreen_image(self, instance, touch):
        """Открыть выбранное изображение во весь экран по тапу."""
        if not self.current_image_path:
            return False
        if not instance.collide_point(*touch.pos):
            return False

        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        img = KivyImage(
            source=self.current_image_path,
            allow_stretch=True,
            keep_ratio=True,
        )
        content.add_widget(img)

        btn_close = MDRaisedButton(
            text="Закрыть",
            size_hint_y=None,
            height=50,
        )

        popup = Popup(
            title="Просмотр изображения",
            content=content,
            size_hint=(1, 1),
        )
        btn_close.bind(on_release=lambda *args: popup.dismiss())
        content.add_widget(btn_close)

        popup.open()
        return True
    
    def process_recognition(self):
        """Обработка распознавания"""
        self.results_layout.clear_widgets()
        
        try:
            results = self.api_client.recognize_image(self.current_image_path)
            self.display_results(results)
        except Exception as e:
            self.show_error(f"Критическая ошибка: {str(e)}")
        finally:
            self.recognize_btn.disabled = False
            self.recognize_btn.text = "Распознать"
    
    def show_error(self, message):
        """Показать ошибку"""
        error_card = MDCard(
            orientation='vertical',
            padding=15,
            spacing=10,
            size_hint_y=None,
            adaptive_height=True
        )
        error_label = MDLabel(
            text=message,
            halign="center",
            theme_text_color="Error",
            size_hint_y=None,
            adaptive_height=True
        )
        error_card.add_widget(error_label)
        self.results_layout.add_widget(error_card)
    
    def display_results(self, results):
        """Отображение результатов"""
        # Проверка на ошибку
        if 'error' in results:
            self.show_error(results['error'])
            return
        
        has_labels = bool(results.get('labels'))
        has_text = bool(results.get('text'))
        has_description = bool(results.get('description'))
        has_caption = bool(results.get('caption'))

        # Проверка на полностью пустые результаты
        if not (has_labels or has_text or has_description or has_caption):
            self.show_error("Результаты не найдены")
            return
        
        # Отображение объектов
        labels = results.get('labels', [])
        if labels:
            card = MDCard(
                orientation='vertical',
                padding=15,
                spacing=10,
                size_hint_y=None,
                adaptive_height=True
            )
            title = MDLabel(
                text="Распознанные объекты:",
                font_style="Subtitle1",
                size_hint_y=None,
                height=30
            )
            card.add_widget(title)
            
            for label in labels:
                name = label.get('name', 'Неизвестно')
                confidence = label.get('confidence', 0)
                text = f"• {name}"
                if confidence > 0:
                    text += f" ({confidence:.1%})"
                
                item = MDLabel(
                    text=text,
                    size_hint_y=None,
                    height=30,
                    adaptive_height=True
                )
                card.add_widget(item)
            
            self.results_layout.add_widget(card)
        
        # Отображение текста
        if 'text' in results and results['text']:
            card = MDCard(
                orientation='vertical',
                padding=15,
                spacing=10,
                size_hint_y=None,
                adaptive_height=True
            )
            title = MDLabel(
                text="Распознанный текст:",
                font_style="Subtitle1",
                size_hint_y=None,
                height=30
            )
            card.add_widget(title)
            text_label = MDLabel(
                text=results['text'],
                size_hint_y=None,
                adaptive_height=True
            )
            card.add_widget(text_label)
            self.results_layout.add_widget(card)
        
        # Отображение описания
        if 'description' in results and results['description']:
            card = MDCard(
                orientation='vertical',
                padding=15,
                spacing=10,
                size_hint_y=None,
                adaptive_height=True
            )
            title = MDLabel(
                text="Описание:",
                font_style="Subtitle1",
                size_hint_y=None,
                height=30
            )
            card.add_widget(title)
            desc_label = MDLabel(
                text=results['description'],
                size_hint_y=None,
                adaptive_height=True
            )
            card.add_widget(desc_label)
            self.results_layout.add_widget(card)

        # Отображение подписи к изображению
        if 'caption' in results and results['caption']:
            card = MDCard(
                orientation='vertical',
                padding=15,
                spacing=10,
                size_hint_y=None,
                adaptive_height=True
            )
            title = MDLabel(
                text="Описание изображения:",
                font_style="Subtitle1",
                size_hint_y=None,
                height=30
            )
            card.add_widget(title)
            caption_label = MDLabel(
                text=results['caption'],
                size_hint_y=None,
                adaptive_height=True
            )
            card.add_widget(caption_label)
            self.results_layout.add_widget(card)


class ImageRecognitionApp(MDApp):
    """Главный класс приложения"""
    
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Purple"
        Window.clearcolor = get_color_from_hex("#1a1a2e")
        return ImageRecognitionScreen()


if __name__ == '__main__':
    ImageRecognitionApp().run()
