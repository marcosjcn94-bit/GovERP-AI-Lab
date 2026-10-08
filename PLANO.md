# Aplicação de OTIMIZA.md

Plano aprovado em 2026-10-07. Fonte: OTIMIZA.md.

- [x] Dependências Python travadas, setup e check reproduzíveis.
- [x] Banco pronto antes de migrations; CLP como atualização explícita.
- [x] Benchmark com timer exclusivo do seed.
- [x] CI GitHub Actions e Dependabot configurados.
- [x] Playwright com PostgreSQL isolado e sem modelo real.
- [x] OTIMIZA.md e referência no AGENTS.md global, com backup.
- [x] Validação local, revisão independente e registro das limitações.

Decisão: Node 24 LTS instalado; Node 20 encerrou o suporte.
Fonte: https://github.com/nodejs/Release

Execução na branch existente `codex/gov-erp-ai-lab`; documentos, dados, configuração e artifacts anteriores preservados.
11 testes pytest e 3 E2E aprovados; bootstrap repetido duas vezes. API/interface locais restabelecidas.

Evidências: `artifacts/otimiza-validation.md`.

Pendências de ambiente: primeira execução do CI/Dependabot no GitHub (sem remote) e confirmação do carregamento global em nova sessão. Benchmark de 100 atualizado, sem nova medição.

## Testes, acesso e arquitetura — 2026-10-07

Escopo autorizado: testar e registrar os defeitos do site, criar o diagrama com Archify e configurar o Studio. A stack de observabilidade abaixo é uma recomendação; sua integração continua pendente.

### Validação automática

| Verificação | Resultado nesta execução | Evidência |
|---|---|---|
| pytest existente | 11 aprovados em 6,55 s, após restaurar o ambiente principal | Saída de `python -m pytest -q` |
| E2E Chromium existente | 3 aprovados em 34,0 s | `.runtime/playwright-report/` |
| Execução E2E completa | 152,505 s; zero chamadas de modelo; limpeza com código 0 | `.runtime/e2e-report.json`, medido em 2026-10-07T21:21:55Z |
| API principal | `/health/ready` com banco `ready` | Consulta local após reiniciar os serviços |
| Studio local | Grafo carregado; intenções `report`, `audit` e `documents` corretas; zero chamadas de modelo | `.runtime/studio-report.json` |
| Docker MCP | Handshake, lista de ferramentas e chamada somente leitura `browser_tabs` aprovados | `.runtime/mcp-docker-report.json` |
| Lockfiles | Projeto principal: 69 pacotes; Studio: 79; ambos consistentes em verificação offline | `uv lock --check --offline`, incluindo `--project studio` |

O E2E usa PostgreSQL temporário em 5441 e API/frontend em 8001/5174. Os três casos cobrem relatório com fallback, recusa financeira ao cidadão e recusa ao gestor em município não autorizado. Esses três casos não representam cobertura completa do produto. Os resultados anteriores (11 pytest e 3 E2E) permanecem registrados em `artifacts/otimiza-validation.md`.

### Exploração manual do frontend

| Fluxo | Resultado observado |
|---|---|
| Login do gestor e recarga da página | HTTP 200; sessão preservada |
| Consulta financeira | HTTP 200; tabela com cinco secretarias; explicação determinística quando Ollama não respondeu |
| Abas Relatórios e Conhecimento | Alteram o título e mantêm o assistente genérico; não têm conteúdo próprio |
| Sugestão padrão de fonte/vigência | HTTP 200, intenção `documents`, zero fontes; não comprova ausência de documentos |
| Busca curta por ISS | HTTP 200; uma fonte oficial renderizada; vigência explicitamente não verificada; fallback do modelo |
| Pergunta de auditoria | HTTP 200; intenção `audit`; sinalização de revisão humana |
| Lista de achados em Curitiba | HTTP 200; 88 achados |
| Execução das regras | HTTP 200; 50.000 registros examinados, 88 possíveis duplicidades, zero novos achados |
| Ranking de Curitiba | HTTP 200; resultado disponível; 13 pilares renderizados |
| Logout | Retorna à tela de acesso |
| Cidadão consultando dados restritos | HTTP 403; mensagem de perfil sem permissão; nenhuma tabela financeira |
| Gestor entrando em Londrina | HTTP 403; mensagem de município não autorizado |
| Senha inválida | HTTP 401; mensagem de credenciais inválidas |
| Auditor entrando em Londrina | HTTP 200; lista vazia de achados; interface sem controles de revisão |
| Pergunta vazia | HTTP 422, porém a interface mostra `[object Object]` e mantém a resposta anterior |
| Desktop 1440 × 900 | Largura da página de 1440 px, sem transbordamento horizontal |
| Mobile 390 × 844 | Largura da página de 475 px, com transbordamento horizontal de 85 px |

Evidências visuais: `artifacts/frontend-desktop.png` e `artifacts/frontend-mobile.png`, inspecionadas pelo agente. Revisão humana continua pendente. Snapshots e logs de exploração estão em `.playwright-mcp/`; esse diretório foi preservado, e sua limpeza não foi executada. Os resultados manuais anteriores — gestor, assistente, auditoria, ranking, recusas e logout — foram confirmados ou ampliados nesta execução.

Ocorrências de ambiente: o banco principal estava parado, causando falha na lista de municípios. Após iniciar o banco, uma conexão antiga do checkpointer ainda causou HTTP 500 no assistente. Reiniciar API/interface pelos scripts existentes restabeleceu o serviço. Uma consulta excedeu os 30 s de espera do explorador e depois retornou HTTP 200 com fallback; o timeout padrão do modelo é 120 s. Isso não foi corrigido no código.

### Pendências concretas

- [ ] P2: implementar conteúdo próprio nas abas Relatórios e Conhecimento.
- [ ] P2: corrigir a apresentação de erros de validação (pergunta vazia mostra `[object Object]`) e deixar claro quando a resposta anterior fica visível.
- [ ] P2: eliminar o transbordamento horizontal em 390 px; verificar o hash longo do ranking e demais elementos largos.
- [ ] P2: oferecer a revisão de achados pela interface, caso esse fluxo deva fazer parte do frontend. O endpoint existe, mas não há controles na tela; nenhuma decisão humana de aprovação/rejeição foi simulada.
- [ ] P3: ajustar a sugestão documental para recuperar fontes relevantes; a sugestão atual retorna zero, enquanto a busca curta encontra uma fonte.
- [ ] P3: corrigir separadores literais `?` no texto do ranking e o favicon com HTTP 404 observado na exploração anterior.
- [ ] Avaliar o tempo até o fallback do Ollama e a recuperação da API quando o PostgreSQL reinicia.
- [ ] Revisão humana das telas, das fontes/vigência e dos achados; funcionamento com modelo local real, concorrência e produção não validados.
- [ ] Confirmar a exposição das ferramentas globais do MCP Docker em uma nova sessão do Codex; o handshake direto aprovado não prova esse carregamento.
- [ ] Verificar o serviço de segredos e o canal de notificações OAuth do Docker Desktop, que emitiram avisos no Gateway.
- [x] Abrir o Studio oficial após autorização específica; grafo e conexão local confirmados.
- [ ] Fazer login no LangSmith para validar a visualização do resultado após enviar uma pergunta; a interface redirecionou para autenticação, embora a execução local tenha concluído.
- [ ] Integrar a observabilidade recomendada, executar CI/Dependabot no GitHub e medir novamente o benchmark de 100.

Conclusão do frontend: os fluxos testados acima têm evidências, mas o aceite de “todas as funcionalidades funcionando” permanece pendente por causa dos defeitos e lacunas listados. Nenhum defeito funcional do site foi corrigido nesta tarefa.

### Como visualizar o projeto

No PowerShell, a partir de `C:\Users\mjcn9\Desktop\EQUIPLANO`:

```powershell
.\scripts\start.ps1
```

Abra <http://127.0.0.1:5173>. A API responde em <http://127.0.0.1:8000/health/ready>. O Docker Desktop precisa estar ativo e acessível para o PostgreSQL em 5440. O projeto foi restabelecido e estava pronto nesta validação. Para encerrar API/interface:

```powershell
.\scripts\stop.ps1
```

Esse comando mantém o banco ativo. Para parar apenas o banco preservando seu volume, use `docker compose stop database`. Evite executar `start.ps1` novamente enquanto os processos já estiverem ativos; reinicie com `stop.ps1` seguido de `start.ps1`.

### Como acessar o LangGraph

Configuração: `langgraph.json`, script `scripts/studio.ps1` e dependências travadas em `studio/pyproject.toml` / `studio/uv.lock`. O Studio usa `studio/.venv`, separado da API principal: `langgraph-api` 0.15.3 exige Starlette >= 1.3.1, incompatível com a faixa atual do FastAPI da aplicação. A dependência `colorama` foi incluída somente para Windows, após reproduzir sua ausência no formatador de logs.

O catálogo global `C:/Users/mjcn9/.codex/PLUGINS-SKILLS-CODEX.md` recebeu a entrada da ferramenta, conforme as instruções AGENTS.md atualizadas. A instalação do CLI permanece restrita ao ambiente deste projeto.

```powershell
.\scripts\studio.ps1
```

O script instala/sincroniza pelo lockfile e inicia o servidor em loopback, porta 2024. Para não abrir navegador automaticamente, use `-NoBrowser`. Em execução normal no terminal, `Ctrl+C` encerra o Studio.

- API local: <http://127.0.0.1:2024/ok> e <http://127.0.0.1:2024/docs>.
- Interface oficial: <https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024>. Esse endereço é hospedado pela LangChain e se conecta ao servidor local; pode exigir login.
- Grafo: `question_router`, carregado de `src/gov_erp/workflow.py:question_graph`, com `START → route → END`.
- Teste de entrada: informe o campo `question`; despesas geram `report`, revisão/duplicidades gera `audit`, ISS gera `documents`.

O grafo exposto ao Studio classifica a intenção. Os cálculos, busca documental, auditoria e autorização são executados pela FastAPI fora desse grafo e não aparecem como nós adicionais. A API principal usa `PostgresSaver`; o servidor de desenvolvimento do Studio usa sua persistência local em `.langgraph_api/`, ignorada pelo Git. Tracing LangSmith e analytics do CLI foram desativados; `.env` e credenciais do banco não são carregados por essa configuração.

A abertura da interface oficial foi inicialmente rejeitada pela aprovação automática e só foi repetida após autorização explícita do usuário. O Studio exibiu `question_router`, os nós `__start__ → route → __end__` e o estado `Connected`. Evidência visual inspecionada pelo agente: `artifacts/langgraph-studio.png`.

Uma pergunta sintética enviada pelo botão `Submit` executou no servidor local e retornou `intent=report`, sem tarefas ou próximos nós pendentes. Execução: `01a11850-33dc-7a42-bf80-f8594635d321`; thread: `01a11850-335c-7300-8564-51715a02868c`; evidência sanitizada: `.runtime/studio-ui-report.json`. Após enviar, o navegador redirecionou para login do LangSmith, impedindo a inspeção do resultado nessa tela. A interface também avisou sobre ausência de `LANGSMITH_API_KEY` e registrou HTTP 403 na atualização do onboarding hospedado; isso não impediu carregar o grafo nem executar localmente. Não foi adicionada chave nem feita autenticação.

Limite desta validação: servidor, topologia, três intenções pela API e uma execução iniciada pelo Studio aprovados; visualização do resultado após login e deploy em produção continuam não validados. Para repetir pela interface, acesse o endereço oficial acima, faça login com sua própria conta se solicitado, abra `question_router`, expanda `question` e envie uma pergunta sintética. Não é necessário habilitar tracing para os testes locais registrados.

Fontes: [CLI e configuração](https://docs.langchain.com/langsmith/cli), [Studio](https://github.com/langchain-ai/docs/blob/main/src/oss/langgraph/studio.mdx), [versões do Agent Server](https://docs.langchain.com/langsmith/agent-server-changelog).

### Docker Desktop e MCP global

Docker Desktop 4.93.0 e Engine 29.8.1 responderam no contexto `desktop-linux`. O erro inicial de acesso ao pipe veio da restrição da sessão; a conexão foi verificada fora desse bloqueio. Não foi necessário iniciar/reinstalar o Docker Desktop.

A configuração global existente de `MCP_DOCKER`, em `%USERPROFILE%\.codex\config.toml`, executa `docker.exe mcp gateway run --profile codex`. O perfil contém Playwright, Memory, Docker Hub e Docker Docs. O dry-run encontrou 46 ferramentas dos servidores; o handshake completo listou 54, incluindo ferramentas internas do Gateway, e executou `browser_tabs` sem erro. Gateway: `Docker AI MCP Gateway` 2.0.1, protocolo negociado `2024-11-05`.

Essa configuração global já existe. A automação dos scripts Compose pela CLI não depende do MCP; o perfil atual oferece navegador, memória, Docker Hub e documentação, sem comprovar uma ferramenta MCP de administração do Engine local. Para automatizar containers locais, o caminho validado neste projeto é a CLI Docker/Compose pelos scripts existentes.

Para conferir em uma nova sessão:

1. Mantenha o Docker Desktop ativo e confirme `docker version` com seção Server.
2. No MCP Toolkit, confirme o perfil `codex` e os servidores necessários.
3. Reabra o Codex e confirme as ferramentas realmente disponíveis antes de automatizar por MCP.
4. Se os avisos persistirem, confira o serviço de segredos e OAuth no Desktop; não refaça autenticações nem substitua credenciais sem investigar a integração afetada.

Não houve alteração da configuração global, de segredos ou de perfis nesta tarefa. Fontes: [MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/toolkit/) e [perfis do Gateway](https://docs.docker.com/ai/mcp-catalog-and-toolkit/profiles/).

### Observabilidade recomendada e passos

| Ferramenta local | Função |
|---|---|
| OpenTelemetry SDK + instrumentação FastAPI/SQLAlchemy/HTTPX | Correlação de requisições, acesso ao banco, chamadas ao Ollama e spans do roteador |
| OpenTelemetry Collector | Receber, filtrar e exportar sinais |
| Prometheus | Métricas de disponibilidade, erros e duração |
| Grafana | Painéis e alertas |
| Tempo | Traces por requisição/execução |
| Loki | Logs estruturados e sanitizados |

Sequência proposta para integração futura:

1. Aproveitar o `run_id` dos registros de execução e acrescentar `request_id` para correlacionar API, grafo e modelo; padronizar logs JSON com resultado e duração.
2. Instrumentar HTTP, SQL e chamadas ao Ollama; acrescentar spans de classificação e serviço de domínio, sem anexar perguntas ou respostas completas.
3. Subir Collector, Prometheus, Grafana, Tempo e Loki localmente com Compose e armazenamento/retensão limitados.
4. Criar painéis para requisições por rota/status, latência p50/p95, disponibilidade da API/banco/modelo, proporção de fallback e execuções de auditoria. Usar rótulos de baixa cardinalidade; `run_id`, usuário e pergunta não devem ser rótulos de métricas.
5. Validar com uma consulta aprovada e uma recusa esperada: localizar os mesmos IDs nos logs/traces, confirmar as métricas e inspecionar se há segredos ou conteúdo indevido.
6. Configurar alertas para serviço indisponível, crescimento de 5xx e aumento persistente de latência/fallback; recusa 401/403 esperada deve permanecer identificável.

Excluir senha, cookies, CSRF, cabeçalhos de autorização, strings de conexão, prompts e documentos completos. Revisar permissões dos painéis e dos dados antes de compartilhar. Começar com os logs já existentes em `.runtime` e os registros de execução; a stack acima ainda não está integrada. Algumas bibliotecas OTel são dependências internas do servidor do Studio, o que não equivale à instrumentação da API principal. Custos financeiros e ganhos de latência não foram medidos.

Fontes: [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/), [instrumentação FastAPI](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html).

### Diagrama entregue com Archify

- HTML interativo: `artifacts/arquitetura-e-fluxo.html`; origem: `artifacts/arquitetura-e-fluxo.architecture.json`.
- `deliver`: 9/9 checks, perfil `showcase`, zero erros e avisos. Recibo: `artifacts/arquitetura-e-fluxo.delivery.json`.
- Especificação: 5.398 bytes, SHA-256 `9e115e620eb3e1ffee7e10c03e1fdb856ca63fe3e4e4aed286bbd5ed7b0a623b`.
- HTML: 811.708 bytes, SHA-256 `ed52277f7c219d66177f9fbbdba1b47d5a2f55d780db16dc4e8834e604bf5be4`.
- `visual-check`: aprovado em 1440×900, 1600×1000, 1920×1080 e 2048×1320, sem transbordamento; capturas clara/escura nas duas resoluções extremas. Recibo: `artifacts/arquitetura-e-fluxo.visual-check.json`.
- Revisão perceptual pelo agente: quatro imagens inspecionadas, relações sem colisões visíveis, cartões e nós contidos; zero rodadas de correção após essa revisão. Revisão humana permanece pendente.
- Texto autoral em português; controles fixos do viewer e `<html lang>` usam o inglês padrão do Archify.
- Componentes e fluxos refletem o código atual; observabilidade está identificada como planejada. O diagrama não comprova deploy ou operação em produção.

## Execução do plano aprovado — 2026-10-07

Esta atualização substitui as pendências de implementação e observabilidade registradas acima; os resultados anteriores foram preservados como histórico.

| Escopo | Estado e evidência |
|---|---|
| Interface de relatórios, busca documental, revisão de auditoria e responsividade | Implementada; oito fluxos Playwright aprovados, incluindo viewport de 390 × 844. Relatório: `.runtime/e2e-report.json`; testes: `frontend/e2e/critical-flow.spec.ts`. |
| Validação de entrada e contratos | Justificativas e perguntas normalizadas no backend; 13 testes Python aprovados. |
| Correlação e recuperação | `X-Request-ID` correlacionado ao `run_id`; API retomou após reinício do PostgreSQL temporário e respondeu antes/depois. Evidência: `.runtime/recovery-report.json`. |
| LangSmith | Trace recebido no projeto `goverp-ai-lab-local`; API confirmou entradas e saídas vazias e ausência de metadados da aplicação. `ls_run_depth` é metadado técnico do LangChain. Evidência sanitizada: `.runtime/langsmith-report.json`. A chave permanece apenas em `.env`. |
| Observabilidade local | Métrica Prometheus, log Loki e trace Tempo confirmados por requisição; perfil opcional configurado e desligado após o smoke test. Evidência: `.runtime/observability-report.json`. |
| Suíte local | Ruff, verificação de formatação, 13 testes e build TypeScript/Vite aprovados. Relatório: `.runtime/check-report.json`. |
| Benchmark isolado | 100 municípios, 200.000 transações, 3.000 documentos, 75,04 MiB; seed idempotente medido em 2,52 s, sem chamadas de modelo. Escopo exclui migrations e CLP; mantém comparações do relatório anterior em `data/benchmark-100-report.json`. |
| Ollama local | `qwen3:4b` respondeu via HTTP local em 6,59 s (18 tokens de entrada, 16 de saída). Isso valida o servidor/modelo local, não a qualidade da explicação fiscal nem avaliação humana. |

Pendencias externas ou de julgamento humano: revisar manualmente os fluxos e a qualidade das explicacoes e validar qualquer deploy. O repositorio GitHub publico ja esta configurado; CI passou no branch principal em 2026-10-08. Cinco PRs do Dependabot aguardam checks atualizados e revisao; nenhuma foi mesclada. Nenhum deploy foi feito. Backend e frontend locais estavam ativos no inicio e nao foram reiniciados; os testes usaram servicos temporarios isolados.

## GitHub, CI e Dependabot - 2026-10-08

Repositorio publico: https://github.com/marcosjcn94-bit/GovERP-AI-Lab. O remote origin aponta para esse repositorio e a branch codex/gov-erp-ai-lab e a branch padrao atual. O workflow Quality roda em push e pull request; o Dependabot atualiza semanalmente uv, npm e GitHub Actions. A execucao CI 37772601356 passou no commit 6c59f9d, incluindo testes, build e E2E com PostgreSQL e Chromium. Cinco PRs de dependencias estao abertas. Os checks iniciais falharam no script de recuperacao antes de duas correcoes ja aprovadas no branch padrao; os checks das PRs precisam de nova execucao e revisao. Nenhuma atualizacao foi mesclada.