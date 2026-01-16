import xml.etree.ElementTree as ET
from string_cleaner import string_cleaner
from check_language import LanguageRegistry

class GlossaryCleaner:
    def __init__(self):
        self.langChecker = LanguageRegistry()
        
    def create_langSchema(self, cleanRoot, langReg:dict):
        langsNode = ET.SubElement(cleanRoot, 'resourceLanguages')
        for language in langReg.keys():
            langNode = ET.SubElement(langsNode, 'language')
            langNode.text = langReg[language]
        return cleanRoot

    def extract_lexicalData(self, cleanRoot, term_list:list, language=''):
        # find language in lexvo (all terms the same, monolingual resource)
        langReg = {}
        langReg = self.langChecker.check_lang(language, langReg)
        # create a lexical data node to store the clean data
        lexDataNode = ET.SubElement(cleanRoot, 'lexicalData')
        for ind in range(len(term_list)):
            # lexical concept node and data
            conceptNode = ET.SubElement(lexDataNode, 'lexConcept')
            conceptID = f"LC{ind+1}"
            conceptNode.set('conceptID', conceptID)
            # get term and termID
            term = term_list[ind]
            termID = f"{conceptID}_{string_cleaner(term)}"
            # lexical entry node and id
            entryRecsNode = ET.SubElement(conceptNode, 'entryRecords')
            entryNode = ET.SubElement(entryRecsNode, 'lexEntry')
            entryNode.set('entryID', f"{termID}_entry")
            # add language information of the entry
            entryNode.set('orig_lang', language)
            langReg = self.langChecker.check_lang(language, langReg)
            entryNode.set('ref_lang', '')
            if language in langReg.keys():
                entryNode.set('ref_lang', langReg[language])
            # sense node and data
            senseNode = ET.SubElement(entryNode, 'lexSense')
            senseNode.set('senseID', f"{termID}_sense")
            # form node and data
            formNode = ET.SubElement(entryNode, 'lexForm')
            formNode.set('formID', f"{termID}_form")
            textNode = ET.SubElement(formNode, 'form')
            textNode.text = term
        self.create_langSchema(cleanRoot, langReg)
        return cleanRoot, langReg

    def create_langSchema(self, cleanRoot, langReg:dict):
        langsNode = ET.SubElement(cleanRoot, 'resourceLanguages')
        for langTag in langReg.keys():
            langNode = ET.SubElement(langsNode, 'language')
            if langReg[langTag] == '':
                langNode.text = langTag
            else:
                langNode.text = langReg[langTag]
        return cleanRoot

    def clean_terminology(self, filePath, language=''):
        # read data
        f = open(filePath, encoding='utf8')
        data = f.read()
        # split terms, and erase empty values
        term_list = data.split('\n')
        term_list = [term for term in term_list if term.strip()]
        # create the output's root (XML)
        cleanRoot = ET.Element("root")
        cleanRoot, langReg = self.extract_lexicalData(cleanRoot, term_list, language)
        cleanRoot = self.create_langSchema(cleanRoot, langReg)
        return cleanRoot