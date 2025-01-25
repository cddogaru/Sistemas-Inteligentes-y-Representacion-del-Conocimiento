import pickle as pkl
from argparse import Namespace
from dataclasses import dataclass
from time import time
from typing import Dict, List

from ..indexer.indexer import Index

@dataclass
class Result:
    """Clase que contendrá un resultado de búsqueda"""

    url: str
    snippet: str

    def __str__(self) -> str:
        return f"{self.url} -> {self.snippet}"

class Retriever:
    """Clase que representa un recuperador"""

    def __init__(self, args: Namespace):
        self.args = args
        self.index = self.load_index()

    def search_query(self, query: str) -> List[Result]:
        """Método para resolver una query.
        Este método debe ser capaz, al menos, de resolver consultas como:
        "grado AND NOT master OR docencia", con un procesado de izquierda
        a derecha. Por simplicidad, podéis asumir que los operadores AND,
        NOT y OR siempre estarán en mayúsculas.

        Args:
            query (str): consulta a resolver
        Returns:
            List[Result]: lista de resultados que cumplen la consulta
        """
        terms = query.split()
        temp_postings = None

        while terms:
            term = terms.pop(0)
            if term == "AND":
                next_term = terms.pop(0)
                temp_postings = self._and_(temp_postings, self.index.postings.get(next_term, []))
            elif term == "OR":
                next_term = terms.pop(0)
                temp_postings = self._or_(temp_postings, self.index.postings.get(next_term, []))
            elif term == "NOT":
                next_term = terms.pop(0)
                not_postings = self._not_(self.index.postings.get(next_term, []))
                temp_postings = not_postings if temp_postings is None else self._and_(temp_postings, not_postings)
            else:
                term_postings = self.index.postings.get(term, [])
                temp_postings = term_postings if temp_postings is None else self._or_(temp_postings, term_postings)

        if temp_postings is None:
            return []

        results = []
        for doc_id in temp_postings:
            document = self.index.documents[doc_id]
            results.append(Result(url=document.url, snippet=document.text[:200]))
        for result in results:
            print(result)  # Asegúrate de imprimir los resultados aquí
        return results

    def search_from_file(self, fname: str) -> Dict[str, List[Result]]:
        """Método para hacer consultas desde fichero.
        Debe ser un fichero de texto con una consulta por línea.

        Args:
            fname (str): ruta del fichero con consultas
        Return:
            Dict[str, List[Result]]: diccionario con resultados de cada consulta
        """
        results = {}
        with open(fname, "r") as fr:
            ts = time()
            queries = fr.readlines()
            for query in queries:
                query = query.strip()
                results[query] = self.search_query(query)
                print(f"Query: {query}")
                if results[query]:
                    for result in results[query]:
                        print(result)
                else:
                    print("No results found.")
            te = time()
            print(f"Time to solve {len(queries)} queries: {te-ts}s")
        return results

    def load_index(self) -> Index:
        """Método para cargar un índice invertido desde disco."""
        with open(self.args.index_file, "rb") as fr:
            index = pkl.load(fr)
            print(f"Loaded index with {len(index.documents)} documents and {len(index.postings)} terms.")
            return index

    def _and_(self, posting_a: List[int], posting_b: List[int]) -> List[int]:
        """Método para calcular la intersección de dos posting lists.
        Será necesario para resolver queries que incluyan "A AND B"
        en `search_query`.

        Args:
            posting_a (List[int]): una posting list
            posting_b (List[int]): otra posting list
        Returns:
            List[int]: posting list de la intersección
        """
        if not posting_a or not posting_b:
            return []

        result = []
        i, j = 0, 0
        while i < len(posting_a) and j < len(posting_b):
            if posting_a[i] == posting_b[j]:
                result.append(posting_a[i])
                i += 1
                j += 1
            elif posting_a[i] < posting_b[j]:
                i += 1
            else:
                j += 1
        return result

    def _or_(self, posting_a: List[int], posting_b: List[int]) -> List[int]:
        """Método para calcular la unión de dos posting lists.
        Será necesario para resolver queries que incluyan "A OR B"
        en `search_query`.

        Args:
            posting_a (List[int]): una posting list
            posting_b (List[int]): otra posting list
        Returns:
            List[int]: posting list de la unión
        """
        if not posting_a:
            return posting_b
        if not posting_b:
            return posting_a

        result = []
        i, j = 0, 0
        while i < len(posting_a) or j < len(posting_b):
            if i < len(posting_a) and (j >= len(posting_b) or posting_a[i] <= posting_b[j]):
                if not result or result[-1] != posting_a[i]:
                    result.append(posting_a[i])
                i += 1
            if j < len(posting_b) and (i >= len(posting_a) or posting_b[j] <= posting_a[i]):
                if not result or result[-1] != posting_b[j]:
                    result.append(posting_b[j])
                j += 1
        return result

    def _not_(self, posting_a: List[int]) -> List[int]:
        """Método para calcular el complementario de una posting list.
        Será necesario para resolver queries que incluyan "NOT A"
        en `search_query`

        Args:
            posting_a (List[int]): una posting list
        Returns:
            List[int]: complementario de la posting list
        """
        all_docs = set(range(len(self.index.documents)))
        excluded_docs = set(posting_a)
        return sorted(list(all_docs - excluded_docs))
