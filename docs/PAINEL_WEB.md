# Painel web e integração de dados

Contribuição de **[SrPoggers](https://github.com/YoshiroD)** ao Flood Fusion SP.

## 1. Objetivo da entrega

O projeto já possuía o pipeline de coleta, anotação, normalização temporal,
geocodificação e fusão. Esta entrega acrescenta uma interface web para consultar
os arquivos produzidos por essas etapas, explorar ocorrências e conferir suas fontes.

O painel funciona com os dados disponíveis, mesmo antes da conclusão do pipeline.
Não é necessário abrir os CSVs e JSONLs manualmente para consultar os registros.

## 2. Front-end

Implementado em HTML, CSS e JavaScript, com Leaflet 1.9.4 para o mapa.
Não exige Node.js, compilação ou instalação de pacotes npm para executar.

### Visão geral

- Indicadores calculados a partir do recorte selecionado: quantidade de registros,
  registros intransitáveis, vias distintas e duração média das obstruções com término.
- Mapa de Itaquera com camadas de fusão, notícias geolocalizadas e malha viária,
  quando os respectivos GeoJSONs estiverem disponíveis.
- Linha do tempo com horários de Brasília e data indicada em cada registro.
- Resumo das fontes e acesso à tabela de ocorrências.

### Ocorrências

- Busca por via, referência ou fonte, desconsiderando acentos e maiúsculas.
- Filtros por data, condição da via e base de dados.
- Consulta separada dos registros CGE e do resultado da fusão.
- Janela de detalhes com início, término, duração, sentido, referência, origem,
  status da fusão, confiança atribuída e dados originais.
- Exportação CSV dos registros filtrados, com codificação UTF-8, separador `;`
  e tratamento de valores que poderiam ser interpretados como fórmulas.

### Fontes e notícias

- Consulta ao texto disponível, sua data de publicação e ao endereço original.
- Exibição das entidades extraídas e das expressões temporais anotadas.
- Reunião das etapas de um mesmo artigo por identificador, mantendo suas anotações.
- Inventário e download dos arquivos CSV, JSONL e GeoJSON presentes em `data/`.
- Identificação de coleta bruta como não validada: a presença no corpus não
  significa que o texto seja evidência de alagamento.

### Pipeline e metodologia

- Disponibilidade dos arquivos de cada etapa, com estado disponível, parcial ou pendente.
- Comandos de referência para executar as etapas pelo terminal.
- Explicação do buffer de 300 metros, das regras de confiança e das limitações do estudo.

A interface possui layouts para desktop e celular, navegação por teclado,
detalhes em diálogo e mensagens para ausência de dados ou falha de leitura.

## 3. Integração com os dados existentes

O servidor `web_server.py` usa a biblioteca padrão do Python e disponibiliza:

| Rota | Função |
|---|---|
| `/` | Interface do painel |
| `/api/dashboard` | Leitura e adaptação dos dados locais para a interface |
| `/api/files/<caminho>` | Download de um arquivo permitido dentro de `data/` |

O CSV `data/processed/cge_itaquera.csv` alimenta a base de registros oficiais.
Os JSONLs de `data/raw/` e `data/processed/` alimentam o corpus e suas anotações.
Os GeoJSONs são incorporados conforme sua disponibilidade:

| Arquivo | Uso |
|---|---|
| `intransitabilidade_itaquera_final.geojson` | Ocorrências fusionadas e suas geometrias |
| `noticias_geolocalizadas.geojson` | Camada espacial das notícias |
| `itaquera_network.geojson` | Camada opcional da malha viária |

O botão **Atualizar dados** relê os arquivos sem reiniciar o servidor.
O painel não executa o scraper, não reprocessa a fusão e não modifica os arquivos de origem.
O servidor escuta somente em `127.0.0.1`; esta entrega é voltada à execução local.

## 4. Estado dos dados nesta entrega

Na cópia utilizada para desenvolvimento, havia:

- 6 registros CGE: 5 intransitáveis em 17/01/2024 e 1 transitável em 18/01/2024.
- 4 nomes distintos de vias no CSV.
- 2 textos únicos: um boletim CGE anotado e uma notícia bruta fora do tema.
- Nenhum GeoJSON final, de notícias ou de malha viária disponível localmente.

Esses números descrevem a base verificada e não ficam fixados nos indicadores:
o painel os recalcula a partir dos arquivos e filtros.

Sem GeoJSON, o mapa mostra a região como referência e informa a ausência de geometrias.
Não são criadas coordenadas, correspondências ou notas de confiança artificiais.
Os resultados históricos documentados no README não são usados como dados substitutos.

O front preserva as etiquetas de fonte do resultado da fusão. O pipeline atual pode
rotular o texto como G1 mesmo quando o corpus anotado contém um boletim CGE;
essa limitação é explicada nos detalhes e na metodologia. O algoritmo original
de fusão não foi alterado nesta entrega.

## 5. Como executar e revisar

Na raiz do repositório:

```powershell
python web_server.py
```

Abra `http://127.0.0.1:8765`. Para mudar a porta:

```powershell
python web_server.py --port 8766
```

O painel não precisa das dependências geoespaciais para consultar os arquivos.
O mapa base do OpenStreetMap precisa de internet. Leaflet está incluído no
repositório com sua licença; as fontes Google Fonts têm alternativas locais.

Sugestão de revisão manual:

1. Busque por `Itagimirim` e confira o intervalo 16:23–17:15 e a duração de 52 minutos.
2. Selecione 18/01/2024 e confira o registro transitável.
3. Combine essa data com a condição intransitável e confira o estado sem resultados.
4. Abra os detalhes de uma via e o link de seu boletim de origem.
5. Exporte o recorte em CSV.
6. Consulte as entidades e os arquivos do boletim na tela de fontes.
7. Selecione o resultado da fusão e confira o estado pendente quando não há GeoJSON.
8. Após gerar os produtos do pipeline, use Atualizar dados e examine as novas camadas.

## 6. Validação realizada

Foram adicionados cinco testes do adaptador de dados em `tests/test_dashboard.py`:

- Preservação dos registros transitáveis, sem inventar geometrias ou confiança.
- Reunião das etapas de um artigo sem perder anotações.
- Continuidade da leitura diante de uma linha JSONL inválida.
- Reconhecimento de um novo GeoJSON na leitura seguinte.
- Identificação de GeoJSON inválido como indisponível.

```powershell
python -m unittest discover -s tests -p test_dashboard.py -v
python -m pytest -q
```

Na validação da entrega, os **8 testes** passaram: 5 novos e 3 já existentes.
Também foram verificados a sintaxe JavaScript, as rotas HTTP, a rejeição de acesso
a arquivos fora das pastas permitidas e os fluxos principais no navegador,
incluindo o layout de celular. O desenho das camadas geográficas com dados reais
continua dependente dos GeoJSONs ausentes nesta cópia.

## 7. Organização dos arquivos

| Arquivo | Responsabilidade |
|---|---|
| `frontend/index.html` | Estrutura das telas, navegação e créditos |
| `frontend/styles.css` | Identidade visual e adaptação de layout |
| `frontend/app.js` | Filtros, indicadores, tabelas, mapa, detalhes e exportação |
| `frontend/vendor/` | Leaflet e licença de distribuição |
| `web_server.py` | Servidor local e adaptação dos dados |
| `tests/test_dashboard.py` | Testes da integração |
| `README.md` | Instruções de execução e créditos dos três colaboradores |

