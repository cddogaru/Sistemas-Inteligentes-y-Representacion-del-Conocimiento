from argparse import Namespace
from queue import Queue
from typing import Set
import os
import requests
import json
import re


class Crawler:
    """Clase que representa un Crawler"""

    def __init__(self, args: Namespace):
        self.args = args
        self.visited = set()  # URLs visitadas

    def crawl(self) -> None:
        """
        Método para crawlear la URL base.
        """
        queue = Queue()
        queue.put(self.args.url)
        crawled_count = 0

        # Mientras haya URLs por procesar y no se supere el límite máximo
        while not queue.empty() and crawled_count < self.args.max_webs:
            current_url = queue.get()
            if current_url in self.visited:
                continue

            try:
                # Realiza la petición HTTP con User-Agent
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/91.0.4472.124 Safari/537.36"
                    )
                }
                response = requests.get(current_url, headers=headers)
                response.raise_for_status()  # Verifica si hubo errores en la respuesta
            except requests.RequestException as e:
                print(f"Error al obtener {current_url}: {e}")
                continue

            # Guarda el contenido de la página en un archivo
            content = response.text
            self.save_page(current_url, content)

            # Marca la URL como visitada
            self.visited.add(current_url)
            crawled_count += 1

            # Extrae las URLs y las agrega a la cola
            for url in self.find_urls(content):
                if url not in self.visited:
                    queue.put(url)

    def save_page(self, url: str, content: str) -> None:
        """
        Guarda el contenido de una página web en un archivo JSON.
        """
        if not os.path.exists(self.args.output_folder):
            os.makedirs(self.args.output_folder)

        # Nombre del archivo basado en el número de páginas visitadas
        filename = os.path.join(self.args.output_folder, f"{len(self.visited)}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({"url": url, "text": content}, f, ensure_ascii=False, indent=4)

    def find_urls(self, text: str) -> Set[str]:
        """
        Encuentra URLs en el texto de una web.
        """
        # Expresión regular para encontrar URLs con "href" que comiencen con "https://universidadeuropea.com"
        href_pattern = r'href=["\'](https://universidadeuropea\.com[^\s"\'<>]*)["\']'
        urls = re.findall(href_pattern, text)
        return set(urls)  # Devuelve un conjunto con URLs únicas
