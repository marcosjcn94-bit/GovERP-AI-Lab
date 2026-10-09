import { expect, test } from "@playwright/test";

async function enter(page: import("@playwright/test").Page, email = "gestor@demo.pr.gov.br") {
  await page.getByLabel("Email demonstrativo").fill(email);
  await page.getByRole("button", { name: "Acessar demonstracao" }).click();
  await expect(page.getByRole("heading", { name: "Assistente de gestao municipal" })).toBeVisible();
}

test("logout limpa relatorio, fontes e ranking antes de entrar como cidadao", async ({ page }) => {
  await page.goto("/");
  await enter(page);
  await page.getByRole("button", { name: "Relatorios", exact: true }).click();
  await page.getByRole("button", { name: "Gerar relatório" }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await page.getByRole("button", { name: "Conhecimento", exact: true }).click();
  await page.getByLabel("Buscar fontes municipais").fill("ISS");
  await page.getByRole("button", { name: "Buscar fontes" }).click();
  await expect(page.locator(".knowledge-source")).not.toHaveCount(0);
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await enter(page, "cidadao@demo.pr.gov.br");
  await page.getByRole("button", { name: "Relatorios", exact: true }).click();
  await expect(page.getByRole("table")).toHaveCount(0);
  await page.getByRole("button", { name: "Conhecimento", exact: true }).click();
  await expect(page.locator(".knowledge-source")).toHaveCount(0);
  await expect(page.getByLabel("Buscar fontes municipais")).toHaveValue("");
});

test("resposta atrasada nao restaura resultado apos logout", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/assistant", async route => {
    const response = await route.fetch();
    await gate;
    await route.fulfill({ response }).catch(() => undefined);
  });
  await page.goto("/");
  await enter(page);
  const requested = page.waitForRequest("**/api/assistant");
  await page.getByRole("button", { name: "Consultar" }).click();
  await requested;
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page.getByRole("button", { name: "Acessar demonstracao" })).toBeVisible();
  release();
  await enter(page, "cidadao@demo.pr.gov.br");
  await expect(page.locator(".result-panel")).toHaveCount(0);
});

test("sessao expirada limpa dados e informa motivo", async ({ page }) => {
  await page.goto("/");
  await enter(page);
  await page.route("**/api/assistant", route => route.fulfill({ status: 401, json: { detail: "Sessao invalida ou expirada" } }));
  await page.getByRole("button", { name: "Consultar" }).click();
  await expect(page.getByRole("button", { name: "Acessar demonstracao" })).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("expirada");
});

test("falha no logout informa revogacao pendente e oculta dados", async ({ page }) => {
  await page.goto("/");
  await enter(page);
  await page.route("**/api/auth/logout", route => route.fulfill({ status: 503, json: { detail: "Banco local indisponivel" } }));
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page.getByRole("button", { name: "Acessar demonstracao" })).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("revogacao");
});

test("troca de municipio limpa resultados anteriores", async ({ page }) => {
  await page.goto("/");
  await enter(page, "auditor@demo.pr.gov.br");
  await page.getByRole("button", { name: "Consultar" }).click();
  await expect(page.locator(".result-panel")).toBeVisible();
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await page.getByLabel("Municipio").selectOption("4113700");
  await enter(page, "auditor@demo.pr.gov.br");
  await expect(page.locator(".result-panel")).toHaveCount(0);
});

test("pergunta vazia apos sucesso remove resultado e mostra validacao", async ({ page }) => {
  await page.goto("/");
  await enter(page);
  await page.getByRole("button", { name: "Consultar" }).click();
  await expect(page.locator(".result-panel")).toBeVisible();
  await page.getByLabel("O que voce precisa consultar?").fill("   ");
  await page.getByRole("button", { name: "Consultar" }).click();
  await expect(page.getByRole("alert")).toContainText("question");
  await expect(page.locator(".result-panel")).toHaveCount(0);
});
