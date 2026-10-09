# GovERP AI Lab

Laboratório local de relatórios verificáveis, conhecimento municipal com fontes e
revisão de possíveis duplicidades. ERP e documentos demonstrativos usam dados
sintéticos; nomes dos municípios, referências oficiais e ranking CLP são públicos
reais e identificados separadamente. Revisão administrativa permanece humana.

## Executar

Requisitos: Windows/PowerShell, uv 0.12.21, Python 3.12 gerenciado pelo uv,
Node 24 e Docker Desktop com Compose. Ollama é opcional.

~~~powershell
.\scripts\bootstrap.ps1
.\scripts\start.ps1
~~~

Abra http://127.0.0.1:5173. Bootstrap preserva o `.env`, usa os lockfiles,
espera o PostgreSQL e aplica migrations/seed. Não baixa modelo ou ranking CLP.
A API escuta em 8000 e o banco funcional em 5440, somente em loopback.

Contas demonstrativas: `gestor@demo.pr.gov.br`, `auditor@demo.pr.gov.br`
e `cidadao@demo.pr.gov.br`; senha `Local-Demo-Only-2026!`.
Gestor acessa Curitiba; auditor e cidadão têm escopos municipais distintos,
sempre limitados por perfil. Cidadão não recebe dados financeiros.
Credenciais demonstrativas são públicas; segredos reais ficam apenas no `.env`.

Para parar API/interface pelos PIDs verificados: `.\scripts\stop.ps1`.
Para parar o banco funcional explicitamente: `docker compose stop database`.

## Produto e arquitetura

- React 19, TypeScript 7, Vite 8; logout/troca de sessão cancela requisições e
  limpa resultados, relatório, fontes, ranking e achados. Expiração exige novo login.
- FastAPI executa autorização, cálculos, busca documental e auditoria.
- PostgreSQL 18/pgvector, Alembic e RLS; conexão da aplicação usa papel separado
  do proprietário. A extensão vetorial existe; embeddings ainda não foram implementados.
- LangGraph classifica intenção e guarda checkpoints por sessão. Serviços de domínio
  são executados pela API; o grafo não executa SQL arbitrário.
- Relatórios consideram apenas pagamentos `paid`, com memória de cálculo e
  percentual não calculado quando o período anterior não é positivo.
- Auditor confirma, rejeita ou solicita informações com justificativa. Revisões
  concorrentes são serializadas: primeira decisão válida vence, seguinte retorna 409.
- Ranking mostra resultados publicados pelo CLP, fonte e hash; a aplicação não
  recalcula notas. Município fora do recorte aparece como indisponível.

[Arquitetura interativa](artifacts/arquitetura-e-fluxo.html) · [Decisões](ADR.md) ·
[Estado e evidências](PLANO.md).

## Qwen experimental e restrito

`GOVERP_MODEL_ENABLED=false` é o padrão. Para experimentar o Qwen já instalado
no Ollama local, configure explicitamente `GOVERP_MODEL_ENABLED=true` no `.env`.
Nome padrão: `qwen3:4b`; endpoint: http://127.0.0.1:11434.

O backend prepara frases de cálculos e metadados das fontes. O modelo recebe
somente fatos identificados, sem pergunta original ou documentos completos,
e retorna `{"fact_ids":["f1"]}`. O backend aceita um a cinco IDs únicos conhecidos,
sem campos extras, e monta todo o texto exibido com os avisos obrigatórios.
JSON Schema, `think:false`, temperatura zero, uma tentativa e timeout total de
no máximo 20 segundos. Saída inválida, incompleta ou indisponível aciona resumo determinístico.
Auditoria e buscas sem fontes nunca chamam o modelo.

`/api/assistant` mantém seus campos e acrescenta `explanation_status`:
`deterministic`, `model_validated` ou `model_fallback`; `fallback_reason` é sanitizado.
A UI distingue esses estados. Modelo desabilitado não conta como chamada ou falha.

O piloto real de 2026-10-09 teve **0/12 composições aceitas e 12 timeouts**;
todos exibiram fallback. A proteção de sustentação foi implementada, mas a
qualidade/utilidade do modelo neste hardware permanece não aprovada.
[Evidência congelada](artifacts/qwen-restricted-evaluation.json).

## Validação reproduzível

~~~powershell
.\scripts\check.ps1
.\scripts\e2e.ps1 -InstallBrowser
.\scripts\observability-smoke.ps1
uv run --locked --extra dev --managed-python python scripts/evaluate-qwen.py
~~~

Após instalar Chromium uma vez, execute E2E sem `-InstallBrowser`.
Check roda Ruff, formato, pytest, pacote Python e build frontend.
E2E usa banco PostgreSQL temporário em 5441, API 8001 e UI 5174; verifica
sessão/perfil/município/CSRF, entradas inválidas, concorrência, responsividade e
recuperação após reinício do banco. Não usa o banco funcional nem chama Qwen.
Os relatórios ficam em `.runtime/`; CI `Quality` reutiliza os checks e guarda
relatórios de recuperação e traces de falha por sete dias.

O [repositório público](https://github.com/marcosjcn94-bit/GovERP-AI-Lab) possui
remote, CI e Dependabot. Integração exige Quality aprovado no SHA atual.
Avaliação real Qwen e revisão humana são gates locais separados do CI.
Evidências atuais: [aceite local](artifacts/acceptance-local.json) e
[revisão visual da arquitetura](artifacts/architecture-review.json).
O diagrama tem conteúdo em português; controles do viewer e `html lang` usam inglês.

## Observabilidade e LangSmith

Para o dashboard local opcional:

~~~powershell
.\scripts\observability.ps1 up
.\scripts\start.ps1 -EnableObservability
~~~

Grafana: http://127.0.0.1:3000; Prometheus 9090, Loki 3100, Tempo 3200 e Collector
4318. Senha Grafana fica no `.env`. Retenção e armazenamento são limitados;
armazenamento temporário não é uma estratégia de recuperação de produção.
Para parar: `.\scripts\observability.ps1 down`.

O smoke cria serviços temporários próprios, correlaciona request_id, run_id e
trace_id, verifica métrica de rota/status, interrompe somente seu banco, exige
503 sanitizado, observa `GovERPApiUnavailable` firing após dois minutos e resolução
após recuperar. Exportação contém apenas IDs, rota, método, status e duração;
SQL/client spans foram retirados para evitar conteúdo em exceções.

Passo a passo aplicado de OTIMIZA: definir aceite → IDs/logs sanitizados →
traces/métricas → falha controlada → correlação/alerta → recuperação → relatório.
Serviços ativos isoladamente não comprovam esse fluxo.

LangSmith é externo e opcional. Chave somente em `.env`;
`LANGSMITH_HIDE_INPUTS`, `LANGSMITH_HIDE_OUTPUTS` e `LANGSMITH_HIDE_METADATA`
protegem o roteador. `scripts/verify-langsmith.ps1` verifica o envio sanitizado.
`scripts/studio.ps1` inicia Studio local em 2024; login na UI do LangSmith é
uma interação humana separada. MCP Docker e OAuth globais não são alterados.

## Dados, histórico e limites

Seed idempotente: 10 municípios, 148.000 lançamentos e 1.120 documentos sintéticos.
Referências oficiais têm URL/hash, com vigência explicitamente não verificada.
Atualização CLP é manual: `uv run --locked --extra dev --managed-python python -m gov_erp.rankings`.
Benchmark isolado de 100 municípios: `.\scripts\benchmark-100.ps1`.
Medições anteriores estão em [otimiza-validation.md](artifacts/otimiza-validation.md)
e no histórico Git; não representam carga concorrente ou SLO de produção.

Revisão humana das telas, fontes, explicações e achados permanece pendente.
Não há deploy externo, embeddings, atualização automática CLP, identidade
federada, trilha imutável ou recuperação de desastre de produção nesta entrega.
Hashes identificam conteúdo armazenado; não autenticam sua origem ou vigência.
