import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import App from '../../pages/WorkbenchPage';

const result = {
  gel_stress: { quantity: 'zero_second_gel_stress', value: 5.099247582, unit: 'Pa' },
  pressure: { quantity: 'interior_break_gel_pressure', value: 25496.23791, unit: 'Pa' },
  components: [{ length_m: 100, inner_diameter_m: 0.08, pressure_pa: 25496.23791 }],
  source: { rpm: 3, dial: 10, stress_lb_ft2_per_dial: 0.01065, lb_ft2_to_pa: 47.88025898033584 },
  scope: 'string interior only', model_id: 'openoil.rheology.fann-zero-second-gel-break-pressure',
  model_version: '1.0.0', input_schema_version: '1', result_schema_version: '1',
  applicability: { status: 'supported', assumptions: 'Uniform zero-second gel', limitations: 'No annulus or timed gels.' },
};

function setup(response: unknown = result) {
  const fetcher = vi.fn(async (url: RequestInfo | URL) => {
    if (url === '/api/v1/cases') return Response.json([]);
    if (url === '/api/v1/rheology/gel-break-pressure/calculate') return Response.json(response);
    throw new Error(`Unexpected route: ${url}`);
  });
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}

async function openStudy() {
  const user = userEvent.setup(); render(<App />);
  const nav = within(screen.getByRole('navigation', { name: 'Workbench studies' }))
    .getByRole('button', { name: /Gel and break pressure study/ });
  await user.click(nav);
  expect(nav).toHaveAttribute('aria-current', 'page');
  return user;
}

describe('gel and interior break pressure', () => {
  it('submits Fann 3 rpm and component geometry, shows SI breakdown and invalidates stale results', async () => {
    const fetcher = setup();
    const user = await openStudy();
    await user.type(screen.getByLabelText('3 rpm dial reading'), '10');
    await user.type(screen.getByLabelText('Component 1 length (m)'), '100');
    await user.type(screen.getByLabelText('Component 1 inner diameter (m)'), '0.08');
    await user.click(screen.getByRole('button', { name: 'Calculate interior break-gel pressure' }));
    expect(await screen.findByRole('table', { name: 'Interior break-gel component pressures' })).toHaveTextContent('25,496');
    expect(screen.getByRole('region', { name: 'Gel and interior pressure result' })).toHaveTextContent('String interior only');
    expect(fetcher).toHaveBeenLastCalledWith('/api/v1/rheology/gel-break-pressure/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dial_3_rpm: 10, components: [{ length_m: 100, inner_diameter_m: 0.08 }] }),
    });
    await user.clear(screen.getByLabelText('3 rpm dial reading'));
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('rejects invalid inputs without requesting or displaying a result', async () => {
    const fetcher = setup();
    const user = await openStudy();
    await user.type(screen.getByLabelText('3 rpm dial reading'), '-1');
    await user.click(screen.getByRole('button', { name: 'Calculate interior break-gel pressure' }));
    expect(screen.getByRole('alert')).toHaveTextContent('nonnegative');
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('rejects an invalid response without displaying an engineering result', async () => {
    setup({ ...result, scope: 'annulus' });
    const user = await openStudy();
    await user.type(screen.getByLabelText('3 rpm dial reading'), '10');
    await user.type(screen.getByLabelText('Component 1 length (m)'), '100');
    await user.type(screen.getByLabelText('Component 1 inner diameter (m)'), '0.08');
    await user.click(screen.getByRole('button', { name: 'Calculate interior break-gel pressure' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid gel-break response');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });
});
