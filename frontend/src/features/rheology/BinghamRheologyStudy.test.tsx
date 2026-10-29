import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import App from '../../pages/WorkbenchPage';

vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });

const result = {
  readings: [
    { rpm: 300, dial: 50, shear_rate_s_inv: 510.999, shear_stress_pa: 25.496237907028835 },
    { rpm: 600, dial: 75, shear_rate_s_inv: 1021.998, shear_stress_pa: 38.24435686054325 },
  ],
  plastic_viscosity: { quantity: 'plastic_viscosity', value: 0.02494744403318679, unit: 'Pa·s' },
  yield_point: { quantity: 'yield_point', value: 12.748118953514417, unit: 'Pa' },
  model_id: 'openoil.rheology.fann-bingham', model_version: '1.0.0',
  input_schema_version: '1', result_schema_version: '1',
  applicability: {
    status: 'supported',
    assumptions: 'Bingham plastic model derived from 300 and 600 rpm readings.',
    limitations: 'Additional readings are observed points, not part of a regression. Not validated for field decisions.',
  },
};

function setup() {
  const fetcher = vi.fn(async (url: RequestInfo | URL, _init?: RequestInit) => {
    if (url === '/api/v1/cases') return Response.json([]);
    if (url === '/api/v1/rheology/bingham/calculate') return Response.json(result);
    throw new Error(`Unexpected route: ${url}`);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App />);
  return { fetcher, user: userEvent.setup() };
}

async function openStudy(user: ReturnType<typeof userEvent.setup>) {
  const navigation = screen.getByRole('navigation', { name: 'Workbench studies' });
  const nav = within(navigation).getByRole('button', { name: /Bingham rheology study/ });
  nav.focus();
  await user.keyboard('{Enter}');
  expect(nav).toHaveFocus();
  expect(nav).toHaveAttribute('aria-current', 'page');
  expect(screen.getByRole('link', { name: 'Skip to inputs' })).toHaveAttribute('href', '#bingham-rheology');
  expect(screen.queryByRole('button', { name: /Save/ })).not.toBeInTheDocument();
  return nav;
}

async function enterRequiredReadings(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('300 rpm dial reading'), '50');
  await user.type(screen.getByLabelText('600 rpm dial reading'), '75');
}

async function calculate(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'Calculate Bingham rheology' }));
}

describe('bounded calculate-only Bingham rheology study', () => {
  it('posts the required readings and renders SI parameters, graph, accessible data and provenance', async () => {
    const { fetcher, user } = setup();
    await openStudy(user);
    await enterRequiredReadings(user);
    expect(fetcher.mock.calls).toEqual([['/api/v1/cases']]);
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    await calculate(user);
    expect(await screen.findByRole('table', { name: 'Bingham rheology parameters' })).toHaveTextContent('0.024947');
    expect(screen.getByRole('table', { name: 'Bingham rheology parameters' })).toHaveTextContent('Pa·s');
    expect(screen.getByRole('table', { name: 'Bingham rheology parameters' })).toHaveTextContent('12.748');
    expect(screen.getByRole('img', { name: /Observed shear stress and derived Bingham model/ })).toBeVisible();
    const data = screen.getByRole('table', { name: 'Rheology shear data' });
    expect(data).toHaveTextContent('300');
    expect(data).toHaveTextContent('600');
    expect(data).toHaveTextContent('510.999');
    expect(data).toHaveTextContent('25.4962');
    expect(screen.getByText(result.model_id)).toBeVisible();
    expect(screen.getByText(result.applicability.assumptions)).toBeVisible();
    expect(fetcher).toHaveBeenLastCalledWith('/api/v1/rheology/bingham/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ readings: [{ rpm: 300, dial: 50 }, { rpm: 600, dial: 75 }] }),
    });
    expect(fetcher.mock.calls.filter(([, init]) => init)).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: /Hydraulics & saved cases/ }));
    expect(screen.getByText(/No saved cases/)).toBeVisible();
    await user.click(screen.getByRole('button', { name: /Bingham rheology study/ }));
    expect(screen.getByRole('table', { name: 'Rheology shear data' })).toBeVisible();
    expect(fetcher.mock.calls).toHaveLength(2);
    await user.clear(screen.getByLabelText('300 rpm dial reading'));
    await user.type(screen.getByLabelText('300 rpm dial reading'), '49');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.queryByText(result.model_id)).not.toBeInTheDocument();
  });

  it('includes optional observations and rejects duplicate or invalid readings without an HTTP request', async () => {
    const { fetcher, user } = setup();
    await openStudy(user);
    await enterRequiredReadings(user);
    await user.click(screen.getByRole('button', { name: 'Add optional reading' }));
    await user.type(screen.getByLabelText('Optional reading 1 RPM'), '100');
    await user.type(screen.getByLabelText('Optional reading 1 dial reading'), '25');
    fetcher.mockResolvedValueOnce(Response.json({ ...result, readings: [
      { rpm: 100, dial: 25, shear_rate_s_inv: 170.333, shear_stress_pa: 12.748118953514417 },
      ...result.readings,
    ] }));
    await calculate(user);
    expect(await screen.findByRole('table', { name: 'Rheology shear data' })).toHaveTextContent('100');
    expect(fetcher).toHaveBeenLastCalledWith('/api/v1/rheology/bingham/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ readings: [
        { rpm: 300, dial: 50 }, { rpm: 600, dial: 75 }, { rpm: 100, dial: 25 },
      ] }),
    });
    const requestCount = fetcher.mock.calls.length;
    await user.clear(screen.getByLabelText('Optional reading 1 RPM'));
    await user.type(screen.getByLabelText('Optional reading 1 RPM'), '600');
    await calculate(user);
    expect(screen.getByRole('alert')).toHaveTextContent('RPM readings must be unique positive finite numbers.');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(fetcher.mock.calls).toHaveLength(requestCount);
  });

  it('clears stale results on API errors and invalid response data', async () => {
    const { fetcher, user } = setup();
    await openStudy(user);
    await enterRequiredReadings(user);
    await calculate(user);
    await screen.findByRole('table', { name: 'Rheology shear data' });
    fetcher.mockResolvedValueOnce(Response.json({ detail: 'derived yield point must be nonnegative' }, { status: 422 }));
    await calculate(user);
    expect(await screen.findByRole('alert')).toHaveTextContent('derived yield point must be nonnegative');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.queryByText(result.model_id)).not.toBeInTheDocument();
  });
});
