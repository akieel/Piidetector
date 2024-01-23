import re
import tkinter as tk
from tkinter import filedialog

def detect_pii(file_path, selected_pii):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            
        regex_patterns = {
            'Email Address': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'Phone Number': r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            'Address': r'\b\d+\s+[\w\s]+,\s+\w+\b|\b\d+\s+[\w\s]+\b',
            'Social Security Number': r'\b\d{3}-?\d{2}-?\d{4}\b',
            'Credit Card Number': r'\b\d{4}-?\d{4}-?\d{4}-?\d{4}\b',
        }
        
        detected_pii = {}
        
        for pattern_name, pattern in regex_patterns.items():
            if pattern_name in selected_pii:
                matches = re.findall(pattern, content)
                
                if matches:
                    if pattern_name == 'Address':
                        formatted_addresses = []
                        
                        for address in matches:
                            formatted_address = ' '.join(re.findall(r'\b\d+\b|\w+', address))
                            formatted_addresses.append(formatted_address)
                        
                        detected_pii[pattern_name] = formatted_addresses
                    else:
                        detected_pii[pattern_name] = matches
                    
        return detected_pii
    
    except Exception as e:
        return f"Error: {str(e)}"

def browse_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename()
    return file_path

def save_report(result):
    save_path = filedialog.asksaveasfilename(defaultextension=".txt")
    
    if save_path != "":
        with open(save_path, 'w') as file:
            file.write("Detected PII:\n")
            file.write("-----------------------\n")
            
            if not result:
                file.write("No PII found in the file.\n")
            else:
                for pii_type, piis in result.items():
                    file.write(f"{pii_type}:\n")
                    for pii in piis:
                        file.write(f"   {pii}\n")
                    file.write("-----------------------\n")
        
        print("Report saved successfully.")
    else:
        print("Report not saved.")
        return

def select_pii_types():
    selected_pii = []
    pii_types = [
        'Email Address',
        'Phone Number',
        'Address',
        'Social Security Number',
        'Credit Card Number',
    ]
    
    print("Select the types of PII to scan:")
    
    for index, pii_type in enumerate(pii_types, start=1):
        print(f"{index}. {pii_type}")
    
    option = input("Enter the numbers of the PII types (comma-separated): ")
    options = option.split(',')
    
    for opt in options:
        opt = opt.strip()
        if opt.isdigit() and 1 <= int(opt) <= len(pii_types):
            selected_pii.append(pii_types[int(opt)-1])
    
    return selected_pii

file_path = browse_file()

if file_path != "":
    selected_pii = select_pii_types()
    result = detect_pii(file_path, selected_pii)
    
    print("Scanning complete.")
    
    if not result:
        print("No PII found in the file.")
    else:
        print("\nDetected PII:")
        print("-----------------------")
        for pii_type, piis in result.items():
            print(f"{pii_type}:")
            for pii in piis:
                print(f"   {pii}")
            print("-----------------------")
        
        save_report(result)
else:
    print("No file selected.")