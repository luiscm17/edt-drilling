import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import App from './App';

const input = {
  sections: [{ length_m: 100, pipe_id_m: 0.08, pipe_od_m: 0.1, hole_id_m: 0.2 }],
  density_kg_m3: 1000, viscosity_pa_s: 0.1, flow_m3_s: 0.001,
};
const passage = { velocity_m_s: 0.2, reynolds: 160, regime: 'laminar', darcy_factor: 0.4, pressure_loss_pa: 1000 };
const result = {
  sections: [{ pipe: passage, annulus: { ...passage, pressure_loss_pa: 200 } }],
  depth_m: 100, pipe_friction_pa: 1000, annular_friction_pa: 200,
  hydrostatic_pa: 980665, bottomhole_annular_pa: 980865, ecd_kg_m3: 1000.204,
};
const record = { id: 1, input, result };
function api(records: typeof record[] = []) {
  const fetcher = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
    if (url === '/api/cases' && !init) return Response.json(records);
    if (url === '/api/cases/1') return Response.json(record);
    if (url === '/api/cases') return Response.json(record, { status: 201 });
    return Response.json(result);
  });
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}

describe('engineering workbench public interactions', () => {
  it('edits SI inputs, calculates without saving, and renders table and labelled plots', async () => {
    const fetcher = api(); const user = userEvent.setup(); render(<App />);
    expect(screen.getByText(/not WellPlan parity/i)).toBeVisible();
    await waitFor(() => expect(screen.getByLabelText('Density (kg/m³)')).toBeEnabled());
    await user.clear(screen.getByLabelText('Density (kg/m³)'));
    await user.type(screen.getByLabelText('Density (kg/m³)'), '1100');
    await user.click(screen.getByRole('button', { name: 'Calculate' }));
    await screen.findByRole('table', { name: 'Section pressure losses' });
    expect(fetcher).toHaveBeenCalledWith('/api/calculate', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ ...input, density_kg_m3: 1100 }),
    }));
    expect(fetcher.mock.calls.some(([url, init]) => url === '/api/cases' && init)).toBe(false);
    expect(screen.getByRole('table', { name: 'Pressure and density summary' })).toHaveTextContent('980,865');
    expect(screen.getByRole('table', { name: 'Pressure and density summary' })).toHaveTextContent('1,000.2');
    expect(screen.getByRole('table', { name: 'Section pressure losses' })).toHaveTextContent('1,000');
    expect(screen.getByRole('img', { name: /Section friction losses/ })).toBeVisible();
    expect(screen.getByRole('img', { name: /Annular pressure versus vertical depth/ })).toBeVisible();
    await user.type(screen.getByLabelText('Flow (m³/s)'), '1');
    expect(screen.queryByRole('table', { name: 'Section pressure losses' })).not.toBeInTheDocument();
    expect(screen.getByText(/Inputs changed/)).toBeVisible();
  });

  it('adds and removes geometry sections with accessible SI fields', async () => {
    api(); const user = userEvent.setup(); render(<App />);
    await user.click(screen.getByRole('button', { name: 'Add section' }));
    const second = screen.getByRole('group', { name: 'Section 2' });
    await user.clear(within(second).getByLabelText('Length (m)'));
    await user.type(within(second).getByLabelText('Length (m)'), '50');
    await user.click(within(second).getByRole('button', { name: 'Remove section 2' }));
    expect(screen.queryByRole('group', { name: 'Section 2' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Remove section 1' })).toBeDisabled();
  });

  it('saves current inputs, lists saved cases, and loads their inputs and snapshot', async () => {
    const fetcher = api(); const user = userEvent.setup(); render(<App />);
    await user.click(screen.getByRole('button', { name: 'Save case' }));
    await screen.findByRole('button', { name: /Load case 1/ });
    expect(fetcher).toHaveBeenCalledWith('/api/cases', expect.objectContaining({
      method: 'POST', body: JSON.stringify(input),
    }));
    await user.clear(screen.getByLabelText('Density (kg/m³)'));
    await user.type(screen.getByLabelText('Density (kg/m³)'), '1200');
    await user.click(screen.getByRole('button', { name: /Load case 1/ }));
    await waitFor(() => expect(screen.getByLabelText('Density (kg/m³)')).toHaveValue(1000));
    expect(fetcher).toHaveBeenCalledWith('/api/cases/1');
    expect(screen.getByRole('table', { name: 'Section pressure losses' })).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Refresh cases' }));
    expect(fetcher).toHaveBeenCalledWith('/api/cases');
  });

  it('loads the initial list and exposes exact rejection detail without a false result or save', async () => {
    const fetcher = api([record]); const user = userEvent.setup(); render(<App />);
    await screen.findByRole('button', { name: /Load case 1/ });
    fetcher.mockImplementation(async () => Response.json({ detail: 'Reynolds number outside supported regimes' }, { status: 422 }));
    for (const action of ['Calculate', 'Save case']) {
      await user.click(screen.getByRole('button', { name: action }));
      expect(await screen.findByRole('alert')).toHaveTextContent(/^Reynolds number outside supported regimes$/);
      expect(screen.queryByRole('table', { name: 'Section pressure losses' })).not.toBeInTheDocument();
      expect(screen.getAllByRole('button', { name: /Load case/ })).toHaveLength(1);
    }
  });

  it('reports network errors and allows retry', async () => {
    const fetcher = api(); const user = userEvent.setup(); render(<App />);
    await waitFor(() => expect(fetcher).toHaveBeenCalledWith('/api/cases'));
    fetcher.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    await user.click(screen.getByRole('button', { name: 'Calculate' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to fetch');
    await user.click(screen.getByRole('button', { name: 'Calculate' }));
    expect(await screen.findByRole('table', { name: 'Section pressure losses' })).toBeVisible();
  });
});
