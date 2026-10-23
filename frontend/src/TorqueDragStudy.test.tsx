import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import App from './App';

vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });
const contribution = {
  submerged_weight_n_m: 100, axial_gravity_n: 1000, normal_force_n: 0,
  axial_friction_n: 0, rotational_friction_n: 0,
  pickup_tension_n: 1000, slackoff_tension_n: 1000, rotating_torque_nm: 0,
};
const result = { sections: [contribution, { ...contribution, submerged_weight_n_m: 200,
  axial_gravity_n: 4000, pickup_tension_n: 4000, slackoff_tension_n: 4000 }],
  pickup_tension_n: 5000, slackoff_tension_n: 5000, rotating_torque_nm: 0 };
function setup() {
  const fetcher = vi.fn(async (url: RequestInfo | URL) => {
    if (url === '/api/v1/cases') return Response.json([]);
    if (url === '/api/v1/torque-drag/calculate') return Response.json(result);
    throw new Error(`Unexpected route: ${url}`);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App />);
  return { fetcher, user: userEvent.setup() };
}
async function fill(user: ReturnType<typeof userEvent.setup>, label: string, value: string) {
  const field = screen.getByLabelText(label);
  await user.clear(field); await user.type(field, value);
}

describe('calculate-only torque and drag study', () => {
  it('selects the study by keyboard, sends ordered raw SI inputs, audits contributions and never saves', async () => {
    const { user, fetcher } = setup();
    const studyButton = screen.getByRole('button', { name: /Torque & drag study/ });
    studyButton.focus(); await user.keyboard('{Enter}'); expect(studyButton).toHaveFocus();
    expect(studyButton).toHaveAttribute('aria-current', 'page');
    const panel = screen.getByRole('region', { name: 'Torque & drag study' });
    expect(within(panel).getByText(/no doglegs or buckling/i)).toBeVisible();
    expect(within(panel).getByText(/no field suitability or vendor-runtime parity/i)).toBeVisible();
    await fill(user, 'Study inclination (° from vertical)', '0');
    await fill(user, 'Study density (kg/m³)', '0');
    await fill(user, 'Axial friction coefficient (dimensionless)', '0.2');
    await fill(user, 'Rotational friction coefficient (dimensionless)', '0.3');
    await fill(user, 'Study length (m)', '10');
    await fill(user, 'Study pipe OD (m)', '0.1');
    await fill(user, 'Air weight (N/m)', '100');
    await user.click(within(panel).getByRole('button', { name: 'Add study section' }));
    const second = within(panel).getByRole('group', { name: 'Study section 2' });
    for (const [label, value] of [['Study length (m)', '20'], ['Study pipe OD (m)', '0.2'], ['Air weight (N/m)', '200']]) {
      const field = within(second).getByLabelText(label);
      await user.clear(field); await user.type(field, value);
    }
    await user.click(within(panel).getByRole('button', { name: 'Calculate study' }));
    expect(await within(panel).findByRole('table', { name: 'Torque and drag section contributions' })).toBeVisible();
    expect(fetcher).toHaveBeenCalledWith('/api/v1/torque-drag/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        sections: [{ length_m: 10, pipe_od_m: 0.1, air_weight_n_m: 100 },
          { length_m: 20, pipe_od_m: 0.2, air_weight_n_m: 200 }],
        inclination_deg: 0, density_kg_m3: 0, axial_friction_coefficient: 0.2, rotational_friction_coefficient: 0.3,
      }),
    });
    const summary = within(panel).getByRole('table', { name: 'Torque and drag SI summary' });
    expect(within(summary).getAllByRole('row').slice(1).map(row => row.textContent)).toEqual([
      'Pickup surface tension5,000N', 'Slackoff surface tension5,000N', 'Rotating contact torque0N·m',
    ]);
    const table = within(panel).getByRole('table', { name: 'Torque and drag section contributions' });
    const rows = within(table).getAllByRole('row');
    expect(rows).toHaveLength(3);
    expect(within(rows[1]).getAllByRole('cell').map(cell => cell.textContent)).toEqual(['100', '1,000', '0', '0', '0', '1,000', '1,000', '0']);
    expect(within(rows[2]).getAllByRole('cell').map(cell => cell.textContent)).toEqual(['200', '4,000', '0', '0', '0', '4,000', '4,000', '0']);
    for (const label of ['Submerged weight (N/m)', 'Axial gravity (N)', 'Normal force (N)', 'Axial friction (N)',
      'Rotational friction (N)', 'Pickup (N)', 'Slackoff (N)', 'Torque (N·m)']) {
      expect(within(table).getByRole('columnheader', { name: label })).toBeVisible();
    }
    expect(within(panel).getByRole('status')).toHaveTextContent('Study complete. Not saved; hydraulic ledger unchanged.');
    expect(within(panel).queryByRole('button', { name: /save/i })).not.toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([url]) => url !== '/api/v1/cases')).toHaveLength(1);
    const callsBeforeNavigation = fetcher.mock.calls.length;
    await user.click(screen.getByRole('button', { name: /Hydraulics & saved cases/ }));
    expect(screen.getByText(/No saved cases/)).toBeVisible();
    expect(screen.queryByRole('table', { name: 'Torque and drag SI summary' })).not.toBeInTheDocument();
    await user.click(studyButton);
    expect(screen.getByRole('table', { name: 'Torque and drag SI summary' })).toHaveTextContent('5,000');
    expect(within(second).getByLabelText('Study length (m)')).toHaveValue(20);
    expect(fetcher.mock.calls).toHaveLength(callsBeforeNavigation);
    await user.click(within(second).getByRole('button', { name: 'Remove study section 2' }));
    expect(within(panel).queryByRole('table')).not.toBeInTheDocument();
    expect(within(panel).getByRole('button', { name: 'Remove study section 1' })).toBeDisabled();
  });

  it('clears both result tables on edits and server, network or non-JSON failure, and permits retry', async () => {
    const { user, fetcher } = setup();
    await user.click(screen.getByRole('button', { name: /Torque & drag study/ }));
    const calculate = () => user.click(screen.getByRole('button', { name: 'Calculate study' }));
    await calculate();
    await screen.findByRole('table', { name: 'Torque and drag SI summary' });
    await fill(user, 'Study density (kg/m³)', '0');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    for (const [failure, message] of [
      [() => Promise.resolve(Response.json({ detail: 'slackoff tension must be nonnegative in every section' }, { status: 422 })), 'slackoff tension must be nonnegative in every section'],
      [() => Promise.reject(new TypeError('Failed to fetch')), 'Failed to fetch'],
      [() => Promise.resolve(new Response('Internal Server Error', { status: 500 })), 'Request failed (500)'],
    ] as const) {
      await calculate(); await screen.findByRole('table', { name: 'Torque and drag SI summary' });
      fetcher.mockImplementationOnce(failure);
      await calculate();
      expect(await screen.findByRole('alert')).toHaveTextContent(message);
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: /Hydraulics & saved cases/ }));
      expect(screen.getByText(/No saved cases/)).toBeVisible();
      await user.click(screen.getByRole('button', { name: /Torque & drag study/ }));
    }
    await calculate();
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(await screen.findByRole('table', { name: 'Torque and drag SI summary' })).toBeVisible();
    expect(fetcher.mock.calls.every(([url]) => ['/api/v1/cases', '/api/v1/torque-drag/calculate'].includes(String(url)))).toBe(true);
  });
});
