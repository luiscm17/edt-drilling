import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import App from './App';

// jsdom has no layout engine; charts start with their declared initial dimensions.
vi.stubGlobal('ResizeObserver', class {
  observe() {}
  unobserve() {}
  disconnect() {}
});

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
const provenance = {
  model_id: 'openoil.hydraulics.newtonian-concentric-vertical', model_version: '1.0.0',
  units: 'SI', input_schema_version: '1', result_schema_version: '1',
  assumptions: ['Steady incompressible single-phase Newtonian flow; constant properties.'],
  created_at: '2026-01-01T00:00:00+00:00',
};
const snapshot = { input, result, provenance };
const record = { id: 1, ...snapshot };
function api(records: (Omit<typeof record, 'provenance'> & { provenance: typeof provenance | null })[] = []) {
  const fetcher = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
    if (url === '/api/v2/cases' && !init) return Response.json(records);
    if (url === '/api/v2/cases/1') return Response.json(records[0] ?? record);
    if (url === '/api/v2/cases') return Response.json(record, { status: 201 });
    if (url === '/api/v2/calculate') return Response.json(snapshot);
    throw new Error(`Unexpected route: ${url}`);
  });
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}

describe('OpenOil public V2 workbench', () => {
  it('isolates bit/nozzle edits and rejection from retained hydraulic snapshots and legacy studies', async () => {
    const fetcher = api([record]); const user = userEvent.setup(); render(<App />);
    await user.click(await screen.findByRole('button', { name: /Load case 1/ }));
    await screen.findByRole('table', { name: 'Section pressure losses' });
    await user.click(screen.getByRole('button', { name: /Bit\/nozzle pressure-loss study/ }));
    await user.type(screen.getByLabelText('Bit/nozzle density (kg/m³)'), '1000');
    await user.type(screen.getByLabelText('Bit/nozzle flow (m³/s)'), '0.02');
    await user.type(screen.getByLabelText('Bit/nozzle total flow area (m²)'), '0.0004');
    fetcher.mockResolvedValueOnce(Response.json({ detail: 'invalid request body' }, { status: 422 }));
    await user.click(screen.getByRole('button', { name: 'Calculate bit/nozzle pressure loss' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/^invalid request body$/);
    const calls = fetcher.mock.calls.length;
    await user.click(screen.getByRole('button', { name: /Nozzle velocity study/ }));
    expect(screen.getByLabelText('Nozzle flow (m³/s)')).toHaveValue(null);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Torque & drag study/ }));
    expect(screen.getByLabelText('Study density (kg/m³)')).toHaveValue(1000);
    await user.click(screen.getByRole('button', { name: /Hydraulics & saved cases/ }));
    expect(screen.getByRole('table', { name: 'Section pressure losses' })).toHaveTextContent('1,000');
    expect(screen.getByLabelText('Density (kg/m³)')).toHaveValue(1000);
    expect(screen.getAllByRole('button', { name: /Load case/ })).toHaveLength(1);
    expect(fetcher.mock.calls).toHaveLength(calls);
    fetcher.mockResolvedValueOnce(Response.json({ ...record, id: 2 }, { status: 201 }));
    await user.click(screen.getByRole('button', { name: 'Save case' }));
    expect(fetcher).toHaveBeenLastCalledWith('/api/v2/cases', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input_schema_version: '1', input }),
    });
  });
  it('isolates nozzle edits and failures while retaining both existing studies, requests and ledger', async () => {
    const fetcher = api([record]); const user = userEvent.setup(); render(<App />);
    await user.click(await screen.findByRole('button', { name: /Load case 1/ }));
    await screen.findByRole('table', { name: 'Section pressure losses' });
    await user.click(screen.getByRole('button', { name: /Torque & drag study/ }));
    await user.clear(screen.getByLabelText('Study density (kg/m³)'));
    await user.type(screen.getByLabelText('Study density (kg/m³)'), '900');
    const contribution = { submerged_weight_n_m: 100, axial_gravity_n: 1000, normal_force_n: 0,
      axial_friction_n: 0, rotational_friction_n: 0, pickup_tension_n: 1000,
      slackoff_tension_n: 1000, rotating_torque_nm: 0 };
    fetcher.mockResolvedValueOnce(Response.json({ sections: [contribution],
      pickup_tension_n: 1000, slackoff_tension_n: 1000, rotating_torque_nm: 0 }));
    await user.click(screen.getByRole('button', { name: 'Calculate study' }));
    await screen.findByRole('table', { name: 'Torque and drag SI summary' });
    expect(fetcher).toHaveBeenLastCalledWith('/api/torque-drag/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        sections: [{ length_m: 100, pipe_od_m: 0.1, air_weight_n_m: 300 }], inclination_deg: 30,
        density_kg_m3: 900, axial_friction_coefficient: 0.2, rotational_friction_coefficient: 0.3,
      }),
    });
    const nozzle = screen.getByRole('button', { name: /Nozzle velocity study/ });
    nozzle.focus(); await user.keyboard('{Enter}');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    await user.type(screen.getByLabelText('Nozzle flow (m³/s)'), '0.02');
    await user.type(screen.getByLabelText('Total nozzle flow area (m²)'), '0.0004');
    fetcher.mockResolvedValueOnce(Response.json({ detail: 'invalid request body' }, { status: 422 }));
    await user.click(screen.getByRole('button', { name: 'Calculate nozzle velocity' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/^invalid request body$/);
    const calls = fetcher.mock.calls.length;
    await user.click(screen.getByRole('button', { name: /Torque & drag study/ }));
    expect(screen.getByLabelText('Study density (kg/m³)')).toHaveValue(900);
    expect(screen.getByRole('table', { name: 'Torque and drag SI summary' })).toHaveTextContent('1,000');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Hydraulics & saved cases/ }));
    expect(screen.getByLabelText('Density (kg/m³)')).toHaveValue(1000);
    expect(screen.getByRole('table', { name: 'Section pressure losses' })).toHaveTextContent('1,000');
    expect(screen.getAllByRole('button', { name: /Load case/ })).toHaveLength(1);
    expect(fetcher.mock.calls).toHaveLength(calls);
    await user.click(screen.getByRole('button', { name: 'Calculate' }));
    await screen.findByRole('table', { name: 'Section pressure losses' });
    expect(fetcher).toHaveBeenLastCalledWith('/api/v2/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input_schema_version: '1', input }),
    });
    await user.click(nozzle);
    expect(screen.getByLabelText('Nozzle flow (m³/s)')).toHaveValue(0.02);
    expect(screen.getByRole('alert')).toHaveTextContent(/^invalid request body$/);
  });
  it('switches exclusive study views by keyboard without requests or losing hydraulic state', async () => {
    const fetcher = api([record]); const user = userEvent.setup(); render(<App />);
    await user.click(await screen.findByRole('button', { name: /Load case 1/ }));
    await screen.findByRole('table', { name: 'Section pressure losses' });
    const navigation = screen.getByRole('navigation', { name: 'Workbench studies' });
    const hydraulics = within(navigation).getByRole('button', { name: /Hydraulics/ });
    const torque = within(navigation).getByRole('button', { name: /Torque & drag/ });
    expect(hydraulics).toHaveAttribute('aria-current', 'page');
    expect(screen.queryByRole('region', { name: 'Torque & drag study' })).not.toBeInTheDocument();
    torque.focus(); await user.keyboard('{Enter}');
    expect(torque).toHaveFocus();
    expect(torque).toHaveAttribute('aria-current', 'page');
    expect(hydraulics).not.toHaveAttribute('aria-current');
    expect(screen.getByRole('region', { name: 'Torque & drag study' })).toBeVisible();
    expect(screen.queryByRole('table', { name: 'Section pressure losses' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Save case' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Skip to inputs' })).toHaveAttribute('href', '#torque-drag');
    await user.click(hydraulics);
    expect(screen.getByRole('table', { name: 'Section pressure losses' })).toHaveTextContent('1,000');
    expect(screen.getByLabelText('Density (kg/m³)')).toHaveValue(1000);
    expect(screen.getByRole('button', { name: /Load case 1/ })).toBeVisible();
    expect(fetcher.mock.calls).toEqual([['/api/v2/cases'], ['/api/v2/cases/1']]);
  });
  it('retains hydraulic snapshots and ledger while the independent study is edited', async () => {
    const fetcher = api([record]); const user = userEvent.setup(); render(<App />);
    await user.click(await screen.findByRole('button', { name: /Load case 1/ }));
    await screen.findByRole('table', { name: 'Section pressure losses' });
    await user.click(screen.getByRole('button', { name: /Torque & drag study/ }));
    const study = screen.getByRole('region', { name: 'Torque & drag study' });
    await user.clear(within(study).getByLabelText('Study density (kg/m³)'));
    await user.type(within(study).getByLabelText('Study density (kg/m³)'), '900');
    await user.click(screen.getByRole('button', { name: /Hydraulics & saved cases/ }));
    expect(screen.getByLabelText('Density (kg/m³)')).toHaveValue(1000);
    expect(screen.getByRole('table', { name: 'Section pressure losses' })).toHaveTextContent('1,000');
    expect(screen.getByRole('button', { name: /Load case 1/ })).toBeVisible();
    fetcher.mockResolvedValueOnce(Response.json({ ...record, id: 2 }, { status: 201 }));
    await user.click(screen.getByRole('button', { name: 'Save case' }));
    expect(fetcher).toHaveBeenCalledWith('/api/v2/cases', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ input_schema_version: '1', input }),
    }));
    await user.click(screen.getByRole('button', { name: /Torque & drag study/ }));
    expect(within(study).getByLabelText('Study density (kg/m³)')).toHaveValue(900);
    expect(fetcher.mock.calls.some(([url]) => String(url).includes('torque-drag'))).toBe(false);
  });

  it('edits SI inputs, posts only the strict V2 envelope, and clears stale results', async () => {
    const fetcher = api(); const user = userEvent.setup(); render(<App />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('OpenOil');
    expect(screen.getByRole('complementary', { name: 'Engineering scope warning' })).toHaveTextContent(/not validated for field decisions/i);
    expect(screen.getByRole('complementary', { name: 'Engineering scope warning' })).toBeVisible();
    await waitFor(() => expect(screen.getByLabelText('Density (kg/m³)')).toBeEnabled());
    await user.clear(screen.getByLabelText('Density (kg/m³)'));
    await user.type(screen.getByLabelText('Density (kg/m³)'), '1100');
    await user.click(screen.getByRole('button', { name: 'Calculate' }));
    await screen.findByRole('table', { name: 'Section pressure losses' });
    expect(fetcher).toHaveBeenCalledWith('/api/v2/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input_schema_version: '1', input: { ...input, density_kg_m3: 1100 } }),
    });
    expect(fetcher.mock.calls.filter(([, init]) => init)).toHaveLength(1);
    expect(screen.getByRole('table', { name: 'Pressure and density summary' })).toHaveTextContent('980,865');
    expect(screen.getByRole('table', { name: 'Pressure and density summary' })).toHaveTextContent('1,000.2');
    expect(screen.getByRole('table', { name: 'Section pressure losses' })).toHaveTextContent('1,000');
    expect(screen.getByRole('img', { name: /Section friction losses/ })).toBeVisible();
    expect(screen.getByRole('img', { name: /Annular pressure versus vertical depth/ })).toBeVisible();
    await user.click(screen.getByText('Profile values (accessible data)'));
    expect(screen.getByRole('table', { name: 'Annular pressure profile values' })).toHaveTextContent('980,865');
    expect(screen.getByText(provenance.model_id)).toBeVisible();
    expect(screen.getByText(/Model version 1.0.0/)).toBeVisible();
    expect(screen.getByText(/Input schema 1 · Result schema 1 · SI/)).toBeVisible();
    await user.type(screen.getByLabelText('Flow (m³/s)'), '1');
    expect(screen.queryByRole('table', { name: 'Section pressure losses' })).not.toBeInTheDocument();
    expect(screen.queryByText(provenance.model_id)).not.toBeInTheDocument();
    expect(screen.getByText(/Inputs changed/)).toBeVisible();
  });

  it('adds and removes sections while retaining one and accessible SI fields', async () => {
    api(); const user = userEvent.setup(); render(<App />);
    await user.click(screen.getByRole('button', { name: 'Add section' }));
    const second = screen.getByRole('group', { name: 'Section 2' });
    await user.clear(within(second).getByLabelText('Length (m)'));
    await user.type(within(second).getByLabelText('Length (m)'), '50');
    await user.click(within(second).getByRole('button', { name: 'Remove section 2' }));
    expect(screen.queryByRole('group', { name: 'Section 2' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Remove section 1' })).toBeDisabled();
  });

  it('saves a snapshot, refreshes the ledger and loads without recalculation', async () => {
    const fetcher = api(); const user = userEvent.setup(); render(<App />);
    await user.click(screen.getByRole('button', { name: 'Save case' }));
    await screen.findByRole('button', { name: /Load case 1/ });
    expect(fetcher).toHaveBeenCalledWith('/api/v2/cases', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ input_schema_version: '1', input }),
    }));
    await user.clear(screen.getByLabelText('Density (kg/m³)'));
    await user.type(screen.getByLabelText('Density (kg/m³)'), '1200');
    await user.click(screen.getByRole('button', { name: /Load case 1/ }));
    await waitFor(() => expect(screen.getByLabelText('Density (kg/m³)')).toHaveValue(1000));
    expect(fetcher).toHaveBeenCalledWith('/api/v2/cases/1');
    expect(fetcher.mock.calls.filter(([, init]) => init)).toHaveLength(1);
    expect(screen.getByRole('table', { name: 'Section pressure losses' })).toBeVisible();
    expect(screen.getByText(/Loaded case 1. Results are a stored snapshot/)).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Refresh cases' }));
    expect(fetcher).toHaveBeenCalledWith('/api/v2/cases');
  });

  it('marks legacy provenance unknown in the ledger and loaded snapshot', async () => {
    const fetcher = api([{ ...record, provenance: null }]); const user = userEvent.setup(); render(<App />);
    const load = await screen.findByRole('button', { name: /Load case 1/ });
    expect(load).toHaveTextContent('Unknown model · legacy snapshot');
    await user.click(load);
    expect(await screen.findByText('Unknown model · legacy snapshot', { selector: 'strong' })).toBeVisible();
    expect(screen.queryByText(provenance.model_id)).not.toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Section pressure losses' })).toHaveTextContent('1,000');
    expect(fetcher.mock.calls.filter(([, init]) => init)).toHaveLength(0);
  });

  it('shows exact rejection detail, clears previous results and leaves the ledger unchanged', async () => {
    const fetcher = api([record]); const user = userEvent.setup(); render(<App />);
    await user.click(await screen.findByRole('button', { name: /Load case 1/ }));
    await screen.findByRole('table', { name: 'Section pressure losses' });
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
    await waitFor(() => expect(fetcher).toHaveBeenCalledWith('/api/v2/cases'));
    fetcher.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    await user.click(screen.getByRole('button', { name: 'Calculate' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to fetch');
    await user.click(screen.getByRole('button', { name: 'Calculate' }));
    expect(await screen.findByRole('table', { name: 'Section pressure losses' })).toBeVisible();
  });

  it.each(['Refresh cases', 'Load case 1'])('clears a loaded result when %s fails without changing the ledger', async action => {
    const fetcher = api([record]); const user = userEvent.setup(); render(<App />);
    await user.click(await screen.findByRole('button', { name: /Load case 1/ }));
    await screen.findByRole('table', { name: 'Section pressure losses' });
    fetcher.mockResolvedValueOnce(Response.json({ detail: 'case not found' }, { status: 404 }));
    await user.click(screen.getByRole('button', { name: new RegExp(action) }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/^case not found$/);
    expect(screen.queryByRole('table', { name: 'Section pressure losses' })).not.toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /Load case/ })).toHaveLength(1);
  });

  it('distinguishes non-JSON infrastructure failure and clears a loaded result', async () => {
    const fetcher = api([record]); const user = userEvent.setup(); render(<App />);
    await user.click(await screen.findByRole('button', { name: /Load case 1/ }));
    await screen.findByRole('table', { name: 'Section pressure losses' });
    fetcher.mockResolvedValueOnce(new Response('Internal Server Error', { status: 500 }));
    await user.click(screen.getByRole('button', { name: 'Calculate' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/^Request failed \(500\)$/);
    expect(screen.queryByRole('table', { name: 'Section pressure losses' })).not.toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /Load case/ })).toHaveLength(1);
  });
});
