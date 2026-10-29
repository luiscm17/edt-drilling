import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import App from '../../pages/WorkbenchPage';

vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });
const result = { power: { quantity: 'hydraulic_power', value: 0.123456, unit: 'hp' },
  pressure_boundary: 'annulus', model_id: 'openoil.hydraulics.documented-pressure-loss-power',
  model_version: '1.0.0', input_schema_version: '1', result_schema_version: '1',
  applicability: { status: 'supported', assumptions: 'User-supplied loss.', limitations: 'Not bit loss.' } };
function setup() {
  const fetcher = vi.fn(async (url: RequestInfo | URL) => {
    if (url === '/api/v1/cases') return Response.json([]);
    if (url === '/api/v1/bit-hydraulic-power/calculate') return Response.json(result);
    throw new Error(`Unexpected route: ${url}`);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App />);
  return { fetcher, user: userEvent.setup() };
}

describe('bounded pressure-loss power study', () => {
  it('sends explicit passage and SI quantities, shows power with provenance, without saving', async () => {
    const { fetcher, user } = setup();
    await user.click(screen.getByRole('button', { name: /Hydraulic power study/ }));
    await user.type(screen.getByLabelText('Circulation rate (m³/s)'), '0.01');
    await user.type(screen.getByLabelText('Supplied pressure loss (Pa)'), '2000');
    await user.selectOptions(screen.getByLabelText('Pressure-loss passage'), 'annulus');
    await user.click(screen.getByRole('button', { name: 'Calculate hydraulic power' }));
    expect(await screen.findByRole('table', { name: 'Hydraulic power result' })).toHaveTextContent('0.123456');
    expect(screen.getByRole('table', { name: 'Hydraulic power result' })).toHaveTextContent('hp');
    expect(screen.getByText('openoil.hydraulics.documented-pressure-loss-power')).toBeVisible();
    expect(fetcher.mock.calls).toEqual([['/api/v1/cases'], ['/api/v1/bit-hydraulic-power/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ flow_m3_s: 0.01, pressure_loss_pa: 2000, pressure_boundary: 'annulus' }),
    }]]);
    expect(screen.queryByRole('button', { name: 'Save case' })).not.toBeInTheDocument();
  });

  it('rejects blank inputs locally and clears stale power after edits', async () => {
    const { fetcher, user } = setup();
    await user.click(screen.getByRole('button', { name: /Hydraulic power study/ }));
    await user.click(screen.getByRole('button', { name: 'Calculate hydraulic power' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Enter positive finite flow and pressure loss');
    expect(fetcher).toHaveBeenCalledTimes(1);
    await user.type(screen.getByLabelText('Circulation rate (m³/s)'), '0.01');
    await user.type(screen.getByLabelText('Supplied pressure loss (Pa)'), '2000');
    await user.selectOptions(screen.getByLabelText('Pressure-loss passage'), 'annulus');
    await user.click(screen.getByRole('button', { name: 'Calculate hydraulic power' }));
    expect(await screen.findByRole('table', { name: 'Hydraulic power result' })).toBeVisible();
    await user.clear(screen.getByLabelText('Supplied pressure loss (Pa)'));
    expect(screen.queryByRole('table', { name: 'Hydraulic power result' })).not.toBeInTheDocument();
  });
});
