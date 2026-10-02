from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.scraper.models import RawNewsArticle
from src.temporal.normalize import normalizar_expressao_tempo

SP_TZ = ZoneInfo("America/Sao_Paulo")


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


def test_ancoragem_ontem_com_hora():
    t0 = datetime(2024, 1, 18, 10, 0, tzinfo=SP_TZ)
    inicio, fim = normalizar_expressao_tempo("ontem às 18h", t0)

    assert inicio.date() == datetime(2024, 1, 17).date()
    assert inicio.hour == 18
    assert fim.hour == 19


def test_ancoragem_periodo_tarde():
    t0 = datetime(2024, 1, 18, 20, 0, tzinfo=SP_TZ)
    inicio, fim = normalizar_expressao_tempo("nesta tarde", t0)

    assert inicio.date() == datetime(2024, 1, 18).date()
    assert inicio.hour == 12
    assert fim.hour == 17
    assert fim.minute == 59