import xml.etree.ElementTree as ET
from string_cleaner import string_cleaner
from check_language import LanguageRegistry

class TBXCleaner:
    def __init__(self):
        self.namespaces = {
            'basic': 'http://www.tbxinfo.net/ns/basic',
            'min': 'http://www.tbxinfo.net/ns/min',
            'tbx': 'urn:iso:std:iso:30042:ed-2',
            'xml': 'http://www.w3.org/XML/1998/namespace'
            }
        self.langChecker = LanguageRegistry()

    def extract_conceptData(self, tbxConceptNode, conceptNode):
        tbxConceptID = tbxConceptNode.attrib['id']
        conceptNode.set('originalID', tbxConceptID)
        conceptNode.set('conceptID', f"LC{tbxConceptID}")
        # check if the concept has associated domains
        tbxConceptDomains = tbxConceptNode.findall('./min:subjectField', self.namespaces)
        if len(tbxConceptDomains) > 0:
            conceptDomainsNode = ET.SubElement(conceptNode, 'conceptDomains')
            for tbxDomain in tbxConceptDomains:
                conceptDomainNode = ET.SubElement(conceptDomainsNode, 'conceptDomain')
                domainID = f"{string_cleaner(tbxDomain.text)}_domain"
                conceptDomainNode.set('domainRef', domainID)
        return conceptNode
    
    def create_domainSchema(self, tbxRoot, cleanRoot):
        '''Create the schema of the domains'''
        domainSchemaNode = ET.SubElement(cleanRoot, 'domainSchema')
        tbxConcepts = tbxRoot.findall('./tbx:text/tbx:body/tbx:conceptEntry', self.namespaces)
        domainSet = set()
        for tbxConcept in tbxConcepts:
            tbxFields = tbxConcept.findall('./min:subjectField', self.namespaces)
            for tbxField in tbxFields:
                domainSet.add(tbxField.text)
        for domain in domainSet:
            domainNode = ET.SubElement(domainSchemaNode, 'domain')
            domainNode.text = domain
            domainNode.set('domainID', f"{string_cleaner(domain)}_domain")
        return cleanRoot

    def create_langSchema(self, cleanRoot, langReg:dict):
        langsNode = ET.SubElement(cleanRoot, 'resource_languages')
        for language in langReg.keys():
            langNode = ET.SubElement(langsNode, 'language')
            langNode.text = langReg[language]
        return cleanRoot    

    def extract_defs(self, langSections, conceptNode, lang_registry:dict):
        cleanDefsNode = ET.SubElement(conceptNode, 'definitions')
        for langSec in langSections:
            language = langSec.attrib["{http://www.w3.org/XML/1998/namespace}lang"]
            lang_registry = self.langChecker.check_lang(language, lang_registry)
            tbxDescGrpNodes = langSec.findall('./tbx:descripGrp', self.namespaces)
            for tbxDescInd in range(len(tbxDescGrpNodes)):
                # current descGrp node (tbx)
                tbxDescGrpNode = tbxDescGrpNodes[tbxDescInd]
                # create a clean node for current description, set: id, language and text
                cleanDefInfoNode = ET.SubElement(cleanDefsNode, 'definitionInfo')
                defID = f"{conceptNode.attrib['conceptID']}_{language}_def{tbxDescInd+1}"
                cleanDefInfoNode.set('definitionID', defID)
                cleanDefInfoNode.set('orig_lang', language)
                cleanDefInfoNode.set('ref_lang', lang_registry[language])
                # create subnode for the text of the definition
                cleanDefNode = ET.SubElement(cleanDefInfoNode, 'definition')
                cleanDefNode.text = tbxDescGrpNode.find('./basic:definition', self.namespaces).text
                tbxDescRef = tbxDescGrpNode.find('./basic:source', self.namespaces)
                if tbxDescRef != None:
                    descRefID = f"{string_cleaner(tbxDescRef.text)}" #TODO: add resource title
                    # create clean defRef node and set text and id
                    cleanDefRefNode = ET.SubElement(cleanDefInfoNode, 'defRef')
                    cleanDefRefNode.set('refID', descRefID)
                    cleanDefRefNode.text = tbxDescRef.text
        return conceptNode, lang_registry

    def extract_termData(self, langSections, conceptNode, lang_registry):
        entryRecsNode = ET.SubElement(conceptNode, 'entryRecords')
        for langSec in langSections:
            language = langSec.attrib["{http://www.w3.org/XML/1998/namespace}lang"]
            lang_registry = self.langChecker.check_lang(language, lang_registry)
            tbxTermSecs = langSec.findall('./tbx:termSec', self.namespaces)
            for tbxTermSec in tbxTermSecs:
                # extract all the relevant data from the TBX (term and grammatical info)
                term = tbxTermSec.find('./tbx:term', self.namespaces).text
                # create a base id for the term to be used in the entryID and formID
                cleanTerm = string_cleaner(term)
                termID = f"{conceptNode.attrib['conceptID']}_{language}_{cleanTerm}"
                # create clean node for the entry and its realted info
                cleanEntryNode = ET.SubElement(entryRecsNode, 'lexEntry')
                entryID = termID + "_entry"
                cleanEntryNode.set('entryID', entryID)
                cleanEntryNode.set('orig_lang', language)
                cleanEntryNode.set('ref_lang', lang_registry[language])
                # create clean subnode for the sense and its related info
                cleanSenseNode = ET.SubElement(cleanEntryNode, 'lexSense')
                senseID = termID + "_sense"
                cleanSenseNode.set('senseID', senseID)
                # prepare formID
                formID = f"{termID}_form"
                # create clean subnode for the form and its related info
                cleanFormNode = ET.SubElement(cleanEntryNode, 'lexForm')
                cleanFormNode.set('formID', formID) # añadir id 
                # node for the form (text)
                textNode = ET.SubElement(cleanFormNode, 'form')
                textNode.text = term
        return conceptNode
    
    def create_semRels(self, conceptNode):
        entryNodes = conceptNode.findall('./lexEntry')
        if len(entryNodes) >= 2:
            for entryInd in range(len(entryNodes)):
                currentLang = entryNodes[entryInd].attrib['orig_lang']
                termSenseNode = entryNodes[entryInd].find('./lexSense')
                for compInd in range(len(entryNodes)):
                    if entryInd != compInd:
                        comparisonLang = entryNodes[compInd].attrib['orig_lang']
                        compSenseID = entryNodes[compInd].find('./lexSense').attrib['senseID']
                        if currentLang == comparisonLang:
                            synRelNode = ET.SubElement(termSenseNode, 'synRel')
                            synRelNode.set("with", compSenseID)
                        else: 
                            transRelNode = ET.SubElement(termSenseNode, 'transRel')
                            transRelNode.set("with", compSenseID)
        return conceptNode
    
    def extract_lexicalData(self, tbxRoot, cleanRoot, lang_registry):
        # create a lexical data node to store the clean data
        lexDataNode = ET.SubElement(cleanRoot, 'lexicalData')
        # find all the concept in the tbx and iterate
        tbxConcepts = tbxRoot.findall('./tbx:text/tbx:body/tbx:conceptEntry', self.namespaces)
        for tbxConcept in tbxConcepts:
            # create a node for the concept and extract concept info
            conceptNode = ET.SubElement(lexDataNode, 'lexConcept')
            conceptNode = self.extract_conceptData(tbxConcept, conceptNode)
            # iterate over the language sections of the concept
            langSections = tbxConcept.findall('./tbx:langSec', self.namespaces)
            conceptNode, lang_registry = self.extract_defs(langSections, conceptNode, lang_registry)
            conceptNode = self.extract_termData(langSections, conceptNode, lang_registry)
            conceptNode = self.create_semRels(conceptNode)
        return cleanRoot, lang_registry      


    def clean_terminology(self, filePath):
        # load data
        tree = ET.parse(filePath)
        tbxRoot = tree.getroot()
        # create the output's root (XML)
        cleanRoot = ET.Element("root")
        # extract domains
        cleanRoot = self.create_domainSchema(tbxRoot, cleanRoot)
        # extract terminological data
        lang_registry = {}
        cleanRoot, lang_registry = self.extract_lexicalData(tbxRoot, cleanRoot, lang_registry)
        # create domain registry
        cleanRoot = self.create_langSchema(cleanRoot, lang_registry)
        return cleanRoot