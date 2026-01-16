from preprocessor_glossary import GlossaryCleaner
from preprocessor_tbx import TBXCleaner
from preprocessor_termcat import TermcatCleaner
from preprocessor_iate import IATECleaner
from preprocessor_unterm import UNTermCleaner
from pathlib import Path


PREPROCESSORS = {
    'glossary': {
        "format": '.txt',
        "converter": GlossaryCleaner(),
        "page2_template": 'pag2_glosario.html',
        "mandatory_fields": ['author', 'title', 'resource_lang'],
        "optional_fields": ['resource_link']
        },
    'termcat_xml': {
        "format": '.xml',
        "converter": TermcatCleaner(),
        "page2_template": 'pag2_no_glosario.html',
        "mandatory_fields": ['author', 'title'],
        "optional_fields": ['resource_link']
        },
    'tbx_basic': {
        "format": '.tbx',
        "converter": TBXCleaner(),
        "page2_template": 'pag2_no_glosario.html',
        "mandatory_fields": ['author', 'title'],
        "optional_fields": [ 'resource_link']
        },
    'iate_json': {
        "format": '.json',
        "converter": IATECleaner(),
        "page2_template": 'pag2_no_glosario.html',
        "mandatory_fields": ['author', 'title'],
        "optional_fields": ['resource_link']
        },
    'unterm_csv': {
        "format": '.xlsx',
        "converter": UNTermCleaner(),
        "page2_template": 'pag2_no_glosario.html',
        "mandatory_fields": ['author', 'title'],
        "optional_fields": ['resource_link']
    }
}

# Source (scripts) folder
SCR_DIR = Path(__file__).parent

# Data folder for session folders
DATA_DIR = Path(SCR_DIR, '../data')

# this name is strictly linked to the file name in mapeathor templates
TEMP_FILENAME = 'clean_terminology'

# template for split parts
SPLIT_FILENAME = 'clean_part_'

# Config for Mapeathor
MAPEATHOR = {
    'template': 'https://docs.google.com/spreadsheets/d/1PpJ327pgdAwHmRDx9-oDiV02XdCO82mzJoo4bFikgGo/edit?usp=sharing',
    'language': 'rml2014'
}

# Mapper: path, heap size, and max size of input file to avoid crash (in bytes)
# Note: heap_size and max_size are closely related 
# Note: serialization and suffix are closely related
MAPPER = {
    'java': Path(SCR_DIR, 'jdk-17.0.17+10/bin/java'),
    'mapper' : Path(SCR_DIR, 'rmlmapper-7.3.1-r374-all.jar'),
    'heap_size' : '8G', 
    'max_size': 300000000,
    'serialization': 'turtle',
    'suffix': 'ttl'
}

# prefixes for turtle in case of split and merge
PRXS = {
        "base": "http://myexample.com/" ,
        "dbo": "http://dbpedia.org/ontology/" ,
        "dct": "http://purl.org/dc/terms/" ,
        "dul": "http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#" ,
        "etv": "https://w3id.org/def/easytv#" ,
        "eurovoc": "http://eurovoc.europa.eu/" ,
        "foaf": "http://xmlns.com/foaf/0.1/" ,
        "lexicog": "http://www.w3.org/ns/lemon/lexicog#" ,
        "lexinfo": "http://www.lexinfo.net/ontology/3.0/lexinfo#" ,
        "lexvo": "http://lexvo.org/id/" ,
        "lv": "http://lexvo.org/id/iso639-3/" ,
        "lvont": "http://lexvo.org/ontology#" ,
        "ms": "http://w3id.org/meta-share/meta-share/" ,
        "olia": "http://purl.org/olia/olia.owl#" ,
        "ontolex": "http://www.w3.org/ns/lemon/ontolex#", 
        "owl": "http://www.w3.org/2002/07/owl#" ,
        "prov": "http://www.w3.org/ns/prov#" ,
        "rdf": "https://www.w3.org/1999/02/22-rdf-syntax-ns#" ,
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#" ,
        "rico": "https://www.ica.org/standards/RiC/ontology#" ,
        "rml": "http://w3id.org/rml/" ,
        "skos": "http://www.w3.org/2004/02/skos/core#" ,
        "synsem": "http://www.w3.org/ns/lemon/synsem#" ,
        "termlex": "https://termlex.oeg.fi.upm.es/termlex#" ,
        "vartrans": "http://www.w3.org/ns/lemon/vartrans#" ,
        "wdt": "https://www.wikidata.org/wiki/Property:" ,
        "xsd": "http://www.w3.org/2001/XMLSchema#"
    }