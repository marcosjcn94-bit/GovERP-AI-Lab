# GovERP AI Lab

Laboratório local demonstrativo de apoio a serviços municipais, análise fiscal, auditoria assistida e comparação de indicadores. A aplicação usa dados financeiros artificiais; os nomes dos municípios são identidades públicas reais do Paraná. Não é um ERP operacional, não substitui parecer técnico e não acessa dados privados de prefeituras.

## Executar localmente

Requisitos: Windows com PowerShell, uv 0.12.21, Python 3.12 gerenciado pelo uv, Node.js 24 LTS, Docker Desktop com Compose, e Ollama local (opcional para explicações por IA). O banco fica em um volume Docker próprio, a API e a interface só escutam em `127.0.0.1`, e chamadas ao modelo usam `http://127.0.0.1:11434`.

```powershell
.\scripts\bootstrap.ps1
.\scripts\start.ps1
```

O bootstrap usa `uv.lock` e `npm ci`, espera o PostgreSQL ficar pronto e preserva o `.env` existente. Não baixa o ranking CLP automaticamente.

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

Medição nesta máquina em 2026-10-07: a carga histórica de 100 municípios, incluindo importação CLP, levou 34,85 s e ocupou 74,62 MiB ao final da carga (74,87 MiB após o smoke test da API); a base funcional de 10 municípios tem 55,36 MiB. A consulta SQL de relatório, aquecida, teve média de 1,29 ms na amostra de 100 e 5,90 ms na amostra de 10, pois Curitiba tinha 2.000 linhas no cenário de teste e 50.000 no funcional. O script atualizado mede apenas `gov_erp.seed` (incluindo consulta IBGE); essa nova medição não foi executada nesta alteração. São medições locais de uma máquina e de uma consulta; não representam carga simultânea ou SLO de produção.

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

## Desenvolvimento e validação

```powershell
.\scripts\check.ps1
.\scripts\e2e.ps1 -InstallBrowser
```

`check.ps1` executa Ruff, formatação, pytest e build, sem exigir Docker, e registra duração/código de saída em `.runtime/check-report.json`.

`e2e.ps1` cria PostgreSQL temporário em `127.0.0.1:5441`, migra e gera dados sintéticos; Playwright inicia API em `8001` e interface em `5174`. Valida consulta do gestor com fallback determinístico, logout, recusa ao cidadão e município não autorizado. O banco temporário é removido ao final, inclusive após falha; não usa o banco funcional nem chama Qwen. Após instalar Chromium uma vez, use o comando sem `-InstallBrowser`. Relatório, duração e traces de falha ficam em `.runtime/e2e-report.json`, `.runtime/playwright-report` e `.runtime/playwright-results`.

Os testes pytest cobrem cálculos, auditoria determinística, tokens de sessão e geração sintética. E2E cobre os fluxos descritos com PostgreSQL real; qualidade do Qwen, carga simultânea e revisão humana continuam sendo avaliações separadas.

O workflow `.github/workflows/ci.yml` reutiliza esses comandos em pull requests ou execução manual, com actions por SHA, permissões de leitura e retenção de relatórios de 7 dias. Dependabot propõe atualizações semanais. O repositório local não possui remote: CI e Dependabot estão configurados, mas ainda não foram executados no GitHub.

Para atualizar a referência pública CLP explicitamente:

```powershell
uv run --locked --extra dev --managed-python python -m gov_erp.rankings
```

Esse comando acessa a fonte pública. Consulte `PLANO.md` e `artifacts/otimiza-validation.md` para o estado e as evidências desta melhoria.

## Tracing LangSmith e observabilidade local

### Onde guardar a chave LangSmith

Guarde `LANGSMITH_API_KEY` somente no `.env` local, na raiz do projeto. O arquivo já é ignorado pelo Git. Nunca cole a chave em `langgraph.json`, no frontend, em comandos, capturas ou `ADR.md`. O `.env.example` contém apenas instruções e parâmetros não secretos. `scripts/start.ps1` e `scripts/studio.ps1` leem do `.env` somente as variáveis LangSmith necessárias e as entregam ao processo filho sem imprimi-las.

O projeto configura o endpoint US `https://api.smith.langchain.com` e `goverp-ai-lab-local`. Entradas, saídas e metadados ficam ocultos antes do envio (`LANGSMITH_HIDE_INPUTS`, `LANGSMITH_HIDE_OUTPUTS` e `LANGSMITH_HIDE_METADATA`). A chave autoriza a API; abrir a interface oficial do LangSmith pode exigir login no navegador, que é uma autenticação separada. Este tracing é opcional e usa a rede do LangSmith; a IA de explicação continua local no Ollama.

### OTel, métricas, logs e traces no computador

A instrumentação OpenTelemetry da FastAPI, SQLAlchemy e HTTPX fica desligada por padrão. Com Docker ativo, os passos para ligar são:

```powershell
.\scripts\observability.ps1 up
.\scripts\start.ps1 -EnableObservability
```

Abra Grafana em `http://127.0.0.1:3000` (senha aleatória criada em `.env`, usuário `admin`); o dashboard **GovERP AI Lab · ambiente local** mostra requisições, latências p50/p95, fallback do modelo e achados demonstrativos. Fontes Prometheus, Tempo e Loki já vêm provisionadas. Prometheus, Tempo e Loki também respondem em portas locais `9090`, `3200` e `3100`; o Prometheus verifica `/health/ready` pela rede interna do Docker. Alertas cobrem indisponibilidade por 2 min, 5xx acima de 5% com pelo menos 20 requisições, p95 acima de 30 s com amostra mínima e fallback acima de 50% com ao menos 10 explicações.

As portas publicadas são apenas loopback. Prometheus retém até 7 dias/480 MB; Tempo e Loki retêm por 7 dias. Armazenamentos de Prometheus (512 MB), Tempo (512 MB), Loki (256 MB) e Grafana (128 MB) são temporários e limitados: param de acumular no disco do projeto, mas os dados se perdem ao recriar/parar os respectivos containers. Rótulos de métricas não incluem município, usuário, pergunta ou ID da execução. Logs de requisição incluem somente ID, rota, método, status e duração. A instrumentação não grava parâmetros SQL, corpo HTTP ou cabeçalhos de autenticação.

Para desativar e parar a stack: `.\scripts\observability.ps1 down`. Para consultar traces sanitizados do grafo, use o projeto `goverp-ai-lab-local` na interface do LangSmith. O trace da chamada do roteador não significa que o Studio exponha etapas de negócio adicionais; cálculos, busca, autorização e auditoria continuam executados pela API.


### Evid?ncia da execu??o local ? 2026-10-07

Oito testes Playwright, 13 testes Python e o build de produ??o passaram. Um smoke test confirmou m?tricas Prometheus, logs Loki e traces Tempo. O PostgreSQL tempor?rio foi reiniciado e a API respondeu antes e depois. O projeto LangSmith recebeu traces com entradas, sa?das e metadados da aplica??o ocultos. Relat?rios sanitizados ficam em `.runtime/`.

O benchmark de 100 munic?pios foi atualizado: 200.000 transa??es, 3.000 documentos, 75,04 MiB e 2,52 s para uma execu??o idempotente do seed. Esse tempo cobre somente `gov_erp.seed` (consulta IBGE, gera??o sint?tica e inserts), exclui migrations e CLP e n?o ? compar?vel diretamente com a medi??o hist?rica de carga completa. O script preserva no relat?rio as medi??es funcionais anteriores.
