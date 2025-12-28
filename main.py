"""
Приложение для пакетного распознавания изображений из папки
"""

import os
import glob
from kivymd.app import MDApp  # type: ignore[reportMissingImports]
from kivymd.uix.button import MDRaisedButton  # type: ignore[reportMissingImports]
from kivymd.uix.label import MDLabel  # type: ignore[reportMissingImports]
from kivymd.uix.boxlayout import MDBoxLayout  # type: ignore[reportMissingImports]
from kivymd.uix.card import MDCard  # type: ignore[reportMissingImports]
from kivy.uix.screenmanager import Screen  # type: ignore[reportMissingImports]
from kivy.uix.scrollview import ScrollView  # type: ignore[reportMissingImports]
from kivy.uix.filechooser import FileChooserIconView  # type: ignore[reportMissingImports]
from kivy.core.window import Window  # type: ignore[reportMissingImports]
from kivy.clock import Clock  # type: ignore[reportMissingImports]
from kivy.utils import get_color_from_hex, platform  # type: ignore[reportMissingImports]
from kivy.uix.popup import Popup  # type: ignore[reportMissingImports]
from kivy.uix.boxlayout import BoxLayout  # type: ignore[reportMissingImports]
from kivy.uix.image import Image as KivyImage  # type: ignore[reportMissingImports]

from api_client import ImageRecognitionAPI


class ImageRecognitionScreen(Screen):
    """Главный экран приложения"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_client = ImageRecognitionAPI()
        self.selected_folder = None
        self.image_paths = []
        self.results_data = []
        self._current_popup = None
        self.build_ui()

        if platform in ("android", "ios"):
            Clock.schedule_once(lambda dt: self.select_folder(None), 0.5)
    
    def build_ui(self):
        """Построение интерфейса"""
        main = MDBoxLayout(orientation='vertical', padding=20, spacing=15)
        
        title = MDLabel(
            text="Пакетное распознавание изображений",
            theme_text_color="Custom",
            text_color=get_color_from_hex("#ffffff"),
            font_style="H5",
            halign="center",
            size_hint_y=None,
            height=50,
        )
        main.add_widget(title)
        
        self.folder_label = MDLabel(
            text="Папка не выбрана",
            theme_text_color="Secondary",
            halign="center",
            size_hint_y=None,
            height=30,
        )
        main.add_widget(self.folder_label)
        
        self.select_btn = MDRaisedButton(
            text="Выбрать папку с изображениями",
            size_hint_y=None,
            height=50,
            on_release=self.select_folder
        )
        main.add_widget(self.select_btn)
        
        self.recognize_btn = MDRaisedButton(
            text="Распознать все изображения",
            size_hint=(1, None),
            height=50,
            disabled=True,
            on_release=self.recognize_images,
        )
        main.add_widget(self.recognize_btn)
        
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
    
    def select_folder(self, instance):
        """Выбор папки с изображениями"""
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        info_label = MDLabel(
            text="Дважды кликните по папке или выберите папку и нажмите 'Выбрать'",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=40,
            halign="center"
        )
        content.add_widget(info_label)
        
        filechooser = FileChooserIconView()
        filechooser.bind(on_submit=self.on_folder_double_click)
        content.add_widget(filechooser)
        
        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        btn_cancel = MDRaisedButton(text="Отмена", on_release=lambda x: popup.dismiss())
        btn_select = MDRaisedButton(
            text="Выбрать текущую папку",
            on_release=lambda x: self.on_folder_selected(filechooser.path, popup)
        )
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_select)
        content.add_widget(btn_layout)
        
        popup = Popup(title="Выберите папку с изображениями", content=content, size_hint=(0.9, 0.9))
        self._current_popup = popup
        popup.open()
    
    def on_folder_double_click(self, filechooser, path, selection):
        """Обработка двойного клика по папке"""
        if os.path.isdir(path):
            self.on_folder_selected(path, self._current_popup)
    
    def on_folder_selected(self, folder_path, popup):
        """Обработка выбранной папки"""
        if folder_path and os.path.isdir(folder_path):
            self.selected_folder = folder_path
            extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.PNG', '*.JPG', '*.JPEG']
            self.image_paths = []
            for ext in extensions:
                self.image_paths.extend(glob.glob(os.path.join(folder_path, ext)))
                self.image_paths.extend(glob.glob(os.path.join(folder_path, '**', ext), recursive=True))
            
            self.image_paths = sorted(list(set(self.image_paths)))
            
            count = len(self.image_paths)
            self.folder_label.text = f"Выбрана папка: {os.path.basename(folder_path)} ({count} изображений)"
            self.recognize_btn.disabled = count == 0
            
            if count == 0:
                self.show_error("В выбранной папке не найдено изображений")
            popup.dismiss()
    
    def recognize_images(self, instance):
        """Распознавание всех изображений из папки"""
        if not self.image_paths:
            return
        
        self.recognize_btn.disabled = True
        self.recognize_btn.text = f"Обработка 0/{len(self.image_paths)}..."
        self.results_layout.clear_widgets()
        self.results_data = []
        
        loading = MDLabel(
            text="Подождите, модель обрабатывает изображения (первый запуск может занять несколько минут)...",
            halign="center",
            size_hint_y=None,
            height=70
        )
        self.results_layout.add_widget(loading)
        
        Clock.schedule_once(lambda dt: self.process_batch_recognition(), 0.1)
    
    def process_batch_recognition(self):
        """Пакетная обработка всех изображений"""
        self.results_layout.clear_widgets()
        total = len(self.image_paths)
        
        for idx, image_path in enumerate(self.image_paths):
            try:
                self.recognize_btn.text = f"Обработка {idx + 1}/{total}..."
                results = self.api_client.recognize_image(image_path)
                
                if 'error' in results:
                    description = f"Ошибка: {results['error']}"
                else:
                    description = results.get('caption', 'Описание не получено')
                
                self.results_data.append({
                    'image_path': image_path,
                    'description': description
                })
                
            except Exception as e:
                self.results_data.append({
                    'image_path': image_path,
                    'description': f"Ошибка: {str(e)}"
                })
        
        self.display_table_results()
        self.recognize_btn.disabled = False
        self.recognize_btn.text = "Распознать все изображения"
    
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
    
    def display_table_results(self):
        """Отображение результатов в виде таблицы с изображениями"""
        if not self.results_data:
            self.show_error("Нет данных для отображения")
            return
        
        title_card = MDCard(
            orientation='vertical',
            padding=15,
            size_hint_y=None,
            height=50,
            radius=[16, 16, 0, 0],
        )
        title = MDLabel(
            text=f"Результаты распознавания ({len(self.results_data)} изображений)",
            font_style="Subtitle1",
            halign="center",
            size_hint_y=None,
            height=30,
        )
        title_card.add_widget(title)
        self.results_layout.add_widget(title_card)
        
        header_card = MDCard(
            orientation='horizontal',
            padding=10,
            size_hint_y=None,
            height=40,
            radius=[0, 0, 0, 0],
        )
        
        header_image = MDLabel(
            text="Изображение",
            font_style="Subtitle2",
            size_hint_x=0.3,
            halign="center",
        )
        header_description = MDLabel(
            text="Описание",
            font_style="Subtitle2",
            size_hint_x=0.7,
            halign="center",
        )
        header_card.add_widget(header_image)
        header_card.add_widget(header_description)
        self.results_layout.add_widget(header_card)
        
        for idx, result in enumerate(self.results_data):
            row_card = MDCard(
                orientation='horizontal',
                padding=10,
                spacing=10,
                size_hint_y=None,
                height=120,
                radius=[0, 0, 0, 0] if idx < len(self.results_data) - 1 else [0, 0, 16, 16],
            )
            
            image_container = MDBoxLayout(
                orientation='vertical',
                size_hint_x=0.3,
                padding=5,
            )
            try:
                img = KivyImage(
                    source=result['image_path'],
                    allow_stretch=True,
                    keep_ratio=True,
                    size_hint=(1, 1),
                )
                img.bind(on_touch_down=lambda instance, touch, path=result['image_path']: self.open_fullscreen_image(path, touch))
                image_container.add_widget(img)
            except Exception:
                error_label = MDLabel(
                    text="Ошибка\nзагрузки",
                    halign="center",
                    theme_text_color="Error",
                    size_hint=(1, 1),
                )
                image_container.add_widget(error_label)
            
            row_card.add_widget(image_container)
            
            description_container = MDBoxLayout(
                orientation='vertical',
                size_hint_x=0.7,
                padding=5,
            )
            description_label = MDLabel(
                text=result['description'],
                halign="left",
                valign="top",
                size_hint_y=None,
                adaptive_height=True,
                text_size=(None, None),
            )
            description_container.add_widget(description_label)
            row_card.add_widget(description_container)
            
            self.results_layout.add_widget(row_card)
    
    def open_fullscreen_image(self, image_path, touch):
        """Открыть изображение во весь экран по клику"""
        if not image_path or not touch.is_double_tap:
            return False
        
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        try:
            img = KivyImage(
                source=image_path,
                allow_stretch=True,
                keep_ratio=True,
            )
            content.add_widget(img)
        except Exception:
            error_label = MDLabel(
                text="Не удалось загрузить изображение",
                halign="center",
                theme_text_color="Error",
            )
            content.add_widget(error_label)
        
        btn_close = MDRaisedButton(
            text="Закрыть",
            size_hint_y=None,
            height=50,
        )
        
        popup = Popup(
            title=os.path.basename(image_path),
            content=content,
            size_hint=(0.9, 0.9),
        )
        btn_close.bind(on_release=lambda *args: popup.dismiss())
        content.add_widget(btn_close)
        
        popup.open()
        return True


class ImageRecognitionApp(MDApp):
    """Главный класс приложения"""
    
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Purple"
        Window.clearcolor = get_color_from_hex("#1a1a2e")
        return ImageRecognitionScreen()


if __name__ == '__main__':
    ImageRecognitionApp().run()
