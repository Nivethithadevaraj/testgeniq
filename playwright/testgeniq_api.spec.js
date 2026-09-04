const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://127.0.0.1:8000';

test.describe('TestGenIQ API Validation', () => {

  test('GET /health returns 200', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/health`);

    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('status', 'healthy');
  });

  test('GET / returns API information', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/`);

    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('application', 'TestGenIQ Target API');
    expect(body).toHaveProperty('status', 'running');
  });

  test('POST /tasks creates a task', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/tasks`, {
      data: {
        title: 'Playwright Test Task',
        priority: 'high',
        completed: false
      }
    });

    expect(response.status()).toBe(200);

    const body = await response.json();

    expect(body).toHaveProperty('id');
    expect(body.title).toBe('Playwright Test Task');
    expect(body.priority).toBe('high');
    expect(body.completed).toBe(false);
  });

  test('GET /tasks returns task list', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/tasks`);

    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('POST /tasks rejects invalid priority', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/tasks`, {
      data: {
        title: 'Invalid Priority Task',
        priority: 'invalid'
      }
    });

    expect([400, 422]).toContain(response.status());
  });

  test('GET /tasks/{task_id} handles missing task', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/tasks/999999`);

    expect(response.status()).toBe(404);
  });

});