import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import App from '../../pages/WorkbenchPage';

vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });

const result = {
  parameters: {
    reference_stress_pa: { value: 10, unit: 'Pa' },
    zero_shear_stress_pa: { value: 3, unit: 'Pa' },
    high_shear_viscosity_pa_s: { value: 0.2, unit: 'Pa·s' },
    stress_exponent: { value: 2, unit: '1' }, rate_exponent: { value: 2, unit: '1' },
  },
  curve: [{ shear_rate_s_inv: 0, shear_stress_pa: 3 },
    { shear_rate_s_inv: 40, shear_stress_pa: Math.sqrt(73) }],
  model_id: 'openoil.rheology.generalized-herschel-bulkley-parametric',
  model_version: '1.0.0', input_schema_version: '1', result_schema_version: '1',
  applicability: { status: 'supported', assumptions: 'Parametric evaluation of supplied SI values.',
    limitations: 'No Fann fit or hydraulic coupling; not validated for field decisions.' },
};
function setup() {
  const fetcher = vi.fn(async (url: RequestInfo | URL) => {
    if (url === '/api/v1/cases') return Response.json([]);
    if (url === '/api/v1/rheology/generalized-hb/calculate') return Response.json(result);
    throw new Error(`Unexpected route: ${url}`);
  });
  vi.stubGlobal('fetch', fetcher); render(<App />);
  return { user: userEvent.setup(), fetcher };
}
function field(name: string) {
  return within(document.getElementById('generalized-hb-rheology')!).getByLabelText(name);
}
async function inputs(user: ReturnType<typeof userEvent.setup>, exponent = '2') {
  await user.type(field('Reference stress (Pa)'), '10');
  await user.type(field('Zero-shear stress (Pa)'), '3');
  await user.type(field('High-shear viscosity (Pa·s)'), '0.2');
  await user.type(field('Stress exponent (m)'), exponent);
  await user.type(field('Rate exponent (n)'), '2');
  await user.type(field('Shear rates (s⁻¹), comma-separated'), '0, 40');
}
async function open(user: ReturnType<typeof userEvent.setup>) {
  const nav = within(screen.getByRole('navigation', { name: 'Workbench studies' }))
    .getByRole('button', { name: /Generalized Herschel–Bulkley study/ });
  nav.focus(); await user.keyboard('{Enter}');
  expect(nav).toHaveAttribute('aria-current', 'page');
  expect(screen.getByRole('link', { name: 'Skip to inputs' })).toHaveAttribute('href', '#generalized-hb-rheology');
}

describe('generalized HB parameter evaluator', () => {
  it('posts explicit SI parameters and renders only a model curve with accessible table', async () => {
    const { user, fetcher } = setup(); await open(user); await inputs(user);
    await user.click(screen.getByRole('button', { name: 'Evaluate generalized rheology' }));
    expect(await screen.findByRole('table', { name: 'Generalized rheology curve data' })).toHaveTextContent('8.544');
    expect(screen.getByRole('img', { name: /Generalized rheology model curve in SI units/ })).toBeVisible();
    expect(screen.getByText(result.model_id)).toBeVisible();
    expect(screen.queryByText(/Observed readings/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Save case/ })).not.toBeInTheDocument();
    expect(fetcher).toHaveBeenLastCalledWith('/api/v1/rheology/generalized-hb/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reference_stress_pa: 10, zero_shear_stress_pa: 3,
        high_shear_viscosity_pa_s: 0.2, stress_exponent: 2, rate_exponent: 2,
        shear_rates_s_inv: [0, 40] }),
    });
    await user.clear(field('Stress exponent (m)'));
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('rejects duplicate rates locally and clears results on server errors', async () => {
    const { user, fetcher } = setup(); await open(user); await inputs(user);
    await user.clear(field('Shear rates (s⁻¹), comma-separated'));
    await user.type(field('Shear rates (s⁻¹), comma-separated'), '0, 0');
    const count = fetcher.mock.calls.length;
    await user.click(screen.getByRole('button', { name: 'Evaluate generalized rheology' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Shear rates must be unique nonnegative finite numbers.');
    expect(fetcher.mock.calls).toHaveLength(count);
    await user.clear(field('Shear rates (s⁻¹), comma-separated'));
    await user.type(field('Shear rates (s⁻¹), comma-separated'), '0, 40');
    await user.click(screen.getByRole('button', { name: 'Evaluate generalized rheology' }));
    await screen.findByRole('table', { name: 'Generalized rheology curve data' });
    fetcher.mockResolvedValueOnce(Response.json({ detail: 'calculation outside finite numerical range' }, { status: 422 }));
    await user.click(screen.getByRole('button', { name: 'Evaluate generalized rheology' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('calculation outside finite numerical range');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });
});
