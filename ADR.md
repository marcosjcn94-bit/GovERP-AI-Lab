# Registros de decisões arquiteturais

Registro breve das decisões que afetam arquitetura, segurança e operação do GovERP AI Lab. Valores financeiros, documentos e execuções do produto continuam demonstrativos, conforme indicado no README.

## ADR-001 — Cálculos e autorização determinísticos

- **Data:** 2026-10-07
- **Decisão:** Regras fiscais, relatórios, permissões por perfil/município e auditoria continuam no backend determinístico. O modelo local organiza explicações; uma ocorrência de auditoria exige decisão humana.
- **Consequências:** Respostas financeiras mantêm memória de cálculo e fonte; texto gerado não altera valores nem confirma fraude. Dados da demonstração permanecem sintéticos.

## ADR-002 — API e LangGraph Studio em ambientes separados

- **Data:** 2026-10-07
- **Decisão:** A API principal e o servidor de desenvolvimento do Studio mantêm ambientes Python separados e serviços em loopback. O Studio inspeciona o roteador e não amplia permissões ou executa operações de ERP.
- **Consequências:** Dependências de desenvolvimento e Studio são travadas independentemente; disponibilidade local não representa deploy público.

## ADR-003 — LangSmith opcional com traces sanitizados

- **Data:** 2026-10-07
- **Decisão:** Credencial em `.env` ignorado pelo Git; projeto local próprio; exportação habilitada somente depois de ocultar entradas, saídas e metadados sensíveis. A chave nunca entra no código, no frontend ou neste arquivo.
- **Consequências:** Perguntas, respostas, documentos, identidades e dados municipais não são requisitos de observabilidade; autenticação da interface oficial permanece uma sessão do navegador independente da chave.

## ADR-004 — Observabilidade local isolada e limitada

- **Data:** 2026-10-07
- **Decisão:** OpenTelemetry, Collector, Prometheus, Grafana, Tempo e Loki rodam num perfil Compose opcional; a aplicação continua funcional se eles estiverem desligados. Retenção, cardinalidade e armazenamento são limitados.
- **Consequências:** Logs e traces usam IDs de execução; rótulos de métricas não identificam usuários, municípios ou solicitações. Métricas locais não comprovam SLO de produção.

## ADR-005 — Revisão explícita, sem decisão automatizada

- **Data:** 2026-10-07
- **Decisão:** O auditor pode confirmar, rejeitar ou pedir informações sobre um achado com justificativa. Resultados permanecem separados por município e permissão.
- **Consequências:** Um alerta não é acusação, fraude confirmada, bloqueio de pagamento ou substituto de revisão humana.

## ADR-006 — Execução local e entrega remota condicionada

- **Data:** 2026-10-07
- **Decisão:** Esta execução conclui e valida o projeto local e prepara sua configuração para o repositório GitHub indicado; não publica nem faz push.
- **Consequências:** CI e Dependabot remotos só serão reportados como configurados até uma execução observada no GitHub.


## ADR-007 - CI e Dependabot ativos no GitHub

- **Data:** 2026-10-08
- **Decisao:** Publicar o projeto no repositorio publico existente marcosjcn94-bit/GovERP-AI-Lab, com CI em push e pull request e atualizacoes semanais do Dependabot para uv, npm e GitHub Actions.
- **Consequencias:** A branch codex/gov-erp-ai-lab e a branch padrao atual. O CI passou no commit 6c59f9d. Atualizacoes de dependencias exigem checks atuais e revisao; nenhuma PR e mesclada automaticamente. Esta decisao atualiza o estado operacional descrito no ADR-006.