from datetime import datetime, timezone
from src.scraper.models import RawNewsArticle

def test_raw_news_article_serialization():
    article = RawNewsArticle(
        article_id="test12345",
        url="https://g1.globo.com/sp/sao-paulo/noticia/teste.ghtml",
        portal="g1",
        termo_busca="alagamento",
        data_coleta=datetime.now(timezone.utc),
        data_publicacao=datetime.now(timezone.utc),
        titulo="Notícia de Teste para Validação",
        subtitulo="Subtítulo de teste",
        corpo_texto="Este é um texto suficientemente longo para passar pelo validador com sucesso garantido."
    )
    data = article.model_dump(by_alias=True)
    assert data["id"] == "test12345"
    assert data["title"] == "Notícia de Teste para Validação"
    assert "body" in data