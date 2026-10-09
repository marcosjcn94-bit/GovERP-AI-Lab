import { expect, test, type APIRequestContext } from "@playwright/test";

const base = "http://127.0.0.1:8001";
async function login(request: APIRequestContext, email = "auditor@demo.pr.gov.br", city = "4106902") {
  const response = await request.post(`${base}/api/auth/login`, { data: {
    email, password: "Local-Demo-Only-2026!", municipality_id: city,
  } });
  expect(response.status()).toBe(200);
  return { "x-csrf-token": (await response.json()).csrf_token };
}
async function pending(request: APIRequestContext, headers: Record<string, string>) {
  expect((await request.post(`${base}/api/audits/run`, { headers })).status()).toBe(200);
  const findings = await (await request.get(`${base}/api/audits/findings?limit=200`)).json();
  return findings.find((item: { status: string }) => item.status === "pending_review").id as string;
}

for (const decision of ["confirmed", "rejected", "needs_information"]) {
  test(`revisao ${decision} preserva decisao e impede nova revisao`, async ({ request }) => {
    const headers = await login(request);
    const id = await pending(request, headers);
    const data = { decision, note: "Evidencias sinteticas revisadas para este teste." };
    const response = await request.post(`${base}/api/audits/findings/${id}/review`, { headers, data });
    expect(response.status()).toBe(200);
    expect((await response.json()).status).toBe(decision);
    expect((await request.post(`${base}/api/audits/findings/${id}/review`, { headers, data })).status()).toBe(409);
  });
}

test("revisoes simultaneas persistem somente uma decisao", async ({ request }) => {
  const headers = await login(request);
  const id = await pending(request, headers);
  const decisions = ["confirmed", "rejected"];
  const responses = await Promise.all(decisions.map(decision => request.post(
    `${base}/api/audits/findings/${id}/review`, { headers, data: { decision, note: "Revisao concorrente com evidencia sintetica." } },
  )));
  expect(responses.map(response => response.status()).sort()).toEqual([200, 409]);
  const winner = await responses.find(response => response.status() === 200)!.json();
  const findings = await (await request.get(`${base}/api/audits/findings?limit=200`)).json();
  expect(findings.find((item: { id: string }) => item.id === id).status).toBe(winner.status);
});

test("validacao, CSRF, perfil e municipio protegem os contratos", async ({ request }) => {
  const headers = await login(request);
  const id = await pending(request, headers);
  const url = `${base}/api/audits/findings/${id}/review`;
  const data = { decision: "confirmed", note: "Revisao demonstrativa com evidencias." };
  expect((await request.post(url, { data })).status()).toBe(403);
  expect((await request.post(url, { headers, data: { ...data, note: "   " } })).status()).toBe(422);
  expect((await request.get(`${base}/api/reports/paid-by-department?start=2025-12-31&end=2025-01-01`)).status()).toBe(422);
  expect((await request.post(`${base}/api/assistant`, { headers, data: { question: "   " } })).status()).toBe(422);
  const manager = await login(request, "gestor@demo.pr.gov.br");
  expect((await request.post(url, { headers: manager, data })).status()).toBe(403);
  const otherCity = await login(request, "auditor@demo.pr.gov.br", "4113700");
  expect((await request.post(url, { headers: otherCity, data })).status()).toBe(404);
});
