from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.temporal.normalize import processar_noticias_temporais
from src.spatial.geocode import geocodificar_noticias
from src.spatial.fusion import executar_fusao


def main() -> None:
    caminho_raw = Path("data/raw/noticias_itaquera.jsonl")
    caminho_anotadas = Path("data/processed/noticias_anotadas.jsonl")
    caminho_temporais = Path("data/processed/noticias_temporais.jsonl")
    caminho_geo = Path("data/processed/noticias_geolocalizadas.geojson")
    caminho_cge = Path("data/processed/cge_itaquera.csv")
    caminho_final = Path("data/processed/intransitabilidade_itaquera_final.geojson")

    print("[1/5] A executar scraper de notícias do G1...")
    if not caminho_raw.exists():
        subprocess.run([sys.executable, "-m", "src.scraper.g1_scraper"], check=True)

    print("[2/5] A processar anotação de entidades nomeadas (NER)...")
    if not caminho_anotadas.exists():
        subprocess.run(
            [
                sys.executable,
                "-m",
                "src.ner.annotate",
                "--input",
                str(caminho_raw),
            ],
            check=True,
        )

    print("[3/5] A normalizar expressões temporais...")
    processar_noticias_temporais(
        input_path=str(caminho_anotadas),
        output_path=str(caminho_temporais),
    )

    print("[4/5] A geocodificar logradouros na malha viária de Itaquera...")
    geocodificar_noticias(
        input_path=str(caminho_temporais),
        output_path=str(caminho_geo),
    )

    print("[5/5] A executar fusão multimodal espaço-temporal (G1 + CGE)...")
    executar_fusao(
        cge_csv_path=str(caminho_cge),
        noticias_geojson_path=str(caminho_geo),
        output_geojson_path=str(caminho_final),
    )

    print("Pipeline executado com sucesso de ponta a ponta.")


if __name__ == "__main__":
    main()