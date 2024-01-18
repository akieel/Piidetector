import re

def detect_pii(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        
        regex_patterns = {
            'Email Address': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'Phone Number': r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            'Address': r'\b\d+\s+[\w\s]+,\s+\w+\b|\b\d+\s+[\w\s]+\b',
           
        }
        
        detected_pii = {}
        
        for pattern_name, pattern in regex_patterns.items():
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

# Get the file path from the user
file_path = input("Enter the file path to scan: ")


result = detect_pii(file_path)


print("Detected PII:")
if not result:
    print("No PII found in the file.")
else:
    for pii_type, piis in result.items():
        print(f"{pii_type}:")
        for pii in piis:
            print(pii)
        print()
