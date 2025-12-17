<div align="justify">
  
# TermiGraph_esp

<p align="center">
  <img src="img/termigraph_logo.svg" alt="termigraph_logo" style="width:30%; height:auto;">
</p>

Repositorio en español para el código de TermiGraph.

Índice:

1. [Sobre TermiGraph](https://github.com/proyectoTeresIA/TermiGraph_esp/tree/main?tab=readme-ov-file#sobre-termigraph)
2. [Flujo de la conversión](https://github.com/proyectoTeresIA/TermiGraph_esp/tree/main?tab=readme-ov-file#flujo-de-la-conversi%C3%B3n)
3. [Interfaz](https://github.com/proyectoTeresIA/TermiGraph_esp/tree/main?tab=readme-ov-file#interfaz)

## Sobre TermiGraph

TermiGraph es un servicio de conversión que consta de cinco módulos, los cuales dependen del formato:

1. **Glosarios monolingües:** listas de términos, los cuales se han de separar con un salto de línea. Los ficheros deben ser texto plano (_.txt_).
2. **Terminologías TBX-Basic:** terminologías en formato TBX-Basic (_.tbx_) con el estilo DCT. Este conversor a sido desarrollado tomando como base los recursos de [UZEI](https://uzei.eus/es/).
3. **XML (TERMCAT):** terminologías en XML (_.xml_) que siguen la estructura definida por [TERMCAT](https://www.termcat.cat/es) en los recursos de la colección [_Terminologia Oberta_](https://www.termcat.cat/ca/terminologia-oberta).
4. **JSON (IATE):** recursos JSON (_.json_) que siguen la estructura definida por [IATE](https://iate.europa.eu/home).
5. **Excell (UNTerm):** terminologías en hoja de cálculos Excel (_.xlsx_) basado en la estructura de [UNTerm](https://unterm.un.org/unterm2/es/).

**Próximamente:** guía para el usuario con la documentación sobre cada estructura

## Flujo de la conversión

1. **Preprocesado:** cada recurso presenta carácteristicas únicas, tanto de estructura como de contenido, y a menudo la información contenida en el recurso se ha de atomizar o separar. Por ejemplo, la información relativa a la categoría gramatical, el género y el número se presenta en bloque, mientras que en RDF cada elemento se representa mediante una propiedad distinta. Asimismo, durante este proceso, se trata de normalizar la representación de los idiomas mediante el uso de Lexvo. En ocasiones, también se generan formas como 'profesor' y 'profesora' a partir de 'profesor -a'.
2. **Generación de mapeos:** para establecer las correspondencias entre los datos preprocesados y las ontologías, se requiere un fichero de mapeo que contiene las reglas a seguir. Este fichero se crea mediante Mapeathor, una herramienta de generación de reglas basada en spreedcheets (hojas de cálculo). Esta herramienta facilita la generación de los mapeos ya que reduce el nivel de conocimiento técnico necesario.
3. **Transformación a RDF:** teniendo en cuenta tanto el fichero de mapeos como los datos preprocesados, los datos son finalmente transformados a RDF mediante la herramienta RMLMapper


  
## Interfaz
Puede convertir sus recursos mediante la interfaz de TermiGraph, disponible en: https://termigraph.teresia.linkeddata.es/ 
Para convertir los recursos simplemente debe rellenar el formulario, el cual consta de dos páginas:
1. Carga del recurso: se ha de subir el fichero a convertir e indicar el tipo de conversor que se quiere aplicar, en base a la estructura del fichero que se está enviando.
2. Metadatos del recurso: se recogen metadatos acerca del recurso, en particular, el nombre del recurso, el idioma (sólo de los glosarios), los dominios (basado en [EuroVoc](https://eur-lex.europa.eu/browse/eurovoc.html?locale=es)), los autores, y el enlace al recurso original.

<p align="center">
    <img src="img/termigraph_paso1.svg" alt="termigraph_paso1" style="width:30%; height:auto;">
    <img src="img/termigraph_paso2.svg" alt="termigraph_paso2" style="width:30%; height:auto;" >
</p>


</div>
