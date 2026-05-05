```
 ██████╗  █████╗ ██████╗ ██╗███╗   ███╗██████╗  ██████╗
██╔════╝ ██╔══██╗██╔══██╗██║████╗ ████║██╔══██╗██╔═══██╗
██║  ███╗███████║██████╔╝██║██╔████╔██║██████╔╝██║   ██║
██║   ██║██╔══██║██╔══██╗██║██║╚██╔╝██║██╔═══╝ ██║   ██║
╚██████╔╝██║  ██║██║  ██║██║██║ ╚═╝ ██║██║     ╚██████╔╝
 ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚═╝      ╚═════╝
```

Garimpo é uma ferramenta forense de linha de comando para recuperar arquivos apagados ou perdidos em imagens brutas de disco (`.img`, `.dd`, `.raw`, `.iso`). Ela procura assinaturas conhecidas de formatos de arquivo, extrai candidatos e gera relatórios com offsets, tamanhos e hashes.

## Sumário

- [O que é o Garimpo?](#o-que-é-o-garimpo)
- [Recursos](#recursos)
- [Formatos suportados](#formatos-suportados)
- [Arquitetura](#arquitetura)
- [Instalação](#instalação)
- [Primeiros passos](#primeiros-passos)
- [Interface web](#interface-web)
- [Exemplos de uso](#exemplos-de-uso)
- [Estrutura de saída](#estrutura-de-saída)
- [Modos de varredura](#modos-de-varredura)
- [Sistema de plugins](#sistema-de-plugins)
- [Relatórios](#relatórios)
- [Configuração](#configuração)
- [Testes](#testes)
- [Limitações](#limitações)
- [Uso ético e legal](#uso-ético-e-legal)

## O que é o Garimpo?

O Garimpo recupera arquivos sem depender de um sistema de arquivos montado ou íntegro. Em vez disso, ele percorre a imagem byte a byte, encontra cabeçalhos e rodapés conhecidos e grava os dados candidatos em uma pasta de saída.

É útil para investigação forense, resposta a incidentes, estudos, desafios de CTF e recuperação controlada de dados apagados acidentalmente.


## Recursos

- Operação somente leitura: a imagem de origem não é modificada.
- Varredura por blocos, com uso de memória baixo e previsível.
- Plugins nativos para JPEG, PNG, PDF, ZIP, DOCX, XLSX, PPTX, GIF, BMP, MP4 e TXT.
- Validação estrutural por formato.
- Supressão de duplicados por SHA-256.
- Cálculo de MD5, SHA-1 e SHA-256.
- Relatórios JSON e CSV com evidências forenses.
- Modos `fast` e `deep`.
- Barra de progresso com `tqdm` e saída rica com `rich`.
- Arquitetura de plugins simples de estender.
- Compatível com Linux e Windows usando Python 3.10+.

## Formatos suportados

| Formato | Extensão | Detecção | Fechamento |
|---|---:|---|---|
| JPEG | `.jpg` | SOI + marcadores APP | EOI `FF D9` |
| PNG | `.png` | Assinatura PNG + IHDR | Bloco IEND |
| PDF | `.pdf` | Cabeçalho `%PDF-` | Marcador `%%EOF` |
| ZIP | `.zip` | Local File Header | End of Central Directory |
| DOCX | `.docx` | ZIP + `word/document.xml` | End of Central Directory |
| XLSX | `.xlsx` | ZIP + `xl/workbook.xml` | End of Central Directory |
| PPTX | `.pptx` | ZIP + `ppt/presentation.xml` | End of Central Directory |
| GIF | `.gif` | GIF87a / GIF89a | Trailer `3B` |
| BMP | `.bmp` | Assinatura `BM` + tamanho no cabeçalho | Delimitado por tamanho |
| MP4 | `.mp4` | Caixa `ftyp` no início | Delimitado por tamanho |
| TXT | `.txt` | Proporção de bytes imprimíveis | Heurístico, apenas em `deep` |

## Arquitetura

```text
garimpo/
├── cli.py              Entrada de linha de comando com Click
├── config.py           Dataclass ScanConfig
├── scanner.py          Motor de varredura por blocos
├── signatures.py       Base FileSignature e resultado CarveResult
├── plugins/            Plugins de formatos suportados
├── recovery.py         Orquestra varredura, filtros e gravação
├── validators.py       Deduplicação e filtros de confiança
├── reports.py          Relatórios JSON e CSV
├── hashing.py          Cálculo de MD5, SHA-1 e SHA-256
├── logging_config.py   Configuração de logs com Rich
├── utils.py            Utilidades multiplataforma
└── __init__.py
```

Fluxo principal:

```text
Argumentos da CLI → ScanConfig
                 ↓
          RecoveryEngine.run()
                 ↓
          Scanner.scan() → CarveResult
                 ↓
          apply_filters()
                 ↓
          _write_candidate()
                 ↓
          write_reports()
```

## Instalação

```bash
git clone https://github.com/hssnsm/f-garimpo.git
cd garimpo
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
garimpo version
```

No Windows PowerShell:

```powershell
git clone https://github.com/hssnsm/f-garimpo.git
cd garimpo
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
garimpo version
```

Para desenvolvimento:

```bash
pip install -e ".[dev]"
```

## Primeiros passos

```bash
python samples/create_samples.py
garimpo scan samples/sample_basic.img
garimpo list-plugins
```

Por padrão, os arquivos recuperados e os relatórios são gravados em `garimpo_output/`.

## Interface web

Além do modo de terminal, o projeto inclui uma interface web local para enviar imagens de disco, acompanhar o processamento e baixar os resultados recuperados.

Para iniciar:

```bash
garimpo web
```

Ou definindo host, porta e diretório de dados:

```bash
garimpo web --host 127.0.0.1 --port 5000 --data-dir garimpo_web_data
```

A interface permite:

- enviar imagens `.img`, `.dd`, `.raw`, `.iso` e `.bin`;
- acompanhar a análise em tempo real;
- visualizar arquivos recuperados;
- baixar relatórios JSON/CSV;
- baixar um pacote ZIP com todos os resultados da sessão.

## Exemplos de uso

```bash
garimpo scan /caminho/para/disco.img
garimpo scan disco.img --formats jpeg,png
garimpo scan disco.img --mode deep
garimpo scan disco.img --output /evidencias/caso-001/recuperados/
garimpo scan disco.img --max-size 10MB
garimpo scan disco.img --max-files 50
garimpo scan disco.img --report json
garimpo scan disco.img --no-validate --no-hash
garimpo scan disco.img --verbose --log-file scan_debug.log
```

## Estrutura de saída

```text
garimpo_output/
├── imagem_jpeg/
│   └── carved_000000.jpg
├── imagem_png/
│   └── carved_000000.png
├── documento_pdf/
│   └── carved_000000.pdf
├── reports/
│   ├── report.json
│   └── report.csv
└── garimpo_scan.log
```

## Modos de varredura

| Modo | Comportamento |
|---|---|
| `fast` | Padrão. Ignora resultados corrompidos. É mais preciso e rápido. |
| `deep` | Mantém achados parciais ou corrompidos e ativa a busca heurística por texto. Gera mais falsos positivos. |

## Sistema de plugins

Cada plugin herda de `FileSignature` e declara nome, extensão, MIME type, cabeçalhos, rodapés, limites de tamanho e um método `validate()`. Para adicionar um formato, crie um arquivo em `src/garimpo/plugins/` e registre a classe em `plugins/__init__.py`.

## Relatórios

Quando `--report` não é `none`, o Garimpo cria relatórios em `reports/`:

- `report.json`: relatório completo, com resumo e lista de evidências.
- `report.csv`: visão tabular para planilhas e auditoria.

Campos principais: índice, tipo, extensão, offsets inicial/final, tamanho, status, confiança da validação, hashes e caminho de saída.

## Configuração

| Opção | Padrão | Descrição |
|---|---:|---|
| `IMAGE` | obrigatório | Caminho da imagem bruta |
| `-o / --output` | `garimpo_output` | Diretório de saída |
| `-f / --formats` | todos | Lista de formatos separados por vírgula |
| `-m / --mode` | `fast` | Modo de varredura |
| `--max-size` | `100MB` | Tamanho máximo por arquivo |
| `--chunk-size` | `64KB` | Tamanho do bloco de leitura |
| `--report` | `all` | `json`, `csv`, `all` ou `none` |
| `--no-validate` | desligado | Desativa validação estrutural |
| `--no-hash` | desligado | Pula cálculo de hashes |
| `--no-dedup` | desligado | Mantém duplicados |
| `--max-files` | `0` | Limite de arquivos recuperados; `0` não limita |
| `--log-level` | `INFO` | Verbosidade dos logs |
| `--log-file` | automático | Caminho do log completo |

## Testes

```bash
pip install -e ".[dev]"
pytest
pytest tests/test_scanner.py -v
```

## Limitações

- Arquivos fragmentados podem sair truncados no primeiro intervalo.
- Partições criptografadas precisam ser descriptografadas antes da análise.
- Dados sobrescritos não podem ser recuperados.
- Nomes de arquivo, datas e pastas originais não são reconstruídos.
- MP4/MOV recuperados podem exigir reparo externo, por exemplo com `ffmpeg`.
- A detecção de TXT é heurística e pode gerar falsos positivos.

## Uso ético e legal

Use somente em imagens ou dispositivos que você possui ou tem autorização expressa para examinar.
