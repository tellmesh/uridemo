export const URI_PATTERN = /^(?<scheme>[a-z][a-z0-9+.-]*):\/\/(?<target>[^/]+)\/(?:(?<resource>[^/]+)\/)?(?<kind>command|query)\/(?<operation>[^/?#]+)$/i;

export function parseUri(uri) {
  const match = URI_PATTERN.exec(String(uri || '').trim());
  if (!match) {
    throw new Error(`Invalid URI: ${uri}`);
  }
  const groups = match.groups;
  return Object.freeze({
    kind: groups.kind.toLowerCase(),
    operation: groups.operation,
    raw: uri,
    resource: groups.resource || groups.scheme.toLowerCase(),
    scheme: groups.scheme.toLowerCase(),
    target: groups.target,
  });
}

export function payloadFromElement(element) {
  const raw = element?.getAttribute('data-payload');
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`Invalid JSON in data-payload: ${raw}`, { cause: error });
  }
}

export function uriFromElement(element) {
  if (!element) return null;
  const dataUri = element.getAttribute('data-uri');
  if (dataUri) return dataUri.trim();
  const href = element.getAttribute('href');
  if (!href || !href.startsWith('#')) return null;
  const uri = decodeURIComponent(href.slice(1));
  return uri.includes('://') ? uri : null;
}

export async function dispatchUri(uri, {
  context = {},
  endpoint = '/api/dispatch',
  fetchImpl = fetch,
  payload = {},
} = {}) {
  const parsed = parseUri(uri);
  const response = await fetchImpl(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      context,
      kind: parsed.kind,
      operation: parsed.operation,
      payload,
      resource: parsed.resource,
      scheme: parsed.scheme,
      target: parsed.target,
      uri: parsed.raw,
    }),
  });
  if (!response.ok) {
    throw new Error(`URI dispatch failed: ${response.status} ${response.statusText}`);
  }
  return response.json().catch(() => null);
}

export function createUriActions({
  context = {},
  endpoint = '/api/dispatch',
  fetchImpl = fetch,
  root = document,
  selector = '[data-uri], a[href^="#"]',
} = {}) {
  const resolveContext = (element) => ({
    element: {
      tag: element.tagName.toLowerCase(),
      text: element.textContent.trim(),
    },
    source: 'frontend',
    ...(typeof context === 'function' ? context(element) : context),
  });

  async function dispatchElement(element) {
    const uri = uriFromElement(element);
    if (!uri) return null;
    const payload = payloadFromElement(element);
    return dispatchUri(uri, {
      context: resolveContext(element),
      endpoint,
      fetchImpl,
      payload,
    });
  }

  async function onClick(event) {
    const element = event.target.closest(selector);
    if (!element || !root.contains(element)) return;
    const uri = uriFromElement(element);
    if (!uri) return;
    try {
      parseUri(uri);
    } catch {
      return;
    }

    event.preventDefault();
    element.setAttribute('aria-busy', 'true');
    try {
      const response = await dispatchElement(element);
      element.dispatchEvent(new CustomEvent('uri:success', {
        bubbles: true,
        detail: { response, uri },
      }));
    } catch (error) {
      element.dispatchEvent(new CustomEvent('uri:error', {
        bubbles: true,
        detail: { error, uri },
      }));
      console.error(error);
    } finally {
      element.removeAttribute('aria-busy');
    }
  }

  root.addEventListener('click', onClick);
  return {
    destroy() {
      root.removeEventListener('click', onClick);
    },
    dispatchElement,
    parseUri,
  };
}
