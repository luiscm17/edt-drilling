import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { HerschelBulkleyFitStudy } from './HerschelBulkleyFitStudy';

const result = {
  parameters: { yield_stress_pa: { value: 2, unit: 'Pa' }, consistency_index_pa_s_n: { value: 3, unit: 'Pa·s^n' }, flow_behavior_index: { value: 0.5, unit: '1' } },
  points: [1, 4, 9].map(g => ({ rpm: g, dial: g, shear_rate_s_inv: g, shear_stress_pa: 2+3*Math.sqrt(g), predicted_stress_pa: 2+3*Math.sqrt(g), residual_pa: 0 })),
  diagnostics: { objective: 'unweighted stress least squares; discrete n grid', sse_pa2: 0, rmse_pa: 0, max_abs_residual_pa: 0,
    evaluations: 391, n_min: 0.05, n_max: 2, n_step: 0.005, near_optimal_n_min: 0.5, near_optimal_n_max: 0.5, near_optimal_count: 1, at_n_bound: false,
    warning: 'Finite grid selection is not proof of uniqueness.' },
  model_id: 'openoil.rheology.fann-herschel-bulkley-fit', model_version: '1.0.0', input_schema_version: '1', result_schema_version: '1',
  applicability: { status: 'supported', assumptions: 'Conventional HB.', limitations: 'No vendor parity or field validation.' },
};
async function enter() {
  const user = userEvent.setup();
  for (const [i, g] of [1, 4, 9].entries()) {
    await user.type(screen.getByLabelText(`HB reading ${i+1} RPM`), String(g));
    await user.type(screen.getByLabelText(`HB reading ${i+1} dial`), String(g));
  }
  return user;
}
const button = () => screen.getByRole('button', { name: 'Fit conventional HB' });

describe('bounded conventional HB fit', () => {
  it('posts only readings and exposes SI observations, predictions and diagnostics; edits invalidate', async () => {
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(Response.json(result))); vi.stubGlobal('fetch', fetcher);
    render(<HerschelBulkleyFitStudy />); const user = await enter(); await user.click(button());
    expect(await screen.findByRole('table', { name: 'HB measured and predicted data' })).toHaveTextContent('Predicted stress (Pa)');
    expect(screen.getByRole('region', { name: 'HB fit result' })).toHaveTextContent('τ₀: 2 Pa');
    expect(screen.getByRole('region', { name: 'HB fit result' })).toHaveTextContent('not proof of uniqueness');
    expect(screen.getByRole('region', { name: 'HB fit result' })).toHaveTextContent('RMSE: 0 Pa');
    expect(fetcher).toHaveBeenCalledExactlyOnceWith('/api/v1/rheology/herschel-bulkley-fit/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ readings: [1, 4, 9].map(g => ({ rpm: g, dial: g })) }),
    });
    await user.type(screen.getByLabelText('HB reading 1 dial'), '1');
    expect(screen.queryByRole('region', { name: 'HB fit result' })).not.toBeInTheDocument();
    await user.click(button()); await screen.findByRole('region', { name: 'HB fit result' });
    await user.click(screen.getByRole('button', { name: 'Add HB reading' }));
    expect(screen.queryByRole('region', { name: 'HB fit result' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Remove HB reading 4' }));
    expect(screen.getByRole('button', { name: 'Remove HB reading 1' })).toBeDisabled();
  });
  it('rejects blanks and duplicate RPM locally and shows exact server rejection', async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({ detail: 'degenerate readings: insufficient stress variation' }, { status: 422 })); vi.stubGlobal('fetch', fetcher);
    render(<HerschelBulkleyFitStudy />); const user = userEvent.setup(); await user.click(button());
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter positive finite RPM and nonnegative finite dial for every reading.');
    expect(fetcher).not.toHaveBeenCalled(); await enter();
    await user.clear(screen.getByLabelText('HB reading 2 RPM')); await user.type(screen.getByLabelText('HB reading 2 RPM'), '1');
    await user.click(button()); expect(await screen.findByRole('alert')).toHaveTextContent('RPM readings must be unique.');
    expect(fetcher).not.toHaveBeenCalled();
    await user.clear(screen.getByLabelText('HB reading 2 RPM')); await user.type(screen.getByLabelText('HB reading 2 RPM'), '4');
    await user.click(button()); expect(await screen.findByRole('alert')).toHaveTextContent(/^degenerate readings: insufficient stress variation$/);
  });
  it.each(['network', 'non-json', 'malformed', 'nonfinite'])('clears stale results on %s and permits retry', async kind => {
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(result)); vi.stubGlobal('fetch', fetcher);
    render(<HerschelBulkleyFitStudy />); const user = await enter(); await user.click(button()); await screen.findByRole('region', { name: 'HB fit result' });
    if (kind === 'network') fetcher.mockRejectedValueOnce(new Error('Failed to fetch'));
    else fetcher.mockResolvedValueOnce(kind === 'non-json' ? new Response('bad', { status: 500 }) : Response.json({ ...result,
      diagnostics: kind === 'malformed' ? {} : { ...result.diagnostics, rmse_pa: null } }));
    await user.click(button()); await screen.findByRole('alert');
    expect(screen.queryByRole('region', { name: 'HB fit result' })).not.toBeInTheDocument();
    fetcher.mockResolvedValueOnce(Response.json(result)); await user.click(button()); await screen.findByRole('region', { name: 'HB fit result' });
  });
});
