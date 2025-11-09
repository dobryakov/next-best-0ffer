import { randomUUID } from 'node:crypto';
import { URL } from 'node:url';

const DEFAULT_BASE_URL = process.env.API_URL ?? 'http://localhost:9090';

export function createNboClient({ baseUrl = DEFAULT_BASE_URL } = {}) {
  const normalized = normalizeBaseUrl(baseUrl);

  return {
    async createCustomer(payload) {
      return request({
        baseUrl: normalized,
        method: 'POST',
        path: '/customers',
        body: payload,
      });
    },

    async updateCustomer(customerId, payload) {
      return request({
        baseUrl: normalized,
        method: 'PUT',
        path: `/customer/${customerId}`,
        body: payload,
      });
    },

    async sendEvent(payload) {
      return request({
        baseUrl: normalized,
        method: 'POST',
        path: '/events',
        body: payload,
      });
    },

    async getRecommendation(customerId, params = {}) {
      return request({
        baseUrl: normalized,
        method: 'GET',
        path: `/nbo/${customerId}`,
        query: params,
      });
    },
  };
}

async function request({ baseUrl, method, path, body, query }) {
  const url = buildUrl(baseUrl, path, query);
  const headers = {
    Accept: 'application/json',
    'X-Trace-Id': randomUUID(),
  };

  const init = { method, headers };

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }

  const response = await fetch(url, init);
  const text = await response.text();

  if (!response.ok) {
    const message = text ? `${response.status} ${response.statusText}: ${text}` : `${response.status} ${response.statusText}`;
    throw new Error(message);
  }

  if (!text) {
    return null;
  }

  return JSON.parse(text);
}

function normalizeBaseUrl(value) {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

function buildUrl(baseUrl, path, query) {
  const url = new URL(path, baseUrl);
  if (query) {
    Object.entries(query)
      .filter(([, value]) => value !== undefined && value !== null)
      .forEach(([key, value]) => {
        url.searchParams.set(key, value);
      });
  }
  return url.toString();
}

