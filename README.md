# GovERP AI Lab

Laboratório local demonstrativo de apoio a serviços municipais, análise fiscal, auditoria assistida e comparação de indicadores. A aplicação usa dados financeiros artificiais; os nomes dos municípios são identidades públicas reais do Paraná. Não é um ERP operacional, não substitui parecer técnico e não acessa dados privados de prefeituras.

## Executar localmente

Requisitos: Windows com PowerShell, Python 3.12+, Node.js 20+, Docker Desktop com Compose, e Ollama local (opcional para explicações por IA). O banco fica em um volume Docker próprio, a API e a interface só escutam em `127.0.0.1`, e chamadas ao modelo usam `http://127.0.0.1:11434`.

```powershell
.\scripts\bootstrap.ps1
.\scripts\start.ps1
```

Abra `http://127.0.0.1:5173`. A senha das contas demonstrativas é `Local-Demo-Only-2026!`; troque-a antes de compartilhar a máquina ou qualquer captura de tela. O gestor está autorizado apenas para Curitiba; auditor e cidadão são contas demonstrativas multi-município com acesso restringido por perfil. A conta cidadão não vê dados financeiros.

O Ollama é opcional. Para habilitar texto explicativo local, instale o Ollama e baixe `qwen3:4b` por conta própria. Sem modelo disponível, os valores e conclusões determinísticas continuam funcionando e a API sinaliza a indisponibilidade do modelo. Não há chamadas a serviço de IA pago.

Para encerrar a API/interface pelos PIDs verificados pelo projeto, execute `.\scripts\stop.ps1`; o PostgreSQL pode ser parado com `docker compose stop database`. Os logs de execução ficam em `.runtime/`.

## Dados e dimensões

`python -m gov_erp.seed` gera 10 municípios funcionais: 2 de porte grande, 4 intermediários e 4 pequenos, com 148.000 lançamentos e 1.120 documentos sintéticos. Valores financeiros são gerados por chave determinística e podem ser recriados de forma idempotente. Os documentos oficiais de Curitiba são trechos de referência, têm URL e hash do conteúdo capturado, e estão explicitamente marcados como não verificados quanto à vigência.

Para o cenário isolado de 100 municípios (2.000 lançamentos e 30 documentos por município), use:

```powershell
.\scripts\benchmark-100.ps1
```

O script cria `goverp_benchmark100`, consulta o catálogo público do IBGE para obter os municípios do Paraná e grava 200.000 lançamentos e 3.000 documentos sem alterar o banco funcional `goverp`. O payload e o manifesto do snapshot IBGE ficam em `data/snapshots/`; a medição de duração e tamanho PostgreSQL fica em `data/benchmark-100-report.json`. Ela não equivale a uma prova de produção ou a 100 organizações simultâneas.

Medição nesta máquina em 2026-10-07: o seed de 100 municípios levou 34,85 s e ocupou 74,62 MiB ao final da carga (74,87 MiB após o smoke test da API); a base funcional de 10 municípios tem 55,36 MiB. A consulta SQL de relatório, aquecida, teve média de 1,29 ms na amostra de 100 e 5,90 ms na amostra de 10, pois Curitiba tinha 2.000 linhas no cenário de teste e 50.000 no funcional. São medições locais de uma máquina e de uma consulta; não representam carga simultânea ou SLO de produção.

## Arquitetura

- React, TypeScript e Vite para a interface local.
- FastAPI para sessão, permissões, relatórios, busca documental e auditoria.
- PostgreSQL 18 com extensão pgvector, migrations Alembic, controle por linha (RLS) e conexão da aplicação com papel separado do proprietário.
- LangGraph com checkpoints persistidos no PostgreSQL para coordenar intenções de consulta. O grafo não executa SQL arbitrário nem concede ações ao modelo.
- Cálculos fiscais e achados de possível duplicidade são determinísticos. O LLM local pode apenas explicar resultados estruturados, nunca altera os valores calculados.
- A busca documental usa full-text search em português. A coluna vetorial está preparada, mas embeddings e busca semântica vetorial não estão implementados nesta versão.
- A aba Competitividade exibe notas e posições publicadas pelo CLP para a edição 2026, com pilar, fonte, hash e população. Apenas 8 dos 10 municípios funcionais aparecem no recorte CLP, que cobre municípios acima de 80 mil habitantes; dois sem linha no ranking são mostrados como indisponíveis. A aplicação não recalcula as notas.

## Limites de uso e segurança

- Toda linha do ERP, documento de demonstração, resposta de IA e resultado do seed é sintético. Nunca importe dados pessoais, fiscais ou bancários reais nesta demonstração.
- A comparação de despesas considera apenas pagamentos com estado `paid`; empenhado, liquidado, cancelado e pago são conceitos separados. Percentual de variação não é calculado quando o período anterior é zero.
- A regra de auditoria aponta duplicidades potenciais; não classifica fraude. Um auditor humano deve decidir cada caso.
- Fontes públicas são evidência contextual, não confirmação de vigência ou aconselhamento jurídico. Confira o texto oficial vigente antes de uso administrativo.
- Hashes identificam os trechos armazenados, mas não autenticam a página de origem.
- A atualização do ranking CLP é manual pelo comando `python -m gov_erp.rankings`; atualização incremental automatizada, multiusuário federado, rate limit, trilha imutável, recuperação de desastre e implantação externa não estão implementados nesta versão.
- Credenciais, chave de sessão, dados e logs locais ficam fora do Git. As contas e senha de demonstração são conhecidas.

## Desenvolvimento

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format --check src tests
npm --prefix frontend run build
```

Os testes automatizados cobrem cálculos, auditoria determinística, tokens de sessão e geração sintética. Testes de integração contra PostgreSQL, avaliação humana das respostas e medições de carga precisam ser executados separadamente antes de declarar esses aspectos validados.
