<div align="center">
Flood Fusion SP

Fusão espaço-temporal de notícias e registros da Defesa Civil para mapear a intransitabilidade viária causada por chuvas severas.

Python GeoPandas OSMnx Pydantic Tests

</div>
Visão geral

O Flood Fusion SP é um pipeline de dados que une duas fontes com naturezas muito diferentes:

Texto não estruturado: notícias do jornalismo digital (G1);
Registros institucionais abertos: dados da Defesa Civil (CGE / SAISP).

A partir delas, o sistema converte menções em linguagem natural ("ontem à noite", "por volta das 18h", "na Rua Boipeva") e chamados técnicos em geometrias georreferenciadas, produzindo um mapa vetorial das vias que ficaram intransitáveis durante eventos pluviométricos severos.

Escopo de validação: distrito de Itaquera, município de São Paulo.

Funcionalidades
Componente	O que faz
Ingestão e extração	Coleta automatizada com deduplicação criptográfica e validação de contratos de dados via Pydantic V2.
Reconhecimento de entidades (NER)	Extrai logradouros e referências a eventos do texto jornalístico com spaCy (pt_core_news_sm).
Normalização temporal	Ancora termos relativos ao instante de publicação (t₀) e os resolve em intervalos fechados no padrão ISO 8601 (UTC).
Map-matching espacial	Extrai a malha viária do OpenStreetMap via OSMnx, normaliza logradouros em português e aplica fuzzy matching com métrica de confiança e fallback para centroide territorial.
Fusão espaço-temporal	Cruza as duas fontes em SIRGAS 2000 / UTM 23S (EPSG:31983) com buffer radial de 300 m e teste de sobreposição de intervalos de tempo.
Produto final	GeoJSON (RFC 7946) com status de validação cruzada e grau de confiança por ocorrência.
Arquitetura
G1 Digital News
Named Entity Recognition
Temporal Anchoring
OSMnx Map Matching
CGE / SAISP Records
Schema Normalization
Temporal Standardization
Geocoding / Spatial Index
Spatio-Temporal Fusion(buffer métrico +sobreposição temporal)
intransitabilidade_itaquera_final.geojson
Dicionário de dados

O produto final é gerado em data/processed/intransitabilidade_itaquera_final.geojson, como uma FeatureCollection compatível com a RFC 7946.

Campo	Tipo	Descrição	Valores possíveis / exemplo
logradouro	string	Nome identificado da via ou trecho crítico.	"Rua Boipeva", "Avenida Radial Leste"
inicio_evento	string	Timestamp UTC estimado do início da obstrução.	ISO 8601, ex.: "2024-01-17T18:00:00+00:00"
fim_evento	string	Timestamp UTC da normalização do tráfego.	ISO 8601, ex.: "2024-01-17T21:59:00+00:00"
status_fusao	string	Categoria de validação cruzada do evento.	CONFIRMADO_DUPLO, APENAS_CGE, APENAS_MIDIA
fontes	string	Fornecedor(es) de dados que sustentam a evidência.	"G1+CGE", "CGE", "G1"
confianca_geral	float	Grau de certeza estimado da ocorrência, em [0.0, 1.0].	1.0 (dupla confirmação), 0.85 (oficial)
geometry	Geometry	Primitiva vetorial georreferenciada em WGS 84 (EPSG:4326).	Point ou LineString
Estrutura do repositório
text
flood-fusion-sp/
├── data/
│   ├── raw/                  # Ingestão bruta de notícias (JSON Lines)
│   └── processed/            # Registros padronizados, malhas OSM e GeoJSONs consolidados
├── src/
│   ├── scraper/              # Modelos Pydantic V2 e scrapers HTTP resilientes
│   ├── ner/                  # Extração e anotação semântica de entidades nomeadas
│   ├── temporal/             # Ancoragem relativa e conversão para ISO 8601
│   └── spatial/              # Geocodificação OSMnx, correspondência difusa e fusão métrica
├── tests/                    # Suíte de validação e testes de regressão (pytest)
├── main.py                   # Orquestrador ponta a ponta da esteira
└── requirements.txt          # Dependências do ambiente
Instalação e execução
Pré-requisitos
Python 3.10 ou superior
Bibliotecas GDAL e GEOS instaladas no sistema
Configuração do ambiente

Windows (PowerShell)

powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download pt_core_news_sm

Linux / macOS

bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download pt_core_news_sm
Executando o pipeline completo

Para rodar todo o fluxo, da ingestão até o GeoJSON final:

bash
python main.py
Validação de qualidade

Para executar os testes unitários dos modelos e da ancoragem temporal:

bash
python -m pytest
Visualizando o resultado

O GeoJSON gerado pode ser aberto diretamente no QGIS, no geojson.io ou carregado em Python:

python
import geopandas as gpd

gdf = gpd.read_file("data/processed/intransitabilidade_itaquera_final.geojson")
gdf[gdf["status_fusao"] == "CONFIRMADO_DUPLO"].explore()
<div align="center">

Desenvolvido por yanpefnsc & Hyak00

</div>
