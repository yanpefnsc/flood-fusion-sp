# Flood Fusion SP

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![GeoPandas](https://img.shields.io/badge/GeoPandas-Vector%20GIS-brightgreen.svg)](https://geopandas.org/)
[![OSMnx](https://img.shields.io/badge/OSMnx-Road%20Networks-orange.svg)](https://osmnx.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Pipeline de fusão espaço-temporal de dados textuais não estruturados (jornalismo digital) e registos institucionais abertos (defesa civil) para caracterização e mapeamento vetorial da intransitabilidade viária decorrente de eventos pluviométricos severos. 

O escopo territorial de validação do projeto compreende o distrito de **Itaquera**, no município de São Paulo.

---

## 1. Arquitetura Metodológica

O sistema opera uma esteira sequencial que converte menções em linguagem natural e chamados técnicos em geometrias georreferenciadas:

[ G1 Digital News ]        [ CGE / SAISP Records ]
│                           │
▼                           ▼
[ Named Entity Recog. ]     [ Schema Normalization ]
│                           │
▼                           ▼
[ Temporal Anchoring  ]     [ Temporal Standardization ]
│                           │
▼                           ▼
[ OSMnx Map Matching  ]     [ Geocoding / Spatial Index ]
│                           │
└─────────────┬─────────────┘
▼
[ Spatio-Temporal Fusion ]
(Metric Buffer + Time Overlap)
│
▼
[ intransitabilidade_itaquera_final.geojson ]


### Componentes do Pipeline

1. **Ingestão & Extração**: Recolha automatizada com deduplicação criptográfica e validação de contratos de dados via Pydantic V2.
2. **Normalização Temporal**: Ancoragem em tempo de publicação ($t_0$) que resolve termos relativos de linguagem natural ("ontem", "nesta madrugada", "por volta das 18h") em intervalos cronológicos fechados compatíveis com ISO 8601 UTC.
3. **Mapeamento Espacial (Map-Matching)**: Extração topológica da malha viária vetorial do OpenStreetMap via OSMnx, normalização de logradouros em português e correspondência difusa (*fuzzy string matching*) com métricas de confiança e recurso a centroide territorial.
4. **Fusão Espaço-Temporal**: Cruzamento das duas fontes em espaço projetado SIRGAS 2000 / UTM zone 23S (EPSG:31983) aplicando *buffer* métrico radial (300 m) e teste de sobreposição de intervalos temporais.

---

## 2. Dicionário de Dados do Produto Consolidado

O produto final da esteira é gerado em `data/processed/intransitabilidade_itaquera_final.geojson`, estruturado como uma `FeatureCollection` compatível com a norma RFC 7946 (GeoJSON).

| Campo | Tipo | Descrição | Valores Possíveis / Exemplo |
| :--- | :--- | :--- | :--- |
| `logradouro` | `string` | Nome identificado da via ou troço crítico. | `"Rua Boipeva"`, `"Avenida Radial Leste"` |
| `inicio_evento` | `string` | Timestamp UTC estimado de início da obstrução. | Norma ISO 8601 (`"2024-01-17T18:00:00+00:00"`) |
| `fim_evento` | `string` | Timestamp UTC de normalização do tráfego. | Norma ISO 8601 (`"2024-01-17T21:59:00+00:00"`) |
| `status_fusao` | `string` | Categoria de validação cruzada do evento. | `CONFIRMADO_DUPLO`, `APENAS_CGE`, `APENAS_MIDIA` |
| `fontes` | `string` | Fornecedor(es) de dados que sustentam a evidência. | `"G1+CGE"`, `"CGE"`, `"G1"` |
| `confianca_geral` | `float` | Grau de certeza estimado da ocorrência viária ($[0.0, 1.0]$). | `1.0` (dupla confirmação), `0.85` (oficial) |
| `geometry` | `Geometry` | Primitiva vetorial georreferenciada em WGS 84. | `Point` ou `LineString` em EPSG:4326 |

---

## 3. Estrutura do Repositório

```text
flood-fusion-sp/
├── data/
│   ├── raw/                  # Ingestão bruta de notícias (JSON Lines)
│   └── processed/            # Registos padronizados, malhas OSM e GeoJSONs consolidados
├── src/
│   ├── scraper/              # Modelos Pydantic V2 e scrapers HTTP resilientes
│   ├── ner/                  # Extração e anotação semântica de entidades nomeadas
│   ├── temporal/             # Ancoragem relativa e conversão para ISO 8601
│   └── spatial/              # Geocodificação OSMnx, correspondência difusa e fusão métrica
├── tests/                    # Suíte de validação e testes de regressão (pytest)
├── main.py                   # Orquestrador ponta a ponta da esteira
└── requirements.txt          # Dependências do ambiente
