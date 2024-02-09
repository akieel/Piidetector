import re
import tkinter as tk
from tkinter import filedialog, messagebox, Checkbutton, IntVar, simpledialog, scrolledtext, Toplevel, Entry, Label, Button
from tkinter.ttk import Separator, Style
import csv
from fpdf import FPDF
import os
from PyPDF2 import PdfReader
import docx
import openpyxl
import pythoncom
from pptx import Presentation
import pytesseract
from PIL import Image
import logging
import datetime
from cryptography.fernet import Fernet
import json
from json.decoder import JSONDecodeError
import flask
from threading import Thread
from tkinter import ttk
from tkinter.messagebox import showinfo
from pdf2image import convert_from_path

# Initialize logging
logging.basicConfig(filename='pii_scan_log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = flask.Flask(__name__)

# Generate or load a previously stored encryption key
def load_or_generate_key():
    key_path = 'encryption.key'
    if os.path.exists(key_path):
        with open(key_path, 'rb') as key_file:
            key = key_file.read()
    else:
        key = Fernet.generate_key()
        with open(key_path, 'wb') as key_file:
            key_file.write(key)
    return key

encryption_key = load_or_generate_key()
cipher_suite = Fernet(encryption_key)

def encrypt_text(text):
    if isinstance(text, str):
        text = text.encode()
    encrypted_text = cipher_suite.encrypt(text)
    return encrypted_text

def decrypt_text(encrypted_text):
    decrypted_text = cipher_suite.decrypt(encrypted_text).decode()
    return decrypted_text

def convert_pdf_to_images(pdf_path):
    return convert_from_path(pdf_path)


def read_file_content(file_path):
    try:
        if file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        elif file_path.endswith('.pdf'):
            try:
                reader = PdfReader(file_path)
                text = ''
                for page in reader.pages:
                    text += page.extractText() + ' '
                if not text.strip():  # If text extraction returned empty, attempt OCR
                    images = convert_pdf_to_images(file_path)
                    text = ' '.join([pytesseract.image_to_string(image) for image in images])
                return text
            except Exception as e:
                logging.error(f"Error reading PDF file {file_path}: {e}")
                messagebox.showerror("Error", f"Could not read PDF file: {file_path}")
                return None
        elif file_path.endswith('.docx'):
            doc = docx.Document(file_path)
            text = '\n'.join(paragraph.text for paragraph in doc.paragraphs)
            return text
        elif file_path.endswith('.xlsx'):
            workbook = openpyxl.load_workbook(file_path)
            text = ''
            for sheet in workbook.sheetnames:
                ws = workbook[sheet]
                for row in ws.iter_rows(values_only=True):
                    if row:
                        text += ' '.join([str(cell) for cell in row if cell is not None]) + '\n'
            return text
        elif file_path.endswith('.pptx'):
            pythoncom.CoInitialize()  # Needed when running in thread
            pres = Presentation(file_path)
            text = ''
            for slide in pres.slides:
                for shape in slide.shapes:
                    if hasattr(shape, 'text'):
                        text += shape.text + '\n'
            return text
        elif file_path.endswith('.pdf'):
            # Attempt OCR for image-based PDFs
            images = convert_pdf_to_images(file_path)
            text = ''
            for image in images:
                text += pytesseract.image_to_string(image) + '\n'
            return text
        else:
            logging.warning(f"Unsupported file format for {file_path}")
            messagebox.showerror("Unsupported File", "The selected file format is not supported.")
            return None
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        messagebox.showerror("Error", f"Could not read file: {file_path}")
        return None

def load_settings():
    settings_path = 'settings.json'
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as settings_file:
                settings = json.load(settings_file)
            # Compile the regex patterns if they exist in settings
            if "custom_patterns" in settings:
                settings["custom_patterns"] = {k: re.compile(v) for k, v in settings["custom_patterns"].items()}
            return settings
        except JSONDecodeError:
            # Return empty settings or default settings if JSON is malformed or empty
            return {}
    else:
        # Return empty settings or default settings if file doesn't exist
        return {}

def save_settings(settings):
    settings_path = 'settings.json'
    with open(settings_path, 'w') as settings_file:
        json.dump(settings, settings_file)

def compile_regex_patterns(custom_patterns=None):
    default_patterns = {
        'Email Address': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'Phone Number': re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
        'Address': re.compile(r'\b\d+\s+[\w\s]+,\s+\w+\b|\b\d+\s+[\w\s]+\b'),
        'Social Security Number': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
        'Credit Card Number': re.compile(r'\b\d{4}-?\d{4}-?\d{4}-?\d{4}\b'),
        'Passport Number': re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'),
        'Driver\'s License Number': re.compile(r'\b[Ss]\d{7,8}\b'),
    }
    if custom_patterns:
        default_patterns.update(custom_patterns)
    return default_patterns

def detect_pii(file_path, selected_pii, custom_patterns=None):
    content = read_file_content(file_path)
    if content is None:
        logging.info(f"No content read from {file_path}")
        return {}
    
    regex_patterns = compile_regex_patterns(custom_patterns)
    detected_pii = {}
    
    for pattern_name, pattern in regex_patterns.items():
        if pattern_name in selected_pii:
            matches = pattern.findall(content)
            if matches:
                detected_pii[pattern_name] = matches
                logging.info(f"Detected {pattern_name} in {file_path}")
    if not detected_pii:
        logging.info(f"No PII detected in {file_path}")
    return detected_pii

@app.route('/api/scan', methods=['POST'])
def api_scan():
    data = flask.request.json
    file_path = data['file_path']
    selected_pii = data['selected_pii']
    custom_patterns = data.get('custom_patterns', {})
    result = detect_pii(file_path, selected_pii, custom_patterns)
    return flask.jsonify(result)

class PiiScannerApp:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        self.custom_patterns = self.settings.get("custom_patterns", {})
        self.pii_selections = []  # Ensure this is initialized here
        self.setup_ui()
    
    def setup_ui(self):
        self.root.title("PII Scanner")
        self.root.geometry("800x600")
        
        self.style = Style(self.root)
        self.style.configure('TCheckbutton', font=('Arial', 10))
        
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.top_frame = tk.Frame(self.main_frame)
        self.top_frame.pack(fill=tk.X)
        
        self.bottom_frame = tk.Frame(self.main_frame)
        self.bottom_frame.pack(fill=tk.BOTH, expand=True)
        
        self.file_button = tk.Button(self.top_frame, text="Select Files", command=self.browse_files)
        self.file_button.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.scan_button = tk.Button(self.top_frame, text="Scan", command=self.scan_files)
        self.scan_button.pack(side=tk.LEFT, padx=10)
        
        self.save_button = tk.Button(self.top_frame, text="Save Report", command=self.save_report_dialog)
        self.save_button.pack(side=tk.LEFT, padx=10)
        
        self.settings_button = tk.Button(self.top_frame, text="Settings", command=self.open_settings)
        self.settings_button.pack(side=tk.LEFT, padx=10)
        
        self.separator = Separator(self.main_frame, orient='horizontal')
        self.separator.pack(fill=tk.X, padx=5, pady=5)
        
        self.check_frame = tk.Frame(self.bottom_frame)
        self.check_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        self.scrollbar = tk.Scrollbar(self.check_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.pii_listbox = tk.Listbox(self.check_frame, yscrollcommand=self.scrollbar.set, selectmode=tk.MULTIPLE)
        self.pii_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.pii_listbox.yview)
        
        self.results_text = scrolledtext.ScrolledText(self.bottom_frame)
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.checkbuttons_frame = tk.Frame(self.check_frame)
        self.checkbuttons_frame.pack(fill=tk.BOTH, expand=True)
        
        self.pii_types = [
            'Email Address', 'Phone Number', 'Address',
            'Social Security Number', 'Credit Card Number', 'Passport Number', 'Driver\'s License Number'
        ] + list(self.custom_patterns.keys())
        for pii_type in self.pii_types:
            var = IntVar()
            chk = Checkbutton(self.checkbuttons_frame, text=pii_type, variable=var, font=('Arial', 10))
            chk.pack(anchor=tk.W, side=tk.TOP, expand=True)
            self.pii_selections.append((pii_type, var))
        
        self.pii_listbox.bind('<<ListboxSelect>>', self.on_select)
    
    def on_select(self, event):
        selections = event.widget.curselection()
        self.selected_pii = [self.pii_types[i] for i in selections]
        
        

    def open_settings(self):
        self.settings_window = Toplevel(self.root)
        self.settings_window.title("Settings")
        self.settings_window.geometry("400x300")
        
        Label(self.settings_window, text="Add Custom PII Pattern Name:").pack()
        self.custom_pii_name_entry = Entry(self.settings_window)
        self.custom_pii_name_entry.pack(pady=5)
        
        Label(self.settings_window, text="Add Custom PII Regex Pattern:").pack()
        self.custom_pii_pattern_entry = Entry(self.settings_window)
        self.custom_pii_pattern_entry.pack(pady=5)
        
        tk.Button(self.settings_window, text="Test Pattern", command=self.test_pattern).pack(pady=10)
        tk.Button(self.settings_window, text="Save Custom PII Pattern", command=self.save_custom_pattern).pack(pady=10)
    
    def save_custom_pattern(self):
        pattern_name = self.custom_pii_name_entry.get()
        pattern_regex = self.custom_pii_pattern_entry.get()
        if pattern_name and pattern_regex:
        # Directly save the string regex, not the compiled object
            self.custom_patterns[pattern_name] = pattern_regex
            self.settings['custom_patterns'] = self.custom_patterns
            save_settings(self.settings)
            messagebox.showinfo("Success", "Custom PII pattern saved.")
            self.settings_window.destroy()
            self.setup_ui()  # Refresh UI to include new custom pattern

    def browse_files(self):
        self.file_paths = filedialog.askopenfilenames()
        if not self.file_paths:
            messagebox.showinfo("Selection", "No files selected.")
    
    def scan_files(self):
        selected_pii = [pii_type for pii_type, var in self.pii_selections if var.get()]
        if self.file_paths and selected_pii:
            logging.info("Scan started.")
            for file_path in self.file_paths:
                try:
                    result = detect_pii(file_path, selected_pii, self.custom_patterns)
                    self.display_results(result, file_path)
                except Exception as e:
                    logging.error(f"Error scanning {file_path}: {e}")
                    messagebox.showerror("Scan Error", f"An error occurred while scanning {file_path}.")
            logging.info("Scan completed.")
        else:
            messagebox.showwarning("Warning", "Please select one or more files and at least one PII type.")

    
    def display_results(self, results, file_path):
        self.results_text.insert(tk.END, f"Results for {os.path.basename(file_path)}:\n")
        if not results:
            self.results_text.insert(tk.END, "No PII found.\n\n")
        else:
            for pii_type, piis in results.items():
                self.results_text.insert(tk.END, f"{pii_type}:\n")
                for pii in piis:
                    self.results_text.insert(tk.END, f"   {pii}\n")
                self.results_text.insert(tk.END, "-----------------------\n")
            self.results_text.insert(tk.END, "\n")
    
    def save_report_dialog(self):
        format_choice = simpledialog.askstring("Save Report", "Enter format (TXT, PDF, CSV):")
        if format_choice:
            self.save_report(format_choice.upper())
    
    def save_report(self, format_choice):
        content = self.results_text.get(1.0, tk.END)
        encrypted_content = encrypt_text(content)
        
        save_path = filedialog.asksaveasfilename(defaultextension=f".{format_choice.lower()}")
        if save_path:
            if format_choice == 'TXT':
                with open(save_path, 'wb') as file:
                    file.write(encrypted_content)
            elif format_choice == 'PDF' or format_choice == 'CSV':
                messagebox.showerror("Error", "Encryption currently supported only for TXT format.")
            messagebox.showinfo("Info", "Report saved successfully.")
            
    def test_pattern(self):
        test_string = simpledialog.askstring("Test Custom Pattern", "Enter text to test pattern:")
        if test_string:
            try:
                pattern = re.compile(self.custom_pii_pattern_entry.get())
                matches = pattern.findall(test_string)
                if matches:
                    messagebox.showinfo("Pattern Test Result", f"Matches found: {', '.join(matches)}")
                else:
                    messagebox.showinfo("Pattern Test Result", "No matches found.")
            except re.error as e:
                messagebox.showerror("Pattern Test Error", f"Invalid regex pattern: {e}")


if __name__ == "__main__":
    api_thread = Thread(target=lambda: app.run(port=5000, debug=True, use_reloader=False))
    api_thread.start()
    root = tk.Tk()
    app = PiiScannerApp(root)
    root.mainloop()