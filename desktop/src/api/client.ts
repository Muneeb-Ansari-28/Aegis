// Typed client for localhost:8765
const BASE_URL = 'http://localhost:8765/api/v1';

export async function checkHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  return res.json();
}
