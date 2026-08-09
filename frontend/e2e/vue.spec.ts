import { test, expect } from '@playwright/test'

test('affiche la page d’accueil publique', async ({ page }) => {
  await page.goto('/')

  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'Le bon prénom, c’est celui que vous aimez ensemble.',
    }),
  ).toBeVisible()
})
