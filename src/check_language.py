from rdflib import Graph, Literal, Namespace
from rdflib.namespace import XSD, RDFS
from pathlib import Path
from unidecode import unidecode

class ISOCodeExtractor:
    def __init__(self):
        ontology = Path(Path(__file__).parent, "lexvo_2013-02-09_reduced.nt")
        # Crear un grafo vacío y el archivo N-Triples
        self.graph = Graph()
        self.graph.parse(ontology, format="nt")

    
    def check_iso(self, lang:str):
        literal_lang = Literal(lang, datatype=XSD.string)
        iso_types = ['iso639P1Code', 'iso639P3PCode']
        lang_urls = set()
        lvont = Namespace("http://lexvo.org/ontology#")
        for iso_type in iso_types:
            iso_prop = lvont[iso_type]  # Aquí creas el URIRef para la propiedad
            q = f"""
                SELECT ?s
                WHERE {{ ?s <{iso_prop}> {literal_lang.n3()} . }}
            """
            results = self.graph.query(q)
            for row in results:
                lang_urls.add(str(row.s))
        return lang_urls

    def get_from_label(self, lang:str):
        lang_results = set()
        for s, p, o in self.graph.triples((None, RDFS.label, None)):
            if isinstance(o, Literal):
                # Check the lexical value regardless of the language tag
                if lang.lower() == str(o.value).lower():  # o.value ignores language
                    lang_results.add(str(s))
                elif lang.lower() == unidecode(str(o.value).lower()):
                    lang_results.add(str(s))
        return lang_results

    def get_url(self, lang:str):
        '''Check if language in lexvo, depending on length. 
        If longer than 2 char, check on codes; otherwise check in labels'''
        lang_url = ''
        if len(lang) <= 3:
            url_set = self.check_iso(lang)
            if len(url_set) == 1:
                for url in url_set:
                    lang_url = url
        else:
            url_set = self.get_from_label(lang)
            if len(url_set) == 1:
                for url in url_set:
                    lang_url = url
        return lang_url
        
class LanguageRegistry:
    def __init__(self):
        self.langSearcher = ISOCodeExtractor()
    
    def check_lang(self, lang:str, registry:dict={}):
        if lang not in registry.keys():
            #check if lang is an exception of lexvo
            exceptions_spanish = ['esp', 'gaztelera']
            if lang in exceptions_spanish:
                lang_url = "http://lexvo.org/id/iso639-3/spa"
                registry[lang] = lang_url
            # if not an exception, search in lexvo
            else:
                lang_url = self.langSearcher.get_url(lang)
                if len(lang_url) > 0:
                    registry[lang] = lang_url
                else: 
                    registry[lang] = ""
        return registry