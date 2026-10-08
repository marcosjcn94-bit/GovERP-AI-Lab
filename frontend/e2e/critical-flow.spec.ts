import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Acessar demonstracao" })).toBeEnabled();
});

test("gestor consulta calculo deterministico com modelo indisponivel e encerra sessao", async ({ page }) => {
  await page.getByRole("button", { name: "Acessar demonstracao" }).click();
  await expect(page.getByRole("heading", { name: "Assistente de gestao municipal" })).toBeVisible();
  const assistantResponse = page.waitForResponse(response => response.url().endsWith("/api/assistant") && response.status() === 200);
  await page.getByRole("button", { name: "Consultar" }).click();
  const response = await assistantResponse;
  const requestId = response.headers()["x-request-id"];
  expect(requestId).toMatch(/^[0-9a-f-]{36}$/i);
  expect((await response.json()).run_id).toBe(requestId);
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Trimestre atual" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Saude", exact: true })).toBeVisible();
  await expect(page.getByText("Explicacao deterministica · modelo local indisponivel")).toBeVisible();
  await expect(page.getByText("ID da execucao:")).toBeVisible();
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page.getByRole("button", { name: "Acessar demonstracao" })).toBeVisible();
});

test("cidadao recebe recusa ao solicitar dados financeiros", async ({ page }) => {
  await page.getByLabel("Email demonstrativo").fill("cidadao@demo.pr.gov.br");
  await page.getByRole("button", { name: "Acessar demonstracao" }).click();
  await expect(page.getByRole("heading", { name: "Assistente de gestao municipal" })).toBeVisible();
  const denied = page.waitForResponse(response => response.url().endsWith("/api/assistant") && response.status() === 403);
  await page.getByRole("button", { name: "Consultar" }).click();
  await denied;
  await expect(page.getByRole("alert")).toHaveText("Perfil sem permissao para esta operacao");
  await expect(page.getByRole("table")).toHaveCount(0);
});

test("gestor nao pode entrar em municipio fora de seu escopo", async ({ page }) => {
  await page.getByLabel("Municipio").selectOption("4113700");
  await page.getByRole("button", { name: "Acessar demonstracao" }).click();
  await expect(page.getByRole("alert")).toHaveText("Municipio nao autorizado");
  await expect(page.getByRole("button", { name: "Acessar demonstracao" })).toBeVisible();
});

test("gestor consulta relatorio por periodo na aba propria", async ({ page }) => {
  await page.getByRole("button", { name: "Acessar demonstracao" }).click();
  await page.getByRole("button", { name: "Relatorios" }).click();
  await expect(page.getByRole("heading", { name: "Comparativo de despesas pagas" })).toBeVisible();
  await page.getByLabel("Data inicial").fill("2025-10-01");
  await page.getByLabel("Data final").fill("2025-12-31");
  await page.getByRole("button", { name: "Gerar relatório" }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("rowheader", { name: "Saude", exact: true })).toBeVisible();
});

test("gestor pesquisa fonte municipal pela aba conhecimento", async ({ page }) => {
  await page.getByRole("button", { name: "Acessar demonstracao" }).click();
  await page.getByRole("button", { name: "Conhecimento" }).click();
  await expect(page.getByRole("heading", { name: "Fontes e vigência documental" })).toBeVisible();
  await page.getByLabel("Buscar fontes municipais").fill("ISS");
  await page.getByRole("button", { name: "Buscar fontes" }).click();
  await expect(page.getByText("Lei Complementar 40 de 2001", { exact: false })).toBeVisible();
  await expect(page.getByText("Vigência não verificada", { exact: false })).toBeVisible();
});

test("auditor decide achado demonstrativo com justificativa", async ({ page }) => {
  await page.getByLabel("Email demonstrativo").fill("gestor@demo.pr.gov.br");
  await page.getByRole("button", { name: "Acessar demonstracao" }).click();
  await page.getByRole("button", { name: "Controle interno" }).click();
  await page.getByRole("button", { name: "Executar regras de auditoria" }).click();
  await expect(page.locator(".finding").first()).toBeVisible();
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await page.getByLabel("Email demonstrativo").fill("auditor@demo.pr.gov.br");
  await page.getByRole("button", { name: "Acessar demonstracao" }).click();
  await page.getByRole("button", { name: "Controle interno" }).click();

  const finding = page.locator(".finding").first();
  await finding.getByLabel("Decisão da revisão").selectOption("confirmed");
  await finding.getByLabel("Justificativa da decisão").fill("Documentos conferidos pelo auditor.");
  await finding.getByRole("button", { name: "Registrar decisão" }).click();
  await expect(finding).toContainText("confirmed");
  await expect(finding).toContainText("Documentos conferidos pelo auditor.");
});

test("gestor pode consultar achados mas nao recebe controles de revisao", async ({ page }) => {
  await page.getByRole("button", { name: "Acessar demonstracao" }).click();
  await page.getByRole("button", { name: "Controle interno" }).click();
  await expect(page.locator(".finding").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Registrar decisão" })).toHaveCount(0);
});

test("conhecimento permanece dentro da largura em viewport mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Acessar demonstracao" }).click();
  await page.getByRole("button", { name: "Conhecimento" }).click();
  await page.getByLabel("Buscar fontes municipais").fill("ISS");
  await page.getByRole("button", { name: "Buscar fontes" }).click();
  await expect(page.getByText("Lei Complementar 40 de 2001", { exact: false })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});
