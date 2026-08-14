from pipeline.model.parsing import html as _html
from pipeline.model.parsing import pdf as _pdf
from pipeline.model.parsing import vision as _vision
from pipeline.stages import parse


def test_env_model_prefers_specific_then_general_then_default():
    assert _vision._env_model("vis", "general", default="d") == "vis"
    assert _vision._env_model(None, "general", default="d") == "general"
    assert _vision._env_model(None, None, default="d") == "d"


def test_empty_string_value_is_ignored():
    assert _vision._env_model("", "general", default="d") == "general"


from pipeline.stages import parse as _p

SEI_HTML = """<html><head><title>SEI/GOV-PI - 0019275450 - SEAD_OFICIO_CIRCULAR</title>
<style>.x{}</style></head><body>
<p class="INTERPI_Cabecalho_Grande_15"><img src="data:image/jpeg;base64,AAAA"/></p>
<p class="CABECALHO">GOVERNO DO ESTADO DO PIAUÍ</p>
<p class="CABECALHO">SECRETARIA DE ADMINISTRAÇÃO DO ESTADO DO PIAUÍ - SEAD-PI</p>
<p class="Texto_Justificado">Aos(Às) Senhores(as) Presidentes das Comissões Permanentes de Licitação.</p>
<p class="Texto_Justificado_Recuo_Primeira_Linha">A Superintendência solicita o nome completo do responsável titular. Contamos com a colaboração de Vossa Senhoria para o cumprimento desta demanda.</p>
<p class="Texto_Centralizado">Atenciosamente,</p>
<p class="Texto_Centralizado">(assinado eletronicamente) Juliana de Carvalho Neves Superintendente</p>
<table><tbody><tr><td>Av. Pedro Freitas, 1900 Centro Administrativo, CEP 64018-900</td></tr></tbody></table>
<div>Criado por ilka.portugal@sead.pi.gov.br, versão 2 em 21/07/2025 12:04:19.</div>
</body></html>"""


def test_parse_html_keeps_body(tmp_path):
    f = tmp_path / "d.html"
    f.write_text(SEI_HTML, encoding="utf-8")
    text, method = _html.parse_html(f)
    assert method == "html-clean"
    assert "Aos(Às) Senhores(as) Presidentes" in text
    assert "Contamos com a colaboração de Vossa Senhoria" in text


def test_parse_html_drops_header(tmp_path):
    f = tmp_path / "d.html"
    f.write_text(SEI_HTML, encoding="utf-8")
    text, _ = _html.parse_html(f)
    assert "GOVERNO DO ESTADO DO PIAUÍ" not in text
    assert "SEI/GOV-PI" not in text
    assert "SECRETARIA DE ADMINISTRAÇÃO" not in text


def test_parse_html_drops_signature_and_footer(tmp_path):
    f = tmp_path / "d.html"
    f.write_text(SEI_HTML, encoding="utf-8")
    text, _ = _html.parse_html(f)
    assert "Atenciosamente" not in text
    assert "assinado eletronicamente" not in text
    assert "Juliana de Carvalho Neves" not in text
    assert "Av. Pedro Freitas" not in text
    assert "Criado por" not in text


def test_strip_signature_and_footer_prefers_signature():
    body = "Corpo do documento. Atenciosamente, Fulano. Av. Rua X. Criado por y em 1/1/2025."
    assert _html._strip_signature_and_footer(body) == "Corpo do documento."


def test_strip_signature_and_footer_fallback_to_footer():
    body = "Corpo do documento sem assinatura. Criado por y em 1/1/2025."
    assert _html._strip_signature_and_footer(body) == "Corpo do documento sem assinatura."


def test_assemble_vision_text_has_no_page_markers():
    parts = ["Conteúdo da página um.", "   ", "Conteúdo da página dois."]
    out = _vision._assemble_vision_text(parts)
    assert out == "Conteúdo da página um.\n\nConteúdo da página dois."
    assert "Página(s)" not in out
    assert "---" not in out


def test_should_use_native_true_for_text_layer():
    assert _pdf._should_use_native("x" * 600, 3) is True


def test_should_use_native_false_for_scanned():
    assert _pdf._should_use_native("", 3) is False
    assert _pdf._should_use_native("x" * 50, 3) is False


def test_should_use_native_false_when_no_pages():
    assert _pdf._should_use_native("anything", 0) is False


def test_strip_body_end_cuts_at_documento_assinado():
    body = "Corpo do documento aqui. Documento assinado eletronicamente por FULANO - Matr.123, em 1/1/2025."
    assert _html._strip_signature_and_footer(body) == "Corpo do documento aqui."


def test_strip_body_end_cuts_at_autenticidade():
    body = "Corpo real do texto. A autenticidade deste documento pode ser conferida no site https://sei.pi.gov.br/x"
    assert _html._strip_signature_and_footer(body) == "Corpo real do texto."


def test_strip_leading_header_removes_top_reference():
    t = ("OFÍCIO CIRCULAR N.° 45/2025/SEAD Teresina/PI, 21 de julho de 2025. "
         "Referência: Caso responda este Ofício, indicar expressamente o Processo nº 00002.007205/2025-62. "
         "Aos(Às) Senhores(as) Presidentes.")
    assert _html._strip_leading_header(t) == "Aos(Às) Senhores(as) Presidentes."


def test_strip_leading_header_noop_without_reference():
    t = "Senhor Diretor, encaminho o presente para análise."
    assert _html._strip_leading_header(t) == t


def test_parse_html_removes_address(tmp_path):
    html = ('<html><body><p class="Texto_Justificado">Conteúdo do corpo do documento.</p>'
            '<p>Av. Pedro Freitas, 1900 Centro Administrativo, BL1 - Bairro São Pedro, '
            'Teresina/PI, CEP 64018-900 Telefone: - http://www.sead.pi.gov.br/</p></body></html>')
    f = tmp_path / "a.html"
    f.write_text(html, encoding="utf-8")
    text, _ = _html.parse_html(f)
    assert "Av. Pedro Freitas" not in text
    assert "Conteúdo do corpo do documento" in text


def test_strip_doc_header_fields_despacho():
    t = ("Despacho Nº: 85/2025/SEAD-PI/GAB/SGP/ASTECSGP3 Teresina/PI, 18 de setembro de 2025. "
         "PROCESSO Nº: 00002.009655/2025-90 DESPACHO Nº 85/2025/SEAD-PI/GAB/SGP/ASTECSGP3-SEAD-PI "
         "PARA: Gabinete - SEAD-PI Excelentíssimo Senhor Secretário, Encaminho os autos para solicitar vagas.")
    assert _html._strip_doc_header_fields(t) == "Excelentíssimo Senhor Secretário, Encaminho os autos para solicitar vagas."


def test_strip_doc_header_fields_memorando():
    t = ("Memorando Nº: 16/2025/SEAD-PI/SGP/DDP/GGP Teresina/PI, 21 de maio de 2025. "
         "PROCESSO Nº 00002.004683/2025-11 DE : SEAD-PI/SGP/DDP/GGP "
         "PARA : Diretoria de Desenvolvimento de Pessoas - SEAD-PI Considerando a necessidade de informações.")
    assert _html._strip_doc_header_fields(t) == "Considerando a necessidade de informações."


def test_strip_doc_header_fields_noop_on_plain_body():
    t = "Aos(Às) Senhores(as) Presidentes das Comissões. Solicitamos os dados."
    assert _html._strip_doc_header_fields(t) == t


def test_strip_doc_header_fields_para_without_anchor_kept():
    t = "PARA : Coordenação Administrativa - CADM Nome Completo Contrato Data"
    assert _html._strip_doc_header_fields(t) == t


def test_strip_doc_header_fields_is_always_a_suffix():
    for t in [
        "Despacho Nº: 1/2025/X Teresina/PI, 1 de maio de 2025. PARA: Gab - X Senhor Diretor, Segue.",
        "PROCESSO Nº 00002.000001/2025-10 Trata-se de algo.",
        "Texto de corpo qualquer sem cabeçalho.",
    ]:
        out = _html._strip_doc_header_fields(t)
        assert out in t


def test_address_regex_consumes_through_url():
    addr = ("Av. Pedro Freitas, 1900 Centro Administrativo, BL1 - Bairro São Pedro, "
            "Teresina/PI, CEP 64018-900 Telefone: - http://www.sead.pi.gov.br/")
    assert _html._ADDRESS_RE.sub("X", "Corpo. " + addr + " fim").replace("X", "").strip() == "Corpo.  fim".replace("  ", " ").strip() or "sead.pi.gov.br" not in _html._ADDRESS_RE.sub("", addr)


def test_strip_garbled_runs_removes_glyph_scatter():
    t = "Texto normal aqui. c q 1 s t a u i 6 i r e s 0 p g n o a t. Mais texto bom completo."
    out = _pdf._strip_garbled_runs(t)
    assert "Texto normal aqui." in out
    assert "Mais texto bom completo." in out
    assert "c q 1 s t a u i" not in out


def test_strip_garbled_runs_keeps_legit_short_words():
    t = "de da do no na em a o e Ana foi ao mar e viu o sol de novo"
    assert _pdf._strip_garbled_runs(t) == t


def test_strip_garbled_runs_noop_on_clean_text():
    t = "Este é um documento perfeitamente normal com palavras completas e coerentes."
    assert _pdf._strip_garbled_runs(t) == t


def test_should_use_native_rejects_garbled_text():
    garbled = " ".join(list("abcdefghij") * 60)
    assert _pdf._should_use_native(garbled, 3) is False


def test_strip_doc_header_fields_noclass_letterhead():
    t = ("GOVERNO DO ESTADO DO PIAUÍ SECRETARIA DE ADMINISTRAÇÃO DO ESTADO DO PIAUÍ "
         "DIRETORIA DO CIASPI - SEAD-PI Ofício Circular Nº: 68/2025/SEAD-PI/SGP/CIASPI "
         "Teresina/PI, 30 de abril de 2025 Aos Diretores, FUESPI, SASC, SADA.")
    assert _html._strip_doc_header_fields(t) == "Aos Diretores, FUESPI, SASC, SADA."


def test_strip_leading_letterhead_no_dateline():
    t = ("GOVERNO DO ESTADO DO PIAUÍ SECRETARIA DA ADMINISTRAÇÃO DO ESTADO DO PIAUÍ "
         "Sr. Superintendente, Trata-se da solicitação de pagamento.")
    assert _html._strip_doc_header_fields(t) == "Sr. Superintendente, Trata-se da solicitação de pagamento."


def test_strip_leading_letterhead_spares_body_mention():
    t = "Sr. Diretor, o Programa de Eficiência no Governo do Estado do Piauí avança."
    assert _html._strip_doc_header_fields(t) == t


def test_split_flag_list_normalizes_ext_flag():
    assert _p._split_flag_list(".html") == [".html"]
    assert _p._split_flag_list(".html,.pdf") == [".html", ".pdf"]
    assert _p._split_flag_list(".html .pdf") == [".html", ".pdf"]
    assert _p._split_flag_list([".html", ".pdf"]) == [".html", ".pdf"]
    assert _p._split_flag_list(None) is None
    assert _p._split_flag_list("") is None


def test_parse_prescans_and_sets_progress_total(tmp_path):
    from argparse import Namespace
    src = tmp_path / "in" / "00002.000001_2025-10"
    for doc in ("A", "B", "C"):
        d = src / doc
        d.mkdir(parents=True)
        (d / f"{doc}.txt").write_text(f"corpo {doc}", encoding="utf-8")
    out = tmp_path / "parsed"
    for doc in ("A", "B"):
        pd = out / doc
        pd.mkdir(parents=True)
        (pd / "text.txt").write_text("old", encoding="utf-8")

    class _Rec:
        def __init__(self):
            self.total = None
            self.advances = 0
        def set_total(self, n):
            self.total = n
        def advance(self, n=1):
            self.advances += n

    rec = _Rec()
    args = Namespace(input=str(tmp_path / "in"), output=str(out), processo=None,
                     limit=0, skip_existing=True, max_pdf_pages=10, ext=[".txt"], workers=1)
    summary = parse._execute(args, None, rec)

    assert rec.total == 1
    assert rec.advances == 1
    assert summary["skipped"] == 2
    assert summary["ok"] == 1
    assert summary["total"] == 3
    assert (out / "C" / "text.txt").read_text(encoding="utf-8") == "corpo C"
    assert (out / "A" / "text.txt").read_text(encoding="utf-8") == "old"
