import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import App from '../../pages/WorkbenchPage';

vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });

const result = {
  parameters: {
    yield_stress_pa: { value: 3, unit: 'Pa' },
    consistency_index_pa_s_n: { value: 0.2, unit: 'Pa·s^n' },
    flow_behavior_index: { value: 1, unit: '1' },
  },
  curve: [{ shear_rate_s_inv: 0, shear_stress_pa: 3 },
    { shear_rate_s_inv: 40, shear_stress_pa: 11 }],
  model_id: 'openoil.rheology.herschel-bulkley-parametric',
  model_version: '1.0.0', input_schema_version: '1', result_schema_version: '1',
  applicability: { status: 'supported', assumptions: 'Supplied SI parameters only.',
    limitations: 'No Fann fit, hydraulics or field validation.' },
};

it('evaluates the conventional model as an independent, accessible parametric curve', async () => {
  const fetcher = vi.fn(async (url: RequestInfo | URL) => {
    if (url === '/api/v1/cases') return Response.json([]);
    if (url === '/api/v1/rheology/herschel-bulkley/calculate') return Response.json(result);
    throw new Error(`Unexpected route: ${url}`);
  });
  vi.stubGlobal('fetch', fetcher);
  const user = userEvent.setup(); render(<App />);
  const nav = within(screen.getByRole('navigation', { name: 'Workbench studies' }))
    .getByRole('button', { name: /Herschel–Bulkley study Yield stress/ });
  nav.focus(); await user.keyboard('{Enter}');
  expect(nav).toHaveAttribute('aria-current', 'page');
  const study = within(document.getElementById('herschel-bulkley-rheology')!);
  await user.type(study.getByLabelText('Yield stress (Pa)'), '3');
  await user.type(study.getByLabelText('Consistency index (Pa·sⁿ)'), '0.2');
  await user.type(study.getByLabelText('Flow behavior index (n)'), '1');
  await user.type(study.getByLabelText('Shear rates (s⁻¹), comma-separated'), '0, 40');
  await user.click(study.getByRole('button', { name: 'Evaluate Herschel–Bulkley rheology' }));
  expect(await screen.findByRole('table', { name: 'Herschel–Bulkley curve data' })).toHaveTextContent('11');
  expect(screen.getByRole('img', { name: /Herschel–Bulkley model curve in SI units/ })).toBeVisible();
  expect(fetcher).toHaveBeenLastCalledWith('/api/v1/rheology/herschel-bulkley/calculate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ yield_stress_pa: 3, consistency_index_pa_s_n: 0.2,
      flow_behavior_index: 1, shear_rates_s_inv: [0, 40] }),
  });
  await user.clear(study.getByLabelText('Flow behavior index (n)'));
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});
