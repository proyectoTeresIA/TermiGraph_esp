import re
import pandas as pd
import xml.etree.ElementTree as ET
from check_language import LanguageRegistry
from string_cleaner import string_cleaner
from config_unterm import UNTERM_VALUES, FIELD_COUNTER, TERM_CLEANER


class UNTermCleaner:
    def __init__(self):
        self.langChecker = LanguageRegistry()
   
    def create_domainSchema(self, unterm_df, cleanRoot):
        domainSchema = ET.SubElement(cleanRoot, 'domainSchema')
        utm_dom_col = unterm_df['Categorization']
        domain_set = set()
        for domain_string in utm_dom_col:
            if type(domain_string) == str:
                for domain in domain_string.split(';'):
                    domain = domain.strip()
                    if domain != '':
                        domain_set.add(domain)
        for domain in domain_set:
            domain_node = ET.SubElement(domainSchema, 'domain')
            domainID = f"{string_cleaner(domain.strip())}_domain"
            domain_node.set('domainID', domainID)
            domain_node.text = domain
        return cleanRoot

    def create_langSchema(self, cleanRoot, langReg:dict):
        langsNode = ET.SubElement(cleanRoot, 'resource_languages')
        for language in langReg.keys():
            langNode = ET.SubElement(langsNode, 'language')
            langNode.text = langReg[language]
        return cleanRoot

    def update_counter(self, counter):
        counter += 1
        if counter == 15:
            counter = 0
        return counter

    def split_data(self, data:str):
        clean_list = []
        if str(data) == 'nan':
            return clean_list 
        data_list = data.split(';')
        for item in data_list:
            item = item.strip()
            clean_list.append(item)
        return clean_list

    def create_semRels(self, conceptNode):
        entryNodes = conceptNode.findall('.//lexEntry')
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

    def organize_termInfo(self, termData:dict, field_config:dict, concept_node):
        # term cleaning
        term = termData['term'].strip()
        for issue in TERM_CLEANER:
            term = re.sub(rf'{issue}', '', term)
        status_labels = UNTERM_VALUES['normAuth'].keys()
        # check if labels in term (erase from term + add to sense)
        normAuth_val = ''
        for term_status in status_labels:
            if term_status in term:
                # erase label from term
                term = term.replace(term_status, '').strip()
                # add normAuth
                normAuth_val = UNTERM_VALUES['normAuth'][term_status]
                break
        # check that after all the cleaning, there is a term
        if term == '':
            return concept_node
        # create related nodes
        entryRecs_node = concept_node.find('entryRecords')
        entry_node = ET.SubElement(entryRecs_node, "lexEntry")
        sense_node = ET.SubElement(entry_node, "lexSense")
        lexform_node = ET.SubElement(entry_node, "lexForm")
        # set ids
        conceptID = concept_node.attrib['conceptID']
        termID = f"{conceptID}_{string_cleaner(term)}"
        entry_node.set('entryID', f"{termID}_entry")
        sense_node.set('senseID', f"{termID}_sense")
        lexform_node.set('formID', f"{termID}_form")
        # set language
        entry_node.set("orig_lang", termData['orig_lang'])
        entry_node.set("ref_lang", termData['ref_lang'])
        # add form to form node
        form_node = ET.SubElement(lexform_node, "form")
        form_node.text = term
        # normative authorization
        if normAuth_val != '':
            normAuth_node = ET.SubElement(sense_node, "normAuth")
            normAuth_node.text = normAuth_val
        # if acronym, add termtype
        if 'termType' in field_config.keys():
            termType_node = ET.SubElement(entry_node, "termType")
            termType_node.text = field_config['termType']
            # if additional normAuth info, add
        if 'normAuth' in field_config.keys():
            normAuth_node = ET.SubElement(sense_node, "normAuth")
            normAuth_node.text = field_config['normAuth']
        # add references
        additional_entry_info = ['reference']
        for field in additional_entry_info:
            if field in termData.keys():
                value = termData[field]
                clean_value = value
                for status_label in status_labels:
                    clean_value = clean_value.replace(status_label, '').strip()
                if clean_value != '':
                    # main field node
                    field_main_node = ET.SubElement(entry_node, f"{field}s")
                    # specific field node
                    field_subnode = ET.SubElement(field_main_node, field)
                    field_subnode.set(f"{field}ID", f"{termID}_{field}")
                    field_subnode.text = value
        # add additional sense information
        additional_sense_info = ['usage', 'context']
        for field in additional_sense_info:
            if field in termData.keys():
                value = termData[field]
                clean_value = value
                for status_label in status_labels:
                    clean_value = clean_value.replace(status_label, '').strip()
                if clean_value != '':
                    # main field node
                    field_main_node = ET.SubElement(sense_node, f"{field}s")
                    field_main_node.set("orig_lang", termData['orig_lang'])
                    field_main_node.set("ref_lang", termData['ref_lang'])
                    # specific field node
                    field_subnode = ET.SubElement(field_main_node, field)
                    field_subnode.set(f"{field}ID", f"{termID}_{field}")
                    field_subnode.text = value
        return concept_node

    def add_termiData(
        self, concept_node, row, col_ind:int, field_config:dict, lang:str, langReg:dict
        ):
        # get concept id to generate the rest of the ids
        conceptID = string_cleaner(concept_node.attrib['originalID'])
        # check there are terms, else skip everything
        if str(row.iloc[col_ind]) == 'nan':
            return concept_node
        # split the terms and add them individually
        terms_list = self.split_data(row.iloc[col_ind])
        sources_list = self.split_data(row.iloc[col_ind+1])
        notes_list = self.split_data(row.iloc[col_ind+2])
        contexts_list = self.split_data(row.iloc[col_ind+3])
        for term_ind in range(len(terms_list)):
            term_data = {
                "term": terms_list[term_ind],
                "orig_lang": lang,
                "ref_lang": langReg[lang]
            }
            # add the usage note of that term
            if (term_ind <= len(notes_list)-1) and (len(notes_list) > 0):
                if notes_list[term_ind] != '':
                    term_data['usage'] = notes_list[term_ind]
            # add the usage example (context) of the term
            if (term_ind <= len(contexts_list)-1) and (len(contexts_list) > 0):
                if contexts_list[term_ind] != '':
                    term_data['context'] = contexts_list[term_ind]
            # add the reference of the term
            if (term_ind <= len(sources_list)-1) and (len(sources_list) > 0):
                if sources_list[term_ind] != '':
                    term_data['reference'] = sources_list[term_ind]
            concept_node = self.organize_termInfo(term_data, field_config, concept_node)
        concept_node = self.create_semRels(concept_node)
        return concept_node

    def add_defsNotes(
        self, concept_node, data:str, colNum:int, lang:str, langReg:dict
        ):
        # if no value, skip the rest
        if str(data) == 'nan':
            return concept_node
        # field equivalences
        field_type = FIELD_COUNTER[colNum]['fieldType']
        # create info node
        field_node = concept_node.find(f'{field_type}s')
        info_node = ET.SubElement(field_node, f'{field_type}Info')
        # set language
        info_node.set('orig_lang', lang)
        info_node.set('ref_lang', langReg[lang])  
        # create and set id
        conceptID = string_cleaner(concept_node.attrib['originalID'])
        dataID = f"{conceptID}_{lang}_{field_type}"  
        info_node.set(f"{field_type}ID", dataID)
        # set text value
        text_node = ET.SubElement(info_node, f'{field_type}')
        text_node.text = data
        return concept_node


    def extract_colData(
        self, row, columns:list, concept_node, langReg:dict
        ):
        ''''
            Counter goes from 0 to 14. At 15 should start again
        '''
        # add domains, if any
        domain_data = row['Categorization']
        if str(domain_data) != 'nan':
            # add generic node for organiztion
            domains_node = ET.SubElement(concept_node, 'conceptDomains')
            # split domains and iterate. Create subnode for each one and add id
            domains_list = domain_data.split(';')
            for domain in domains_list:
                domainID = f"{string_cleaner(domain.strip())}_domain"
                domain_node = ET.SubElement(domains_node, 'domain')
                domain_node.set('domainID', domainID)
        # iterate over the cols with the lexical/terminological data
        counter = 0
        orig_lang= ''
        for col_ind in range(4, 109):
            # get language if changed (only changes in preferred terms)
            if FIELD_COUNTER[counter]['fieldType'] == 'preferred_term':
                orig_lang = columns[col_ind].replace(' preferred', '')
                if orig_lang not in langReg.keys():
                    langReg = self.langChecker.check_lang(orig_lang, langReg)
            # add concept data (defs and lang notes)
            if FIELD_COUNTER[counter]['fieldType'] in ['definition', 'note']:
                data = row.iloc[col_ind]
                concept_node = self.add_defsNotes(
                    concept_node, data, counter, orig_lang, langReg
                    )
            # enrtu records node
            entryRecs_node = ET.SubElement(concept_node, "entryRecords")
            # add if terms
            entry_fields = ['preferred_term', 'alternate_term', 'acronym']
            if FIELD_COUNTER[counter]['fieldType'] in entry_fields:
                field_config = FIELD_COUNTER[counter]
                concept_node = self.add_termiData(
                    concept_node, row, col_ind, field_config, orig_lang, langReg
                )
            # update counter
            counter = self.update_counter(counter)
        return concept_node

    
    def extract_data(self, unterm_df, cleanRoot):
        lexData_node = ET.SubElement(cleanRoot, 'lexicalData')
        columns = unterm_df.columns.tolist()
        col_len = len(columns)
        langReg = {}
        for index, row in unterm_df.iterrows():
            # create concept and set ids
            concept_node = ET.SubElement(lexData_node, 'lexConcept')
            concept_node.set('conceptID', f"{row['Record ID']}_concept")
            concept_node.set('originalID', row['Record ID'])    
            # create defs and notes nodes
            defs_node = ET.SubElement(concept_node, 'definitions')
            notes_node = ET.SubElement(concept_node, 'notes')
            # iterate over the cols to get the info of the terminological record
            concept_node = self.extract_colData(row, columns, concept_node, langReg)
        return cleanRoot, langReg


    def clean_terminology(self, file_path):
        # load file into pandas
        unterm_df = pd.read_excel(file_path)
        # create new clean tree
        cleanRoot = ET.Element("root")
        # start cleaning the data
        cleanRoot = self.create_domainSchema(unterm_df, cleanRoot)
        # extract terminological content
        cleanRoot, langReg = self.extract_data(unterm_df, cleanRoot)
        # create language schema
        cleanRoot = self.create_langSchema(cleanRoot, langReg)
        return cleanRoot