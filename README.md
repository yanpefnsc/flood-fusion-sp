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
