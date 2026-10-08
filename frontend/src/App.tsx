import { FormEvent, useEffect, useState } from "react";

type City = { id: string; name: string; uf: string };
type Session = { user_id: string; display_name: string; role: string; municipality_id: string; municipality_name: string; csrf_token: string };
type Finding = { id: string; rule_id: string; record_ids: string[]; evidence: Record<string, string>; status: string; review_note?: string };
type Report = { current_period: { start: string; end: string }; previous_period: { start: string; end: string }; departments: Record<string, { previous: string; current: string; absolute_change: string; percentage_change: string | null }> };
type DocumentSource = { title: string; excerpt: string; source_url: string; source_hash: string; source_kind: string; vigency_verified: boolean; valid_from: string | null; valid_until: string | null };
type RunResult = { run_id: string; intent: string; answer: string; model?: string; model_fallback: boolean; result: Record<string, unknown>; human_review_required: boolean };
type Ranking = { available: boolean; municipality_name?: string; edition_year?: number; population?: number; overall_score?: string; overall_rank?: number; rank_change?: number | null; pillars?: Record<string, { score: number; rank: number; rank_change: number | null }>; source_url: string; source_sha256?: string; message?: string };

async function api<T>(path: string, init: RequestInit = {}, csrf?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("content-type", "application/json");
  if (csrf) headers.set("x-csrf-token", csrf);
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Falha na requisicao local." }));
    throw new Error(readableError(body.detail) ?? `Erro HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function readableError(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (typeof item === "string") return item;
      if (!item || typeof item !== "object") return "Entrada invalida";
      const error = item as { loc?: unknown[]; msg?: unknown };
      const field = Array.isArray(error.loc)
        ? error.loc.filter((part): part is string => typeof part === "string" && part !== "body").join(" → ")
        : "";
      const message = typeof error.msg === "string" ? error.msg : "Entrada invalida";
      return field ? `${field}: ${message}` : message;
    }).join("; ");
  }
  if (detail && typeof detail === "object" && "msg" in detail) {
    const message = (detail as { msg: unknown }).msg;
    return typeof message === "string" ? message : null;
  }
  return null;
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [cities, setCities] = useState<City[]>([]);
  const [selectedCity, setSelectedCity] = useState("");
  const [email, setEmail] = useState("gestor@demo.pr.gov.br");
  const [password, setPassword] = useState("Local-Demo-Only-2026!");
  const [question, setQuestion] = useState("Compare as despesas pagas por secretaria e mostre a memoria de calculo.");
  const [result, setResult] = useState<RunResult | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [ranking, setRanking] = useState<Ranking | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [reportRange, setReportRange] = useState({ start: "2025-10-01", end: "2025-12-31" });
  const [documentQuery, setDocumentQuery] = useState("");
  const [documents, setDocuments] = useState<DocumentSource[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("Visao geral");

  useEffect(() => {
    api<City[]>("/api/public/municipalities").then((all) => {
      setCities(all);
      setSelectedCity(all.find((city) => city.id === "4106902")?.id ?? all[0]?.id ?? "");
    }).catch((e: Error) => setError(e.message));
    api<Omit<Session, "csrf_token"> & { csrf_token: string }>("/api/auth/session")
      .then(setSession).catch(() => undefined);
  }, []);

  async function login(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const value = await api<Session>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password, municipality_id: selectedCity }) });
      setSession(value); setTab("Visao geral");
    } catch (e) { setError(e instanceof Error ? e.message : "Nao foi possivel entrar."); }
    finally { setBusy(false); }
  }

  async function logout() {
    if (!session) return;
    await api("/api/auth/logout", { method: "POST" }, session.csrf_token).catch(() => undefined);
    setSession(null); setResult(null); setFindings([]);
  }

  async function ask(event: FormEvent) {
    event.preventDefault(); if (!session) return;
    setResult(null);
    setBusy(true); setError("");
    try { setResult(await api("/api/assistant", { method: "POST", body: JSON.stringify({ question }) }, session.csrf_token)); }
    catch (e) { setError(e instanceof Error ? e.message : "Consulta nao concluida."); }
    finally { setBusy(false); }
  }

  async function loadReport(event: FormEvent) {
    event.preventDefault();
    if (!session) return;
    setReport(null);
    setError("");
    const start = new Date(`${reportRange.start}T00:00:00Z`);
    const end = new Date(`${reportRange.end}T00:00:00Z`);
    if (!reportRange.start || !reportRange.end || Number.isNaN(start.valueOf()) || Number.isNaN(end.valueOf()) || end < start || (end.valueOf() - start.valueOf()) / 86_400_000 > 366) {
      setError("Informe um periodo valido de ate 367 dias.");
      return;
    }
    setBusy(true);
    try {
      const parameters = new URLSearchParams({ start: reportRange.start, end: reportRange.end });
      setReport(await api<Report>(`/api/reports/paid-by-department?${parameters}`));
    } catch (e) { setError(e instanceof Error ? e.message : "Nao foi possivel consultar o relatorio."); }
    finally { setBusy(false); }
  }

  async function searchKnowledge(event: FormEvent) {
    event.preventDefault();
    if (!session) return;
    setDocuments([]);
    setError("");
    const query = documentQuery.trim();
    if (query.length < 3) {
      setError("Digite ao menos tres caracteres para buscar fontes.");
      return;
    }
    setBusy(true);
    try {
      const parameters = new URLSearchParams({ query, limit: "5" });
      const result = await api<{ sources: DocumentSource[] }>(`/api/documents/search?${parameters}`);
      setDocuments(result.sources);
    } catch (e) { setError(e instanceof Error ? e.message : "Nao foi possivel consultar as fontes."); }
    finally { setBusy(false); }
  }

  async function reviewFinding(event: FormEvent<HTMLFormElement>, findingId: string) {
    event.preventDefault();
    if (!session) return;
    const form = new FormData(event.currentTarget);
    const decision = form.get("decision");
    const note = form.get("note");
    if (typeof decision !== "string" || typeof note !== "string") return;
    setError("");
    try {
      await api(`/api/audits/findings/${findingId}/review`, {
        method: "POST",
        body: JSON.stringify({ decision, note }),
      }, session.csrf_token);
      await loadFindings();
    } catch (e) { setError(e instanceof Error ? e.message : "Nao foi possivel salvar a revisao."); }
  }

  async function loadFindings() {
    if (!session) return;
    try { setFindings(await api<Finding[]>("/api/audits/findings")); }
    catch (e) { setFindings([]); setError(e instanceof Error ? e.message : "Falha ao carregar auditoria."); }
  }

  async function loadRanking() {
    if (!session) return;
    try { setRanking(await api<Ranking>(`/api/public/rankings/${session.municipality_id}`)); }
    catch (e) { setError(e instanceof Error ? e.message : "Falha ao consultar o ranking publico."); }
  }

  async function runAudit() {
    if (!session) return;
    setBusy(true); setError("");
    try {
      const outcome = await api<{ run_id: string; examined: number; possible_duplicates: number; new_findings: number }>("/api/audits/run", { method: "POST" }, session.csrf_token);
      setResult({ run_id: outcome.run_id, intent: "audit", answer: `${outcome.possible_duplicates} possiveis duplicidades; ${outcome.new_findings} novos achados. Revise cada evidência.`, model_fallback: true, result: outcome, human_review_required: outcome.possible_duplicates > 0 });
      await loadFindings();
    } catch (e) { setError(e instanceof Error ? e.message : "Auditoria nao concluida."); }
    finally { setBusy(false); }
  }

  if (!session) return <main className="login-layout">
    <section className="login-card">
      <div className="brand-mark">G</div><p className="eyebrow">AMBIENTE LOCAL · DADOS SINTETICOS</p>
      <h1>GovERP AI Lab</h1><p className="muted">Relatorios verificaveis, auditoria explicavel e conhecimento municipal com fontes.</p>
      <form onSubmit={login} className="stack">
        <label>Email demonstrativo<input value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" /></label>
        <label>Senha<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></label>
        <label>Municipio<select value={selectedCity} onChange={(e) => setSelectedCity(e.target.value)}>{cities.map((city) => <option key={city.id} value={city.id}>{city.name} · {city.uf}</option>)}</select></label>
        <button disabled={busy || !selectedCity}>{busy ? "Entrando..." : "Acessar demonstracao"}</button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      <p className="fine">Credenciais locais de demonstracao. Nenhum dado municipal real e carregado.</p>
    </section>
  </main>;

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">G</span><div><b>GovERP</b><small>AI LAB</small></div></div>
      <p className="nav-caption">ESPACO DE TRABALHO</p>
      {[["Visao geral", "◫"], ["Relatorios", "▤"], ["Controle interno", "◇"], ["Conhecimento", "⌕"], ["Competitividade", "CLP"]].map(([label, icon]) => <button key={label} aria-label={label} className={`nav-item ${tab === label ? "active" : ""}`} onClick={() => { setTab(label); if (label === "Controle interno") loadFindings(); if (label === "Competitividade") loadRanking(); }}>{icon}<span>{label}</span></button>)}
      <div className="sidebar-bottom"><span className="online-dot" />Execucao somente local<small>Sem custo de modelo</small></div>
    </aside>
    <main className="workspace">
      <header className="topbar"><div><span className="breadcrumb">GovERP AI Lab</span><span className="slash">/</span><b>{tab}</b></div><div className="user-menu"><span className="city-tag">{session.municipality_name} · PR</span><span className="avatar">{session.display_name.slice(0, 1).toUpperCase()}</span><span>{session.display_name}</span><button className="text-button" onClick={logout}>Sair</button></div></header>
      <section className="page-content">
        <div className="page-heading"><div><p className="eyebrow">{session.municipality_name.toUpperCase()} · AMBIENTE DEMONSTRATIVO</p><h1>{tab === "Visao geral" ? "Assistente de gestao municipal" : tab}</h1><p className="muted">Consulte, confira os dados de origem e revise resultados antes de agir.</p></div><span className="read-only"><span className="lock">⌑</span> ERP em modo leitura</span></div>
        <div className="notice"><span>ⓘ</span><span><b>Dados inteiramente sinteticos.</b> Nomes dos municipios e fontes oficiais sao identificados separadamente.</span></div>
        {tab === "Relatorios" ? <section className="panel tab-panel">
          <div className="panel-title"><div><span className="panel-icon">▤</span><div><h2 className="panel-heading">Comparativo de despesas pagas</h2><small>Calculo deterministico · dados demonstrativos da cidade selecionada</small></div></div></div>
          <form className="filter-form" onSubmit={loadReport}>
            <label>Data inicial<input type="date" value={reportRange.start} onChange={(event) => setReportRange({ ...reportRange, start: event.target.value })} required /></label>
            <label>Data final<input type="date" value={reportRange.end} onChange={(event) => setReportRange({ ...reportRange, end: event.target.value })} required /></label>
            <button disabled={busy}>{busy ? "Calculando..." : "Gerar relatório"}</button>
          </form>
          {error && <p className="error" role="alert">{error}</p>}
          {report && <><p className="muted">Periodo atual: {report.current_period.start} a {report.current_period.end} · Periodo anterior: {report.previous_period.start} a {report.previous_period.end}</p><ReportTable report={report} /></>}
          {!report && !error && <div className="empty-state"><p>Escolha um periodo para gerar o comparativo</p><small>Somente pagamentos com status pago entram no calculo.</small></div>}
        </section> : tab === "Conhecimento" ? <section className="panel tab-panel">
          <div className="panel-title"><div><span className="panel-icon">⌕</span><div><h2 className="panel-heading">Fontes e vigência documental</h2><small>Busca restrita ao municipio e ao acesso do seu perfil</small></div></div></div>
          <form className="filter-form search-form" onSubmit={searchKnowledge}>
            <label>Buscar fontes municipais<input type="search" value={documentQuery} onChange={(event) => setDocumentQuery(event.target.value)} maxLength={512} minLength={3} placeholder="Ex.: ISS ou iluminação pública" required /></label>
            <button disabled={busy || documentQuery.trim().length < 3}>{busy ? "Buscando..." : "Buscar fontes"}</button>
          </form>
          {error && <p className="error" role="alert">{error}</p>}
          {documents.map((source) => <article className="source-card knowledge-source" key={source.source_url}>
            <div className="source-meta"><span className={source.source_kind === "official" ? "badge official" : "badge synthetic"}>{source.source_kind === "official" ? "Fonte oficial" : "Documento sintetico"}</span><span>{source.vigency_verified ? "Vigência verificada" : "Vigência não verificada"}</span></div>
            <b>{source.title}</b><p>{source.excerpt}</p>
            <p className="muted">{source.valid_from ?? "Inicio nao informado"} a {source.valid_until ?? "fim nao informado"}</p>
            <code className="source-hash">SHA-256: {source.source_hash}</code><p><a href={source.source_url} target="_blank" rel="noreferrer">Abrir fonte oficial ↗</a></p>
          </article>)}
          {documents.length === 0 && !error && <div className="empty-state"><p>Nenhuma fonte encontrada</p><small>Amplie ou simplifique a busca. Resultados indisponiveis nao confirmam que um documento nao existe.</small></div>}
        </section> : <>
        <div className="content-grid">
          <section className="panel ask-panel">
            <div className="panel-title"><div><span className="sparkle">✳</span><div><b>Assistente municipal</b><small>Respostas ligadas a dados e documentos da cidade selecionada</small></div></div><span className="model-chip">QWEN · LOCAL</span></div>
            <form onSubmit={ask}><label htmlFor="question">O que voce precisa consultar?</label><textarea id="question" rows={4} maxLength={512} value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ex.: Compare despesas pagas do ultimo trimestre por secretaria."/><div className="prompt-bottom"><span>O calculo fica no backend. O modelo apenas organiza a explicacao.</span><button disabled={busy}>{busy ? "Consultando..." : "Consultar  →"}</button></div></form>
            {error && <p className="error" role="alert">{error}</p>}
            <div className="suggestions"><small>SUGESTOES</small><button onClick={() => setQuestion("Compare as despesas pagas por secretaria e mostre a memoria de calculo.")}>Despesas pagas no trimestre <span>↗</span></button><button onClick={() => setQuestion("Quais pagamentos precisam de revisao e por que?")}>Achados que precisam de revisao <span>↗</span></button><button onClick={() => { setQuestion("ISS"); setTab("Conhecimento"); }}>Localizar fonte e vigencia <span>↗</span></button></div>
          </section>
          <section className="panel evidence-panel">
            <div className="panel-title"><div><span className="panel-icon">⌕</span><div><b>Fontes da resposta</b><small>Proveniencia verificavel</small></div></div><span className="source-count">{result && Array.isArray(result.result.sources) ? result.result.sources.length : result ? "ERP" : "—"}</span></div>
            {!result && <div className="empty-state"><div className="empty-icon">▱</div><p>Suas fontes aparecerao aqui</p><small>Cada dado financeiro ou trecho documental aponta sua origem.</small></div>}
            {result?.result && Array.isArray(result.result.sources) && (result.result.sources as Array<{ title: string; excerpt: string; source_url: string; source_kind: string; vigency_verified: boolean }>).map((source) => <article className="source-card" key={source.source_url}><div className="source-meta"><span className={source.source_kind === "official" ? "badge official" : "badge synthetic"}>{source.source_kind === "official" ? "Fonte oficial" : "Documento sintetico"}</span><span>{source.vigency_verified ? "Vigencia verificada" : "Vigencia nao verificada"}</span></div><b>{source.title}</b><p>{source.excerpt}</p><a href={source.source_url} target="_blank" rel="noreferrer">Abrir fonte ↗</a></article>)}
            {result && !Array.isArray(result.result.sources) && <div className="erp-source"><span className="source-symbol">▤</span><div><b>ERP demonstrativo</b><small>Base sintetica · sem registros reais</small><small>Periodo: {String((result.result.current_period as { start?: string } | undefined)?.start ?? "2025-10-01")} a {String((result.result.current_period as { end?: string } | undefined)?.end ?? "2025-12-31")}</small><small>ID da execucao: {result.run_id.slice(0, 12)}</small></div></div>}
          </section>
        </div>
        {result && <section className="panel result-panel"><div className="result-heading"><div><p className="eyebrow">RESULTADO · {result.intent.toUpperCase()}</p><h2>{result.answer}</h2><span className="muted">{result.model ? `Explicacao local: ${result.model}` : "Explicacao deterministica · modelo local indisponivel"}</span></div>{result.human_review_required && <span className="review-tag">Revisao humana pendente</span>}</div>
          {result.intent === "report" && <div className="table-wrap"><table><thead><tr><th>Secretaria</th><th>Trimestre anterior</th><th>Trimestre atual</th><th>Variacao</th><th>Variacao %</th></tr></thead><tbody>{Object.entries((result.result.departments ?? {}) as Record<string, { previous: string; current: string; absolute_change: string; percentage_change: string | null }>).map(([name, row]) => <tr key={name}><td>{name}</td><td>{money(row.previous)}</td><td>{money(row.current)}</td><td>{money(row.absolute_change)}</td><td>{row.percentage_change === null ? "N/A: sem base positiva" : `${row.percentage_change}%`}</td></tr>)}</tbody></table></div>}
          {result.intent === "audit" && <p className="muted">{JSON.stringify(result.result)} Nenhum alerta determina fraude, bloqueio de pagamento ou recuperacao.</p>}
        </section>}
        {tab === "Controle interno" && <section className="panel audit-panel"><div className="panel-title"><div><span className="panel-icon">◇</span><div><b>Auditoria explicavel</b><small>Regras deterministicas · decisao humana pelo auditor</small></div></div><button onClick={runAudit} disabled={busy}>{busy ? "Verificando..." : "Executar regras de auditoria"}</button></div><p className="muted">Uma correspondencia e um pedido de revisao, nao uma acusacao de fraude.</p>{findings.map((item) => <article className="finding" key={item.id}><b>Possivel pagamento duplicado</b><span className="review-tag">{reviewLabel(item.status)}</span><p>Registros: {item.record_ids.join(", ")} · documento {item.evidence.invoice_reference} · {money(item.evidence.amount)}</p>{item.review_note && <p>Justificativa: {item.review_note}</p>}{item.status === "pending_review" && session.role === "auditor" && <form className="review-form" onSubmit={(event) => reviewFinding(event, item.id)}><label>Decisão da revisão<select name="decision" defaultValue="confirmed"><option value="confirmed">Confirmar ocorrência</option><option value="rejected">Rejeitar ocorrência</option><option value="needs_information">Solicitar mais informações</option></select></label><label>Justificativa da decisão<textarea name="note" minLength={12} maxLength={800} required placeholder="Registre a evidência revisada e o motivo da decisão." /></label><button>Registrar decisão</button></form>}</article>)}</section>}
        {tab === "Competitividade" && <section className="panel audit-panel">
          <div className="panel-title"><div><span className="panel-icon">CLP</span><div><b>Ranking publico de competitividade</b><small>Resultado publicado pelo CLP - edicao 2026</small></div></div></div>
          {!ranking && <p className="muted">Carregando resultado publicado...</p>}
          {ranking && !ranking.available && <><p className="muted">{ranking.message}</p><a href={ranking.source_url} target="_blank" rel="noreferrer">Consultar escopo e metodologia do CLP</a></>}
          {ranking?.available && <>
            <p className="muted">{ranking.municipality_name} · populacao de referencia {ranking.population?.toLocaleString("pt-BR")} · posicao geral {ranking.overall_rank} · nota {Number(ranking.overall_score).toFixed(2)}. Delta de posicao: {ranking.rank_change ?? "nao comparavel"}.</p>
            <div className="table-wrap"><table><thead><tr><th>Pilar</th><th>Nota CLP</th><th>Posicao</th><th>Delta</th></tr></thead><tbody>{Object.entries(ranking.pillars ?? {}).map(([name, item]) => <tr key={name}><td>{name}</td><td>{item.score.toFixed(2)}</td><td>{item.rank}</td><td>{item.rank_change ?? "nao comparavel"}</td></tr>)}</tbody></table></div>
            <p className="muted">Dados importados da planilha oficial; esta aplicacao nao recalcula notas ou posicoes. SHA-256: {ranking.source_sha256}</p>
            <a href={ranking.source_url} target="_blank" rel="noreferrer">Abrir planilha do CLP</a>
          </>}
        </section>}
        </>}
        <footer className="footer"><span>GovERP AI Lab · demonstracao local</span><span>Fontes, calculos e permissoes verificaveis</span></footer>
      </section>
    </main>
  </div>;
}

function reviewLabel(status: string) {
  return ({ pending_review: "Pendente de revisao", confirmed: "confirmed · Confirmado", rejected: "rejected · Rejeitado", needs_information: "needs_information · Informacoes solicitadas" } as Record<string, string>)[status] ?? status;
}

function ReportTable({ report }: { report: Report }) {
  const entries = Object.entries(report.departments);
  return <div className="table-wrap"><table>
    <caption className="table-caption">Pagamentos por secretaria · comparacao entre periodos</caption>
    <thead><tr><th scope="col">Secretaria</th><th scope="col">Periodo anterior</th><th scope="col">Periodo atual</th><th scope="col">Variacao</th><th scope="col">Variacao %</th></tr></thead>
    <tbody>{entries.length ? entries.map(([name, row]) => <tr key={name}>
      <th scope="row">{name}</th><td>{money(row.previous)}</td><td>{money(row.current)}</td><td>{money(row.absolute_change)}</td><td>{row.percentage_change === null ? "N/A: sem base positiva" : `${row.percentage_change}%`}</td>
    </tr>) : <tr><td colSpan={5}>Sem pagamentos no periodo consultado.</td></tr>}</tbody>
  </table></div>;
}

function money(value: string | undefined) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value ?? 0));
}
