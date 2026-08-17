import { expect, test } from '@playwright/test'


test.skip('affiche le socle Mentor IA après authentification', async ({ page }) => {
  // Ce scénario sera activé quand un utilisateur Keycloak de test sera fourni
  // par l'environnement d'intégration continue.
  await page.goto('/')
  await expect(page.locator('h1')).toHaveText('Mentor IA')
})
