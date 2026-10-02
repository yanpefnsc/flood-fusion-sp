from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import geopandas as gpd
import osmnx as ox
from shapely import union_all
from shapely.geometry import Point, mapping

from src.spatial.matcher import melhor_correspondencia, normalizar_logradouro


class ItaqueraGeocoder:
    def __init__(self, cache_path: str = "data/processed/itaquera_network.geojson"):
        self.cache_path = Path(cache_path)
        self.edges_gdf = self._carregar_ou_baixar_malha()
        self.centroide = self._obter_uniao(self.edges_gdf.geometry).centroid

    def _obter_uniao(self, geometries: Any) -> Any:
        try:
            return union_all(geometries)
        except Exception:
            return geometries.unary_union

    def _carregar_ou_baixar_malha(self) -> gpd.GeoDataFrame:
        if self.cache_path.exists():
            return gpd.read_file(self.cache_path)

        graph = ox.graph_from_place("Itaquera, São Paulo, Brazil", network_type="drive")
        _, edges = ox.graph_to_gdfs(graph)
        edges = edges.reset_index()

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        subset = edges[["geometry", "name", "highway", "length"]].dropna(subset=["geometry"]).copy()
        subset["name_clean"] = subset["name"].apply(normalizar_logradouro)
        subset.to_file(self.cache_path, driver="GeoJSON")
        return subset

    def geocodificar_entidade(self, texto_entidade: str) -> Tuple[Any, float, str]:
        if not texto_entidade:
            return self.centroide, 0.1, "CENTROIDE_FALLBACK"

        nomes_unicos = [n for n in self.edges_gdf["name_clean"].unique() if n and n != "NONE"]
        cand, score = melhor_correspondencia(texto_entidade, nomes_unicos, limiar=0.70)

        if cand and score >= 0.70:
            sub = self.edges_gdf[self.edges_gdf["name_clean"] == cand]
            geom = self._obter_uniao(sub.geometry)
            metodo = "EXATO" if score >= 0.95 else "SIMILARIDADE"
            return geom, float(score), metodo

        return self.centroide, 0.2, "CENTROIDE_FALLBACK"


def extrair_nomes_logradouros(entidades: List[Any]) -> List[str]:
    resultados = []
    for ent in entidades:
        if isinstance(ent, dict):
            tipo = ent.get("type") or ent.get("label") or ""
            if tipo in ("LOGRADOURO", "PONTO_DE_REFERENCIA"):
                texto = ent.get("text") or ent.get("entity") or ""
                if texto:
                    resultados.append(str(texto))
        elif isinstance(ent, (list, tuple)) and len(ent) >= 2:
            rotulo = str(ent[1])
            if any(k in rotulo for k in ("LOGRADOURO", "PONTO_DE_REFERENCIA")):
                resultados.append(str(ent[0]))
        elif isinstance(ent, str) and ent.strip():
            resultados.append(ent.strip())
    return resultados


def geocodificar_noticias(
    input_path: str = "data/processed/noticias_temporais.jsonl",
    output_path: str = "data/processed/noticias_geolocalizadas.geojson",
) -> None:
    geocoder = ItaqueraGeocoder()
    features: List[Dict[str, Any]] = []

    src = Path(input_path)
    dst = Path(output_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    with src.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)

            entidades = item.get("entities", [])
            logradouros = extrair_nomes_logradouros(entidades)

            melhor_geom = geocoder.centroide
            maior_conf = 0.1
            logradouro_resolvido = None
            metodo_resolucao = "CENTROIDE_FALLBACK"

            for log in logradouros:
                geom, conf, metodo = geocoder.geocodificar_entidade(log)
                if conf > maior_conf:
                    melhor_geom = geom
                    maior_conf = conf
                    logradouro_resolvido = log
                    metodo_resolucao = metodo
                    if conf >= 0.95:
                        break

            feature = {
                "type": "Feature",
                "geometry": mapping(melhor_geom),
                "properties": {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "inicio_evento": item.get("inicio_evento"),
                    "fim_evento": item.get("fim_evento"),
                    "logradouro_extraido": logradouro_resolvido,
                    "metodo_geocodificacao": metodo_resolucao,
                    "confianca_espacial": maior_conf,
                    "source_url": item.get("source_url") or item.get("url"),
                },
            }
            features.append(feature)

    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    gdf.to_file(dst, driver="GeoJSON")


if __name__ == "__main__":
    geocodificar_noticias()