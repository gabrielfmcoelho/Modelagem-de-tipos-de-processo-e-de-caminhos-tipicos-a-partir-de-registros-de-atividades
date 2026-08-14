# Literatura brasileira e lusófona — mineração de processos, SEI e dados processuais públicos

Levantamento feito em 2026-08-04 para a conversão do artigo em TCC (pt-BR).
Escopo: o que uma banca brasileira de Engenharia de Software esperaria ver citado
sobre (i) mineração de processos na administração pública brasileira, (ii) o SEI,
(iii) *trace clustering* em produção lusófona, (iv) jurimetria, (v) literatura
cinzenta de CNJ/CGU/TCU.

**Regra aplicada:** só entra na lista principal o que eu **abri** (página do
periódico/anais, repositório institucional, API do Crossref ou fonte oficial).
O que não consegui abrir está na seção "Não verificado". Nada foi inferido de
memória.

**Convenções de tipo:**
`revisado por pares` = periódico ou anais com revisão declarada ·
`tese/dissertação` = trabalho de pós-graduação em repositório institucional ·
`cinzenta` = relatório técnico, norma, documentação oficial ou estudo de caso
institucional sem revisão por pares.

---

## 1. Mineração de processos aplicada à administração pública brasileira

### 1.1 DINKOWSKI, Tassiane Giacomelli; AVILA, Diego Toralles; THOM, Lucinéia Heloisa. Fifteen years of process mining in Brazil: current contributions, most used techniques, and challenges. In: SIMPÓSIO BRASILEIRO DE SISTEMAS DE INFORMAÇÃO (SBSI), 21., 2025, Recife. **Anais** [...]. Porto Alegre: SBC, 2025. p. 409-418.

- DOI: 10.5753/sbsi.2025.246519 — https://sol.sbc.org.br/index.php/sbsi/article/view/34357
- Tipo: **revisado por pares** (anais SBSI/SBC, trilha principal)
- Verificação: **verificada** — página dos anais aberta + registro Crossref conferido.
- Contribui: revisão sistemática de 153 estudos brasileiros de mineração de
  processos ao longo de quinze anos, organizados em nove grupos de contribuição,
  com levantamento das técnicas mais usadas e dos desafios recorrentes —
  notadamente qualidade de dados. É a peça que responde literalmente à pergunta
  "o que já se fez no Brasil?" e permite posicionar o trabalho como brasileiro
  dentro de uma agenda brasileira, não como aplicação isolada.
- Onde entra: abertura da subseção de mineração de processos no setor público
  (`02-related-work.tex`, §rw-privacy-public), como parágrafo de enquadramento
  nacional antes dos casos individuais. Também serve à introdução do TCC.
- Ressalva: o registro Crossref grafa "Lucináia" (erro do registro); a página da
  SBC e a filiação da autora na UFRGS indicam **Lucinéia** Heloisa Thom.

### 1.2 NEUBAUER, Thais Rodrigues; ARAUJO, Renata Mendes de; FANTINATO, Marcelo; PERES, Sarajane Marques. Transparency promoted by process mining: an exploratory study in a public health product management process. In: WORKSHOP DE COMPUTAÇÃO APLICADA EM GOVERNO ELETRÔNICO (WCGE), 10., 2022. **Anais** [...]. Porto Alegre: SBC, 2022. p. 37-48.

- DOI: 10.5753/wcge.2022.223131 — https://sol.sbc.org.br/index.php/wcge/article/view/20709
- Tipo: **revisado por pares** (WCGE, dentro do Latin American Symposium on Digital Government / SBC)
- Verificação: **verificada** — página dos anais aberta.
- Contribui: log de eventos da agência nacional de vigilância sanitária
  (150.758 casos / 674.987 eventos, conforme relatado pelos autores) analisado
  com mineração de processos explicitamente como instrumento de transparência
  pública. É o antecedente direto — mesmo grupo (EACH-USP) — do artigo da
  Revista da CGU que o repositório já cita, e mostra escala de log comparável à
  do nosso corpus.
- Onde entra: §rw-privacy-public, ao lado de `araujo2023mineracao`, como o
  estudo empírico que sustenta o argumento de transparência (hoje citado só na
  versão de opinião/agenda).

### 1.3 MELAN, Rodrigo Libanez; SILVA, Hewerton Fernandes da; AMÂNCIO-VIEIRA, Saulo Fabiano; BACCARIN, Evandro. Mineração de processos em um órgão público: estudo da diretoria de loteamentos da Prefeitura Municipal de Londrina (PR). **Revista Inovação, Projetos e Tecnologias (IPTEC)**, v. 8, n. 2, p. 221-234, 2020.

- DOI: 10.5585/iptec.v8i2.17620 — https://periodicos.uninove.br/iptec/article/view/17620
- Tipo: **revisado por pares** (periódico com avaliação por pares, indexado Crossref/Scopus segundo a própria política editorial)
- Verificação: **verificada** — página do periódico aberta.
- Contribui: mineração de processos em órgão municipal brasileiro (aprovação de
  loteamentos), motivada por prazos altos de tramitação, combinando indicadores
  quantitativos e método qualitativo. Cobre a esfera municipal, que nenhuma das
  referências atuais alcança — hoje o repositório só tem judiciário (TRE-TO,
  TJSP) e federal.
- Onde entra: §rw-privacy-public, na enumeração de precedentes brasileiros por
  esfera de governo.

### 1.4 XAVIER, Rafael C.; SOUTHIER, Luiz F. P.; CAPELLO, Cinglair A.; SCALABRIN, Edson E.; FERRONATO, Jair J.; TEIXEIRA, Marcelo. Suporte à tomada de decisões em gestão pública municipal por meio de mineração de processos reativa e preditiva. In: WORKSHOP-ESCOLA DE INFORMÁTICA TEÓRICA (WEIT), 8., 2025, Ponta Grossa. **Anais** [...]. Porto Alegre: SBC, 2025. p. 162-171.

- DOI: 10.5753/weit.2025.40454 — https://sol.sbc.org.br/index.php/weit/article/view/40454
- Tipo: **revisado por pares** (anais SBC)
- Verificação: **verificada** — página dos anais aberta.
- Contribui: combina descoberta retrospectiva com previsão de tempo de
  conclusão de trâmites administrativos municipais, identificando setores
  problemáticos. É o precedente brasileiro mais próximo do nosso uso de predição
  *sobre* processos administrativos — ainda que lá a predição seja o produto e
  aqui seja instrumento de medida.
- Onde entra: §rw-percluster ou §rw-ppm, como nota de que a combinação
  descoberta + predição já foi tentada em administração pública brasileira, e
  para marcar a diferença de papel dado à predição.

### 1.5 VASCONCELOS, Gyslla; VITERBO, José; BERNARDINI, Flavia. Assessing the capability of open government data for process mining: a study on a Brazilian open data portal. In: ANNUAL INTERNATIONAL CONFERENCE ON DIGITAL GOVERNMENT RESEARCH (dg.o), 2025. **Proceedings** [...]. Delft: TU Delft OPEN Publishing, 2025.

- DOI: 10.59490/dgo.2025.1041 — https://proceedings.open.tudelft.nl/DGO2025/article/view/1041
- Tipo: **revisado por pares** (dg.o, conferência internacional consolidada em governo digital; autores da UFF)
- Verificação: **verificada** — página dos proceedings aberta + Crossref conferido.
  Faixa de páginas não consta do registro.
- Contribui: método para classificar conjuntos do portal brasileiro de dados
  abertos (dados.gov.br) segundo aptidão para mineração de processos; encontram
  24% relevantes, 23% em formato tabular datado e apenas 1% já em formato de log
  de eventos. É evidência empírica brasileira de que dado público publicado
  raramente é dado processual utilizável — exatamente o argumento de que
  divulgação ≠ inteligibilidade que a §rw-legal já faz com literatura anglófona.
- Onde entra: §rw-legal, junto a `janssen2012benefits`, agora com número
  brasileiro; e na justificativa de por que foi preciso construir o log a partir
  do sistema, e não baixá-lo de um portal.

### 1.6 FUJIWARA, Ricardo Shigueru. **Mineração de processos como ferramenta de mitigação e prevenção de fraudes na gestão pública**. 2021. Dissertação (Mestrado em Gestão da Informação) — Universidade Federal do Paraná, Curitiba, 2021.

- URI: https://hdl.handle.net/1884/72005
- Tipo: **dissertação** (mestrado, repositório institucional UFPR)
- Verificação: **verificada** — registro do repositório aberto. O nome do
  orientador não consta da página de metadados que abri.
- Contribui: mineração de processos sobre dados abertos de execução de obras
  públicas, com foco em detecção de anomalias/fraude. Demonstra a linha de
  aplicação "controle" (não eficiência, não transparência) na produção
  brasileira de pós-graduação.
- Onde entra: opcional. Serve à seção de trabalhos relacionados do TCC para
  mostrar amplitude de finalidades no Brasil; não é necessário na versão
  internacional.

### 1.7 ROZINAT, Anne. **Government process mining in the Brazilian executive branch**. IEEE Task Force on Process Mining, 2019 (atualizado em 7 jan. 2020). Estudo de caso.

- URL: https://www.tf-pm.org/resources/casestudy/government-process-mining-in-the-brazilian-executive-branch
- Tipo: **cinzenta** (estudo de caso institucional da IEEE Task Force on Process Mining, sem revisão por pares)
- Verificação: **verificada** — página aberta. **Atenção:** a página **não**
  identifica o sistema de origem dos dados (não confirma SEI). Não afirmar que
  usou SEI.
- Contribui: registro de que mineração de processos foi aplicada a processos
  regulatórios do Poder Executivo Federal brasileiro, apontando sobreposição
  regulatória, gargalos e retrabalho. Vale como evidência de adoção prática no
  governo federal, não como resultado científico.
- Onde entra: nota de rodapé ou frase de contexto na introdução/cenário. Não
  usar como base de comparação metodológica.

---

## 2. O SEI (Sistema Eletrônico de Informações)

### 2.1 SORIANO, Fabiano; DIAS, Carina Santos; VALERIANO, Mariangela Oliveira Gomes; SANTOS, Matheus Silva. Sistema Eletrônico de Informações (SEI) na administração pública: avanços, desafios e perspectivas a partir de uma revisão sistemática da literatura. **P2P e Inovação**, v. 12, n. 1, e-7637, 2025.

- DOI: 10.21728/p2p.2025v12n1e-7637 — https://revista.ibict.br/p2p/article/view/7637
- Tipo: **revisado por pares** (periódico do IBICT)
- Verificação: **verificada** — página do periódico aberta.
- Contribui: **a** revisão sistemática sobre o SEI. Consolida ganhos de
  eficiência e sustentabilidade e, mais útil para nós, os problemas persistentes
  de interoperabilidade, segurança da informação e preservação digital. É a
  citação que fecha a pergunta "o SEI já foi estudado?" de uma vez.
- Onde entra: seção de cenário/contexto do TCC (caracterização do SEI), primeira
  citação; e §rw-privacy-public para justificar por que o SEI é objeto legítimo
  de estudo.

### 2.2 FULTON, Denise de Carvalho Pires; FARIAS, Josivania Silva; ALFINITO, Solange; ALMEIDA, Juliana Pascualote Lemos de. Adoção do Sistema Eletrônico de Informações (SEI) pelo Ministério da Justiça: uma avaliação na ótica de usuários. **Revista do Serviço Público**, v. 69, n. 4, p. 1015-1036, 2018.

- DOI: 10.21874/rsp.v69i4.3624 — https://revista.enap.gov.br/index.php/RSP/article/view/3624
- Tipo: **revisado por pares** (RSP/ENAP — periódico de referência em administração pública no Brasil)
- Verificação: **verificada** — página do periódico aberta.
- Contribui: avaliação de adoção do SEI com 208 usuários do Ministério da
  Justiça, sob o modelo de Moore & Benbasat, com análise fatorial exploratória.
  Dá base empírica revisada por pares para afirmar que o SEI é sistema adotado e
  estudado, e que a percepção de vantagem relativa varia com experiência e
  idade do usuário.
- Onde entra: seção de cenário. Também útil como contraponto: a literatura de
  SEI mediu **percepção de usuário**, não **comportamento do processo** — que é
  a lacuna que este trabalho ocupa.

### 2.3 SILVA, Leandro Gonçalves; SOUZA, Rosália Beber de. A gestão de documentos e tramitação de processos na administração pública, com a utilização do Sistema Eletrônico de Informações – SEI: um estudo de caso na Universidade Federal de Viçosa. **Múltiplos Olhares em Ciência da Informação**, v. 10, 2020.

- DOI: 10.35699/2237-6658.2020.25838 — https://periodicos.ufmg.br/index.php/moci/article/view/25838
- Tipo: **revisado por pares** (periódico da UFMG, Ciência da Informação)
- Verificação: **verificada** — página do periódico aberta.
- Contribui: estudo de caso na UFV; conclui por ganho de eficiência, mas alerta
  que o SEI **não é um sistema informatizado de gestão arquivística de
  documentos**, o que gera risco de preservação e inconsistências. Esse achado é
  diretamente útil: sustenta, com fonte brasileira revisada, a premissa de que
  os metadados declarados no SEI não são confiáveis — que é a premissa da RQ1.
- Onde entra: seção de cenário e, sobretudo, na justificativa da pergunta de
  pesquisa (a taxonomia declarada da administração não registra o tipo de
  processo de forma confiável).

### 2.4 NOWAK, Mary Anne Muraski. **A utilização do Sistema Eletrônico de Informações - SEI no serviço público: inovação tecnológica para melhoria na eficiência administrativa e no conhecimento institucional**. 2018. Dissertação (Mestrado em Desenvolvimento Econômico) — Universidade Federal do Paraná, Curitiba, 2018.

- URI: https://hdl.handle.net/1884/55992
- Tipo: **dissertação** (mestrado, repositório UFPR)
- Verificação: **verificada** — registro do repositório aberto.
- Contribui: implantação do SEI na UFPR sob ótica qualitativa, com foco em
  capacitação e conhecimento institucional. Reforço secundário; usar apenas se a
  banca pedir mais lastro nacional sobre adoção.
- Onde entra: opcional, seção de cenário.

### 2.5 BAPTISTA, Patrícia Ferreira; ANTOUN NETTO, Leonardo Silveira. O processo administrativo eletrônico e sua disciplina no direito administrativo brasileiro: entre novos desafios e velhos problemas. **Revista de Direito Administrativo**, v. 282, n. 3, p. 85-110, 2023.

- DOI: 10.12660/rda.v282.2023.90156 — https://periodicos.fgv.br/rda/article/view/90156
- Tipo: **revisado por pares** (RDA/FGV — periódico jurídico de primeira linha no Brasil)
- Verificação: **verificada** — página do periódico aberta.
- Contribui: análise jurídica do processo administrativo eletrônico brasileiro
  com foco explícito no SEI, argumentando que a digitalização **não** resolveu
  os problemas burocráticos anteriores, criou desafios novos para garantias do
  Estado de Direito e pode ser mera "transposição burocrática". É a peça que dá
  à §rw-legal um ancoradouro doutrinário brasileiro, hoje inexistente — a seção
  discute procedimento administrativo só com Suksi, Bovens, Ananny.
- Onde entra: §rw-legal, como a leitura jurídica nacional do objeto; e na
  motivação (tornar o "as-is" inspecionável antes de automatizar).

### 2.6 Base normativa e documentação oficial do SEI/PEN (literatura cinzenta oficial)

**a) BRASIL. Decreto nº 8.539, de 8 de outubro de 2015.** Dispõe sobre o uso do
meio eletrônico para a realização do processo administrativo no âmbito dos
órgãos e das entidades da administração pública federal direta, autárquica e
fundacional.
- Fonte oficial aberta: CONARQ/gov.br —
  https://www.gov.br/conarq/pt-br/legislacao-arquivistica/decretos-federais/decreto-no-8-539-de-8-de-outubro-de-2015
  (texto integral no Planalto: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/decreto/d8539.htm)
- Tipo: **cinzenta / normativa**
- Verificação: **ementa e data verificadas** na página oficial do CONARQ. O
  Planalto recusou conexão nas duas tentativas (ECONNRESET); **os artigos não
  foram lidos por mim**. Não citar artigo específico sem abrir o texto.
- Contribui: é o marco normativo que torna obrigatório o processo administrativo
  eletrônico na esfera federal e que dá origem institucional ao PEN/SEI.
- Onde entra: seção de cenário do TCC, primeira frase de caracterização do SEI.

**b) BRASIL. Lei nº 14.129, de 29 de março de 2021.** Dispõe sobre princípios,
regras e instrumentos para o Governo Digital e para o aumento da eficiência
pública [...].
- Fonte oficial aberta: https://www.gov.br/governodigital/pt-br/legislacao/lei-do-governo-digital
  (texto no Planalto: http://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/L14129.htm)
- Tipo: **cinzenta / normativa**
- Verificação: **ementa e data verificadas** na página oficial do Governo
  Digital. Artigos não lidos.
- Contribui: completa o arco normativo (LAI 2011 → CDU 2017 → Decreto 8.539/2015
  → Governo Digital 2021) e altera justamente a LAI e o Código de Defesa do
  Usuário, ambos já citados no `references.bib`. Fecha a cadeia legal que a
  §rw-legal usa hoje só com `brasil2011lai` e `brasil2017cdu`.
- Onde entra: §rw-legal / seção legal do TCC.

**c) BRASIL. Ministério da Gestão e da Inovação em Serviços Públicos.
Sistema Eletrônico de Informações — SEI.** Portal Serviços Compartilhados.
- URL: https://www.gov.br/servicoscompartilhados/pt-br/assuntos/gestao-documental/sistema-eletronico-de-informacoes-sei
- Tipo: **cinzenta / documentação oficial**
- Verificação: **verificada** — página aberta. Confirma textualmente: o SEI é a
  solução oficial do Governo Federal para produção e gestão de documentos e
  processos administrativos eletrônicos; **desenvolvido pelo Tribunal Regional
  Federal da 4ª Região (TRF4)**; **cedido gratuitamente a instituições públicas
  desde 2013**.
- Onde entra: caracterização do cenário. É a fonte a citar para "quem
  desenvolveu" e "como é distribuído" — não usar sites de universidades para isso.

**d) BRASIL. Ministério da Gestão e da Inovação em Serviços Públicos.
Processo Eletrônico Nacional (PEN).**
- URL: https://www.gov.br/gestao/pt-br/assuntos/gestaoeinovacao/informacoes-sistemas-e-servicos-de-gestao/processo-eletronico-nacional/conteudo/processo-eletronico-nacional-pen
- Tipo: **cinzenta / documentação oficial**
- Verificação: **verificada** — página aberta. Define o PEN como infraestrutura
  pública de processo administrativo eletrônico, sob a Secretaria de Gestão e
  Inovação (DTGES); registra o Acordo de Cooperação Técnica de junho de 2023
  entre o Ministério e o TRF4 para desenvolvimento colaborativo do SEI.
- Nota: a página **não** informa número de órgãos usuários. Não afirmar
  "usado por N órgãos" com base nela.
- Onde entra: caracterização do cenário, um parágrafo antes do SEI propriamente.

---

## 3. *Trace clustering* e descoberta de tipos de processo em produção lusófona

### 3.1 ARAÚJO, Thiago; CARMO, Danilo; LIMA, Ricardo; OLIVEIRA, Adriano. Trace clustering for judicial process simplification: identifying patterns and enhancing anaslysis [sic]. **Artificial Intelligence and Law**, 2025.

- DOI: 10.1007/s10506-025-09481-7 — https://link.springer.com/article/10.1007/s10506-025-09481-7
- Tipo: **revisado por pares** (Artificial Intelligence and Law, Springer — mesmo periódico de `vianna2024topic`, `tinarrage2025empirical`, `medvedeva2023rethinking`)
- Verificação: **verificada via registro Crossref** (autores, título, periódico,
  ano, data de publicação 22 out. 2025) **e via páginas de resumo**. O texto
  integral está atrás de paywall — **não li o artigo completo**. Volume, número
  e número de artigo ainda não constavam do registro.
- **Atenção:** o título registrado contém o erro tipográfico "anaslysis". Ele
  está assim no registro do editor. Reproduzir como está ou usar `[sic]`, mas
  **não** "corrigir" silenciosamente, ou a busca por DOI não bate.
- **Atenção 2:** o Crossref registra os nomes em forma curta ("Thiago Araújo",
  "Ricardo Lima", "Adriano Oliveira"). Se a banca exigir nome completo ABNT,
  confirmar no PDF publicado antes de expandir.
- Contribui: **é o trabalho brasileiro mais próximo deste TCC que existe.**
  Aplica *trace clustering* a logs judiciais de três unidades de Juizado
  Especial brasileiras, com pré-processamento, codificação e algoritmos de
  agrupamento; relata que **os clusters encontrados corresponderam a tipos
  distintos de procedimento judicial**, avalia os modelos derivados por
  perspectiva estrutural e comportamental, e submete o resultado a **validação
  por especialistas jurídicos**.
- Onde entra: **obrigatório em §rw-clustering.** Precisa ser tratado
  explicitamente, porque (a) confirma independentemente a premissa central de
  que agrupamento de trilhas faz emergir tipos de procedimento, e (b) fez a
  validação por especialistas que a §threats admite não ter feito. A distinção a
  declarar: lá o domínio é judicial e há modelo de referência procedimental; aqui
  é administrativo, sem modelo "as-is" documentado, e a avaliação é por
  desempenho preditivo por cluster com controles de nulo. Ignorar este artigo
  seria a falha mais visível do capítulo.

### 3.2 NEUBAUER, Thais Rodrigues; FANTINATO, Marcelo; PERES, Sarajane Marques. Agrupamento interativo aplicado à mineração de processos. In: WORKSHOP DE TESES E DISSERTAÇÕES EM SISTEMAS DE INFORMAÇÃO (WTDSI), SIMPÓSIO BRASILEIRO DE SISTEMAS DE INFORMAÇÃO (SBSI), 15., 2019, Aracaju. **Anais Estendidos** [...]. Porto Alegre: SBC, 2019. p. 45-48.

- DOI: 10.5753/sbsi.2019.7438 — https://sol.sbc.org.br/index.php/sbsi_estendido/article/view/7438
- Tipo: **revisado por pares** (anais estendidos SBC; é resumo de dissertação em workshop de teses — peso menor que trilha principal)
- Verificação: **verificada** — página dos anais aberta + Crossref conferido.
- **Atenção:** duas divergências no registro. (i) O Crossref registra o título em
  inglês, "Interactive trace clustering", enquanto a página dos anais traz o
  título em português. (ii) A página da SBC grafa o sobrenome como "Neubaer"
  (erro); a forma correta, confirmada em todas as demais publicações da autora,
  é **Neubauer**. Decidir uma forma e ser consistente.
- Contribui: é o único trabalho em português que encontrei tratando
  *trace clustering* como objeto (não como ferramenta), inclusive fixando o termo
  "agrupamento de traços". Usa três esquemas de representação vetorial de
  trilhas, o que dialoga diretamente com `song2009trace`.
- Onde entra: §rw-clustering, como registro de que a discussão de representação
  vs. algoritmo também foi feita na comunidade brasileira de SI, e para ancorar
  a terminologia em português no TCC.

### 3.3 NEUBAUER, Thais Rodrigues; PAMPONET SOBRINHO, Glaucia; FANTINATO, Marcelo; PERES, Sarajane Marques. Visualization for enabling human-in-the-loop in trace clustering-based process mining tasks. In: IEEE INTERNATIONAL CONFERENCE ON BIG DATA (BIG DATA), 2021, Orlando. **Proceedings** [...]. IEEE, 2021. p. 3548-3556.

- DOI: 10.1109/BigData52589.2021.9671985
- Tipo: **revisado por pares** (IEEE BigData)
- Verificação: **verificada via registro Crossref** (autores completos, título,
  páginas, ano, local). **Não abri a página do IEEE nem o PDF.**
- Contribui: versão madura da linha anterior; põe o especialista humano no laço
  do agrupamento de trilhas por meio de visualização. É o contraste útil ao
  nosso desenho: eles injetam conhecimento de domínio *durante* o agrupamento,
  nós avaliamos partições emergentes *depois*, sem intervenção — o mesmo eixo
  "wrapper vs. post-hoc" que a §rw-clustering já usa contra o ActiTraC.
- Onde entra: §rw-clustering, segundo parágrafo (o de posicionamento).

### 3.4 YAMATE, Bruno Yui; NEUBAUER, Thais Rodrigues; FANTINATO, Marcelo; PERES, Sarajane Marques. **Text-to-SQL oriented to the process mining domain: a PT-EN dataset for query translation**. arXiv:2509.09684, 2025.

- URL: https://arxiv.org/abs/2509.09684
- Tipo: **preprint** (não revisado por pares; a página não declara veículo de publicação)
- Verificação: **verificada** — página do arXiv aberta.
- Contribui: dataset bilíngue português-inglês (1.655 enunciados, 205 comandos
  SQL) para tradução de linguagem natural em consultas no domínio de mineração de
  processos. Marginal para o argumento central; relevante só se o TCC discutir
  acesso em linguagem natural a logs. Registra que o vocabulário de mineração de
  processos em português é objeto de trabalho.
- Onde entra: nada obrigatório. Citar só em trabalhos futuros, se houver.

---

## 4. Jurimetria e análise de dados processuais brasileiros

### 4.1 NUNES, Marcelo Guedes. **Jurimetria: como a estatística pode reinventar o direito**. 2. ed. rev. e atual. São Paulo: Revista dos Tribunais, 2019. 190 p. ISBN 978-85-5321-999-5. (1. ed. 2016, 192 p., ISBN 978-85-203-6794-0.)

- Registro: LexML / Rede Virtual de Bibliotecas —
  https://www.lexml.gov.br/urn/urn:lex:br:rede.virtual.bibliotecas:livro:2019;001163005
- Tipo: **livro** (doutrina; não é revisão por pares, mas é a obra fundadora da disciplina no Brasil e a banca a reconhece)
- Verificação: **verificada** — registro catalográfico do LexML aberto, com
  ISBN, edição, editora, local, ano e paginação.
- **Atenção:** existe uma 3ª edição, de 2024, com título alterado para
  *Jurimetria: estatística, tecnologia e direito*. **Não a verifiquei em fonte
  catalográfica** — ver seção "Não verificado". Se quiser citar a mais recente,
  confirme antes.
- Contribui: define jurimetria no Brasil e é a referência que qualquer banca
  espera ver quando o termo aparece. O `references.bib` cita
  `unger2021jurimetrics`, que **usa** o termo sem ancorá-lo na literatura
  brasileira que o consolidou.
- Onde entra: §rw-privacy-public ou §rw-legal, na primeira ocorrência do termo
  "jurimetria" no TCC.

### 4.2 CONSELHO NACIONAL DE JUSTIÇA (Brasil). **Justiça em números 2025**. Brasília: CNJ, 2025. 650 p. ISBN 978-65-5972-195-5. (Série Relatórios e dados estatísticos do Poder Judiciário.)

- URI: https://bibliotecadigital.cnj.jus.br/xmlui/handle/123456789/1060
- Tipo: **cinzenta** (relatório institucional oficial; alta credibilidade perante banca brasileira)
- Verificação: **verificada** — registro da Biblioteca Digital do CNJ aberto
  (título, editor, local, ano, 650 p., ISBN, série, PDF de 26,24 MB).
- Contribui: fonte oficial das estatísticas do Judiciário brasileiro, publicada
  anualmente desde 2004. Serve para dimensionar a escala do problema de dados
  processuais no país e para justificar por que a análise quantitativa de
  tramitação é agenda instalada, não novidade metodológica.
- Onde entra: introdução/motivação do TCC. Não é referência metodológica.

### 4.3 CONSELHO NACIONAL DE JUSTIÇA (Brasil). **Resolução nº 331, de 20 de agosto de 2020**. Institui a Base Nacional de Dados do Poder Judiciário — DataJud como fonte primária de dados do Sistema de Estatística do Poder Judiciário. DJe/CNJ, n. 274, 25 ago. 2020, p. 2-4.

- URL: https://atos.cnj.jus.br/atos/detalhar/3428
- Tipo: **cinzenta / normativa**
- Verificação: **verificada** — texto do ato aberto no portal oficial de atos do
  CNJ. Art. 1º institui o DataJud; art. 11 prevê que ato da Presidência disporá
  sobre as informações disponibilizadas por API pública.
- Contribui: precedente institucional brasileiro de que dados e metadados
  processuais são tratados como base nacional consultável por API — ou seja, o
  país já normatizou a ideia de que trâmite processual é dado público
  estruturado. Fortalece o argumento de transparência da §rw-legal com norma
  brasileira, não só com LAI.
- Onde entra: §rw-legal ou seção legal do TCC.

---

## 5. CNJ / CGU / TCU — publicações técnicas

Além do CNJ (itens 4.2 e 4.3 acima):

### 5.1 BRASIL. Tribunal de Contas da União. **Referencial básico de governança aplicável a organizações públicas e outros entes jurisdicionados ao TCU**. 3. ed. Brasília: TCU, Secretaria de Controle Externo da Administração do Estado (SecexAdministração), 2020. 242 p.

- PDF: https://portal.tcu.gov.br/data/files/FB/B6/FB/85/1CD4671023455957E18818A8/Referencial_basico_governanca_organizacional_3_edicao.pdf
  (página: https://portal.tcu.gov.br/referencial-basico-de-governanca-organizacional.htm)
- Tipo: **cinzenta** (referencial técnico institucional do TCU)
- Verificação: **verificada** — PDF baixado e a ficha catalográfica lida
  diretamente (título exato, edição 3, TCU/SecexAdministração, Brasília, 2020,
  242 p.). Note que o **título da ficha catalográfica difere do título da capa**:
  a capa diz "Referencial Básico de Governança Organizacional"; a ficha diz
  "Referencial básico de governança aplicável a organizações públicas e outros
  entes jurisdicionados ao TCU". Use a forma da ficha.
- Contribui: define, na voz do órgão de controle externo federal, o que conta
  como governança, prestação de contas e transparência em organização pública
  brasileira. Relevância **indireta**: não trata de dados processuais nem de
  mineração de processos.
- Onde entra: opcional, na motivação institucional do TCC. **Não** usar como
  fundamentação metodológica — seria esticar a fonte.

### 5.2 CGU — já coberto

A **Revista da CGU** já está no `references.bib` via `araujo2023mineracao`
(v. 15, n. 27, p. 203-218, 2023, DOI 10.36428/revistadacgu.v15i27.567). É o
melhor material CGU disponível para este tema e é revisado por pares. Não
encontrei publicação técnica da CGU (fora da revista) sobre mineração de
processos ou dados processuais que valesse citação — o que existe são planos de
dados abertos e metodologias de avaliação de transparência de entes federados,
fora do escopo.

---

## Já citado no `references.bib`

Verifiquei as 117 entradas. O material brasileiro/lusófono **já presente** é:

| Chave | O que é | Observação |
|---|---|---|
| `limaesilva2026analise` | Mineração de processos no TRE-TO, Revista DCS, 2026 | **É o único trabalho já citado que extrai log do próprio SEI.** Vale explicitar isso no texto — hoje a §rw-privacy-public o menciona sem dizer que a fonte é SEI. |
| `araujo2023mineracao` | Mineração de processos e transparência, Revista da CGU, 2023 | Grupo EACH-USP. O estudo empírico correspondente é o item 1.2 acima (WCGE 2022), ainda não citado. |
| `unger2021jurimetrics` | ICAIL 2021, jurimetria com mineração de processos no TJSP | Já ancorado. Falta a base conceitual brasileira de jurimetria (item 4.1). |
| `rocha2024critical` | Tratamento de dados pessoais pelo governo, CLSR 2024 | Contexto LGPD. |
| `canedo2022evaluating` | Conformidade à LGPD em órgão federal, ICEIS/LNBIP 455 | Contexto LGPD. |
| `tinarrage2025empirical` | Súmulas vinculantes do STF, AI&Law 2025 | Direito + ML brasileiro. |
| `vianna2024topic` | Descoberta de tópicos em documentos jurídicos em pt-BR, AI&Law 2024 | Mais próximo em método (não supervisionado + validação por especialistas). |
| `erickson2019comparative` | GDPR × LGPD, Brooklyn J. Int'l L. 2019 | Comparado, não brasileiro. |
| `brasil1988cf`, `brasil2011lai`, `brasil2018lgpd`, `brasil2017cdu` | CF/88, LAI, LGPD, Código de Defesa do Usuário | Base normativa já presente. Falta Decreto 8.539/2015 e Lei 14.129/2021 (item 2.6). |
| `state2016procedurelaw` | Lei estadual de processo administrativo, anonimizada para revisão cega | Restaurar no camera-ready. |

**Nenhuma** das fontes novas propostas neste documento está duplicada no
`references.bib`.

**Lacunas que este levantamento fecha:** (a) nenhuma referência sobre o SEI
enquanto sistema — o artigo estuda o SEI e não cita um único estudo sobre ele;
(b) nenhuma revisão da produção brasileira em mineração de processos;
(c) nenhum trabalho brasileiro de *trace clustering* — e existe um, em AI&Law,
sobre exatamente o mesmo problema (item 3.1); (d) nenhuma doutrina jurídica
brasileira sobre processo administrativo eletrônico; (e) nenhuma base normativa
do processo eletrônico (só LAI/LGPD/CDU, que são adjacentes).

---

## Não verificado

Itens que aparecem em resultados de busca e parecem existir, mas que **não
consegui abrir**. Não citar sem confirmação.

1. **NUNES, Marcelo Guedes. *Jurimetria: estatística, tecnologia e direito*. 3. ed. São Paulo: Revista dos Tribunais, 2024. ~280 p.** — Só vi em livrarias e páginas comerciais; não localizei registro catalográfico oficial. A 2ª ed. (item 4.1) **está** verificada no LexML. Se quiser a 3ª, confirme no LexML/Biblioteca Nacional antes.
2. **BRASIL. Decreto nº 8.539/2015 — texto integral dos artigos.** Ementa verificada no CONARQ; o Planalto recusou conexão (ECONNRESET) em duas tentativas. **Não cite artigo específico** (Art. 1º, 3º, etc.) sem abrir o texto.
3. **BRASIL. Lei nº 14.129/2021 — texto integral dos artigos.** Mesma situação: ementa verificada em fonte oficial, articulado não lido.
4. **Manual do Usuário SEI / Manual de Administração do SEI (PEN — `manuais.processoeletronico.gov.br`).** Retornou HTTP 403 em duas tentativas (índice e página "Tipo de Processo"). Seria a fonte oficial para caracterizar o conceito de **tipo de processo** no SEI e sua vinculação ao código de classificação documental (CONARQ/TTD) — que é exatamente a taxonomia declarada que o artigo afirma não ser confiável. **Vale insistir**: é a citação mais útil que ficou faltando para a seção de cenário. Tentar por outro cliente/horário.
5. **SCHWAICKARDT, Ederson. Mineração de processos aplicada na gestão [...]. Dissertação, PUC Goiás.** PDF em `tede2.pucgoias.edu.br` retornou HTTP 403. Pelos indícios de busca, o domínio é ERP privado (Protheus), não setor público — provavelmente fora do escopo.
6. **Artigo de revisão sobre jurimetria em *Ciência da Informação em Revista* (UFAL), periodicos.ufal.br/cir/article/view/15703.** Servidor recusou conexão (ECONNREFUSED). Pelo resumo indexado, é revisão bibliográfica de baixo peso; o item 4.1 cobre melhor a função.
7. **"Análise da implementação e impacto do SEI no Instituto Federal do Acre".** Só localizado no ResearchGate; não identifiquei periódico, ano ou DOI. Não usar.
8. **Trabalhos de conclusão de curso citando extração de log do SEI (UFF/Celonis, IFPE/classificação documental com ML).** Localizados como PDFs em repositórios, não abertos. São TCCs de graduação — peso baixo para banca de pós; só perseguir se faltar volume.
9. **Relatório *Justiça em Números 2026*.** Há notícia do CNJ de janeiro de 2026 sobre o estoque processual, mas não localizei o registro catalográfico da edição 2026. A edição **2025 está verificada** (item 4.2).

---

## Entradas BibTeX propostas

Somente fontes verificadas. Chaves escolhidas para não colidir com as 117
existentes (confira `araujo2023mineracao` × `araujo2025trace`).

```bibtex
%% ---- Mineração de processos no Brasil (levantamento pt-BR, ago/2026) ----

%% Revisão sistemática de 15 anos de mineração de processos no Brasil.
%% NB Crossref grafa "Lucináia"; a forma correta é Lucineia/Lucinéia Heloisa Thom (UFRGS).
@inproceedings{dinkowski2025fifteen,
  author    = {Dinkowski, Tassiane Giacomelli and Avila, Diego Toralles and
               Thom, Lucin{\'e}ia Heloisa},
  title     = {Fifteen years of process mining in {Brazil}: current contributions,
               most used techniques, and challenges},
  booktitle = {Anais do XXI Simp{\'o}sio Brasileiro de Sistemas de Informa{\c{c}}{\~a}o
               (SBSI 2025)},
  publisher = {Sociedade Brasileira de Computa{\c{c}}{\~a}o},
  address   = {Porto Alegre},
  pages     = {409--418},
  year      = {2025},
  doi       = {10.5753/sbsi.2025.246519},
  url       = {https://sol.sbc.org.br/index.php/sbsi/article/view/34357}
}

%% Estudo empírico que antecede araujo2023mineracao (mesmo grupo, EACH-USP).
@inproceedings{neubauer2022transparency,
  author    = {Neubauer, Thais Rodrigues and de Araujo, Renata Mendes and
               Fantinato, Marcelo and Peres, Sarajane Marques},
  title     = {Transparency promoted by process mining: an exploratory study in a
               public health product management process},
  booktitle = {Anais do X Workshop de Computa{\c{c}}{\~a}o Aplicada em Governo
               Eletr{\^o}nico (WCGE 2022)},
  publisher = {Sociedade Brasileira de Computa{\c{c}}{\~a}o},
  address   = {Porto Alegre},
  pages     = {37--48},
  year      = {2022},
  doi       = {10.5753/wcge.2022.223131},
  url       = {https://sol.sbc.org.br/index.php/wcge/article/view/20709}
}

@article{melan2020mineracao,
  author  = {Melan, Rodrigo Libanez and da Silva, Hewerton Fernandes and
             Am{\^a}ncio-Vieira, Saulo Fabiano and Baccarin, Evandro},
  title   = {Minera{\c{c}}{\~a}o de processos em um {\'o}rg{\~a}o p{\'u}blico: estudo da
             diretoria de loteamentos da {Prefeitura Municipal de Londrina (PR)}},
  journal = {Revista Inova{\c{c}}{\~a}o, Projetos e Tecnologias (IPTEC)},
  volume  = {8},
  number  = {2},
  pages   = {221--234},
  year    = {2020},
  doi     = {10.5585/iptec.v8i2.17620},
  url     = {https://periodicos.uninove.br/iptec/article/view/17620}
}

@inproceedings{xavier2025suporte,
  author    = {Xavier, Rafael C. and Southier, Luiz F. P. and Capello, Cinglair A. and
               Scalabrin, Edson E. and Ferronato, Jair J. and Teixeira, Marcelo},
  title     = {Suporte {\`a} tomada de decis{\~o}es em gest{\~a}o p{\'u}blica municipal por
               meio de minera{\c{c}}{\~a}o de processos reativa e preditiva},
  booktitle = {Anais do VIII Workshop-Escola de Inform{\'a}tica Te{\'o}rica (WEIT 2025)},
  publisher = {Sociedade Brasileira de Computa{\c{c}}{\~a}o},
  address   = {Porto Alegre},
  pages     = {162--171},
  year      = {2025},
  doi       = {10.5753/weit.2025.40454},
  url       = {https://sol.sbc.org.br/index.php/weit/article/view/40454}
}

%% Faixa de páginas não consta do registro do editor nem do Crossref.
@inproceedings{vasconcelos2025ogd,
  author    = {Vasconcelos, Gyslla and Viterbo, Jos{\'e} and Bernardini, Flavia},
  title     = {Assessing the capability of open government data for process mining:
               a study on a {Brazilian} open data portal},
  booktitle = {Proceedings of the 26th Annual International Conference on Digital
               Government Research (dg.o 2025)},
  publisher = {TU Delft OPEN Publishing},
  year      = {2025},
  doi       = {10.59490/dgo.2025.1041},
  url       = {https://proceedings.open.tudelft.nl/DGO2025/article/view/1041}
}

@mastersthesis{fujiwara2021mineracao,
  author  = {Fujiwara, Ricardo Shigueru},
  title   = {Minera{\c{c}}{\~a}o de processos como ferramenta de mitiga{\c{c}}{\~a}o e
             preven{\c{c}}{\~a}o de fraudes na gest{\~a}o p{\'u}blica},
  school  = {Universidade Federal do Paran{\'a}, Programa de P{\'o}s-Gradua{\c{c}}{\~a}o
             em Gest{\~a}o da Informa{\c{c}}{\~a}o},
  address = {Curitiba},
  year    = {2021},
  type    = {Disserta{\c{c}}{\~a}o (Mestrado)},
  url     = {https://hdl.handle.net/1884/72005}
}

%% Literatura cinzenta: estudo de caso da IEEE Task Force on Process Mining.
%% A página NÃO identifica o sistema de origem dos dados -- não atribuir ao SEI.
@misc{rozinat2019brazilexec,
  author       = {Rozinat, Anne},
  title        = {Government process mining in the {Brazilian} executive branch},
  howpublished = {{IEEE} Task Force on Process Mining, case study},
  year         = {2019},
  note         = {Atualizado em 7 jan. 2020},
  url          = {https://www.tf-pm.org/resources/casestudy/government-process-mining-in-the-brazilian-executive-branch},
  urldate      = {2026-08-04}
}

%% ---- Trace clustering brasileiro ----

%% ATENÇÃO: o título registrado pelo editor contém a errata "anaslysis".
%% Mantido como registrado para que a busca por DOI/título resolva.
%% Nomes de autor em forma curta conforme registro Crossref; expandir só após
%% conferir o PDF publicado.
@article{araujo2025trace,
  author  = {Ara{\'u}jo, Thiago and Carmo, Danilo and Lima, Ricardo and Oliveira, Adriano},
  title   = {Trace clustering for judicial process simplification: identifying patterns
             and enhancing anaslysis},
  journal = {Artificial Intelligence and Law},
  year    = {2025},
  doi     = {10.1007/s10506-025-09481-7},
  note    = {Publicado online em 22 out. 2025}
}

%% NB a página da SBC grafa o sobrenome como "Neubaer" (erro do registro) e o
%% Crossref registra o título traduzido "Interactive trace clustering".
@inproceedings{neubauer2019agrupamento,
  author    = {Neubauer, Thais Rodrigues and Fantinato, Marcelo and Peres, Sarajane Marques},
  title     = {Agrupamento interativo aplicado {\`a} minera{\c{c}}{\~a}o de processos},
  booktitle = {Anais Estendidos do XV Simp{\'o}sio Brasileiro de Sistemas de
               Informa{\c{c}}{\~a}o (SBSI 2019) -- Workshop de Teses e Disserta{\c{c}}{\~o}es
               em Sistemas de Informa{\c{c}}{\~a}o},
  publisher = {Sociedade Brasileira de Computa{\c{c}}{\~a}o},
  address   = {Porto Alegre},
  pages     = {45--48},
  year      = {2019},
  doi       = {10.5753/sbsi.2019.7438},
  url       = {https://sol.sbc.org.br/index.php/sbsi_estendido/article/view/7438}
}

@inproceedings{neubauer2021visualization,
  author    = {Neubauer, Thais Rodrigues and Pamponet Sobrinho, Glaucia and
               Fantinato, Marcelo and Peres, Sarajane Marques},
  title     = {Visualization for enabling human-in-the-loop in trace clustering-based
               process mining tasks},
  booktitle = {2021 {IEEE} International Conference on Big Data (Big Data)},
  publisher = {IEEE},
  address   = {Orlando, FL, USA},
  pages     = {3548--3556},
  year      = {2021},
  doi       = {10.1109/BigData52589.2021.9671985}
}

%% Preprint, sem veículo declarado. Citar apenas em trabalhos futuros.
@misc{yamate2025textsql,
  author       = {Yamate, Bruno Yui and Neubauer, Thais Rodrigues and
                  Fantinato, Marcelo and Peres, Sarajane Marques},
  title        = {Text-to-{SQL} oriented to the process mining domain:
                  a {PT-EN} dataset for query translation},
  year         = {2025},
  howpublished = {arXiv preprint},
  note         = {arXiv:2509.09684},
  url          = {https://arxiv.org/abs/2509.09684}
}

%% ---- SEI: estudos ----

@article{soriano2025sei,
  author  = {Soriano, Fabiano and Dias, Carina Santos and
             Valeriano, Mariangela Oliveira Gomes and Santos, Matheus Silva},
  title   = {Sistema {Eletr{\^o}nico} de {Informa{\c{c}}{\~o}es} ({SEI}) na
             administra{\c{c}}{\~a}o p{\'u}blica: avan{\c{c}}os, desafios e perspectivas
             a partir de uma revis{\~a}o sistem{\'a}tica da literatura},
  journal = {P2P e Inova{\c{c}}{\~a}o},
  volume  = {12},
  number  = {1},
  pages   = {e-7637},
  year    = {2025},
  doi     = {10.21728/p2p.2025v12n1e-7637},
  url     = {https://revista.ibict.br/p2p/article/view/7637}
}

@article{fulton2018adocao,
  author  = {Fulton, Denise de Carvalho Pires and Farias, Josivania Silva and
             Alfinito, Solange and de Almeida, Juliana Pascualote Lemos},
  title   = {Ado{\c{c}}{\~a}o do Sistema Eletr{\^o}nico de Informa{\c{c}}{\~o}es ({SEI})
             pelo {Minist{\'e}rio da Justi{\c{c}}a}: uma avalia{\c{c}}{\~a}o na {\'o}tica
             de usu{\'a}rios},
  journal = {Revista do Servi{\c{c}}o P{\'u}blico},
  volume  = {69},
  number  = {4},
  pages   = {1015--1036},
  year    = {2018},
  doi     = {10.21874/rsp.v69i4.3624},
  url     = {https://revista.enap.gov.br/index.php/RSP/article/view/3624}
}

@article{silva2020gestao,
  author  = {Silva, Leandro Gon{\c{c}}alves and de Souza, Ros{\'a}lia Beber},
  title   = {A gest{\~a}o de documentos e tramita{\c{c}}{\~a}o de processos na
             administra{\c{c}}{\~a}o p{\'u}blica, com a utiliza{\c{c}}{\~a}o do Sistema
             Eletr{\^o}nico de Informa{\c{c}}{\~o}es -- {SEI}: um estudo de caso na
             {Universidade Federal de Vi{\c{c}}osa}},
  journal = {M{\'u}ltiplos Olhares em Ci{\^e}ncia da Informa{\c{c}}{\~a}o},
  volume  = {10},
  year    = {2020},
  doi     = {10.35699/2237-6658.2020.25838},
  url     = {https://periodicos.ufmg.br/index.php/moci/article/view/25838}
}

@mastersthesis{nowak2018utilizacao,
  author  = {Nowak, Mary Anne Muraski},
  title   = {A utiliza{\c{c}}{\~a}o do Sistema Eletr{\^o}nico de Informa{\c{c}}{\~o}es --
             {SEI} no servi{\c{c}}o p{\'u}blico: inova{\c{c}}{\~a}o tecnol{\'o}gica para
             melhoria na efici{\^e}ncia administrativa e no conhecimento institucional},
  school  = {Universidade Federal do Paran{\'a}, Programa de P{\'o}s-Gradua{\c{c}}{\~a}o
             em Desenvolvimento Econ{\^o}mico},
  address = {Curitiba},
  year    = {2018},
  type    = {Disserta{\c{c}}{\~a}o (Mestrado)},
  url     = {https://hdl.handle.net/1884/55992}
}

@article{baptista2023processo,
  author  = {Baptista, Patr{\'i}cia Ferreira and Antoun Netto, Leonardo Silveira},
  title   = {O processo administrativo eletr{\^o}nico e sua disciplina no direito
             administrativo brasileiro: entre novos desafios e velhos problemas},
  journal = {Revista de Direito Administrativo},
  volume  = {282},
  number  = {3},
  pages   = {85--110},
  year    = {2023},
  doi     = {10.12660/rda.v282.2023.90156},
  url     = {https://periodicos.fgv.br/rda/article/view/90156}
}

%% ---- Base normativa e documentação oficial do processo eletrônico ----

%% Ementa e data verificadas na página oficial do CONARQ. ARTICULADO NÃO LIDO --
%% não citar artigo específico sem abrir o texto no Planalto.
@misc{brasil2015decreto8539,
  author       = {{Brasil}},
  title        = {Decreto n\textordmasculine{} 8.539, de 8 de outubro de 2015. Disp{\~o}e
                  sobre o uso do meio eletr{\^o}nico para a realiza{\c{c}}{\~a}o do processo
                  administrativo no {\^a}mbito dos {\'o}rg{\~a}os e das entidades da
                  administra{\c{c}}{\~a}o p{\'u}blica federal direta, aut{\'a}rquica e fundacional},
  year         = {2015},
  howpublished = {Di\'ario Oficial da Uni\~ao, Bras\'ilia, DF},
  url          = {https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/decreto/d8539.htm},
  urldate      = {2026-08-04}
}

%% Ementa e data verificadas no portal oficial do Governo Digital. ARTICULADO NÃO LIDO.
@misc{brasil2021govdigital,
  author       = {{Brasil}},
  title        = {Lei n\textordmasculine{} 14.129, de 29 de mar{\c{c}}o de 2021. Disp{\~o}e
                  sobre princ{\'i}pios, regras e instrumentos para o Governo Digital e para
                  o aumento da efici{\^e}ncia p{\'u}blica},
  year         = {2021},
  howpublished = {Di\'ario Oficial da Uni\~ao, Bras\'ilia, DF},
  note         = {Altera as Leis n\textordmasculine{} 7.116/1983, 12.527/2011 (LAI),
                  12.682/2012 e 13.460/2017},
  url          = {http://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/L14129.htm},
  urldate      = {2026-08-04}
}

@misc{brasil2024sei,
  author       = {{Brasil, Minist{\'e}rio da Gest{\~a}o e da Inova{\c{c}}{\~a}o em
                  Servi{\c{c}}os P{\'u}blicos}},
  title        = {Sistema Eletr{\^o}nico de Informa{\c{c}}{\~o}es -- {SEI}},
  howpublished = {Portal Servi{\c{c}}os Compartilhados},
  note         = {Sistema desenvolvido pelo Tribunal Regional Federal da 4\textordfeminine{}
                  Regi{\~a}o e cedido gratuitamente a institui{\c{c}}{\~o}es p{\'u}blicas
                  desde 2013},
  url          = {https://www.gov.br/servicoscompartilhados/pt-br/assuntos/gestao-documental/sistema-eletronico-de-informacoes-sei},
  urldate      = {2026-08-04}
}

@misc{brasil2024pen,
  author       = {{Brasil, Minist{\'e}rio da Gest{\~a}o e da Inova{\c{c}}{\~a}o em
                  Servi{\c{c}}os P{\'u}blicos}},
  title        = {Processo Eletr{\^o}nico Nacional ({PEN})},
  howpublished = {Portal gov.br},
  url          = {https://www.gov.br/gestao/pt-br/assuntos/gestaoeinovacao/informacoes-sistemas-e-servicos-de-gestao/processo-eletronico-nacional/conteudo/processo-eletronico-nacional-pen},
  urldate      = {2026-08-04}
}

%% ---- Jurimetria e dados processuais ----

%% 2ª edição verificada no LexML. Existe 3ª ed. (2024) com título alterado,
%% NÃO verificada em fonte catalográfica.
@book{nunes2019jurimetria,
  author    = {Nunes, Marcelo Guedes},
  title     = {Jurimetria: como a estat{\'i}stica pode reinventar o direito},
  edition   = {2},
  publisher = {Revista dos Tribunais},
  address   = {S{\~a}o Paulo},
  pages     = {190},
  year      = {2019},
  isbn      = {978-85-5321-999-5},
  url       = {https://www.lexml.gov.br/urn/urn:lex:br:rede.virtual.bibliotecas:livro:2019;001163005}
}

@techreport{cnj2025justicaemnumeros,
  author      = {{Conselho Nacional de Justi{\c{c}}a}},
  title       = {Justi{\c{c}}a em n{\'u}meros 2025},
  institution = {Conselho Nacional de Justi{\c{c}}a},
  address     = {Bras{\'i}lia},
  year        = {2025},
  pages       = {650},
  note        = {S{\'e}rie Relat{\'o}rios e dados estat{\'i}sticos do Poder Judici{\'a}rio.
                 ISBN 978-65-5972-195-5},
  url         = {https://bibliotecadigital.cnj.jus.br/xmlui/handle/123456789/1060},
  urldate     = {2026-08-04}
}

@misc{cnj2020resolucao331,
  author       = {{Conselho Nacional de Justi{\c{c}}a}},
  title        = {Resolu{\c{c}}{\~a}o n\textordmasculine{} 331, de 20 de agosto de 2020.
                  Institui a Base Nacional de Dados do Poder Judici{\'a}rio -- {DataJud}},
  year         = {2020},
  howpublished = {DJe/CNJ, n. 274, 25 ago. 2020, p. 2--4},
  url          = {https://atos.cnj.jus.br/atos/detalhar/3428},
  urldate      = {2026-08-04}
}

%% Título conforme a ficha catalográfica (difere do título de capa).
@techreport{tcu2020referencial,
  author      = {{Brasil, Tribunal de Contas da Uni{\~a}o}},
  title       = {Referencial b{\'a}sico de governan{\c{c}}a aplic{\'a}vel a organiza{\c{c}}{\~o}es
                 p{\'u}blicas e outros entes jurisdicionados ao {TCU}},
  institution = {Tribunal de Contas da Uni{\~a}o, Secretaria de Controle Externo da
                 Administra{\c{c}}{\~a}o do Estado},
  address     = {Bras{\'i}lia},
  edition     = {3},
  year        = {2020},
  pages       = {242},
  url         = {https://portal.tcu.gov.br/referencial-basico-de-governanca-organizacional.htm},
  urldate     = {2026-08-04}
}
```

---

## Prioridade sugerida (se só couberem cinco)

1. `araujo2025trace` — §rw-clustering. Sem ele o capítulo tem um buraco defensável como falha.
2. `soriano2025sei` — cenário. Fecha "o SEI já foi estudado?".
3. `dinkowski2025fifteen` — §rw-privacy-public. Fecha "o que se fez no Brasil?".
4. `baptista2023processo` — §rw-legal. Doutrina brasileira sobre o objeto.
5. `brasil2015decreto8539` — cenário. Base normativa do processo eletrônico.
