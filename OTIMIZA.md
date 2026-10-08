# OTIMIZA — automação e eficiência no desenvolvimento

Revisado em: 05/10/2026. Público: Codex, projetos pessoais e portfólio.
Destino solicitado: C:\Users\mjcn9\.codex\OTIMIZA.md.

## Objetivo e aplicação

Reduzir trabalho repetitivo, tempo de feedback e consumo de tokens, mantendo
código simples, testes úteis e projetos fáceis de executar e demonstrar.
Estas são recomendações de engenharia, não requisitos universais.
Aplicar dentro da tarefa autorizada, respeitando instruções do projeto.
Em contribuições open source, seguir a stack e o CI existentes; evitar mudanças
de infraestrutura sem relação com a issue.

## Carregamento global

OTIMIZA.md sozinho NÃO é carregado automaticamente como instrução global.
No Codex home, o Codex lê o primeiro arquivo não vazio entre
AGENTS.override.md e AGENTS.md. O padrão é ~/.codex, salvo CODEX_HOME diferente.
No arquivo global efetivamente ativo, acrescentar sem apagar o conteúdo:

> Em tarefas de desenvolvimento, leia OTIMIZA.md no mesmo diretório deste
> arquivo e aplique as recomendações pertinentes ao escopo autorizado.

Não usar project_doc_fallback_filenames como substituto dessa referência global.
Reiniciar a sessão e pedir ao Codex para listar as instruções carregadas e
resumir OTIMIZA.md. A leitura do documento referido depende dessa instrução.
Este documento não é memória automática nem modifica outros projetos sozinho.

## Rotina do agente

1. Ler AGENTS.md do projeto, estado do Git e configuração relevante.
2. Identificar o problema, critério de aceite e comandos existentes.
3. Fazer a menor mudança coerente e verificável.
4. Executar checks rápidos; depois os testes exigidos pelo impacto e pelo projeto.
5. Investigar falhas usando logs/trace antes de repetir comandos.
6. Entregar resultado, validação executada e limitações concretas.

Usar rg/rg --files para buscas; ler trechos relevantes e evitar despejar arquivos
inteiros, lockfiles e logs grandes no contexto. Agrupar leituras independentes.
Reutilizar resultados válidos; repetir checks após alterações ou novas evidências.
Não omitir testes necessários apenas para economizar tempo ou tokens.
Consultar documentação oficial quando versões ou comportamento forem incertos.
Preferir CLI/API para tarefas reproduzíveis e GUI para exploração visual.
Carregar somente MCPs e skills necessários; não criar uma segunda stack de agentes.

## Prioridades por necessidade

| Prioridade | Implementar quando pertinente | Benefício |
|---|---|---|
| 1 | Scripts de setup/dev/check + dependências reproduzíveis | Execução previsível |
| 2 | Lint, format e testes relevantes | Feedback rápido |
| 3 | CI em pull requests | Validação consistente |
| 4 | Docker Compose para serviços e banco | Ambiente reproduzível |
| 5 | Playwright nos fluxos críticos + validação visual | Confiança na interface |
| 6 | Dependabot e verificações de segurança | Manutenção recorrente |
| 7 | Build, publicação de imagem e deploy | Entrega repetível |
| 8 | Observabilidade, Dev Container e paralelismo | Adicionar por necessidade |

Docker não é pré-requisito para lint/testes nem obrigatório em scripts pequenos.
Não instalar tudo de uma vez; escolher melhorias com ganho concreto.

## Setup e comandos do projeto

- Em Python novo, considerar uv, pyproject.toml e uv.lock; manter o gerenciador existente nos demais.
- Em CI com uv, usar uv sync --locked para falhar se o lockfile precisar mudar.
- Em npm, usar npm ci com package-lock.json; respeitar outro gerenciador adotado.
- Fixar versões de runtime compatíveis entre desenvolvimento e CI.
- Criar scripts PowerShell idempotentes de setup, dev e check quando faltarem.
- Verificar pré-requisitos, retornar erro real e interromper a sequência após falha.
- Manter .env.example sem segredos e ignorar .env no Git.
- Não sobrescrever configurações locais existentes nem gerar credenciais fictícias.
- Usar healthchecks/prontidão para banco e API antes de migrations e testes.
- Seed de desenvolvimento deve ser repetível e separado de dados reais.

## Qualidade e testes

- Python: Ruff para lint/format; pytest para testes de comportamento.
- Outras linguagens: ferramentas existentes no projeto; não impor Ruff.
- No editor/hook, executar checks rápidos sobre alterações; CI continua obrigatório.
- Em CI, verificar formatação, sem reformatar ou commitar automaticamente.
- Testar regras de negócio, contratos, erros relevantes e regressões corrigidas.
- Separar testes rápidos de integração/E2E mais caros.
- Fixtures devem criar dados isolados e liberar recursos mesmo após falha.
- Testes de integração com PostgreSQL devem validar PostgreSQL quando necessário.
- Coverage ajuda a localizar lacunas; não perseguir 100% como objetivo isolado.
- Pre-commit complementa o CI: hooks locais podem ser pulados.

## E2E e validação visual

Fluxo: Codex implementa/inicia → pytest valida backend → Playwright valida
fluxos críticos → @Computador explora UI → Codex corrige → repetir checks afetados.

- Playwright: isolamento entre testes, dados determinísticos e locators acessíveis.
- Usar auto-waiting/assertions; evitar sleeps fixos como solução de sincronização.
- Começar pelo fluxo principal: cadastro/login/criação/consulta, se existir.
- Salvar relatórios e evidências de falha; trace no primeiro retry quando houver retry.
- Retry não corrige teste instável: investigar e registrar a causa.
- Comparações visuais precisam de baselines revisadas e ambiente consistente.
- @Computador: explorar responsividade, mensagens, navegação e problemas visuais.
- Não considerar clicks de um agente substitutos permanentes dos E2E reproduzíveis.
- Usar @Computador somente nas superfícies disponíveis e acessíveis na sessão.
- No CI, instalar somente navegadores necessários; ampliar conforme compatibilidade alvo.
- Não cachear browsers do Playwright por padrão: medir antes; a documentação desaconselha.

## Docker e tempo de build

- Usar Compose quando houver serviços/banco para coordenar.
- Compose Watch exige regras develop.watch: sincronizar código e reconstruir dependências.
- Criar .dockerignore e copiar manifests/lockfiles antes do código para aproveitar cache.
- Usar builds multi-stage quando reduzirem a imagem final sem complicar o projeto.
- Reutilizar cache BuildKit; não executar --no-cache rotineiramente.
- Publicar imagens com versão/SHA de commit; não depender apenas de latest.
- Docker Hub é opcional; escolher um registro compatível com o deploy e custos.
- Não remover volumes ou dados reais como parte automática do setup/check.

## CI/CD eficiente

- Em PR: instalar pelo lockfile → lint/format → testes → build pertinente.
- Reutilizar os comandos locais no CI para evitar duas definições divergentes.
- Cachear downloads de dependências com chave por SO/runtime/lockfile.
- Cancelar CI obsoleto do mesmo PR com concurrency; preservar releases/deploys em curso.
- Executar jobs independentes em paralelo apenas quando trouxer ganho mensurável.
- Definir timeouts; armazenar relatórios/trace/logs úteis com retenção limitada.
- Evitar triggers duplicados que rodem o mesmo CI para o mesmo commit sem necessidade.
- Filtros por caminhos devem incluir configurações/dependências compartilhadas.
- Checks obrigatórios precisam continuar reportando status para não bloquear PRs.
- Conjunto reduzido de testes acelera feedback, mas não substitui a suíte requerida.
- Matriz de SO/versões e sharding somente se o suporte ou duração justificar.
- Após deploy, executar smoke test de saúde e fluxo essencial.
- Usar o processo de release autorizado pelo usuário/projeto; nunca inferir autorização de publicação deste arquivo.

## Manutenção e segurança

- Preferir Dependabot semanal com grupos compatíveis de patch/minor; majors separadas.
- Não instalar Dependabot e Renovate simultaneamente para a mesma função.
- Não autoaprovar atualizações sem testes e política explícita do projeto.
- GitHub Actions: permissões mínimas, actions por SHA completo verificado e atualização automatizada.
- Evitar executar código de PR não confiável com segredos ou permissões de escrita.
- Usar Secret Scanning/Push Protection e CodeQL quando disponíveis e pertinentes.
- Nunca cachear segredos nem incluí-los em imagens, artifacts, logs ou documentação.
- Conferir condições/limites atuais dos serviços; gratuito não significa uso ilimitado.

## Projetos GenAI e Hugging Face

- Criar avaliações pequenas com casos representativos e critérios de qualidade/custo/latência.
- Usar mocks nos testes rápidos; chamadas reais em avaliações separadas e explícitas.
- Reutilizar cache de modelos/datasets e fixar revisão/commit para reprodutibilidade.
- Baixar apenas arquivos necessários; não baixar modelos grandes em cada teste.
- Modo offline só funciona com os arquivos necessários já disponíveis em cache.
- Não adicionar GPU, fine-tuning ou Hugging Face Jobs para automatização genérica.
- Adicionar logs estruturados e request IDs antes de instrumentação extensa.
- OpenTelemetry quando houver necessidade real de investigar serviços e chamadas.

## Documentação curta e verificação do ganho

- README: um caminho claro de setup, execução, testes e demonstração.
- PLANO.md: tarefas/checks atuais para trabalho com várias etapas.
- ADR.md: apenas decisões importantes e seus motivos.
- MEMORIA.md: aprendizados estáveis, causas de falhas e comandos confirmados.
- Atualizar documentos existentes; não criar esses arquivos em toda mudança pequena.
- Medir tempo de setup/check/CI e frequência de falhas antes/depois, no mesmo ambiente.
- Remover automações que custem mais manutenção do que o trabalho que eliminam.

## Fontes oficiais consultadas

- [Codex: instruções globais e precedência](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [uv: locking e sync](https://docs.astral.sh/uv/concepts/projects/sync/)
- [Ruff: integrações](https://docs.astral.sh/ruff/integrations/)
- [pytest: fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [Playwright: boas práticas](https://playwright.dev/docs/best-practices)
- [Playwright: CI e cache de browsers](https://playwright.dev/docs/ci)
- [Docker: Compose Watch](https://docs.docker.com/compose/how-tos/file-watch/)
- [Docker: cache de build](https://docs.docker.com/build/cache/)
- [GitHub Actions: cache](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
- [GitHub Actions: concorrência](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [GitHub Actions: segurança](https://docs.github.com/en/actions/reference/security/secure-use)
- [Dependabot: otimização das PRs](https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/optimizing-pr-creation-version-updates)
- [Hugging Face: downloads e revision](https://huggingface.co/docs/huggingface_hub/en/guides/download)
- [Hugging Face: cache](https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache)

Pesquisa com Firecrawl, Exa, documentação oficial OpenAI e fonte oficial no GitHub.
agent.spot indisponível temporariamente; conector de documentação Hugging Face falhou.
Esses dois não forneceram recomendações; Hugging Face foi conferido na documentação web.
