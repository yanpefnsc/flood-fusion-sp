# Flood Fusion SP

Pipeline de fusão multimodal espaço-temporal de notícias jornalísticas (G1) e dados governamentais oficiais (Centro de Gerenciamento de Emergências - CGE) para mapeamento da intransitabilidade de vias por alagamento no distrito de Itaquera, São Paulo.

---

## Visão Geral da Arquitetura

O sistema integra processamento de linguagem natural (NER e normalização temporal) com análise geoespacial vetorial sobre grafos viários:

1. **Ingestão & Extração:**
   - Recolha de notícias com deduplicação criptográfica e fallback de timestamps.
   - Reconhecimento de entidades nomeadas (`LOGRADOURO`, `TEMPO`, `PONTO_DE_REFERENCIA`).
   - Obtenção do histórico oficial de chamados de alagamento do CGE/SAISP.

2. **Módulo Temporal:**
   - Ancoragem temporal relativa baseada no timestamp de publicação ($t_0$).
   - Resolução de expressões idiomáticas e períodos do dia ("madrugada", "ontem às 18h", "nesta tarde") convertidos para intervalos ISO 8601 (`inicio_evento` e `fim_evento`).

3. **Módulo Espacial & Geocodificação:**
   - Normalização de prefixos viários e busca difusa por similaridade de texto.
   - Download e cache da malha viária vetorial de Itaquera via OSMnx / OpenStreetMap.
   - Mapeamento de logradouros para geometrias vetoriais com nível de confiança e fallback para centroide.

4. **Fusão Espaço-Temporal Multimodal:**
   - Projeção espacial métrica em SIRGAS 2000 / UTM zone 23S (EPSG:31983).
   - Cruzamento através de buffer espacial (300 m) com sobreposição de intervalos horários.
   - Classificação do grau de intransitabilidade da via:
     - `CONFIRMADO_DUPLO`: Validação cruzada com registo oficial no CGE e repercussão jornalística no G1.
     - `APENAS_CGE`: Ocorrência técnica oficial sem repercussão na imprensa.
     - `APENAS_MIDIA`: Ocorrência pontual reportada pela população/imprensa sem registo no CGE.

---

## Estrutura do Repositório

```text
flood-fusion-sp/
├── data/
│   ├── raw/                  # Notícias brutas do G1 (JSONL)
│   └── processed/            # Bases processadas, CGE, GeoJSONs e malha OSM
├── src/
│   ├── scraper/              # Modelos Pydantic V2 e scraper resiliente
│   ├── ner/                  # Extração e anotação de entidades nomeadas
│   ├── temporal/             # Ancoragem e normalização de intervalos ISO 8601
│   └── spatial/              # Geocodificação OSMnx, matcher difuso e fusão
├── tests/                    # Suíte de testes unitários com pytest
├── main.py                   # Script orquestrador de ponta a ponta
└── requirements.txt          # Dependências do projeto
