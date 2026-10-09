# GovERP AI Lab — conclusão ponta a ponta

Plano de 2026-10-09 aprovado na conversa. Escopo: entrega local e GitHub por PR;
sem deploy externo, mudanças globais de integrações ou revisão humana substituída.
Branch padrão: `codex/gov-erp-ai-lab`; branch de execução: `codex/conclusao-goverp`.
Baseline limpo: `df9a585`. Credenciais e banco funcional preservados.

## Critérios e progresso

| Etapa | Estado | Evidência |
|---|---|---|
| Cinco dependências | Implementado; builds aprovados | setuptools 84.0.0, pytest 9.1.1, TS 7.0.2, Vite 8.3.2, plugin React 6.1.2; locks regenerados |
| Isolamento de sessão | Validado em E2E | AbortController e geração de sessão; limpeza de relatório, fontes, ranking, achados e consulta |
| Revisão concorrente | Validado em PostgreSQL | SELECT FOR UPDATE; sucesso/409 e decisão vencedora persistida |
| Qwen restrito | Mocks aprovados; piloto real limitado | 0/12 aceitos, 12 timeouts; artifacts/qwen-restricted-evaluation.json |
| Erros e correlação | Smoke completo aprovado | Mesmo request_id/run_id/trace_id; 503 sanitizado; alerta firing/resolvido; recuperação e limpeza |
| Gates locais | Aprovados | 34 pytest, 22 E2E, pacote/build e recuperação; artifacts/acceptance-local.json |
| Archify | Aprovado automaticamente e inspecionado pelo agente | 9/9 showcase, zero erros/avisos, quatro resoluções; artifacts/architecture-review.json |
| PR, CI e integração | Gate externo obrigatório | Vincular Dependabot #1–#5; exigir Quality no SHA atual e no commit integrado |

## Contratos

- IA desabilitada por padrão: `GOVERP_MODEL_ENABLED=false`.
- `/api/assistant` preserva seus campos e adiciona `explanation_status`:
  `deterministic`, `model_validated` ou `model_fallback`; `fallback_reason` é sanitizado.
- O modelo recebe fatos preparados pelo backend e retorna somente `fact_ids`:
  de um a cinco IDs únicos conhecidos, sem propriedades extras.
- JSON Schema, `think:false`, temperatura zero, uma tentativa e prazo total de 20 s.
  O backend monta o texto e acrescenta avisos de dados sintéticos/vigência.
- Auditoria e buscas sem fontes são determinísticas. Modelo desabilitado não gera
  métrica de chamada ou fallback. Fallback não é sucesso do modelo.
- Logout limpa dados imediatamente. Falha de revogação é informada; não é escondida.
  Resposta de uma geração anterior nunca restaura dados da sessão.
- Primeira revisão válida de um achado vence; revisão subsequente retorna 409.
  Autorizações por perfil, município, RLS e CSRF permanecem no backend.
- OTel é opcional e não exporta SQL, perguntas, documentos, corpos ou credenciais.
  LangSmith externo permanece sanitizado conforme ADR-003.

## Comandos de aceite

~~~powershell
.\scripts\check.ps1
.\scripts\e2e.ps1
.\scripts\observability-smoke.ps1
uv run --locked --extra dev --managed-python python scripts/evaluate-qwen.py
~~~

E2E: PostgreSQL temporário em 5441, API 8001, interface 5174, modelo e LangSmith
explicitamente desligados. Relatórios de recuperação são guardados também no CI.
Smoke OTel: projeto Compose único, PostgreSQL temporário 15441, API 18002,
Collector 14318, Prometheus 19090, Loki 13100 e Tempo 13200. Reutiliza a regra
GovERPApiUnavailable com `for: 2m`; verifica firing e resolução após recuperação.
Nenhum desses scripts interrompe o banco funcional em 5440.
O SHA integrado e os links das execuções CI são registrados na PR e no relatório
final da execução. Este documento e o recibo local não substituem esse gate externo.

## Decisões de execução

- A branch padrão real é `codex/gov-erp-ai-lab`, confirmada por Git; não existe main.
- O terminal isolado falhou ao iniciar; execução elevada autorizada resolveu o problema.
- TypeScript 7 exige declaração dos imports CSS: adicionado `vite/client`, sem relaxar strict.
- O relatório Qwen congela 12 casos distintos dos mocks. Todos atingiram timeout;
  o modo experimental continua opcional e não foi aprovado como melhoria semântica.
- O teste de revisão não depende da posição do achado: a ordenação pode mudar após reload.
- O canário detectou a query em `http.url` legado; o hook agora remove tanto atributos
  legados quanto atuais. O smoke aprovado não encontrou o canário nos sinais exportados.
- A conexão PostgreSQL tem prazo de 3 s e espera do pool de 5 s; a falha controlada
  anterior revelou espera sem limite de conexão. Isso mantém o 503 utilizável.
- Recuperação detecta Windows por plataforma, compatível com PowerShell 5 e CI Linux.
- Archify preserva conteúdo em português; controles fixos e `html lang` usam inglês.
  Inspeção visual do agente não substitui aprovação humana.
- Git preserva LF nos artifacts e no dataset congelado para manter seus hashes
  idênticos entre checkout Windows/Linux.
- Revisão independente final: dois achados importantes corrigidos, sem menores adiados.
  Configuração legada de timeout aceita; prazo efetivo continua limitado a 20 s.
  Limpeza do smoke continua após falha da API e invalida aprovação se falhar.
  Três regressões reproduziram as falhas antes da correção; suíte final 34/34.
- Pontos separados pela revisão: smoke real comprovado em Windows, execução Linux
  desse smoke não medida; utilidade semântica Qwen e revisão humana não aprovadas;
  CI/merge exigem verificação do SHA publicado. Custo de inferir Linux/qualidade
  indevidamente seria aceite sem evidência; esses limites permanecem explícitos.
- API e App mantêm a organização preexistente acima de 250 linhas para evitar
  fragmentar contratos/estado nesta correção. Serviços, transporte e novos testes
  permanecem separados e menores; futuras extrações podem ser tratadas por domínio.

## Limites e revisão humana

Revisão humana das telas, fontes, explicações e achados continua pendente.
Studio exige sessão do navegador LangSmith; credencial API não comprova login.
MCP Docker registrado/perfil existente não comprova exposição de ferramentas em
nova sessão. Diagnóstico não autoriza mudanças globais.
Embeddings, atualização automática CLP, recursos de produção e deploy são evolução futura.

## Histórico

O histórico anterior permanece em Git no [PLANO do baseline](https://github.com/marcosjcn94-bit/GovERP-AI-Lab/blob/df9a585/PLANO.md),
[ADR.md](ADR.md), [otimiza-validation.md](artifacts/otimiza-validation.md)
e [piloto anterior Qwen](artifacts/qwen3-4b-evaluation.md).
Medições históricas de seed/benchmark não são repetidas como evidência atual.
