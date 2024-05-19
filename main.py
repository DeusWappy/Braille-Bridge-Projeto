from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.lang import Builder
from Algoritmo import tradutor
import pdfplumber
from kivy.clock import Clock
import serial

# Configurar a porta serial do Arduino
arduino_port = '/dev/ttyUSB0'  # Ajuste conforme o seu sistema
baud_rate = 9600
arduino = serial.Serial(arduino_port, baud_rate)

class PDFProcessorApp(App):
    def build(self):
        return Builder.load_file("main.kv")

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
            self.show_error(str(e))

    def process_string(self, input_string):
        self.show_result(input_string)

    def show_result(self, result):
        self.result = result
        self.index = 0
        self.translation_popup = Popup(title='Tradução', size_hint=(None, None), size=(400, 400))
        self.translation_label = Label(text='', size_hint=(None, None), size=(400, 400), font_size="25sp")
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(self.translation_label)
        layout.add_widget(Button(text='Parar', size_hint=(None, None), height=40, on_press=self.stop_translation))
        self.translation_popup.content = layout
        self.translation_popup.open()
        self.is_translating = True
        self.translate_next_character(0)  # Inicia a tradução

    def translate_next_character(self, dt):
        if self.index < len(self.result) and self.is_translating:
            char = self.result[self.index]
            matriz = tradutor(char)
            translation = f'{char}:\n' + '\n'.join(''.join(map(str, row)) for row in matriz)
            self.translation_label.text = translation
            self.send_to_arduino(matriz)
            self.index += 1
            Clock.schedule_once(self.translate_next_character, 2)  # Agenda a próxima tradução após 2 segundos
        else:
            self.stop_translation()

    def send_to_arduino(self, matriz):
        line = ''.join(map(str, [item for sublist in matriz for item in sublist])) + '\n'
        try:
            arduino.write(line.encode('utf-8'))
        except Exception as e:
            print(f"Erro ao enviar para o Arduino: {e}")

    def reset_arduino(self):
        # Envia uma linha de "zeros" para garantir que todos os pistões desçam
        arduino.write('000000\n'.encode('utf-8'))

    def stop_translation(self, *args):
        self.is_translating = False
        Clock.unschedule(self.translate_next_character)
        self.translation_popup.dismiss()
        self.reset_arduino()

    def show_error(self, error_msg):
        popup = Popup(title='Erro',
                      content=Label(text=error_msg),
                      size_hint=(None, None), size=(400, 200))
        popup.open()

if __name__ == '__main__':
    PDFProcessorApp().run()
