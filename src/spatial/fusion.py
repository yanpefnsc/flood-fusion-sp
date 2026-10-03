from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set
from zoneinfo import ZoneInfo

import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping

from src.spatial.geocode import ItaqueraGeocoder

SP_TZ = ZoneInfo("America/Sao_Paulo")


def _extrair_campo(row: pd.Series, *nomes: str, padrao: Any = "") -> Any:
    colunas_map = {str(k).lower().strip(): k for k in row.index}
    for n in nomes:
        chave = n.lower().strip()
        if chave in colunas_map:
            val = row[colunas_map[chave]]
            if pd.notna(val):
                return val
    return padrao


def _montar_timestamp(row: pd.Series, campo_completo: str, campo_data: str, campo_hora: str) -> datetime:
    val_completo = _extrair_campo(row, campo_completo)
    if val_completo:
        ts = pd.to_datetime(val_completo)
        if ts.tzinfo is None:
            return ts.tz_localize(SP_TZ).astimezone(timezone.utc)
        return ts.astimezone(timezone.utc)

    val_data = _extrair_campo(row, campo_data, "data", "date", "dia")
    if not val_data:
        raise ValueError(f"CGE sem coluna de data reconhecida, colunas: {list(row.index)}")
    val_hora = _extrair_campo(row, campo_hora, "hora", "horario", "time", padrao="00:00:00")

    ts = pd.to_datetime(f"{val_data} {val_hora}".strip())
    if ts.tzinfo is None:
        return ts.tz_localize(SP_TZ).astimezone(timezone.utc)
    return ts.astimezone(timezone.utc)


def carregar_e_padronizar_cge(csv_path: str, geocoder: ItaqueraGeocoder) -> gpd.GeoDataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    features: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        status = str(_extrair_campo(row, "status_intransitabilidade", "status", padrao="Intransitável"))
        if "intransit" not in status.lower():
            continue

        t_inicio = _montar_timestamp(row, "data_hora_inicio", "data_inicio", "horario_inicio")
        t_fim = _montar_timestamp(row, "data_hora_fim", "data_fim", "horario_termino")

        logradouro_cge = str(_extrair_campo(row, "via_registrada", "logradouro", "via", "rua", "endereco"))
        geom, conf, metodo = geocoder.geocodificar_entidade(logradouro_cge)

        feature = {
            "type": "Feature",
            "geometry": mapping(geom),
            "properties": {
                "id_origem": f"cge_{idx}",
                "fonte": "CGE",
                "inicio_evento": t_inicio.isoformat(),
                "fim_evento": t_fim.isoformat(),
                "logradouro": logradouro_cge,
                "sentido": _extrair_campo(row, "sentido", padrao=""),
                "status_via": status,
                "confianca_espacial": conf,
            },
        }
        features.append(feature)

    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")


def executar_fusao(
    cge_csv_path: str = "data/processed/cge_itaquera.csv",
    noticias_geojson_path: str = "data/processed/noticias_geolocalizadas.geojson",
    output_geojson_path: str = "data/processed/intransitabilidade_itaquera_final.geojson",
    distancia_buffer_metros: float = 300.0,
) -> None:
    geocoder = ItaqueraGeocoder()
    gdf_cge = carregar_e_padronizar_cge(cge_csv_path, geocoder)
    gdf_noticias = gpd.read_file(noticias_geojson_path)

    cge_m = gdf_cge.to_crs(epsg=31983)
    noticias_m = gdf_noticias.to_crs(epsg=31983)

    cge_casados: Set[Any] = set()
    noticias_casadas: Set[Any] = set()
    registros_finais: List[Dict[str, Any]] = []

    for n_idx, notic in noticias_m.iterrows():
        t_ini_n = datetime.fromisoformat(str(notic["inicio_evento"]).replace("Z", "+00:00"))
        t_fim_n = datetime.fromisoformat(str(notic["fim_evento"]).replace("Z", "+00:00"))
        buffer_geom = notic.geometry.buffer(distancia_buffer_metros)

        casamento_encontrado = False

        for c_idx, cge in cge_m.iterrows():
            t_ini_c = datetime.fromisoformat(str(cge["inicio_evento"]).replace("Z", "+00:00"))
            t_fim_c = datetime.fromisoformat(str(cge["fim_evento"]).replace("Z", "+00:00"))

            overlap_temporal = max(t_ini_n, t_ini_c) <= min(t_fim_n, t_fim_c)
            intersecao_espacial = buffer_geom.intersects(cge.geometry)

            if overlap_temporal and intersecao_espacial:
                cge_casados.add(c_idx)
                noticias_casadas.add(n_idx)
                casamento_encontrado = True

                registros_finais.append({
                    "geometry": notic.geometry,
                    "logradouro": notic.get("logradouro_extraido") or cge.get("logradouro"),
                    "inicio_evento": min(t_ini_n, t_ini_c).isoformat(),
                    "fim_evento": max(t_fim_n, t_fim_c).isoformat(),
                    "status_fusao": "CONFIRMADO_DUPLO",
                    "fontes": "G1+CGE",
                    "confianca_geral": 1.0,
                })
                break

        if not casamento_encontrado:
            registros_finais.append({
                "geometry": notic.geometry,
                "logradouro": notic.get("logradouro_extraido"),
                "inicio_evento": notic["inicio_evento"],
                "fim_evento": notic["fim_evento"],
                "status_fusao": "APENAS_MIDIA",
                "fontes": "G1",
                "confianca_geral": float(notic.get("confianca_espacial", 0.5)),
            })

    for c_idx, cge in cge_m.iterrows():
        if c_idx not in cge_casados:
            registros_finais.append({
                "geometry": cge.geometry,
                "logradouro": cge.get("logradouro"),
                "inicio_evento": cge["inicio_evento"],
                "fim_evento": cge["fim_evento"],
                "status_fusao": "APENAS_CGE",
                "fontes": "CGE",
                "confianca_geral": 0.85,
            })

    gdf_resultado = gpd.GeoDataFrame(registros_finais, crs=31983).to_crs(epsg=4326)
    dst = Path(output_geojson_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    gdf_resultado.to_file(dst, driver="GeoJSON")


if __name__ == "__main__":
    executar_fusao()