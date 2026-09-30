import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Set
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from pydantic import HttpUrl

from src.scraper.models import RawNewsArticle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("G1Scraper")


class G1Scraper:
    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = self._criar_sessao_resiliente()

    def _criar_sessao_resiliente(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        return session

    def _obter_ids_existentes(self, filepath: Path) -> Set[str]:
        if not filepath.exists():
            return set()
        
        ids = set()
        with open(filepath, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        dado = json.loads(linha)
                        if "article_id" in dado:
                            ids.add(dado["article_id"])
                    except json.JSONDecodeError:
                        continue
        return ids

    def buscar_urls(self, termos: List[str]) -> List[str]:
        urls: Set[str] = set()
        feed_url = "https://g1.globo.com/rss/g1/sao-paulo/"
        logger.info(f"A recolher feed oficial do G1 SP: {feed_url}...")

        try:
            resp = self.session.get(feed_url, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Resposta inesperada do feed ({resp.status_code}).")
                return []

            soup = BeautifulSoup(resp.content, "xml")
            itens = soup.find_all("item")

            for item in itens:
                title_elem = item.find("title")
                desc_elem = item.find("description")
                
                titulo = title_elem.get_text() if title_elem else ""
                descricao = desc_elem.get_text() if desc_elem else ""
                texto_item = f"{titulo} {descricao}".lower()

                if any(termo.lower() in texto_item for termo in termos):
                    link_node = item.find("link")
                    if link_node:
                        link_text = link_node.get_text()
                        if link_text:
                            url_materia = link_text.split("?")[0].strip()
                            if "g1.globo.com/sp/" in url_materia:
                                urls.add(url_materia)

        except Exception as e:
            logger.error(f"Erro ao processar feed RSS: {e}")

        logger.info(f"Total de URLs candidatas encontradas no feed: {len(urls)}")
        return list(urls)

    def extrair_materia(self, url: str, termo: str) -> Optional[RawNewsArticle]:
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            title_node = soup.find("h1", class_="content-head__title") or soup.find("h1")
            if not title_node:
                return None
            titulo = title_node.get_text(strip=True)

            subtitle_node = soup.find("h2", class_="content-head__subtitle")
            subtitulo = subtitle_node.get_text(strip=True) if subtitle_node else None

            data_pub = None
            time_node = soup.find("time", itemprop="datePublished")
            if time_node:
                raw_dt = time_node.get("datetime")
                if raw_dt and not isinstance(raw_dt, list):
                    data_pub = date_parser.parse(str(raw_dt))

            paragraphs = soup.find_all("p", class_="content-text__container")
            if not paragraphs:
                article_node = soup.find("article")
                if article_node:
                    paragraphs = article_node.find_all("p")

            corpo_texto = " ".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

            article_id = RawNewsArticle.gerar_article_id(url)

            return RawNewsArticle(
                article_id=article_id,
                url=HttpUrl(url),
                portal="g1",
                termo_busca=termo,
                data_publicacao=data_pub,
                titulo=titulo,
                subtitulo=subtitulo,
                corpo_texto=corpo_texto
            )

        except Exception as e:
            logger.error(f"Erro ao processar notícia em {url}: {e}")
            return None

    def executar(self, termos: List[str], output_filename: str = "noticias_itaquera.jsonl"):
        output_path = self.output_dir / output_filename
        ids_existentes = self._obter_ids_existentes(output_path)
        logger.info(f"Base local carregada: {len(ids_existentes)} artigos já registados.")

        urls = self.buscar_urls(termos)
        novos_registos = 0

        with open(output_path, "a", encoding="utf-8") as f:
            for url in urls:
                article_id = RawNewsArticle.gerar_article_id(url)
                if article_id in ids_existentes:
                    logger.debug(f"Artigo {article_id} ignorado (já presente na base).")
                    continue

                article = self.extrair_materia(url, termo=",".join(termos))
                if article:
                    f.write(article.model_dump_json() + "\n")
                    ids_existentes.add(article.article_id)
                    novos_registos += 1
                    logger.info(f"[NOVO] Ingerido: {article.titulo[:50]}...")
                
                time.sleep(0.5)

        logger.info(f"Execução finalizada: {novos_registos} novos artigos ingeridos em {output_path}")


if __name__ == "__main__":
    scraper = G1Scraper()
    termos_filtro = [
        "chuva",
        "alagamento",
        "inundação",
        "itaquera",
        "zona leste",
        "radial leste",
        "transbordamento",
        "córrego",
        "temporal",
        "deslizamento"
    ]
    scraper.executar(termos=termos_filtro)