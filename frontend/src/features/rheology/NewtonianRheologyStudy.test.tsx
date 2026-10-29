import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { NewtonianRheologyStudy } from './NewtonianRheologyStudy';

const result = {
  readings: [{ rpm: 100, dial: 10, shear_rate_s_inv: 170.333, shear_stress_pa: 5.0992475814 }],
  dynamic_viscosity: { quantity: 'dynamic_viscosity', value: 0.0299369333, unit: 'Pa·s' },
  model_id: 'openoil.rheology.fann-newtonian', model_version: '1.0.0',
  input_schema_version: '1', result_schema_version: '1',
  applicability: { status: 'supported', assumptions: 'Zero yield stress.', limitations: 'No field validation.' },
};
async function enter() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText('Reading 1 RPM'), '100');
  await user.type(screen.getByLabelText('Reading 1 dial'), '10');
  return user;
}

describe('Newtonian rheology', () => {
  it('posts readings, shows accessible SI results and invalidates on every edit', async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json(result)); vi.stubGlobal('fetch', fetcher);
    render(<NewtonianRheologyStudy />); const user = await enter();
    await user.click(screen.getByRole('button', { name: 'Calculate Newtonian rheology' }));
    const table = await screen.findByRole('table', { name: 'Newtonian shear data' });
    expect(table).toHaveTextContent('170.333'); expect(table).toHaveTextContent('5.099');
    expect(screen.getByRole('region', { name: 'Newtonian result' })).toHaveTextContent('0.029937 Pa·s');
    expect(fetcher).toHaveBeenCalledExactlyOnceWith('/api/v1/rheology/newtonian/calculate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ readings: [{ rpm: 100, dial: 10 }] }),
    });
    await user.type(screen.getByLabelText('Reading 1 dial'), '1');
    expect(screen.queryByRole('region', { name: 'Newtonian result' })).not.toBeInTheDocument();
    fetcher.mockResolvedValueOnce(Response.json(result));
    await user.click(screen.getByRole('button', { name: 'Calculate Newtonian rheology' }));
    await screen.findByRole('region', { name: 'Newtonian result' });
    await user.click(screen.getByRole('button', { name: 'Add reading' }));
    expect(screen.queryByRole('region', { name: 'Newtonian result' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Remove reading 2' }));
    expect(screen.getByRole('button', { name: 'Remove reading 1' })).toBeDisabled();
  });

  it('validates blanks and duplicate RPM without a request, and displays exact model rejection', async () => {
    const fetcher = vi.fn().mockResolvedValue(Response.json({ detail: 'readings are inconsistent with a Newtonian model' }, { status: 422 }));
    vi.stubGlobal('fetch', fetcher); render(<NewtonianRheologyStudy />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Calculate Newtonian rheology' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter positive finite RPM and nonnegative finite dial for every reading.');
    expect(fetcher).not.toHaveBeenCalled(); await enter();
    await user.click(screen.getByRole('button', { name: 'Add reading' }));
    await user.type(screen.getByLabelText('Reading 2 RPM'), '100');
    await user.type(screen.getByLabelText('Reading 2 dial'), '20');
    await user.click(screen.getByRole('button', { name: 'Calculate Newtonian rheology' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('RPM readings must be unique.');
    expect(fetcher).not.toHaveBeenCalled();
    await user.clear(screen.getByLabelText('Reading 2 RPM')); await user.type(screen.getByLabelText('Reading 2 RPM'), '200');
    await user.click(screen.getByRole('button', { name: 'Calculate Newtonian rheology' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/^readings are inconsistent with a Newtonian model$/);
    expect(screen.queryByRole('region', { name: 'Newtonian result' })).not.toBeInTheDocument();
  });

  it.each(['network', 'malformed', 'non-json'])('clears results on %s failure and allows retry', async kind => {
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json(result)); vi.stubGlobal('fetch', fetcher);
    render(<NewtonianRheologyStudy />); const user = await enter();
    const calculate = screen.getByRole('button', { name: 'Calculate Newtonian rheology' });
    await user.click(calculate); await screen.findByRole('region', { name: 'Newtonian result' });
    if (kind === 'network') fetcher.mockRejectedValueOnce(new Error('Failed to fetch'));
    else fetcher.mockResolvedValueOnce(kind === 'malformed' ? Response.json({ ...result, dynamic_viscosity: { value: -1 } }) : new Response('bad', { status: 500 }));
    await user.click(calculate); await screen.findByRole('alert');
    expect(screen.queryByRole('region', { name: 'Newtonian result' })).not.toBeInTheDocument();
    fetcher.mockResolvedValueOnce(Response.json(result)); await user.click(calculate);
    expect(within(await screen.findByRole('region', { name: 'Newtonian result' })).getByRole('table')).toBeVisible();
  });
});
