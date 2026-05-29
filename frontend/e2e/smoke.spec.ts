import { expect, test } from '@playwright/test';

test.describe('ProjectForge UI smoke', () => {
  test('landing page renders primary navigation', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'ProjectForge AI' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Open dashboard' })).toBeVisible();
  });

  test('projects page shows create form', async ({ page }) => {
    await page.goto('/projects');
    await expect(page.getByRole('heading', { level: 1, name: 'Projects' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Create project' })).toBeVisible();
  });

  test('login page renders sign-in form', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });
});
