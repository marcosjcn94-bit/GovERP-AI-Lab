import { expect, test } from "@playwright/test";

for (const size of [{ width: 390, height: 844 }, { width: 1440, height: 900 }]) {
  test(`todas as abas sem overflow em ${size.width}x${size.height}`, async ({ page }) => {
    await page.setViewportSize(size);
    await page.goto("/");
    await expect(page.getByRole("button", { name: "Acessar demonstracao" })).toBeEnabled();
    expect((await page.request.get("/favicon.svg")).status()).toBe(200);
    await page.getByRole("button", { name: "Acessar demonstracao" }).click();
    await expect(page.getByRole("heading", { name: "Assistente de gestao municipal" })).toBeVisible();
    for (const tab of ["Visao geral", "Relatorios", "Controle interno", "Conhecimento", "Competitividade"]) {
      await page.getByRole("button", { name: tab, exact: true }).click();
      if (tab === "Relatorios") {
        await page.getByRole("button", { name: "Gerar relatório" }).click();
        await expect(page.getByRole("table")).toBeVisible();
      }
      if (tab === "Conhecimento") {
        await page.getByLabel("Buscar fontes municipais").fill("ISS");
        await page.getByRole("button", { name: "Buscar fontes" }).click();
        await expect(page.locator(".knowledge-source")).not.toHaveCount(0);
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
      await page.screenshot({ path: `../.runtime/ui-${size.width}-${tab.replaceAll(" ", "-")}.png`, fullPage: true });
    }
  });
}

test("hash longo do ranking permanece contido em mobile", async ({ page }) => {
  await page.route("**/api/public/rankings/*", route => route.fulfill({ json: {
    available: true, municipality_name: "Curitiba", population: 1, overall_rank: 1,
    overall_score: "1.00", pillars: {}, source_url: "https://example.org/test", source_sha256: "a".repeat(64),
  } }));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Acessar demonstracao" })).toBeEnabled();
  await page.getByRole("button", { name: "Acessar demonstracao" }).click();
  await page.getByRole("button", { name: "Competitividade", exact: true }).click();
  await expect(page.getByText("a".repeat(64), { exact: false })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});
