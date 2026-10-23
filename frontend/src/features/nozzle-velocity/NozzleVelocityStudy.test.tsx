import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import App from '../../pages/WorkbenchPage';

vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });
function setup() {
  const fetcher = vi.fn(async (url: RequestInfo | URL) => {
    if (url === '/api/v1/cases') return Response.json([]);
    if (url === '/api/v1/nozzle-velocity/calculate') return Response.json({ velocity_m_s: 37.123456 });
    throw new Error(`Unexpected route: ${url}`);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App />);
  return { fetcher, user: userEvent.setup() };
}
async function fill(user: ReturnType<typeof userEvent.setup>, label: string, value: string) {
  const field = screen.getByLabelText(label);
  await user.clear(field);
  if (value) await user.type(field, value);
}
async function open(user: ReturnType<typeof userEvent.setup>) {
  const button = screen.getByRole('button', { name: /Nozzle velocity study/ });
  button.focus(); await user.keyboard(' ');
  expect(button).toHaveFocus();
  expect(button).toHaveAttribute('aria-current', 'page');
  expect(screen.getByRole('link', { name: 'Skip to inputs' })).toHaveAttribute('href', '#nozzle-velocity');
  expect(screen.queryByRole('button', { name: 'Save case' })).not.toBeInTheDocument();
  expect(screen.queryByRole('region', { name: 'Torque & drag study' })).not.toBeInTheDocument();
  return screen.getByRole('region', { name: 'Nozzle velocity study' });
}
async function inputs(user: ReturnType<typeof userEvent.setup>) {
  await fill(user, 'Nozzle flow (m³/s)', '0.02');
  await fill(user, 'Total nozzle flow area (m²)', '0.0004');
}
const calculate = (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByRole('button', { name: 'Calculate nozzle velocity' }));

describe('independent nozzle velocity workspace', () => {
  it('selects a real view, sends raw numeric SI JSON and displays only returned velocity with explicit scope', async () => {
    const { user, fetcher } = setup();
    const panel = await open(user);
    expect(within(panel).queryByRole('table')).not.toBeInTheDocument();
    expect(within(panel).getByText(/0.95.*2.96/)).toBeVisible();
    expect(within(panel).getByText(/No executed vendor numerical parity/)).toBeVisible();
    expect(within(panel).getByText(/documentation-fidelity choice/)).toBeVisible();
    await inputs(user); await calculate(user);
    const table = await screen.findByRole('table', { name: 'Nozzle velocity SI result' });
    expect(table).toHaveTextContent('37.1235');
    expect(table).toHaveTextContent('m/s');
    expect(fetcher.mock.calls).toEqual([
      ['/api/v1/cases'], ['/api/v1/nozzle-velocity/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ flow_m3_s: 0.02, total_nozzle_area_m2: 0.0004 }),
      }],
    ]);
    expect(within(panel).getByRole('status')).toHaveTextContent('Calculation complete. Not saved; hydraulic ledger unchanged.');
    await user.click(screen.getByRole('button', { name: /Hydraulics & saved cases/ }));
    expect(screen.getByText(/No saved cases/)).toBeVisible();
    expect(screen.queryByRole('table', { name: 'Nozzle velocity SI result' })).not.toBeInTheDocument();
    await open(user);
    expect(screen.getByLabelText('Nozzle flow (m³/s)')).toHaveValue(0.02);
    expect(screen.getByRole('table', { name: 'Nozzle velocity SI result' })).toBeVisible();
    expect(fetcher.mock.calls).toHaveLength(2);
  });

  it.each(['', '0', '-1'])('rejects flow or area %j locally, clears stale output and sends no request', async invalid => {
    const { user, fetcher } = setup(); await open(user); await inputs(user);
    for (const label of ['Nozzle flow (m³/s)', 'Total nozzle flow area (m²)']) {
      await calculate(user); await screen.findByRole('table', { name: 'Nozzle velocity SI result' });
      const calls = fetcher.mock.calls.length;
      await fill(user, label, invalid);
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
      await calculate(user);
      expect(screen.getByRole('alert')).toHaveTextContent('Enter positive finite flow and total nozzle area in SI units.');
      expect(screen.getByRole('status')).toHaveTextContent('Invalid inputs. No result is displayed.');
      expect(fetcher.mock.calls).toHaveLength(calls);
      await inputs(user);
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    }
  });

  it('clears results on new requests, exact server errors, network/non-JSON failures and retries', async () => {
    const { user, fetcher } = setup(); await open(user); await inputs(user);
    for (const [failure, message] of [
      [() => Promise.resolve(Response.json({ detail: 'calculation outside finite numerical range' }, { status: 422 })), 'calculation outside finite numerical range'],
      [() => Promise.reject(new TypeError('Failed to fetch')), 'Failed to fetch'],
      [() => Promise.resolve(new Response('Internal Server Error', { status: 500 })), 'Request failed (500)'],
    ] as const) {
      await calculate(user); await screen.findByRole('table', { name: 'Nozzle velocity SI result' });
      fetcher.mockImplementationOnce(failure); await calculate(user);
      expect(await screen.findByRole('alert')).toHaveTextContent(new RegExp(`^${message.replace(/[()]/g, '\\$&')}$`));
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
      expect(screen.getByRole('status')).toHaveTextContent('Calculation failed. No result is displayed; hydraulic ledger unchanged.');
    }
    await calculate(user); await screen.findByRole('table', { name: 'Nozzle velocity SI result' });
    let resolve!: (response: Response) => void;
    fetcher.mockImplementationOnce(() => new Promise<Response>(done => { resolve = done; }));
    await calculate(user);
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Calculate nozzle velocity' })).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('Calculating nozzle velocity…');
    resolve(Response.json({ velocity_m_s: 74.246912 }));
    expect(await screen.findByRole('table', { name: 'Nozzle velocity SI result' })).toHaveTextContent('74.2469');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(fetcher.mock.calls.every(([url]) => ['/api/v1/cases', '/api/v1/nozzle-velocity/calculate'].includes(String(url)))).toBe(true);
  });
});
