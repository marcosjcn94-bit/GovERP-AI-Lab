import { FormEvent, useEffect, useState } from "react";

type City = { id: string; name: string; uf: string };
type Session = { user_id: string; display_name: string; role: string; municipality_id: string; municipality_name: string; csrf_token: string };
type Finding = { id: string; rule_id: string; record_ids: string[]; evidence: Record<string, string>; status: string; review_note?: string };
type RunResult = { run_id: string; intent: string; answer: string; model?: string; model_fallback: boolean; result: Record<string, unknown>; human_review_required: boolean };
type Ranking = { available: boolean; municipality_name?: string; edition_year?: number; population?: number; overall_score?: string; overall_rank?: number; rank_change?: number | null; pillars?: Record<string, { score: number; rank: number; rank_change: number | null }>; source_url: string; source_sha256?: string; message?: string };

async function api<T>(path: string, init: RequestInit = {}, csrf?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("content-type", "application/json");
  if (csrf) headers.set("x-csrf-token", csrf);
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Falha na requisicao local." }));
    throw new Error(body.detail ?? `Erro HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
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
    setBusy(true); setError("");
    try { setResult(await api("/api/assistant", { method: "POST", body: JSON.stringify({ question }) }, session.csrf_token)); }
    catch (e) { setError(e instanceof Error ? e.message : "Consulta nao concluida."); }
    finally { setBusy(false); }
  }

  async function loadFindings() {
    if (!session) return;
    try { setFindings(await api<Finding[]>("/api/audits/findings")); }
    catch (e) { setError(e instanceof Error ? e.message : "Falha ao carregar auditoria."); }
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
      const outcome = await api<{ examined: number; possible_duplicates: number; new_findings: number }>("/api/audits/run", { method: "POST" }, session.csrf_token);
      setResult({ run_id: crypto.randomUUID(), intent: "audit", answer: `${outcome.possible_duplicates} possiveis duplicidades; ${outcome.new_findings} novos achados. Revise cada evidência.`, model_fallback: true, result: outcome, human_review_required: outcome.possible_duplicates > 0 });
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
      {[["Visao geral", "◫"], ["Relatorios", "▤"], ["Controle interno", "◇"], ["Conhecimento", "⌕"], ["Competitividade", "CLP"]].map(([label, icon]) => <button key={label} className={`nav-item ${tab === label ? "active" : ""}`} onClick={() => { setTab(label); if (label === "Controle interno") loadFindings(); if (label === "Competitividade") loadRanking(); }}>{icon}<span>{label}</span></button>)}
      <div className="sidebar-bottom"><span className="online-dot" />Execucao somente local<small>Sem custo de modelo</small></div>
    </aside>
    <main className="workspace">
      <header className="topbar"><div><span className="breadcrumb">GovERP AI Lab</span><span className="slash">/</span><b>{tab}</b></div><div className="user-menu"><span className="city-tag">{session.municipality_name} · PR</span><span className="avatar">{session.display_name.slice(0, 1).toUpperCase()}</span><span>{session.display_name}</span><button className="text-button" onClick={logout}>Sair</button></div></header>
      <section className="page-content">
        <div className="page-heading"><div><p className="eyebrow">{session.municipality_name.toUpperCase()} · AMBIENTE DEMONSTRATIVO</p><h1>{tab === "Visao geral" ? "Assistente de gestao municipal" : tab}</h1><p className="muted">Consulte, confira os dados de origem e revise resultados antes de agir.</p></div><span className="read-only"><span className="lock">⌑</span> ERP em modo leitura</span></div>
        <div className="notice"><span>ⓘ</span><span><b>Dados inteiramente sinteticos.</b> Nomes dos municipios e fontes oficiais sao identificados separadamente.</span></div>
        <div className="content-grid">
          <section className="panel ask-panel">
            <div className="panel-title"><div><span className="sparkle">✳</span><div><b>Assistente municipal</b><small>Respostas ligadas a dados e documentos da cidade selecionada</small></div></div><span className="model-chip">QWEN · LOCAL</span></div>
            <form onSubmit={ask}><label htmlFor="question">O que voce precisa consultar?</label><textarea id="question" rows={4} maxLength={512} value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ex.: Compare despesas pagas do ultimo trimestre por secretaria."/><div className="prompt-bottom"><span>O calculo fica no backend. O modelo apenas organiza a explicacao.</span><button disabled={busy}>{busy ? "Consultando..." : "Consultar  →"}</button></div></form>
            {error && <p className="error" role="alert">{error}</p>}
            <div className="suggestions"><small>SUGESTOES</small><button onClick={() => setQuestion("Compare as despesas pagas por secretaria e mostre a memoria de calculo.")}>Despesas pagas no trimestre <span>↗</span></button><button onClick={() => setQuestion("Quais pagamentos precisam de revisao e por que?")}>Achados que precisam de revisao <span>↗</span></button><button onClick={() => { setQuestion("Qual a fonte oficial sobre ISS e iluminacao publica em Curitiba?"); setTab("Conhecimento"); }}>Localizar fonte e vigencia <span>↗</span></button></div>
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
        {tab === "Controle interno" && <section className="panel audit-panel"><div className="panel-title"><div><span className="panel-icon">◇</span><div><b>Auditoria explicavel</b><small>Regras deterministicas · revisao por servidor</small></div></div><button onClick={runAudit} disabled={busy}>Executar regras de auditoria</button></div><p className="muted">Uma correspondencia e um pedido de revisao, nao uma acusacao de fraude.</p>{findings.map((item) => <article className="finding" key={item.id}><b>Possivel pagamento duplicado</b><span className="review-tag">{item.status}</span><p>Registros: {item.record_ids.join(", ")} · documento {item.evidence.invoice_reference} · {money(item.evidence.amount)}</p></article>)}</section>}
        {tab === "Competitividade" && <section className="panel audit-panel">
          <div className="panel-title"><div><span className="panel-icon">CLP</span><div><b>Ranking publico de competitividade</b><small>Resultado publicado pelo CLP - edicao 2026</small></div></div></div>
          {!ranking && <p className="muted">Carregando resultado publicado...</p>}
          {ranking && !ranking.available && <><p className="muted">{ranking.message}</p><a href={ranking.source_url} target="_blank" rel="noreferrer">Consultar escopo e metodologia do CLP</a></>}
          {ranking?.available && <>
            <p className="muted">{ranking.municipality_name} ? populacao de referencia {ranking.population?.toLocaleString("pt-BR")} ? posicao geral {ranking.overall_rank} ? nota {Number(ranking.overall_score).toFixed(2)}. Delta de posicao: {ranking.rank_change ?? "nao comparavel"}.</p>
            <div className="table-wrap"><table><thead><tr><th>Pilar</th><th>Nota CLP</th><th>Posicao</th><th>Delta</th></tr></thead><tbody>{Object.entries(ranking.pillars ?? {}).map(([name, item]) => <tr key={name}><td>{name}</td><td>{item.score.toFixed(2)}</td><td>{item.rank}</td><td>{item.rank_change ?? "nao comparavel"}</td></tr>)}</tbody></table></div>
            <p className="muted">Dados importados da planilha oficial; esta aplicacao nao recalcula notas ou posicoes. SHA-256: {ranking.source_sha256}</p>
            <a href={ranking.source_url} target="_blank" rel="noreferrer">Abrir planilha do CLP</a>
          </>}
        </section>}
        <footer className="footer"><span>GovERP AI Lab · demonstracao local</span><span>Fontes, calculos e permissoes verificaveis</span></footer>
      </section>
    </main>
  </div>;
}

function money(value: string | undefined) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value ?? 0));
}
