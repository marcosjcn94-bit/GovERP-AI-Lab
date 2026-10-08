# OTIMIZA: implementação e evidências

Executado em 2026-10-07 na branch `codex/gov-erp-ai-lab`. Escopo aprovado: projeto e instruções globais; sem publicação externa.

## Implementado

- Python 3.12 com `uv.lock`, Node 24 com `package-lock.json`; setup usa `uv sync --locked` e `npm ci`.
- Bootstrap espera o healthcheck PostgreSQL e preserva `.env`. Ranking CLP passou a importação manual.
- Benchmark de 100 mede exclusivamente `gov_erp.seed`, incluindo consulta IBGE. Não foi repetido nesta alteração; a duração histórica de 34,85 s incluía CLP e não deve ser comparada diretamente.
- `scripts/check.ps1`: lint, formatação, testes e build; relatório sanitizado de duração/código de saída.
- E2E com Chromium, API/interface reais e PostgreSQL temporário separado; fallback determinístico sem chamada Qwen. Limpeza em `finally`, com código de saída verificado.
- CI para pull requests/execução manual: actions fixadas por SHA, permissões de leitura, caches de dependências, timeout, cancelamento de execução obsoleta e relatórios por 7 dias.
- Dependabot semanal para uv, npm e actions; atualizações major separadas.
- Guia copiado para `C:/Users/mjcn9/.codex/OTIMIZA.md`, hash idêntico ao original. Referência acrescentada ao AGENTS global; conteúdo anterior preservado.
- Backup global: `C:/Users/mjcn9/.codex/backups/AGENTS.before-otimiza-20261007-161526.md`.
- `start.ps1 -NoBrowser` permite inicialização sem abrir janela do navegador.

## Validação executada

| Verificação | Resultado |
|---|---|
| Ruff lint e format | Aprovados |
| pytest | 11 aprovados; 0,81 s internos ao pytest; 4,414 s no comando completo via uv |
| Build TypeScript/Vite | Aprovado; 10,578 s no comando completo |
| E2E final | 3 aprovados; 25,1 s Playwright; 69,524 s incluindo banco, migração, seed e limpeza |
| Limpeza E2E | Código 0; container e rede temporários removidos |
| Bootstrap repetido | 2 execuções aprovadas: 24,323 s e 19,258 s |
| Preservação | Hash do .env inalterado; contagens iguais antes/depois |
| Banco funcional | 10 municípios, 148.000 lançamentos, 1.120 documentos, 8 referências CLP |
| npm audit durante npm ci | 0 vulnerabilidades reportadas; não constitui auditoria completa de segurança |
| Sintaxe PowerShell, YAML e migrações Ruff | Aprovadas |
| Smoke local após reinício | PostgreSQL ready; interface HTTP 200 |
| Revisão independente estática | Sem bloqueadores; codificação README corrigida |

Fluxos E2E: gestor consulta e encerra sessão; cidadão recebe HTTP 403 e não vê tabela financeira; gestor não entra em município fora de seu escopo.

## Falhas e correções registradas

1. E2E inicial falhou em PostgreSQL vazio: primeira migração criava todos os modelos atuais, inclusive tabela CLP da revisão seguinte. A revisão inicial passou a limitar suas tabelas, corrigindo `DuplicateTable`. Duas execuções E2E posteriores passaram. Duração total da tentativa falha: não medida.
2. Primeiro bootstrap de validação falhou na checagem Node: PowerShell Windows removia aspas do argumento JavaScript. Substituído por `node --version` e parsing PowerShell; duas execuções posteriores passaram. Duração da tentativa falha: não medida.
3. Revisão identificou acentos convertidos em `?` na documentação escrita por pipeline. Corrigida escrita UTF-8; texto conferido após gravação.

Não houve chamadas reais ao modelo nesta suíte. Retries locais Playwright: 0; CI permite 1 e mantém evidência de falha. Custo financeiro conciliado da execução e custo por tarefa aceita: não medidos; não foram contratados serviços pagos.

## Evidências locais

- `.runtime/check-report.json`
- `.runtime/e2e-report.json`
- `.runtime/bootstrap-validation.json`
- `.runtime/preservation-report.json`
- `.runtime/smoke-report.json`
- `.runtime/playwright-report/index.html`

A avaliação anterior do Qwen e os arquivos de vídeo existentes em `artifacts/` foram preservados. Esta suíte não reavalia qualidade/latência do Qwen.

## Limites e pendências

- Repositório sem remote: workflow e Dependabot configurados, execução no GitHub não comprovada.
- Referência global disponível e arquivos verificados nesta sessão; carregamento efetivo em uma nova sessão requer reinício e leitura pelo Codex.
- Revisão visual humana, carga simultânea, produção/deploy e equivalência entre versões de modelos não foram validados nesta tarefa.
- Dependências e navegadores baixados localmente; não houve push, publicação ou novo commit.
