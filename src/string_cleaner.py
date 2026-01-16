from unidecode import unidecode

def string_cleaner(text):
    clean_text = unidecode(text) 
    clean_text = clean_text.replace(" ", "_").replace(":", '').replace(";", '')
    clean_text = clean_text.replace(',', '').replace('.', '')
    clean_text = clean_text.replace("'", "").replace('"', '').replace("`",'')
    clean_text = clean_text.replace("<i>", "").replace("</i>", "")
    clean_text = clean_text.replace("+", "").replace("-", "").replace('*','')
    clean_text = clean_text.replace('(', '').replace(')', '')
    clean_text = clean_text.replace('[', '').replace(']', '')
    clean_text = clean_text.replace('{', '').replace('}', '')
    clean_text = clean_text.replace('¿','').replace('?','')
    clean_text = clean_text.replace('¡','').replace('!','')
    clean_text = clean_text.replace('<sub>','').replace('</sub>','')
    clean_text = clean_text.replace('β', 'B')
    clean_text = clean_text.lower()  
    clean_text = clean_text.strip()  

    return clean_text