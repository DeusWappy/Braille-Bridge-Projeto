from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.image import Image
import pdfplumber
from Algoritmo import tradutor
import serial

class LoadingScreen(Screen):
    def on_enter(self):
        self.pb = self.ids.progress_bar
       
        Clock.schedule_once(self.start_loading, 1)

    def start_loading(self, dt):
        Clock.schedule_interval(self.update_progress_bar, 0.1)

    def update_progress_bar(self, dt):
        self.pb.value += 5
        if self.pb.value >= 100:
            Clock.schedule_once(self.switch_to_main, 1)

    def switch_to_main(self, dt):
        self.manager.current = 'main_screen'

class MainScreen(Screen):
    def process_input(self, selected_file, input_text):
        if selected_file:
            pdf_path = selected_file[0]
            self.process_pdf(pdf_path)
        elif input_text.lower().endswith('.pdf'):
            self.process_pdf(input_text)
        else:
            self.process_string(input_text)

    def process_pdf(self, pdf_path):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ''
                for page in pdf.pages:
                    text += page.extract_text()
            self.show_result(text)
        except Exception as e:
            self.print(str(e))

    def process_string(self, input_string):
        self.show_result(input_string)

    def show_result(self, result):
        self.result = result
        self.translation = ""
        self.index = 0
        self.modo_aprendizagem_var = False
        self.translation_popup = Popup(title='Tradução', size_hint=(None, None), size=(400, 400))
    
        main_layout = BoxLayout(orientation='vertical')
    
        scroll_view = ScrollView(size_hint=(1, 1))
        self.translation_label = Label(text='A traduzir...', size_hint = (1,1), pos_hint = {'center_x': 0.5,'center_y':0.5}, font_size="20sp")
        self.translation_label.bind(texture_size=self.translation_label.setter('size'))  
        scroll_view.add_widget(self.translation_label)
        main_layout.add_widget(scroll_view)
        self.parar_botao = Button(text='Parar', size_hint=(None, None), height=40, on_press=self.stop_translation)
        main_layout.add_widget(self.parar_botao)
    
        self.translation_popup.content = main_layout
        self.translation_popup.open()
        self.is_translating = True
        self.arduino_opened = False  # Indica se a conexão com o Arduino está aberta
        self.translate_next_character(0)  # Inicia a tradução

    def translate_next_character(self, dt):
        if self.index < len(self.result) and self.is_translating:
            char = self.result[self.index]
            matriz = tradutor(char)
            self.translation += char + ":" + '\n' + '\n'.join(''.join(map(str, row)) for row in matriz) + "\n\n"
            #self.translation_label.text += translation
            print(matriz)
            self.send_to_arduino(matriz)
            self.index += 1
            Clock.schedule_once(self.translate_next_character, 2)  # Agenda a próxima tradução após 2 segundos
        else:
           print(self.index)
           final_layout = BoxLayout(orientation='vertical')
           final_label = Label(text='Deseja ver o modo de aprendizagem?', size_hint=(1, 1))
           final_layout.add_widget(final_label)
        
           button_layout = BoxLayout(size_hint_y=None, height=40)
           button_layout.add_widget(Button(text='Sim', size_hint=(None, None), on_press=self.modo_aprendizagem))
           button_layout.add_widget(Button(text='Não', size_hint=(None, None), on_press=self.final_popup_dismiss))

           final_layout.add_widget(button_layout)
           self.final_popup = Popup(title='Acabou', content=final_layout, size_hint=(None, None), size=(400, 400))
           self.final_popup.open()

    def modo_aprendizagem(self, instance):
        
        self.final_popup.dismiss()
        self.translation_popup.dismiss()
        
        modo_aprendizagem_popup = Popup(title='Modo de Aprendizagem', size_hint=(None, None), size=(400, 400))
        main_layout2 = BoxLayout(orientation='vertical')
        scroll_view2 = ScrollView()
        result_label = Label(text=self.translation, size_hint_y=None, height=40, font_size="25sp")
        result_label.bind(texture_size=result_label.setter('size'))
        scroll_view2.add_widget(result_label)
        main_layout2.add_widget(scroll_view2)
        sair_botao = Button(text='Sair', size_hint=(None, None), height=40, on_press=modo_aprendizagem_popup.dismiss)
        main_layout2.add_widget(sair_botao)
        modo_aprendizagem_popup.content = main_layout2
        Clock.schedule_once(modo_aprendizagem_popup.open, 3)

    def final_popup_dismiss(self, instance):
        self.final_popup.dismiss()
        if hasattr(self, 'translation_popup'):
            self.translation_popup.dismiss()

    def send_to_arduino(self, matriz):
        if not self.arduino_opened:
            try:
                arduino_port = '/dev/ttyUSB0'  # Ajuste conforme o seu sistema
                baud_rate = 9600
                self.arduino = serial.Serial(arduino_port, baud_rate)
                self.arduino_opened = True
            except Exception as e:
                print(f"Erro ao abrir a conexão com o Arduino: {e}")

        if self.arduino_opened:
            line = ''.join(map(str, [item for sublist in matriz for item in sublist])) + '\n'
            try:
                self.arduino.write(line.encode('utf-8'))
            except Exception as e:
                print(f"Erro ao enviar para o Arduino: {e}")

    def reset_arduino(self):
        if self.arduino_opened:
            try:
                self.arduino.close()  # Fecha a conexão com o Arduino
                self.arduino_opened = False
            except Exception as e:
                print(f"Erro ao fechar a conexão com o Arduino: {e}")

    def stop_translation(self, *args):
        self.is_translating = False
        Clock.unschedule(self.translate_next_character)
        self.reset_arduino()  # Fecha a conexão com o Arduino
        self.translation_popup.dismiss()  # Fecha o popup

class PDFProcessorApp(App):
    def build(self):
        Builder.load_file('loading.kv')
        Builder.load_file('main.kv')
        sm = ScreenManager()
        sm.add_widget(LoadingScreen(name='loading_screen'))
        sm.add_widget(MainScreen(name='main_screen'))
        return sm
       

if __name__ == '__main__':
    PDFProcessorApp().run()

