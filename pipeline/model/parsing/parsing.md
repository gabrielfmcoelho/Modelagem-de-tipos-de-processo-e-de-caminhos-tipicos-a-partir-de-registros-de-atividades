# Parsing — de arquivo baixado a texto plano

**Pergunta.** Qual o texto do documento de abertura de cada processo?

Um despachante (`__init__.py:process_file`) por extensão, e um módulo por formato:
`html.py` · `pdf.py` · `vision.py` · `spreadsheet.py`.

## A fronteira que decide o determinismo

O stage `parse` está declarado **não-determinístico** no registro, mas isso vale para uma parte
do corpus, não para todo ele. A linha exata está em `pdf.py:_should_use_native`:

```python
if _single_char_fraction(text) >= 0.5:   # texto embaralhado -> visão
    return False
return len(text.strip()) / pages_read >= min_cpp   # PDF_NATIVE_MIN_CHARS_PER_PAGE = 100
```

| caminho | quando | determinístico |
|---|---|---|
| **nativo** | o PDF tem ≥ **100 caracteres por página** extraíveis e menos de 50% deles não são caracteres soltos | **sim** — extração de texto pura |
| **visão** | abaixo desse limiar, ou fração de caracteres soltos ≥ 0,5 | **não** — LLM de visão, varia entre execuções idênticas |
| HTML, TXT, planilha, DOCX | sempre | sim, exceto a planilha, que chama LLM para resumir |

Ou seja: mudar `PDF_NATIVE_MIN_CHARS_PER_PAGE` **move documentos entre um caminho reprodutível e
um não reprodutível**, sem que nada no artefato registre a mudança. É o parâmetro mais
consequente do módulo e o único cuja alteração muda a natureza da evidência, não só o seu valor.

## O que cada formato assume

- **`html.py`** — que o documento tem cabeçalho institucional, dateline e assinatura em torno do
  corpo. Doze expressões regulares removem essa moldura. Elas foram ajustadas ao layout do SEI
  desta administração; num outro órgão o corpo extraído seria diferente.
- **`pdf.py`** — que texto extraível existe se o PDF não é digitalizado. `_strip_garbled_runs`
  existe porque fontes mal embutidas produzem texto que *parece* extraído e não é.
- **`vision.py`** — que uma página cabe numa imagem legível. `IMAGE_MAX_DIMENSION` e
  `PAGES_PER_BATCH` limitam custo, não qualidade; aumentá-los não melhora a leitura.
- **`spreadsheet.py`** — que a planilha cabe em `MAX_SPREADSHEET_CHARS` e
  `MAX_SPREADSHEET_COLS`. Além disso o conteúdo é **truncado**, e o truncamento não é registrado
  no texto de saída.

## Saída

`parsed_documents/<doc_id>/text.txt` mais um `metadata.json` por documento. Esses não são
artefatos no sentido do contrato — são intermediários por documento, e por isso escrevem cru,
sem `_meta`. O que entra na cadeia de evidência é o que o `embed` deriva deles.
