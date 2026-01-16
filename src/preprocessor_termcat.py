import re
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from string_cleaner import string_cleaner
from check_language import LanguageRegistry
from unidecode import unidecode


class FormGenerator:
    def __init__(self) -> None:
        self.vowels = ["a", "e", "i", "o", "u"]

    def create_terms(self, wordlist:list, indStore:list):
        fem_Wlist = []
        masc_Wlist = []
        for ind in range(len(wordlist)):
            if ind in indStore:
                fem_Wlist[-1] = wordlist[ind]
            else:
                masc_Wlist.append(wordlist[ind])
                fem_Wlist.append(wordlist[ind])
        mascTerm = ' '.join(masc_Wlist)
        femTerm = ' '.join(fem_Wlist)
        return [mascTerm, femTerm]
        
    def handle_forms(self, termino:str) -> list:
        palabras = termino.split(" ")
        indStore = []
        for wordInd in range(len(palabras)):
            if palabras[wordInd].startswith('-'):
                femSuf = palabras[wordInd].replace('-', '')
                mascForm = palabras[wordInd-1]
                '''if the fem suffix is only one letter (vowel),
                a) replace the ending vowel, or
                b) add it to the masc form (ends in consonant)'''
                # if the fem suffix is only one vowel
                if len(femSuf) == 1:
                    # if the masc form ends with a vowel, we repace it
                    if unidecode(mascForm[-1]) in self.vowels:
                        femForm = mascForm.replace(mascForm[-1], femSuf)
                        palabras[wordInd] = femForm
                        indStore.append(wordInd)
                    # if the masc form ends with a consonant, we add the vowel
                    else:
                        femForm = mascForm+femSuf
                        palabras[wordInd] = femForm
                        indStore.append(wordInd)
                # if the fem suffix is longer than one
                else:
                    chunks = unidecode(mascForm).rsplit(unidecode(femSuf[0]), 1)
                    chunks[-1] = femSuf
                    femForm = ''.join(chunks)
                    palabras[wordInd] = femForm
                    indStore.append(wordInd)
        # once you have all the fem words done, use the indStore to create two lists, fem and masc    
        terms = self.create_terms(palabras, indStore)
        return terms


class FormManagement:
    def __init__(self) -> None:
        BASE_DIR = Path(__file__).parent
        config_name = 'config_termcat.json'
        with open(Path(BASE_DIR, config_name)) as config_file:
            config_data = json.load(config_file)
        self.gramValues = config_data['grammar_values']
        self.dobleForms = config_data['double_forms']
        self.termTypeVals = config_data['termTypes']
        self.form_generator = FormGenerator()

    def split_forms(self, texto:str):
        if " | " in texto:
            return texto.split(" | ")
        elif "<b>| <b>" in texto:
            return texto.split("| ")
        elif " -" in texto:
            return self.form_generator.handle_forms(texto)
        else:
            return [texto, texto]

    def create_formNode(self, entryNode, formAndGram:tuple):
        '''Creamos un nodo por cada forma y añadimos la 
        información relativa a la forma'''
        formNode = ET.SubElement(entryNode, 'lexForm')
        form, gramValue = formAndGram
        # añadimos la forma
        textNode = ET.SubElement(formNode, 'form')
        textNode.text = form
        # creamos id temporal de la forma
        formID = string_cleaner(form)
        # extract pos and add to ID
        pos = self.gramValues[gramValue]['pos']
        if pos:
            formID = f"{formID}_{pos}"
        # añadimos la información extra relativa a la forma o entry
        extraFormFields = ['gender', 'number']
        extraInfo = self.gramValues[gramValue]['additionalInfo']
        for infoType in extraInfo.keys():
            # por si tenemos varios valores de una clase
            if type(extraInfo[infoType]) != list:
                values = [extraInfo[infoType]]
            # seleccionamos bajo qué nodo estará la info
            if infoType in extraFormFields:
                # iteramos
                for value in values:
                    # creamos nodo
                    valueNode = ET.SubElement(formNode, infoType)
                    # añadimos valor  
                    valueNode.text = extraInfo[infoType]
                    # update form ID with the new info
                    formID += f"_{extraInfo[infoType]}" 
            else:
                # iteramos
                for value in values:
                    # creamos nodo
                    valueNode = ET.SubElement(entryNode, infoType)
                    # añadimos valor  
                    valueNode.text = extraInfo[infoType]                   
         # base para crear los ids
        entryID = entryNode.attrib['entryID']
        formNode.set("formID", f"{entryID}_{formID}_form")
        return entryNode

    def clean_forms(self, entryTCNode, entryNode):
        '''En algunos strings encontramos dos formas de un mismo término,
        la masculina y la femenina. Aquí comprobamos si el término tiene 
        más de una forma. En caso de tenerlas, las limpiamos mediante la 
        función split_forms. Sino añadimos el término a la lista tal cual.'''
        if entryTCNode.attrib['categoria'] in self.dobleForms.keys(): 
            splitedForms = self.split_forms(entryTCNode.text)
            formsGramInfo = self.dobleForms[entryTCNode.attrib["categoria"]]
            formsList = []
            for formInd in range(len(splitedForms)):
                formTuple = (splitedForms[formInd], formsGramInfo[formInd])
                formsList.append(formTuple)    
        else:
            formsList = [(entryTCNode.text, entryTCNode.attrib['categoria'])]
        # create form subodes thorugh create_formNode function
        entryForms = [] # to update the entryID
        for formTuple in formsList:
            entryNode = self.create_formNode(entryNode, formTuple)
            # extract pos info and form info to update the entryID
            form, gramValue = formTuple
            pos = self.gramValues[gramValue]['pos']
            cleanForm = string_cleaner(form)
            if cleanForm not in entryForms:
                entryForms.append(cleanForm)
        # add part-os-speech (pos) info
        posNode = ET.SubElement(entryNode, 'part_of_speech')
        posNode.text = pos
        # actualizar el ID de la entry con las formas
        entryID = entryNode.attrib['entryID']
        entryID = f"{entryID}_{'_'.join(entryForms)}"
        if pos != '':
            entryID = f"{entryID}_{pos}"
        entryID = f"{entryID}_entry"
        entryNode.set("entryID", entryID)
        return entryNode

    def manage_signedForm(self, fitxaTC, entryTCNode, entryNode):
        singFormNode = ET.SubElement(entryNode, 'signedForm')
        # search the written term of the signed form
        entries = fitxaTC.findall('.//{}'.format("denominacio"))
        for entry in entries:
            if entry.attrib['tipus']=='principal':
                writtenTerm = string_cleaner(entry.text)
        entryNode.set('entryID', f"{entryNode.attrib['entryID']}_{writtenTerm}")
        singFormNode.set('formID', f"{entryNode.attrib['entryID']}_{writtenTerm}_signedForm")
        # copy video
        videoNode = ET.SubElement(singFormNode, 'video')
        videoNode.set('videoID', f"{entryNode.attrib['entryID']}_video")
        videoNode.text = entryTCNode.text
        return entryNode 




class TermcatCleaner():
    def __init__(self):
        # load config
        # Open and load the JSON file
        config_path = Path(Path(__file__).parent, 'config_termcat.json')
        with config_path.open("r", encoding="utf-8") as file:
            valuesConfig = json.load(file)   
        # search for and load 
        self.signLangVals = valuesConfig['signed_languages']
        self.termTypes = valuesConfig['termTypes']
        self.codeVals = valuesConfig['identifiers']
        # prepare the domain and form cleaners
        self.formCleaner = FormManagement()  
        self.langChecker = LanguageRegistry()
    
    def add_termType(self, entryTC, cleanEntry, field):
        termType = entryTC.attrib[field]
        termTypeNode = ET.SubElement(cleanEntry, 'termType')
        termTypeNode.text = self.termTypes[termType]            
        return cleanEntry

    def manage_langInfo(self, entryTC, cleanEntry, lang:str, langReg:dict):
        cleanEntry.set('orig_lang', '')
        cleanEntry.set('ref_lang', '')
        # if language is actually a code or cas number
        if lang in self.codeVals.keys():
            # get code type and value
            codeType = self.codeVals[entryTC.attrib['llengua']]
            codeValue = entryTC.text
            # prepare the node for code info
            codeNode = ET.SubElement(cleanEntry, codeType)
            # fill node with data
            codeNode.text = codeValue
        # if language is actually term-type
        elif lang in self.termTypes:
            cleanEntry = self.add_termType(entryTC, cleanEntry, 'llengua')
        # if signed language
        elif lang in self.signLangVals.keys():
            cleanEntry.set('ref_lang', f"{self.signLangVals[lang]}")
            langReg[lang] = self.signLangVals[lang]
        # if actually a language
        else:
            # update orig_lang
            cleanEntry.set('orig_lang', lang)
            # check if language in language registry, else add it
            if lang not in langReg.keys():
                langReg = self.langChecker.check_lang(lang, langReg)
            cleanEntry.set('ref_lang', f"{langReg[lang]}")
        return cleanEntry, langReg
            
    
    
    def get_IDs(self, refList, compLists):
        cleanList = []
        for domInd in range(len(refList)):
            domain = refList[domInd]
            domainID = string_cleaner(domain)
            if domInd == 0:
                cleanList.append(domainID)
            else:
                finalID = ''
                for compList in compLists:
                    for compInd in range(len(compList)):
                        compDomain = compList[compInd]
                        if domain != compDomain:
                            finalID = domainID
                        else:
                            prevInd = domInd-1
                            prevCompInd = compInd-1
                            prevDomain = refList[prevInd]
                            prevCompDomain = compList[prevCompInd]   
                            domainID = f"{string_cleaner(prevDomain)}_{string_cleaner(domain)}"
                            compDomainID = f"{string_cleaner(prevCompDomain)}_{string_cleaner(compDomain)}"
                            condition1 = domainID == compDomainID
                            condition2 = prevInd >= 1
                            condition3 = prevCompInd >= 1
                            while condition1 and condition2 and condition3:
                                prevInd = prevInd-1
                                prevCompInd = prevCompInd-1
                                prevDomain = refList[prevInd]
                                prevCompDomain = compList[prevCompInd]   
                                domainID = f"{string_cleaner(prevDomain)}_{string_cleaner(domain)}"
                                compDomainID = f"{string_cleaner(prevCompDomain)}_{string_cleaner(compDomain)}"
                            if len(domainID) > len(finalID):
                                finalID = domainID
                cleanList.append(finalID)            
        return cleanList

    def clean_domains(self, domainChainSet:set):
        '''we split the string of domains first. 
        Then we iterate over all of the lists and generate IDs for each, 
        checking there will be no different subdomais with same ID'''
        splitDomains = []
        for domainChain in domainChainSet:
            split_mark = ' > '
            splitDomains.append(domainChain.split(split_mark)) 
        domain_config = {}
        cleanDomains = {}
        for currentInd in range(len(splitDomains)):
            # we extract the current list from the rest, that will be used to compare
            currentList = splitDomains.pop(currentInd)
            cleanIDList = self.get_IDs(currentList, splitDomains)
            cleanDomains[currentInd] = {"domain_list": currentList,
                                        "id_list": cleanIDList}
            # we insert the current list of analysis back on its original place
            splitDomains.insert(currentInd, currentList)
            # we update the domain config
            domainChain = split_mark.join(currentList)
            lastID = cleanIDList[-1]
            domain_config[domainChain] = lastID
        return cleanDomains, domain_config   

    def create_domainSchema(self, cleanDomains:dict, domainSchemaNode):
        added_ids = set()
        for dictInd in cleanDomains:
            # create the schema, the clean subnodes
            domainDict = cleanDomains[dictInd]
            for idInd in range(len(domainDict["id_list"])):
                domainID = domainDict["id_list"][idInd]
                if domainID not in added_ids:
                    if idInd == 0:
                        domainNode = ET.SubElement(domainSchemaNode, 'domain')
                        domainNode.text = domainDict["domain_list"][idInd]
                        domainNode.set('domainID', domainID)
                        added_ids.add(domainID)
                    else:
                        # find previous domain to create subnode 
                        prevID = domainDict["id_list"][idInd-1]
                        prevNodePath = f".//domain[@domainID='{prevID}']"
                        prevDomainNode = domainSchemaNode.find(prevNodePath)
                        # create subonode and add data
                        currentDomainNode = ET.SubElement(prevDomainNode, 'domain')
                        currentDomainNode.text = domainDict["domain_list"][idInd]
                        currentDomainNode.set('domainID', domainID)
                        # update the register of domains added
                        added_ids.add(domainID)
        return domainSchemaNode   

    def handle_domains(self, inRoot, cleanRoot):
        # create node for the schema
        domainSchemaNode = ET.SubElement(cleanRoot, 'domainSchema')
        # search for the concept with domains, clean domains/hierarchy and set ids
        tcDomainsNode = inRoot.findall('.//areatematica')
        domainChainsSet = set()
        for tcDomainNode in tcDomainsNode:
            domainChainsSet.add(tcDomainNode.text)
        cleanDomains, domain_config = self.clean_domains(domainChainsSet)
        domainSchemaNode = self.create_domainSchema(cleanDomains, domainSchemaNode)
        return cleanRoot, domain_config

    def create_SemRels(self, cleanRoot):
        cleanConcepts = cleanRoot.findall('.//{}'.format("lexConcept"))
        for conceptNode in cleanConcepts:
            entries = conceptNode.findall('.//{}'.format("lexEntry"))
            for entryInd in range(len(entries)):
                termSenseNode = entries[entryInd].find('.//{}'.format("lexSense"))
                for compInd in range(len(entries)):
                    if entryInd != compInd:
                        compSenseID = entries[compInd].find('.//{}'.format("lexSense")).attrib['senseID']
                        if entries[entryInd].attrib['orig_lang'] == entries[compInd].attrib['orig_lang']:
                            synRelNode = ET.SubElement(termSenseNode, 'synRel')
                            synRelNode.set("with", compSenseID)
                        else: 
                            transRelNode = ET.SubElement(termSenseNode, 'transRel')
                            transRelNode.set("with", compSenseID)
        return cleanRoot
    
    def concept_domains(self, fitxa, conceptNode, domain_config):
        domainsNode = ET.SubElement(conceptNode, 'conceptDomains')
        domainsList = fitxa.findall('./areatematica')
        for domain in domainsList:
            domainID = domain_config[domain.text]
            domainNode = ET.SubElement(domainsNode, 'domain')
            domainNode.set('domainRef', domainID)
        return conceptNode
    
    def add_defs_notes(self, fitxa, conceptNode, langReg:dict):
        fields = {'definicio': 'definition',
                  'nota': 'note'
                }      
        for field in fields.keys():
            elementList = fitxa.findall(f'.//{field}')
            if len(elementList) > 0:
                dataNode = ET.SubElement(conceptNode, f'{fields[field]}s')
                counter = {}
                for elem in elementList:
                    # create subnode
                    infoNode = ET.SubElement(dataNode, f'{fields[field]}Info')
                    # extract necessary data
                    lang = elem.attrib['llengua']
                    # update counter
                    if lang not in counter.keys():
                        counter[lang] = 0
                    counter[lang] += 1
                    # create id and update infoNode
                    conceptID = conceptNode.attrib['conceptID']
                    elemID = f"{conceptID}_{lang}_{fields[field]}{counter[lang]}"
                    infoNode.set(f"{fields[field]}ID", elemID)
                    # set language
                    infoNode.set('orig_lang', lang)
                    infoNode.set('ref_lang', "") 
                    langReg = self.langChecker.check_lang(lang, langReg)
                    if lang in langReg.keys():
                        infoNode.set('ref_lang', langReg[lang])
                    # add text in subnode
                    textNode = ET.SubElement(infoNode, f'{fields[field]}')
                    textNode.text = elem.text
        return conceptNode

    def create_sense(self, entryTC, entryNode):
        senseNode =  ET.SubElement(entryNode, 'lexSense')
        entryID = entryNode.attrib['entryID']
        senseID = re.sub(r'_entry$', '_sense', entryID)
        senseNode.set('senseID', senseID)
        if entryTC.attrib['tipus'] == 'remissio':
            normAuthNode = ET.SubElement(senseNode, 'normAuth')
            normAuthNode.text = 'deprecated'
        elif entryTC.attrib['jerarquia'] == 'den. desest.':
            normAuthNode = ET.SubElement(senseNode, 'normAuth')
            normAuthNode.text = 'deprecated'
        return entryNode

    def handle_entries(self, fitxaNode, conceptNode, langReg:dict):
        entriesTC = fitxaNode.findall('.//{}'.format("denominacio"))
        entryRecsNode = ET.SubElement(conceptNode, 'entryRecords')
        for entryTC in entriesTC:
            entryNode =  ET.SubElement(entryRecsNode, 'lexEntry')
            # extract language
            lang = entryTC.attrib['llengua']
            # deal with languages
            entryNode, langReg = self.manage_langInfo(entryTC, entryNode, lang, langReg)
            # set temporal id
            entryID = f"{conceptNode.attrib['conceptID']}_{lang}"
            entryNode.set('entryID', entryID)
            # set entryType (lexical entry, prefix, suffix)
            if entryTC.attrib['categoria'] == 'pfx':
                entryNode.set('entryType', "prefix")
            elif entryTC.attrib['categoria'] == 'sfx':
                entryNode.set('entryType', "suffix")
            else:
                entryNode.set('entryType', "lexicalEntry")  
            # handle signed forms / written forms
            if lang in self.signLangVals.keys():
                entryNode = self.formCleaner.manage_signedForm(fitxaNode, entryTC, entryNode)
            else:
                entryNode = self.formCleaner.clean_forms(entryTC, entryNode)
            # check if it has any termtype in jerarquia or categoria
            termcat_fields = ['jerarquia', 'categoria']
            for field in termcat_fields:
                if entryTC.attrib[field] in self.termTypes.keys():
                    entryNode = self.add_termType(entryTC, entryNode, field)    
            # add sense node and info
            entryNode = self.create_sense(entryTC, entryNode)   
        return conceptNode

    def handle_lexData(self, inRoot, cleanRoot, domain_config:dict, langReg:dict):
        # create a node for the lexical data in the new tree
        termsNode = ET.SubElement(cleanRoot, 'lexicalData')
        # search for the lexical data
        fitxa_nodes = inRoot.findall('.//{}'.format("fitxa"))
        for fitxa in fitxa_nodes:
            conceptNode = ET.SubElement(termsNode, 'lexConcept')
            # copy TC id and create concept ID
            conceptNode.set("tcID", f"{fitxa.attrib['num']}")
            conceptNode.set("conceptID", f"C{fitxa.attrib['num']}")
            # deal with domains
            conceptNode = self.concept_domains(fitxa, conceptNode, domain_config)
            # handle entries, forms and create senses
            conceptNode = self.handle_entries(fitxa, conceptNode, langReg) #it also deals with forms and creates senses
            # add definitions and notes
            conceptNode = self.add_defs_notes(fitxa, conceptNode, langReg)
        # create sense relations (synonyms and translations)
        cleanRoot = self.create_SemRels(cleanRoot)
        return cleanRoot, langReg

    def create_langSchema(self, cleanRoot, langReg:dict):
        langsNode = ET.SubElement(cleanRoot, 'resource_languages')
        for language in langReg.keys():
            langNode = ET.SubElement(langsNode, 'language')
            langNode.text = langReg[language]
        return cleanRoot

    def clean_terminology(self, filePath):
        # load/read tree
        tree = ET.parse(filePath)
        inRoot = tree.getroot()
        # create new clean tree
        cleanRoot = ET.Element("root")
        # start cleaning the data
        cleanRoot, domain_config =  self.handle_domains(inRoot, cleanRoot)
        langReg = {}
        cleanRoot, langReg = self.handle_lexData(inRoot, cleanRoot, domain_config, langReg)
        cleanRoot = self.create_langSchema(cleanRoot, langReg)
        return cleanRoot    