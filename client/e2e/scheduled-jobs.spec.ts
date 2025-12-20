import { test, expect } from '@playwright/test';

test.describe('Scheduled Jobs Page', () => {
  const mockJobs = [
    {
      job_id: 'data-collection',
      job_name: 'Data Collection',
      schedule_type: 'cron',
      schedule_value: '0 */6 * * *',
      enabled: true,
      next_scheduled_run: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
      metadata: { description: 'Collect politician trading data' }
    },
    {
      job_id: 'signal-generation',
      job_name: 'Signal Generation',
      schedule_type: 'cron',
      schedule_value: '0 */2 * * *',
      enabled: true,
      next_scheduled_run: new Date(Date.now() + 1 * 60 * 60 * 1000).toISOString(),
      metadata: { description: 'Generate trading signals' }
    },
    {
      job_id: 'update-stats',
      job_name: 'Update Dashboard Stats',
      schedule_type: 'cron',
      schedule_value: '0 * * * *',
      enabled: false,
      metadata: { description: 'Update dashboard statistics' }
    }
  ];

  const mockExecutions = [
    {
      job_id: 'data-collection',
      started_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
      status: 'success',
      duration_seconds: 45.2
    },
    {
      job_id: 'signal-generation',
      started_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      status: 'success',
      duration_seconds: 12.5
    },
    {
      job_id: 'update-stats',
      started_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      status: 'failed',
      duration_seconds: 5.0,
      error_message: 'Database connection timeout'
    }
  ];

  test.beforeEach(async ({ page }) => {
    // Mock scheduled jobs API
    await page.route('**/rest/v1/scheduled_jobs**', (route) =>
      route.fulfill({
        status: 200,
        json: mockJobs
      })
    );

    // Mock job executions API - use maybeSingle behavior
    await page.route('**/rest/v1/job_executions**', (route) => {
      const url = route.request().url();
      if (url.includes('job_id=eq.')) {
        // Single job query
        const jobId = url.match(/job_id=eq\.([^&]+)/)?.[1];
        const execution = mockExecutions.find(e => e.job_id === jobId);
        return route.fulfill({
          status: 200,
          json: execution ? [execution] : []
        });
      }
      // All executions
      return route.fulfill({
        status: 200,
        json: mockExecutions
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: /scheduled jobs/i }).click();
  });

  test.describe('Page Structure', () => {
    test('should display scheduled jobs heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /scheduled jobs/i })).toBeVisible();
    });

    test('should display description text', async ({ page }) => {
      await expect(page.getByText(/automated data collection|maintenance jobs/i)).toBeVisible();
    });
  });

  test.describe('Scheduler Status', () => {
    test('should display scheduler status', async ({ page }) => {
      await expect(page.getByText(/scheduler is running|scheduler is not running/i)).toBeVisible();
    });
  });

  test.describe('Auto-Refresh Settings', () => {
    test('should display auto-refresh toggle', async ({ page }) => {
      await expect(page.getByLabel(/auto-refresh/i)).toBeVisible();
    });

    test('should display refresh interval input', async ({ page }) => {
      await expect(page.getByLabel(/interval/i)).toBeVisible();
    });
  });

  test.describe('Job Statistics', () => {
    test('should display total jobs count', async ({ page }) => {
      await expect(page.getByText(/total jobs/i)).toBeVisible();
      await expect(page.getByText(/3/)).toBeVisible();
    });

    test('should display enabled jobs count', async ({ page }) => {
      await expect(page.getByText(/enabled jobs/i)).toBeVisible();
    });

    test('should display disabled jobs count', async ({ page }) => {
      await expect(page.getByText(/disabled jobs/i)).toBeVisible();
    });
  });

  test.describe('Jobs List', () => {
    test('should display job names', async ({ page }) => {
      await expect(page.getByText(/data collection/i)).toBeVisible();
      await expect(page.getByText(/signal generation/i)).toBeVisible();
      await expect(page.getByText(/update dashboard stats/i)).toBeVisible();
    });

    test('should display job descriptions', async ({ page }) => {
      await expect(page.getByText(/collect politician trading data/i)).toBeVisible();
      await expect(page.getByText(/generate trading signals/i)).toBeVisible();
    });

    test('should display enabled/disabled status badges', async ({ page }) => {
      await expect(page.getByText(/enabled/i).first()).toBeVisible();
      await expect(page.getByText(/disabled/i)).toBeVisible();
    });

    test('should display schedule information', async ({ page }) => {
      await expect(page.getByText(/every \d+ hour/i)).toBeVisible();
    });
  });

  test.describe('Tabs Navigation', () => {
    test('should display scheduled jobs tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /scheduled jobs/i })).toBeVisible();
    });

    test('should display execution history tab', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /execution history/i })).toBeVisible();
    });

    test('should switch to execution history tab', async ({ page }) => {
      await page.getByRole('tab', { name: /execution history/i }).click();
      await expect(page.getByText(/job execution|execution history/i)).toBeVisible();
    });
  });

  test.describe('Execution History', () => {
    test.beforeEach(async ({ page }) => {
      await page.getByRole('tab', { name: /execution history/i }).click();
    });

    test('should display execution status badges', async ({ page }) => {
      await expect(page.getByText(/success/i).first()).toBeVisible();
    });

    test('should display execution duration', async ({ page }) => {
      await expect(page.getByText(/45\.2s|45\.2 seconds/i)).toBeVisible();
    });
  });

  test.describe('Empty State', () => {
    test('should show empty state when no jobs', async ({ page }) => {
      await page.route('**/rest/v1/scheduled_jobs**', (route) =>
        route.fulfill({ status: 200, json: [] })
      );

      await page.reload();
      await page.getByRole('button', { name: /scheduled jobs/i }).click();

      await expect(page.getByText(/no scheduled jobs found/i)).toBeVisible();
    });
  });

  test.describe('Job Details', () => {
    test('should display job ID', async ({ page }) => {
      await expect(page.getByText(/data-collection/)).toBeVisible();
    });

    test('should display next run time', async ({ page }) => {
      await expect(page.getByText(/next run/i)).toBeVisible();
    });

    test('should display last run information', async ({ page }) => {
      await expect(page.getByText(/last run/i)).toBeVisible();
    });
  });

  test.describe('Download Logs', () => {
    test('should display download logs button when logs available', async ({ page }) => {
      // Jobs with logs should have download button
      await expect(page.getByRole('button', { name: /download/i })).toBeVisible();
    });
  });
});
