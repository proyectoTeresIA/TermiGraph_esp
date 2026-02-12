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

    def extract_conceptData(self, tbxConceptNode, conceptNode, respPers_reg={}):
        tbxConceptID = tbxConceptNode.attrib['id']
        conceptNode.set('originalID', tbxConceptID)
        conceptNode.set('conceptID', f"LC{tbxConceptID}")
        # check if the concept has associated domains
        tbxConceptDomains = tbxConceptNode.findall('./min:subjectField', self.namespaces)
        if len(tbxConceptDomains) > 0:
            conceptDomainsNode = ET.SubElement(conceptNode, 'conceptDomains')
            for tbxDomain in tbxConceptDomains:
                conceptDomainNode = ET.SubElement(conceptDomainsNode, 'conceptDomain')
                domainID = f"{string_cleaner(tbxDomain.text)}"
                conceptDomainNode.set('domainRef', domainID)
        # check if there are any transactions
        conceptNode = self.extract_transaction(tbxConceptNode, conceptNode, respPers_reg)
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
            domainNode.set('domainID', f"{string_cleaner(domain)}")
        return cleanRoot

    def create_langSchema(self, cleanRoot, langReg:dict):
        langsNode = ET.SubElement(cleanRoot, 'resource_languages')
        for language in langReg.keys():
            langNode = ET.SubElement(langsNode, 'language')
            langNode.text = langReg[language]
        return cleanRoot    

    def extract_defs(
        self, langSections, conceptNode, lang_registry:dict, respPers_reg:dict
        ):
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
                def_path = './basic:definition'
                def_value = tbxDescGrpNode.find(def_path, self.namespaces).text
                cleanDefNode.text = def_value
                tbxDescRef = tbxDescGrpNode.find('./basic:source', self.namespaces)
                if tbxDescRef != None:
                    descRefID = f"{string_cleaner(tbxDescRef.text)}" #TODO: add resource title
                    # create clean defRef node and set text and id
                    cleanDefRefNode = ET.SubElement(cleanDefInfoNode, 'defRef')
                    cleanDefRefNode.set('refID', descRefID)
                    cleanDefRefNode.text = tbxDescRef.text
                # check if there are transactions
                cleanDefInfoNode = self.extract_transaction(tbxDescGrpNode, cleanDefInfoNode, respPers_reg)
        return conceptNode, lang_registry

    def extract_respPers(self, tbxRoot):
        '''Función que extrae los metadatos del nodos tbx:refObjectSec de tipo
        respPerson. Devuelve un dict con el registro de personas y sus datos'''
        refObj_path = ".//tbx:back/tbx:refObjectSec[@type='respPerson']/tbx:refObject"
        respPerson_nodes = tbxRoot.findall(refObj_path, self.namespaces)
        respPers_reg = {}
        for respPerson_node in respPerson_nodes:
            personID = respPerson_node.attrib['id']
            respPers_reg[personID] = {}
            item_nodes = respPerson_node.findall('./tbx:item', self.namespaces)
            for item in item_nodes:
                respPers_reg[personID][item.attrib['type']] = item.text
        return respPers_reg

    def extract_transaction(self, tbx_node, clean_node, respPers_reg:dict):
        transac_nodes = tbx_node.findall('./tbx:transacGrp', self.namespaces)
        if len(transac_nodes) > 0:
            transac_n = 0
            for transac_node in transac_nodes:
                # create clean node for transaction and set ID
                clean_transac = ET.SubElement(clean_node, 'transaction')
                parent_attribs = clean_node.attrib
                for attribute in parent_attribs:
                    if ('ID' in attribute) and (attribute != 'originalID'):
                        transac_n += 1
                        parentID = parent_attribs[attribute]
                        transacID = f"{parentID}_transac{transac_n}"
                        clean_transac.set('transacID', transacID)
                # get type and save
                type_path = './/basic:transactionType'
                transacType = transac_node.find(type_path, self.namespaces)
                clean_transacType = ET.SubElement(clean_transac, 'type') 
                clean_transacType.text = transacType.text
                # get date and save
                date_path = './/tbx:date'
                transacDate = transac_node.find(date_path, self.namespaces)
                clean_transacDate = ET.SubElement(clean_transac, 'date') 
                clean_transacDate.text = transacDate.text
                # get user ID
                resp_path = './basic:responsibility'
                transacUser = transac_node.find(resp_path, self.namespaces)
                transacUserID = transacUser.attrib['target']
                # check if ID is registered in tbx:back node
                if transacUserID in respPers_reg.keys():
                    # create clean node for user and set ID
                    clean_respPers = ET.SubElement(clean_transac, 'respPers')
                    persID = f"{transacUserID}_refPers"
                    clean_respPers.set('persID', persID)
                    # save rest of data
                    for infoType in respPers_reg[transacUserID]:
                        subnode = ET.SubElement(clean_respPers, infoType)
                        subnode.text = respPers_reg[transacUserID][infoType]
        return clean_node

    def extract_termData(
        self, langSections, conceptNode, lang_registry:dict, respPers_reg:dict
        ):
        entryRecsNode = ET.SubElement(conceptNode, 'entryRecords')
        for langSec in langSections:
            language = langSec.attrib["{http://www.w3.org/XML/1998/namespace}lang"]
            lang_registry = self.langChecker.check_lang(language, lang_registry)
            tbxTermSecs = langSec.findall('./tbx:termSec', self.namespaces)
            for tbxTermSec in tbxTermSecs:
                # extract all the relevant data from the TBX (term and grammatical info)
                term_tbxNode = tbxTermSec.find('./tbx:term', self.namespaces)
                term = term_tbxNode.text
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
                # check if there are transactions
                cleanEntryNode = self.extract_transaction(
                    tbxTermSec, cleanEntryNode, respPers_reg
                    )
        return conceptNode
    
    def create_semRels(self, conceptNode):
        entryNodes = conceptNode.findall('./entryRecords/lexEntry')
        if len(entryNodes) > 1:
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
    
    def extract_lexicalData(
        self, tbxRoot, cleanRoot, lang_registry:dict, respPers_reg:dict
        ):
        # create a lexical data node to store the clean data
        lexDataNode = ET.SubElement(cleanRoot, 'lexicalData')
        # find all the concept in the tbx and iterate
        concept_path = './tbx:text/tbx:body/tbx:conceptEntry'
        tbxConcepts = tbxRoot.findall(concept_path, self.namespaces)
        for tbxConcept in tbxConcepts:
            # create a node for the concept and extract concept info
            conceptNode = ET.SubElement(lexDataNode, 'lexConcept')
            conceptNode = self.extract_conceptData(
                tbxConcept, conceptNode, respPers_reg
            )
            # iterate over the language sections of the concept
            langSections = tbxConcept.findall('./tbx:langSec', self.namespaces)
            conceptNode, lang_registry = self.extract_defs(
                langSections, conceptNode, lang_registry, respPers_reg
                )
            conceptNode = self.extract_termData(
                langSections, conceptNode, lang_registry, respPers_reg
                )
            conceptNode = self.create_semRels(conceptNode)
        return cleanRoot, lang_registry      


    def clean_terminology(self, filePath):
        # load data
        tree = ET.parse(filePath)
        tbxRoot = tree.getroot()
        # create the output's root (XML)
        cleanRoot = ET.Element("root")
        print('Processing TBX document')
        # extract domains
        cleanRoot = self.create_domainSchema(tbxRoot, cleanRoot)
        print('Domains cleaned')
        # extract respObjects
        respPers_reg = self.extract_respPers(tbxRoot)
        print('Back proccessed')
        # extract terminological data
        lang_registry = {}
        cleanRoot, lang_registry = self.extract_lexicalData(
            tbxRoot, cleanRoot, lang_registry, respPers_reg
            )
        print('Languages proccessed')
        # create domain registry
        cleanRoot = self.create_langSchema(cleanRoot, lang_registry)
        print('Data cleaned')
        return cleanRoot