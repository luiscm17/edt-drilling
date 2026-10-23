import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import App from './App';

vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });
const result = {
  pressure_loss: { quantity: 'bit_nozzle_pressure_loss', value: 556612.8, unit: 'Pa' },
  model_id: 'openoil.hydraulics.documented-bit-nozzle-pressure-loss', model_version: '1.0.0',
  input_schema_version: '1', result_schema_version: '1',
  coefficient: { symbol: 'Cd', value: 0.95, unit: '1', selection: 'fixed documented coefficient' },
  applicability: { status: 'supported', assumptions: 'Steady incompressible single-phase flow; constant density and effective total nozzle area.',
    limitations: 'One contribution only; no aggregate or standpipe pressure. Not validated for field decisions.' },
};
const labels = ['Bit/nozzle density (kg/m³)', 'Bit/nozzle flow (m³/s)', 'Bit/nozzle total flow area (m²)'];
async function setup() {
  const fetcher = vi.fn(async (url: RequestInfo | URL) => {
    if (url === '/api/v2/cases') return Response.json([]);
    if (url === '/api/bit-nozzle-pressure-loss/calculate') return Response.json(result);
    throw new Error(`Unexpected route: ${url}`);
  });
  vi.stubGlobal('fetch', fetcher); render(<App />);
  const user = userEvent.setup();
  const nav = screen.getByRole('button', { name: /Bit\/nozzle pressure-loss study/ });
  nav.focus(); await user.keyboard('{Enter}');
  expect(nav).toHaveFocus(); expect(nav).toHaveAttribute('aria-current', 'page');
  expect(screen.getByRole('link', { name: 'Skip to inputs' })).toHaveAttribute('href', '#bit-nozzle-pressure-loss');
  expect(screen.queryByRole('button', { name: 'Save case' })).not.toBeInTheDocument();
  for (const [i, value] of ['1198.2642731689612', '0.018675', '0.00064516'].entries()) {
    await user.type(screen.getByLabelText(labels[i]), value);
  }
  return { fetcher, user, nav };
}
const calculate = (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByRole('button', { name: 'Calculate bit/nozzle pressure loss' }));

describe('explicit calculate-only bit/nozzle pressure-loss study', () => {
  it('posts SI only on request, renders returned contribution/provenance and retains temporary state', async () => {
    const { user, fetcher, nav } = await setup();
    expect(fetcher.mock.calls).toEqual([['/api/v2/cases']]);
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    await calculate(user);
    expect(await screen.findByRole('table', { name: 'Bit/nozzle pressure-loss SI result' })).toHaveTextContent('556,612.8');
    expect(screen.getByRole('table')).toHaveTextContent('Pa');
    expect(screen.getByText(result.model_id)).toBeVisible();
    expect(screen.getByText(/Model version 1.0.0/)).toBeVisible();
    expect(screen.getByText(/^Cd = 0.95 \(dimensionless\)/)).toBeVisible();
    expect(screen.getByText(result.applicability.assumptions)).toBeVisible();
    expect(fetcher).toHaveBeenLastCalledWith('/api/bit-nozzle-pressure-loss/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ density_kg_m3: 1198.2642731689612, flow_m3_s: 0.018675, total_nozzle_area_m2: 0.00064516 }),
    });
    await user.click(screen.getByRole('button', { name: /Hydraulics & saved cases/ }));
    expect(screen.getByText(/No saved cases/)).toBeVisible();
    await user.click(nav);
    expect(screen.getByRole('table')).toBeVisible();
    expect(fetcher.mock.calls).toHaveLength(2);
    await user.clear(screen.getByLabelText(labels[0]));
    await user.type(screen.getByLabelText(labels[0]), '1200');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.queryByText(result.model_id)).not.toBeInTheDocument();
  });

  it.each(['', '0', '-1', '1e309'])('rejects invalid input %j locally and invalidates stale output', async value => {
    const { user, fetcher } = await setup();
    for (const [i, label] of labels.entries()) {
      await calculate(user); await screen.findByRole('table');
      const calls = fetcher.mock.calls.length;
      await user.clear(screen.getByLabelText(label));
      if (value) await user.type(screen.getByLabelText(label), value);
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
      await calculate(user);
      expect(screen.getByRole('alert')).toHaveTextContent('Enter positive finite density, flow and total nozzle area in SI units.');
      expect(fetcher.mock.calls).toHaveLength(calls);
      await user.clear(screen.getByLabelText(label));
      await user.type(screen.getByLabelText(label), ['1198', '0.018675', '0.00064516'][i]);
    }
  });

  it('clears old output on errors and pending requests, then permits retry', async () => {
    const { user, fetcher } = await setup();
    for (const [failure, message] of [
      [() => Promise.resolve(Response.json({ detail: 'calculation outside finite numerical range' }, { status: 422 })), 'calculation outside finite numerical range'],
      [() => Promise.reject(new TypeError('Failed to fetch')), 'Failed to fetch'],
      [() => Promise.resolve(new Response('bad gateway', { status: 502 })), 'Request failed (502)'],
      [() => Promise.resolve(Response.json({ ...result, pressure_loss: { ...result.pressure_loss, value: -1 } })), 'Invalid bit/nozzle pressure-loss response'],
      [() => Promise.resolve(Response.json({ ...result, applicability: { ...result.applicability, status: 'unsupported' } })), 'Invalid bit/nozzle pressure-loss response'],
    ] as const) {
      await calculate(user); await screen.findByRole('table');
      fetcher.mockImplementationOnce(failure); await calculate(user);
      expect(await screen.findByRole('alert')).toHaveTextContent(message);
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
      expect(screen.queryByText(result.model_id)).not.toBeInTheDocument();
    }
    await calculate(user); await screen.findByRole('table');
    let resolve!: (response: Response) => void;
    fetcher.mockImplementationOnce(() => new Promise<Response>(done => { resolve = done; }));
    await calculate(user);
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Calculate bit/nozzle pressure loss' })).toBeDisabled();
    expect(screen.getByLabelText(labels[0])).toBeDisabled();
    resolve(Response.json(result));
    expect(await screen.findByRole('table')).toBeVisible();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(fetcher.mock.calls.every(([url]) => ['/api/v2/cases', '/api/bit-nozzle-pressure-loss/calculate'].includes(String(url)))).toBe(true);
  });
});
