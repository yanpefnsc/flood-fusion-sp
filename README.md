# Flood Fusion SP

Rotinas de preparação de dados de alagamentos e extração temporal/espacial de notícias.

## Gabarito CGE de Itaquera

`src/cge/download.py` obtém os boletins públicos do arquivo histórico do SAISP e extrai os registros publicados na seção “Pontos de Alagamento - CGE/PMSP”. O recorte fornecido cobre 17 e 18 de janeiro de 2024. Os horários são locais de São Paulo e incluem o fuso `-03:00`; o CSV mantém o início e o fim do ponto de alagamento, a via, o sentido, o status, a referência e a URL de origem.

```powershell
python -m src.cge.download
```

Para outro intervalo, informe as duas datas:

```powershell
python -m src.cge.download --start 2024-01-01 --end 2024-01-31
```

Fonte: [arquivo histórico de chuva do SAISP, boletim de 17/01/2024](https://www.saisp.br/historic/202401/dia17/). O SAISP informa que seus boletins são operados pela Fundação Centro Tecnológico de Hidráulica e que os pontos de alagamento são fornecidos pelo CGE/PMSP.

## Normalização temporal e NER

`src/temporal/normalize.py` ancora datas relativas à data de publicação e converte horários para ISO 8601. Períodos do dia sem hora exata são representados por uma hora de referência (madrugada 05:00, manhã 09:00, tarde 15:00, noite 21:00) e marcados como estimados. Datas sem horário usam 00:00 e precisão `date`.

Por exemplo, com publicação em 17/01/2024, `ontem às 18h` vira `2024-01-16T18:00:00-03:00` e `na última terça-feira à tarde` vira `2024-01-16T15:00:00-03:00` (estimado).

`src/ner/entities.py` combina o modelo pré-treinado português spaCy `pt_core_news_sm` com padrões de endereços e marcos geográficos para rotular `LOGRADOURO` e `PONTO_DE_REFERENCIA`. Sem o modelo, a extração por regras continua disponível.

```powershell
python -m spacy download pt_core_news_sm
python -m src.ner.annotate --spacy-model pt_core_news_sm
```

O repositório não continha um corpus de notícias de entrada. `data/raw/noticias_cge.jsonl` fornece um trecho de notícia oficial do CGE, publicado em 17/01/2024, como exemplo de entrada reproduzível; passe `--input` para processar outro JSONL com `id`, `title`, `published_at`, `body` e `source_url`.

Fonte do trecho: [notícia CGE nº 47619](https://cge.prefeitura.sp.gov.br/v3/noticias.jsp?id=47619).
