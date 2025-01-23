import os
import json
import pickle as pkl
import re
from argparse import Namespace
from dataclasses import dataclass, field
from time import time
from typing import Dict, List
from bs4 import BeautifulSoup
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords


@dataclass
class Document:
    """Dataclass para representar un documento."""
    id: int
    title: str
    url: str
    text: str


@dataclass
class Index:
    """Dataclass para representar un índice invertido."""
    postings: Dict[str, List[int]] = field(default_factory=lambda: {})
    documents: List[Document] = field(default_factory=lambda: [])

    def save(self, output_name: str) -> None:
        """Serializa el índice (`self`) en formato binario usando Pickle."""
        # Crear el directorio si no existe
        output_dir = os.path.dirname(output_name)
        os.makedirs(output_dir, exist_ok=True)

        # Guardar el índice en un archivo binario
        with open(output_name, "wb") as fw:
            pkl.dump(self, fw)


@dataclass
class Stats:
    """Dataclass para representar estadísticas del indexador."""
    n_words: int = field(default_factory=lambda: 0)
    n_docs: int = field(default_factory=lambda: 0)
    building_time: float = field(default_factory=lambda: 0.0)

    def __str__(self) -> str:
        return (
            f"Words: {self.n_words}\n"
            f"Docs: {self.n_docs}\n"
            f"Time: {self.building_time:.2f}s"
        )


class Indexer:
    """Clase que representa un indexador."""

    def __init__(self, args: Namespace):
        self.args = args
        self.index = Index()
        self.stats = Stats()

    def build_index(self) -> None:
        """Construye un índice invertido."""
        ts = time()

        # Procesar cada archivo JSON en la carpeta de entrada
        for filename in os.listdir(self.args.input_folder):
            filepath = os.path.join(self.args.input_folder, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            url = data["url"]
            raw_text = data["text"]

            # Parsear y limpiar el texto
            clean_text = self.parse(raw_text)
            clean_text = self.remove_split_symbols(clean_text)
            clean_text = self.remove_elongated_spaces(clean_text)
            clean_text = self.remove_punctuation(clean_text)

            # Tokenizar y eliminar stopwords
            tokens = self.tokenize(clean_text)
            tokens = self.remove_stopwords(tokens)

            # Crear el documento y añadirlo a la lista
            doc_id = len(self.index.documents)
            title = url  # O extrae el título real del contenido si es posible
            document = Document(id=doc_id, title=title, url=url, text=clean_text)
            self.index.documents.append(document)

            # Actualizar las posting lists del índice
            # Actualizar las posting lists del índice
            for token in tokens:
                if token not in self.index.postings:
                    self.index.postings[token] = []  # Inicializa la posting list si no existe
                if doc_id not in self.index.postings[token]:
                    self.index.postings[token].append(doc_id)


        te = time()

        # Guardar el índice en un archivo binario
        self.index.save(self.args.output_name)

        # Mostrar estadísticas
        self.show_stats(building_time=te - ts)

    def parse(self, text: str) -> str:
        """Extrae el texto del bloque principal de un documento HTML."""
        soup = BeautifulSoup(text, "html.parser")

        # Extraer contenido principal (ejemplo: <div class="page">)
        main_content = soup.find("div", class_="page")
        if main_content:
            text = " ".join(tag.get_text() for tag in main_content.find_all(["h1", "h2", "p", "a"]))
        else:
            # Si no hay un bloque principal definido, usamos todo el texto del HTML
            text = soup.get_text()

        # Convertimos a minúsculas
        return text.lower()

    def tokenize(self, text: str) -> List[str]:
        """Convierte el texto en una lista de palabras."""
        try:
            return word_tokenize(text)
        except LookupError:
            # Si NLTK no tiene los recursos necesarios, usamos un método básico
            return text.split()

    def remove_stopwords(self, words: List[str]) -> List[str]:
        """Elimina palabras vacías (stopwords) de la lista de palabras."""
        stop_words = set(stopwords.words("spanish"))  # Cambia a "english" si es necesario
        return [word for word in words if word not in stop_words]

    def remove_punctuation(self, text: str) -> str:
        """Elimina signos de puntuación del texto."""
        return re.sub(r"[^\w\s]", "", text)

    def remove_elongated_spaces(self, text: str) -> str:
        """Elimina espacios duplicados."""
        return " ".join(text.split())

    def remove_split_symbols(self, text: str) -> str:
        """Elimina símbolos separadores como saltos de línea y tabuladores."""
        return text.replace("\n", " ").replace("\t", " ").replace("\r", " ")

    def show_stats(self, building_time: float) -> None:
        """Muestra estadísticas del proceso de indexación."""
        self.stats.building_time = building_time
        self.stats.n_words = len(self.index.postings)
        self.stats.n_docs = len(self.index.documents)
        print(self.stats)
