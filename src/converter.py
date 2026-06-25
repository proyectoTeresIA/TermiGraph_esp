import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
from string_cleaner import string_cleaner
from rdflib import Graph, Namespace
from config_converter import PREPROCESSORS, SCR_DIR, MAPPER, TEMP_FILENAME, PRXS, MAPEATHOR
import time
import os
import math

def merge_ttls_from_folder(
    dir_path, filter_files='', out_file='merged.ttl', namespaces={}):
    print(f'Checking {dir_path}')
    if not Path(dir_path).is_dir():
        return print('No es una carpeta')
    g = Graph()
    for prefix in namespaces.keys():
        ontoURI = Namespace(namespaces[prefix])
        g.bind(prefix, ontoURI, replace=True)
    print('Namespaces added to graph')
    for file in Path(dir_path).iterdir():  
        # Check if it's a file
        name_check = str(filter_files) in str(file.stem)
        print(filter_files, file.stem, name_check)
        serialization_check = file.suffix == '.ttl'
        if file.is_file() and serialization_check and name_check:  
            print(f'Loading and adding {file}')
            g.parse(file)
    print('-- LOADING FINISHED --')
    g.serialize(out_file, format="turtle")
    print(f'File saved: {out_file}')


def split_xml(tree, out_dir, outname='clean_pt'):
    root = tree.getroot()
    concept_list = root.findall('.//lexConcept')
    concept_num = 600
    splits_needed = math.ceil(len(concept_list)/concept_num)
    splits_reg = []
    for split_ind in range(splits_needed):
        new_root = ET.Element("root")
        # add data, except terminological (only in the fist partition)
        if split_ind == 0:
            for node in root:
                if node.tag != 'lexicalData':
                    new_root.append(node)
        else:
            title_node = root.find('title')
            new_root.append(title_node)
        # add terminological data
        concept_start = concept_num * split_ind
        concept_end = concept_start + concept_num
        lexData_node = ET.SubElement(new_root, 'lexicalData')
        for concept in concept_list[concept_start:concept_end]:
            lexData_node.append(concept)
        new_tree = ET.ElementTree(new_root)
        ET.indent(new_tree, space="\t", level=0)
        file_name = f'{outname}{split_ind}.xml'
        out_path = Path(out_dir, file_name)
        print(f'Saving {file_name}')
        new_tree.write(out_path, encoding="utf-8", xml_declaration=True)
    # erase clean terminology

def add_prov(clean_root, provDict:dict): 
    for field in provDict.keys():
        if field == 'title':
            node = ET.SubElement(clean_root, field)
            node.text = provDict[field]
            fieldID = string_cleaner(provDict[field])
            node.set(f"{field}ID", fieldID)
        elif field in ['author', 'domain']:
            # crear nodo genérico
            node = ET.SubElement(clean_root, f'resource_{field}s')
            # separar los datos(str a list)
            data_list = provDict[field].split(";")
            for element in data_list:
                subnode = ET.SubElement(node, f'resource_{field}')
                subnode.text = element.strip()
                if 'eurovoc:' in element:
                    fieldID = string_cleaner(element.replace('eurovoc:', ''))
                    subnode.set(f"eurovocID", fieldID)
                else:
                    fieldID = string_cleaner(element)
                    subnode.set(f"{field}ID", fieldID)
        elif field == 'resource_link':
            node = ET.SubElement(clean_root, field)
            node.text = provDict[field]
    return clean_root


def convert_from_file(file_path:str, converter_type:str, provData={}):
    start = time.time()
    expected_ext = PREPROCESSORS[converter_type]["format"]
    actual_ext = Path(file_path).suffix
    # if incorrect format, error message
    if expected_ext != actual_ext:
        error_mes = "Error de formato, tipo de fichero o conversor equivocado."
        error_mes += f"Fichero esperado: {expected_ext}"
        error_mes += f"Fichero proporcionado: proporcionado {actual_ext}"
        return error_mes
    # create all the directories necessary for data storage
    file_dir = Path(file_path).parent
    file_name = Path(file_path).stem
    # execute the cleaner and save clean terminology (with temporary name)
    converter = PREPROCESSORS[converter_type]["converter"]
    if converter_type == 'glossary':
        lang = provData['resource_lang']
        clean_terminology = converter.clean_terminology(file_path, lang)
    else:
        clean_terminology = converter.clean_terminology(file_path)
    # add provenance
    clean_terminology = add_prov(clean_terminology, provData)
    # save xml
    clean_terminology = ET.ElementTree(clean_terminology)
    ET.indent(clean_terminology, space="\t", level=0)
    cleanFile = Path(file_dir, f"{TEMP_FILENAME}.xml") 
    clean_terminology.write(cleanFile, encoding="utf-8", xml_declaration=True)
    # create mappings
    out_mappings = f"{file_name}_mappings"
    cmd_mapeathor = (
        f"python -m mapeathor -i {MAPEATHOR['template']} "
        f"-l {MAPEATHOR['language']} -o {out_mappings}"
    )
    subprocess.call(cmd_mapeathor, shell=True, cwd=file_dir)
    # run convrsion, according to file size
    if os.stat(cleanFile).st_size <= MAPPER['max_size']:
        # RUNNING FULL RML MAPPING
        return_code = subprocess.call(
            f"{MAPPER['java']} -Xmx{MAPPER['heap_size']} -jar {MAPPER['mapper']} "
            f"-m {out_mappings}.rml.ttl -o {file_name}_rdf.ttl -s turtle",
            shell=True, cwd=file_dir
        )
        # Rename preprocessed terminology 
        new_file = Path(file_dir, f'{file_name}_clean.xml')
        os.rename(cleanFile, new_file)
    else:
        # If the file is too big, it will fail (oom), so the xml file is split
        print(f"\nFile bigger than {MAPPER['max_size']} bytes\n")
        # Step 1 — Split
        complete_file = Path(file_dir, 'clean_complete.xml')
        os.rename(cleanFile, complete_file)
        print("### SPLITTING CLEAN FILE ###")
        clean_pts_template = "clean_pt"
        split_xml(clean_terminology, file_dir, clean_pts_template)
        parts = sorted([p for p in os.listdir(file_dir) if p.startswith(clean_pts_template)])
        # erase 'clean_terminology.xml' for future steps
        print(f"Created {len(parts)} chunks\n")
        # Step 2 — Process chunks
        print("### CONVERTING EACH SPLIT ###")
        for index, part in enumerate(parts):
            print(f"Processing chunk {index}: {part}")
            # Rename so that the mapping file works correctly
            current_file = Path(file_dir, f"{clean_pts_template}{index}.xml")
            os.rename(current_file, cleanFile)
            # Prepare comamnd
            ttl_templ = f"{file_name}_rdf_pt"
            out_rdf = f"{ttl_templ}{index}.{MAPPER['suffix']}"
            cmd = (
                f"{MAPPER['java']} -Xmx{MAPPER['heap_size']} -jar {MAPPER['mapper']} "
                f"-m {file_name}_mappings.rml.ttl -o {out_rdf} -s {MAPPER['serialization']}"
            )
            # Try creating RDF
            try:
                subprocess.check_call(cmd, shell=True, cwd=file_dir)
                print(f"Completed chunk {index}\n")
                # rename again
                os.rename(cleanFile, current_file)
            except subprocess.CalledProcessError:
                print(f"FAILED {part}")
                continue
        # Step 3 — Merge output
        print("\n### MERGING OUTPUT ###")
        try: 
            merged_file = Path(file_dir, f"{file_name}_rdf.ttl")
            merge_ttls_from_folder(file_dir, ttl_templ, merged_file, PRXS)
            print('RDF created')
        except Exception:
            print('Error while merging')
    end = time.time()
    print('Execution time:', end - start) 
