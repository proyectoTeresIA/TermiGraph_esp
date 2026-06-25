import json
from pathlib import Path
from jsonpath_ng import parse
import xml.etree.ElementTree as ET
from string_cleaner import string_cleaner
from check_language import LanguageRegistry


class IATECleaner:
    def __init__(self):
        configPath = Path(__file__).parent / 'config_iate.json'
        with open(configPath) as f:
            self.config = json.load(f)   
        self.langChecker = LanguageRegistry()

    def check_publicData(self, iateData:dict):
        public = True
        if 'metadata' in iateData.keys():
            confidentiality = iateData['metadata']['confidentiality']['name']
            if confidentiality != 'public':
                public = False
        return public

    def create_domainSchema(self, data, cleanRoot):
        '''Create the schema of the domains'''
        # node for saving schema
        domainSchemaNode = ET.SubElement(cleanRoot, 'domainSchema')
        # get domains
        domains_path = '$.items[*].domains[*].domain[*]'
        expr = parse(domains_path)
        matches = [m.value for m in expr.find(data)]
        domain_reg = []
        for domain_info in matches:
            domain_label = domain_info['name']
            if domain_label in domain_reg:
                continue
            domain_reg.append(domain_label)
            # extract data 
            domainID = string_cleaner(domain_label)
            eurovocID = ''
            if 'eurovoc_code' in domain_info.keys():
                eurovocID = domain_info['eurovoc_code']
            # if top domain, store
            if domain_info['level'] == 1:
                domainNode = ET.SubElement(domainSchemaNode, 'domain')
                domainNode.text = domain_label
                domainNode.set('domainID', domainID)
                domainNode.set('eurovocID', eurovocID)
            if domain_info['level'] > 1:
                # añadir los datos de los dominios anteriores
                topnode = domainSchemaNode
                for top_domain in domain_info['path']:
                    topID = string_cleaner(top_domain)
                    search_path = f"./domain[@domainID='{topID}']" 
                    if topnode.find(search_path) is not None: 
                        topnode = topnode.find(search_path)
                    else:
                        subnode = ET.SubElement(topnode, 'domain')
                        subnode.text = top_domain
                        subnode.set('domainID', topID)
                        subnode.set('eurocovID', '')
                        topnode = subnode
                # añadir los datos del dominio en cuestión
                domainNode = ET.SubElement(topnode, 'domain')
                domainNode.text = domain_label
                domainNode.set('domainID', domainID)
                domainNode.set('eurovocID', eurovocID)
        return cleanRoot

    def add_refs(self, cleanNode, iateRefs, refSource:str):
        if type(iateRefs) == list:
            refNum = 1
            for iateRef in iateRefs:
                public = self.check_publicData(iateRef)
                if public:
                    refNode = ET.SubElement(cleanNode, 'reference')
                    refNode.text = iateRef['text']
                    refNode.set('refID', f"{refSource}_ref{refNum}")
                    refNum += 1
        elif type(iateRefs) == dict:
            public = self.check_publicData(iateRefs)
            if public:
                refNode = ET.SubElement(cleanNode, 'reference')
                refNode.text = iateRefs['text']
                refNode.set('refID', f"{refSource}_ref")
        return cleanNode
    
    def add_defsAndNotes(self, iateConcept:dict, conceptNode, langReg:dict):
        conceptID = conceptNode.attrib['originalID']
        infoTypes = ['definition', 'note']
        for infoType in infoTypes:
            infoTypeNode = ET.SubElement(conceptNode, f"{infoType}s")
            for language in iateConcept['language'].keys():
                iateLangRecord = iateConcept['language'][language]
                if infoType in iateLangRecord.keys():
                    # check if data is public; if not, continue with other data
                    public = self.check_publicData(iateLangRecord[infoType])
                    if not public:
                        continue
                    # create node for all the info of that type
                    infoNode = ET.SubElement(infoTypeNode, f"{infoType}Info")
                    # add def ID
                    infoID = f"{conceptID}_{language}_{infoType}"
                    infoNode.set(f"{infoType}ID", infoID)
                    # add language
                    infoNode.set('orig_lang', language)
                    infoNode.set('ref_lang', '')
                    if language in langReg.keys():
                        infoNode.set('ref_lang', langReg[language])
                    # add text node
                    valueNode = ET.SubElement(infoNode, infoType)
                    value = iateLangRecord[infoType]['value']
                    valueNode.text = value 
                    if 'references' in iateLangRecord[infoType].keys():
                        iateRefs = iateLangRecord[infoType]['references']
                        defNode = self.add_refs(infoNode, iateRefs, infoID)
        return conceptNode

    def get_conceptData(self, iateConcept:dict, conceptNode, langReg:dict):          
        # add information about the concept
        conceptNode = self.add_defsAndNotes(iateConcept, conceptNode, langReg)  
        # add domains
        if 'domains' in iateConcept:
            domainsNode = ET.SubElement(conceptNode, f"conceptDomains")
            for domain in iateConcept['domains']:
                domainNode = ET.SubElement(domainsNode, f"domain")
                domainLabel = domain['domain']['name']
                domainNode.set('domainRef', string_cleaner(domainLabel))
        if 'crossrefs' in iateConcept.keys():
            crossrefsNode = ET.SubElement(conceptNode, f"crossrefs")
            for crossref in iateConcept['crossrefs']:
                # extract crossref type 
                crossrefType = crossref['type']['name']
                crossrefType = crossrefType.replace(' ', '_')
                # extract crossref's concept ID 
                crossrefID = str(crossref['entry']['id'])
                # add data to xml
                crossrefNode = ET.SubElement(crossrefsNode, 'crossref')
                crossrefNode.set('type', crossrefType)
                crossrefNode.set('conceptID', f"{crossrefID}_concept")
                # add crossref terms
                for lang in crossref['entry']['language'].keys():
                    # update language registry
                    langReg = self.langChecker.check_lang(lang, langReg)
                    entries = crossref['entry']['language'][lang]['term_entries']
                    for termRecord in entries:
                        # crate node for the entry and add (temporary) ID
                        entryNode = ET.SubElement(crossrefNode, 'lexEntry')
                        cleanTerm = string_cleaner(termRecord['term_value'])
                        entryID = f"{crossrefID}_{lang}_{cleanTerm}"
                        entryNode.set('entryID', entryID)
                        # set language
                        entryNode.set('orig_lang', lang)
                        entryNode.set('ref_lang', '')
                        if lang in langReg.keys():
                            entryNode.set('ref_lang', langReg[lang])
                        # enrich with entry / term level data
                        entryNode = self.add_termData(termRecord, entryNode)
                        # add form and sense
                        entryNode = self.add_formData(termRecord, entryNode)
                        # add sense (except relations)
                        entryNode = self.add_senseData(termRecord, entryNode)
                        # update entryID
                        entryNode.set('entryID', f"{entryID}_entry")
                crossrefNode = self.create_SemRels(crossrefNode)
        return conceptNode
        
    def get_grammar(self, field:str, termData:dict, cleanNode):
        if termData['grammatical_details'][field] != None:
            fieldValue = termData['grammatical_details'][field]['name']
            if field in self.config.keys():
                valueConfig = self.config[field]
                if fieldValue in valueConfig.keys():
                    fieldNode = ET.SubElement(cleanNode, field)
                    fieldNode.text = valueConfig[fieldValue]
        return cleanNode   

    def add_senseData(self, termData:dict, entryNode):
        # create sense node
        senseNode = ET.SubElement(entryNode, 'lexSense')
        # set sense id
        entryID = entryNode.attrib['entryID']
        senseID = f"{entryID}_sense"
        senseNode.set('senseID', senseID)
        # set extra data related to sense level
        senseFields = ['validation', 'evaluation', 'reliability', 'lifecycle']
        if 'metadata' in termData.keys():
            for field in senseFields:
                if field in termData['metadata'].keys():
                    if field not in self.config.keys():
                        fieldValue = termData['metadata'][field]['name']
                        fieldCode = termData['metadata'][field]['code']
                        fieldNode = ET.SubElement(senseNode, field)
                        fieldNode.text = fieldValue
                        fieldNode.set('code', str(fieldCode))
                    else:
                        fieldValue = termData['metadata'][field]['name']
                        if fieldValue in self.config[field].keys():
                            nodeName = self.config[field][fieldValue]['class']
                            nodeText = self.config[field][fieldValue]['instance']
                            fieldNode = ET.SubElement(senseNode, nodeName)
                            fieldNode.text = fieldValue
        # contexts
        if 'contexts' in termData.keys():
            contextsNode = ET.SubElement(senseNode, 'contexts')
            contextNum = 1
            for contextRecord in termData['contexts']:
                # context node for each of the contexts
                contextNode = ET.SubElement(contextsNode, 'context')
                contextID = f"{entryID}_context{contextNum}"
                contextNode.set('contextID', contextID)
                # set language
                contextNode.set('orig_lang', entryNode.attrib['orig_lang'])
                contextNode.set('ref_lang', entryNode.attrib['ref_lang'])
                # node for context text
                textNode = ET.SubElement(contextNode, 'textValue')
                textNode.text = contextRecord['context']
                # if the context has references, add them
                if 'reference' in contextRecord.keys():
                    contRefsList = contextRecord['reference']
                    contextNode = self.add_refs(contextNode, contRefsList, contextID)
        # usage notes
        if 'language_usage' in termData.keys():
            # create general node for usage
            usagesNode = ET.SubElement(senseNode, 'usages')
            # create node for particular use; create and set usage id
            usageNode = ET.SubElement(usagesNode, 'usage')
            usageID = f"{entryID}_usage1"
            usageNode.set('usageID', usageID)
            # set language
            usageNode.set('orig_lang', entryNode.attrib['orig_lang'])
            usageNode.set('ref_lang', entryNode.attrib['ref_lang'])
            # subnode for text data
            textNode = ET.SubElement(usageNode, 'textValue')
            usageValue = termData['language_usage']['value']
            textNode.text = usageValue
            # get refs and store
            if 'references' in termData['language_usage'].keys():
                termRefs = termData['language_usage']['references']
                refsNode = self.add_refs(usageNode, termRefs, entryID)
        return entryNode

    def add_formData(self, termData:dict, entryNode):        
        # create node for the form data
        lexformNode = ET.SubElement(entryNode, 'lexForm')
        # create id
        form = termData['term_value']
        entryID = entryNode.attrib['entryID']
        formID = f"{entryID}_{string_cleaner(form)}_form"
        # add form
        formNode = ET.SubElement(lexformNode, 'form')
        formNode.text = form
        # set sense id
        lexformNode.set('formID', formID)
        # add form related data
        if 'grammatical_details' in termData.keys():
            grammarFields = ['gender', 'number'] 
            for grField in grammarFields:
                lexformNode = self.get_grammar(grField, termData, lexformNode)
        return entryNode

    def add_termData(self, termData:dict, entryNode):
        # add term level data
        entryID = entryNode.attrib['entryID']
        if 'term_references' in termData.keys():
            refsNode = ET.SubElement(entryNode, 'references')
            termRefs = termData['term_references']
            refsNode = self.add_refs(refsNode, termRefs, entryID)
        if 'type' in termData.keys():
            termtype = termData['type']['name']
            termtypeConfig = self.config['termtypes']
            if termtype in self.config['termtypes'].keys():
                termtypeNode = ET.SubElement(entryNode, 'termType')    
                termtypeNode.text = self.config['termtypes'][termtype]
        if 'grammatical_details' in termData.keys():
            entryNode = self.get_grammar('part_of_speech', termData, entryNode)
        return entryNode 

    def create_SemRels(self, entryRecsNode):
        entries = entryRecsNode.findall(".//lexEntry")
        for entryInd in range(len(entries)):  
            senseLang = entries[entryInd].attrib['orig_lang']
            senseNode = entries[entryInd].find('.//lexSense')
            senseID = senseNode.attrib['senseID']
            for compInd in reversed(range(len(entries))):
                if entryInd == compInd:
                    break
                compSenseNode = entries[compInd].find(".//lexSense")
                compSenseID = compSenseNode.attrib['senseID']
                compLang = entries[compInd].attrib['orig_lang']
                if senseLang == compLang:
                    synRelNode = ET.SubElement(senseNode, 'synRel')                            
                    synRelNode.set("with", compSenseID)
                    compSynRelNode = ET.SubElement(compSenseNode, 'synRel')                            
                    compSynRelNode.set("with", senseID)
                else: 
                    transRelNode = ET.SubElement(senseNode, 'transRel')
                    transRelNode.set("with", compSenseID)
                    compTransRelNode = ET.SubElement(compSenseNode, 'transRel')                            
                    compTransRelNode.set("with", senseID)
        return entryRecsNode

    def extract_lexicalData(self, iate_data:dict, cleanRoot, langReg:dict):
        # create a lexical data node to store the clean data
        lexDataNode = ET.SubElement(cleanRoot, 'lexicalData')
        try:
        # get concepts and iterate over them        
            concepts_list = ref_node = iate_data['items']
        except:
            print("No 'items' (concepts) found")
            return cleanRoot, langReg
        for iateConcept in concepts_list:
            # create concept node and add concept info
            conceptNode = ET.SubElement(lexDataNode, 'lexConcept')
            # add concept id
            conceptID = str(iateConcept['id'])
            conceptNode.set('originalID', conceptID) 
            conceptNode.set('conceptID', f"{conceptID}_concept") 
            # iterate over language level to get terms
            entryRecsNode = ET.SubElement(conceptNode, 'entryRecords')
            for lang in iateConcept['language'].keys():
                # update language registry
                langReg = self.langChecker.check_lang(lang, langReg)
                # get language level info
                iateLangRecord = iateConcept['language'][lang]
                senseReg = {}
                if 'term_entries' in iateLangRecord.keys():
                    termRecords = iateLangRecord['term_entries'] 
                    senseList =[]
                    for termRecord in termRecords:
                        # crate node for the entry and add (temporary) ID
                        entryNode = ET.SubElement(entryRecsNode, 'lexEntry')
                        cleanTerm = string_cleaner(termRecord['term_value'])
                        entryID = f"{conceptID}_{lang}_{cleanTerm}"
                        entryNode.set('entryID', entryID)
                        # set language
                        entryNode.set('orig_lang', lang)
                        entryNode.set('ref_lang', '')
                        if lang in langReg.keys():
                            entryNode.set('ref_lang', langReg[lang])
                        # enrich with entry / term level data
                        entryNode = self.add_termData(termRecord, entryNode)
                        # add form and sense
                        entryNode = self.add_formData(termRecord, entryNode)
                        # add sense (except relations)
                        entryNode = self.add_senseData(termRecord, entryNode)
                        # update entryID
                        entryNode.set('entryID', f"{entryID}_entry")
            # create semantic relations (synonyms and translations)
            entryRecsNode = self.create_SemRels(entryRecsNode)
            # add concept-related data
            conceptNode = self.get_conceptData(iateConcept, conceptNode, langReg)
        return cleanRoot, langReg

    def create_langSchema(self, cleanRoot, langReg:dict):
        langsNode = ET.SubElement(cleanRoot, 'resource_languages')
        for language in langReg.keys():
            langNode = ET.SubElement(langsNode, 'language')
            langNode.text = langReg[language]
        return cleanRoot

    def clean_terminology(self, filePath):
        # load data
        with open(filePath, 'r', encoding='utf-8') as file:
            iate_data = json.load(file)
        # create the output's root (XML)
        cleanRoot = ET.Element("root")
        fileTitle = Path(filePath).stem
        cleanRoot = self.create_domainSchema(iate_data, cleanRoot)
        langReg = {}
        cleanRoot, langReg = self.extract_lexicalData(iate_data, cleanRoot, langReg)
        cleanRoot = self.create_langSchema(cleanRoot, langReg)
        return cleanRoot

if __name__ == '__main__':
    preprocesador = IATECleaner()
    archivo = r'C:\Users\pdiez\Documents\IATE\IATE_RDF\iate_json_files\abogado_results.json'
    outfile = r'C:\Users\pdiez\Downloads\abogado_results_clean.xml'
    clean_terminology = preprocesador.clean_terminology(archivo)
    clean_terminology = ET.ElementTree(clean_terminology)
    ET.indent(clean_terminology, space="\t", level=0)
    cleanFile = Path(outfile) 
    clean_terminology.write(cleanFile, encoding="utf-8", xml_declaration=True)