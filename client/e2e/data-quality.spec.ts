import { test, expect } from '@playwright/test';

test.describe('Data Quality Dashboard', () => {
  const mockChecks = [
    {
      id: '1',
      check_id: 'schema_validation',
      started_at: '2024-01-15T10:00:00Z',
      completed_at: '2024-01-15T10:00:05Z',
      status: 'passed',
      records_checked: 1500,
      issues_found: 0,
      duration_ms: 5000,
      summary: 'All records passed validation',
    },
    {
      id: '2',
      check_id: 'freshness_check',
      started_at: '2024-01-15T09:00:00Z',
      completed_at: '2024-01-15T09:00:02Z',
      status: 'warning',
      records_checked: 500,
      issues_found: 3,
      duration_ms: 2000,
      summary: 'Some records are stale',
    },
    {
      id: '3',
      check_id: 'integrity_check',
      started_at: '2024-01-15T08:00:00Z',
      completed_at: '2024-01-15T08:00:10Z',
      status: 'failed',
      records_checked: 2000,
      issues_found: 15,
      duration_ms: 10000,
      summary: 'Orphaned records detected',
    },
  ];

  const mockIssues = [
    {
      id: '1',
      severity: 'critical',
      issue_type: 'missing_field',
      table_name: 'trading_disclosures',
      field_name: 'ticker',
      record_id: 'rec-123',
      description: 'Missing ticker symbol for disclosure',
      status: 'open',
      created_at: '2024-01-15T10:00:00Z',
    },
    {
      id: '2',
      severity: 'warning',
      issue_type: 'stale_data',
      table_name: 'politicians',
      field_name: 'last_updated',
      record_id: 'rec-456',
      description: 'Politician data not updated in 30+ days',
      status: 'open',
      created_at: '2024-01-14T10:00:00Z',
    },
  ];

  const mockCorrections = [
    {
      id: '1',
      record_id: 'rec-789',
      table_name: 'trading_disclosures',
      field_name: 'ticker',
      old_value: 'FB',
      new_value: 'META',
      correction_type: 'ticker_rename',
      confidence_score: 0.95,
      corrected_by: 'auto',
      status: 'applied',
      created_at: '2024-01-15T09:00:00Z',
    },
    {
      id: '2',
      record_id: 'rec-012',
      table_name: 'trading_disclosures',
      field_name: 'transaction_date',
      old_value: '01/15/2024',
      new_value: '2024-01-15',
      correction_type: 'date_format',
      confidence_score: 0.99,
      corrected_by: 'auto',
      status: 'applied',
      created_at: '2024-01-15T08:00:00Z',
    },
  ];

  test.beforeEach(async ({ page }) => {
    // Mock quality results API
    await page.route('**/rest/v1/data_quality_results**', (route) =>
      route.fulfill({
        status: 200,
        json: mockChecks,
      })
    );

    // Mock quality issues API
    await page.route('**/rest/v1/data_quality_issues**', (route) =>
      route.fulfill({
        status: 200,
        json: mockIssues,
      })
    );

    // Mock quality corrections API
    await page.route('**/rest/v1/data_quality_corrections**', (route) =>
      route.fulfill({
        status: 200,
        json: mockCorrections,
      })
    );

    await page.goto('/admin/data-quality');
  });

  test.describe('Page Structure', () => {
    test('should display dashboard heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /data quality dashboard/i })).toBeVisible();
    });

    test('should display description', async ({ page }) => {
      await expect(page.getByText(/monitor data quality checks/i)).toBeVisible();
    });

    test('should display refresh button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
    });
  });

  test.describe('Metrics Cards', () => {
    test('should display pass rate card', async ({ page }) => {
      await expect(page.getByText(/pass rate/i)).toBeVisible();
    });

    test('should display critical issues card', async ({ page }) => {
      await expect(page.getByText(/critical issues/i)).toBeVisible();
    });

    test('should display warnings card', async ({ page }) => {
      await expect(page.getByText(/warnings/i)).toBeVisible();
    });

    test('should display auto-corrections card', async ({ page }) => {
      await expect(page.getByText('Auto-Corrections', { exact: true })).toBeVisible();
    });

    test('should display last check card', async ({ page }) => {
      await expect(page.getByText(/last check/i)).toBeVisible();
    });
  });

  test.describe('Critical Alert', () => {
    test('should show critical alert when issues exist', async ({ page }) => {
      await expect(page.getByText(/critical issue\(s\) require immediate attention/i)).toBeVisible();
    });
  });

  test.describe('Tabs Navigation', () => {
    test('should display all tabs', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /recent checks/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /open issues/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /corrections/i })).toBeVisible();
    });

    test('should show issue count badge on Open Issues tab', async ({ page }) => {
      const issuesTab = page.getByRole('tab', { name: /open issues/i });
      await expect(issuesTab).toContainText('2');
    });
  });

  test.describe('Recent Checks Tab', () => {
    test('should display checks table', async ({ page }) => {
      await expect(page.getByText(/recent quality checks/i)).toBeVisible();
    });

    test('should display check IDs', async ({ page }) => {
      await expect(page.getByText('schema_validation')).toBeVisible();
      await expect(page.getByText('freshness_check')).toBeVisible();
    });

    test('should display status badges', async ({ page }) => {
      await expect(page.getByText(/passed/i).first()).toBeVisible();
      await expect(page.getByText(/warning/i).first()).toBeVisible();
      await expect(page.getByText(/failed/i).first()).toBeVisible();
    });

    test('should display records checked count', async ({ page }) => {
      await expect(page.getByText('1,500')).toBeVisible();
    });

    test('should display issues found', async ({ page }) => {
      // Check that issues column exists
      await expect(page.getByRole('columnheader', { name: /issues/i })).toBeVisible();
    });
  });

  test.describe('Open Issues Tab', () => {
    test('should switch to issues tab', async ({ page }) => {
      await page.getByRole('tab', { name: /open issues/i }).click();
      await expect(page.getByText(/open data quality issues/i)).toBeVisible();
    });

    test('should display issue severity badges', async ({ page }) => {
      await page.getByRole('tab', { name: /open issues/i }).click();
      await expect(page.getByRole('cell').filter({ hasText: 'critical' }).first()).toBeVisible();
    });

    test('should display issue descriptions', async ({ page }) => {
      await page.getByRole('tab', { name: /open issues/i }).click();
      await expect(page.getByText(/missing ticker symbol/i)).toBeVisible();
    });

    test('should display resolve and ignore buttons', async ({ page }) => {
      await page.getByRole('tab', { name: /open issues/i }).click();
      await expect(page.getByRole('button', { name: /resolve/i }).first()).toBeVisible();
      await expect(page.getByRole('button', { name: /ignore/i }).first()).toBeVisible();
    });

    test('should display table names', async ({ page }) => {
      await page.getByRole('tab', { name: /open issues/i }).click();
      await expect(page.getByRole('cell').filter({ hasText: 'trading_disclosures' }).first()).toBeVisible();
    });
  });

  test.describe('Corrections Tab', () => {
    test('should switch to corrections tab', async ({ page }) => {
      await page.getByRole('tab', { name: /corrections/i }).click();
      await expect(page.getByText(/auto-corrections audit trail/i)).toBeVisible();
    });

    test('should display correction types', async ({ page }) => {
      await page.getByRole('tab', { name: /corrections/i }).click();
      await expect(page.getByText('ticker_rename')).toBeVisible();
      await expect(page.getByText('date_format')).toBeVisible();
    });

    test('should display old and new values', async ({ page }) => {
      await page.getByRole('tab', { name: /corrections/i }).click();
      await expect(page.getByText('FB')).toBeVisible();
      await expect(page.getByText('META')).toBeVisible();
    });

    test('should display confidence scores', async ({ page }) => {
      await page.getByRole('tab', { name: /corrections/i }).click();
      await expect(page.getByText('95%')).toBeVisible();
      await expect(page.getByText('99%')).toBeVisible();
    });

    test('should display rollback button for applied corrections', async ({ page }) => {
      await page.getByRole('tab', { name: /corrections/i }).click();
      await expect(page.getByRole('button', { name: /rollback/i }).first()).toBeVisible();
    });
  });

  test.describe('Loading State', () => {
    test('should show loading spinner while fetching', async ({ page }) => {
      const slowPage = await page.context().newPage();

      await slowPage.route('**/rest/v1/data_quality_results**', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await route.fulfill({ status: 200, json: mockChecks });
      });

      await slowPage.route('**/rest/v1/data_quality_issues**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await slowPage.route('**/rest/v1/data_quality_corrections**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await slowPage.goto('/admin/data-quality');
      await expect(slowPage.locator('.animate-spin').first()).toBeVisible();
      await slowPage.close();
    });
  });

  test.describe('Empty States', () => {
    test('should show empty state for no checks', async ({ page }) => {
      const emptyPage = await page.context().newPage();

      await emptyPage.route('**/rest/v1/data_quality_results**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await emptyPage.route('**/rest/v1/data_quality_issues**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await emptyPage.route('**/rest/v1/data_quality_corrections**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await emptyPage.goto('/admin/data-quality');
      await expect(emptyPage.getByText(/no quality checks have run yet/i)).toBeVisible();
      await emptyPage.close();
    });

    test('should show success message for no open issues', async ({ page }) => {
      const noIssuesPage = await page.context().newPage();

      await noIssuesPage.route('**/rest/v1/data_quality_results**', (route) =>
        route.fulfill({ status: 200, json: mockChecks })
      );

      await noIssuesPage.route('**/rest/v1/data_quality_issues**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await noIssuesPage.route('**/rest/v1/data_quality_corrections**', (route) =>
        route.fulfill({ status: 200, json: mockCorrections })
      );

      await noIssuesPage.goto('/admin/data-quality');
      await noIssuesPage.getByRole('tab', { name: /open issues/i }).click();
      await expect(noIssuesPage.getByText(/no open issues/i)).toBeVisible();
      await noIssuesPage.close();
    });
  });

  test.describe('Refresh Functionality', () => {
    test('should have refresh button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
    });

    test('should be clickable', async ({ page }) => {
      const refreshButton = page.getByRole('button', { name: /refresh/i });
      await expect(refreshButton).toBeEnabled();
    });
  });
});
