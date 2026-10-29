import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import App from '../../pages/WorkbenchPage';

vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });

const result = {
  readings: [
    { rpm: 300, dial: 50, shear_rate_s_inv: 510.999, shear_stress_pa: 25.49623790702883 },
    { rpm: 600, dial: 75, shear_rate_s_inv: 1021.998, shear_stress_pa: 38.244356860543256 },
  ],
  model_curve: [
    { rpm: 300, shear_rate_s_inv: 510.999, shear_stress_pa: 25.49623790702883 },
    { rpm: 600, shear_rate_s_inv: 1021.998, shear_stress_pa: 38.244356860543256 },
  ],
  flow_behavior_index: { quantity: 'flow_behavior_index', value: 0.5849625007211562, unit: '1' },
  consistency_index: { quantity: 'consistency_index', value: 0.6639753206166239, unit: 'Pa·s^n' },
  model_id: 'openoil.rheology.fann-power-law', model_version: '1.0.0',
  input_schema_version: '1', result_schema_version: '1',
  applicability: { status: 'supported', assumptions: 'Derived from 300 and 600 rpm.',
    limitations: 'No hydraulic coupling; not validated for field decisions.' },
};

function setup() {
  const fetcher = vi.fn(async (url: RequestInfo | URL) => {
    if (url === '/api/v1/cases') return Response.json([]);
    if (url === '/api/v1/rheology/power-law/calculate') return Response.json(result);
    throw new Error(`Unexpected route: ${url}`);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App />);
  return { user: userEvent.setup(), fetcher };
}

async function open(user: ReturnType<typeof userEvent.setup>) {
  const nav = within(screen.getByRole('navigation', { name: 'Workbench studies' }))
    .getByRole('button', { name: /Power Law rheology study/ });
  nav.focus(); await user.keyboard('{Enter}');
  expect(nav).toHaveAttribute('aria-current', 'page');
  expect(screen.getByRole('link', { name: 'Skip to inputs' })).toHaveAttribute('href', '#power-law-rheology');
}

function field(name: string) {
  return within(document.getElementById('power-law-rheology')!).getByLabelText(name);
}

describe('independent Power Law study', () => {
  it('shows measured and model SI curve, accessible data, provenance, and no case save', async () => {
    const { user, fetcher } = setup();
    await open(user);
    await user.type(field('300 rpm dial reading'), '50');
    await user.type(field('600 rpm dial reading'), '75');
    await user.click(screen.getByRole('button', { name: 'Calculate Power Law rheology' }));
    expect(await screen.findByRole('table', { name: 'Power Law parameters' })).toHaveTextContent('0.584963');
    expect(screen.getByRole('table', { name: 'Power Law parameters' })).toHaveTextContent('Pa·s^n');
    expect(screen.getByRole('img', { name: /Observed shear stress and derived Power Law model/ })).toBeVisible();
    expect(screen.getByRole('table', { name: 'Power Law shear data' })).toHaveTextContent('510.999');
    expect(screen.getByText(result.model_id)).toBeVisible();
    expect(fetcher).toHaveBeenLastCalledWith('/api/v1/rheology/power-law/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ readings: [{ rpm: 300, dial: 50 }, { rpm: 600, dial: 75 }] }),
    });
    expect(screen.queryByRole('button', { name: /Save case/ })).not.toBeInTheDocument();
    await user.clear(field('300 rpm dial reading'));
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('rejects invalid pairs without request and clears stale results on server errors', async () => {
    const { user, fetcher } = setup();
    await open(user);
    await user.type(field('300 rpm dial reading'), '50');
    await user.type(field('600 rpm dial reading'), '50');
    const calls = fetcher.mock.calls.length;
    await user.click(screen.getByRole('button', { name: 'Calculate Power Law rheology' }));
    expect(screen.getByRole('alert')).toHaveTextContent('600 rpm dial must exceed 300 rpm dial');
    expect(fetcher.mock.calls).toHaveLength(calls);
    await user.clear(field('600 rpm dial reading'));
    await user.type(field('600 rpm dial reading'), '75');
    await user.click(screen.getByRole('button', { name: 'Calculate Power Law rheology' }));
    await screen.findByRole('table', { name: 'Power Law parameters' });
    fetcher.mockResolvedValueOnce(Response.json({ detail: 'calculation outside finite numerical range' }, { status: 422 }));
    await user.click(screen.getByRole('button', { name: 'Calculate Power Law rheology' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('calculation outside finite numerical range');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });
});
