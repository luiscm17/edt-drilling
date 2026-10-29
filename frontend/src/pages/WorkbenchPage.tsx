import { useEffect, useState } from 'react';
import { Results } from '../features/hydraulics/components/Results';
import { TorqueDragStudy } from '../features/torque-drag/TorqueDragStudy';
import { NozzleVelocityStudy } from '../features/nozzle-velocity/NozzleVelocityStudy';
import { BitNozzlePressureLossStudy } from '../features/bit-nozzle-pressure-loss/BitNozzlePressureLossStudy';
import { BinghamRheologyStudy } from '../features/rheology/BinghamRheologyStudy';
import { PowerLawRheologyStudy } from '../features/rheology/PowerLawRheologyStudy';
import type { Inputs, Result, Snapshot, SavedCase, Section } from '../features/hydraulics/types';

const defaultSection: Section = { length_m: 100, pipe_id_m: 0.08, pipe_od_m: 0.1, hole_id_m: 0.2 };
const initial: Inputs = {
  sections: [{ ...defaultSection }], density_kg_m3: 1000, viscosity_pa_s: 0.1, flow_m3_s: 0.001,
};
const geometry = [
  ['length_m', 'Length (m)'], ['pipe_id_m', 'Pipe ID (m)'],
  ['pipe_od_m', 'Pipe OD (m)'], ['hole_id_m', 'Hole ID (m)'],
] as const;
const fluid = [
  ['density_kg_m3', 'Density (kg/m³)'], ['viscosity_pa_s', 'Viscosity (Pa·s)'], ['flow_m3_s', 'Flow (m³/s)'],
] as const;

async function request<T>(path: string, input?: Inputs): Promise<T> {
  const response = input ? await fetch(path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      sections: input.sections.map(section => ({
        length_m: Number(section.length_m), pipe_id_m: Number(section.pipe_id_m),
        pipe_od_m: Number(section.pipe_od_m), hole_id_m: Number(section.hole_id_m),
      })),
      density_kg_m3: Number(input.density_kg_m3), viscosity_pa_s: Number(input.viscosity_pa_s), flow_m3_s: Number(input.flow_m3_s),
    }),
  }) : await fetch(path);
  const body = await response.json().catch(() => {
    throw new Error(`Request failed (${response.status})`);
  });
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`);
  return body;
}

export default function App() {
  const [study, setStudy] = useState<'hydraulics' | 'torque-drag' | 'nozzle-velocity' | 'bit-nozzle-pressure-loss' | 'bingham-rheology' | 'power-law-rheology'>('hydraulics');
  const [inputs, setInputs] = useState(initial);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [cases, setCases] = useState<SavedCase[]>([]);
  const [busy, setBusy] = useState('Loading cases');
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Ready to calculate.');

  useEffect(() => {
    let active = true;
    request<SavedCase[]>('/api/v1/cases').then(records => { if (active) setCases(records); })
      .catch(reason => { if (active) setError(reason.message); })
      .finally(() => { if (active) setBusy(''); });
    return () => { active = false; };
  }, []);

  function edit(next: Inputs) {
    setInputs(next); setSnapshot(null); setError('');
    setStatus('Inputs changed. Calculate or save to produce new results.');
  }
  async function run(label: string, work: () => Promise<void>) {
    setBusy(label); setError('');
    try { await work(); }
    catch (reason) {
      setSnapshot(null);
      setStatus('Request failed. No new result is displayed.');
      setError(reason instanceof Error ? reason.message : 'Request failed');
    } finally { setBusy(''); }
  }
  function calculate(save: boolean) {
    void run(save ? 'Saving case' : 'Calculating', async () => {
      if (save) {
        const record = await request<SavedCase>('/api/v1/cases', inputs);
        setCases(previous => [...previous, record]);
        setSnapshot(record);
        setStatus(`Saved case ${record.id}. Results are a stored snapshot.`);
      } else {
        const calculated = await request<Result>('/api/v1/calculate', inputs);
        setSnapshot({ input: inputs, result: calculated }); setStatus('Calculation complete. Not saved.');
      }
    });
  }

  return <>
    <a className="skip" href={study === 'hydraulics' ? '#inputs' : `#${study}`}>Skip to inputs</a>
    <header className="masthead">
      <div><p className="eyebrow">Drilling engineering workbench</p><h1>OpenOil<span>Independent models · Auditable results</span></h1></div>
      <div className="stamp">SI / ENGINEERING<span>LOCAL WORKSPACE</span><span>NOT VALIDATED FOR FIELD USE</span></div>
    </header>
    <div className="workbench">
      <nav className="study-nav" aria-label="Workbench studies">
        <p className="eyebrow">Study workspace</p>
        <button type="button" aria-current={study === 'hydraulics' ? 'page' : undefined}
          aria-controls="hydraulics-view" onClick={() => setStudy('hydraulics')}>
          <span className="nav-index" aria-hidden="true">01</span>Hydraulics & saved cases
          <small>Circulation · Pressure · ECD</small>
        </button>
        <button type="button" aria-current={study === 'torque-drag' ? 'page' : undefined}
          aria-controls="torque-view" onClick={() => setStudy('torque-drag')}>
          <span className="nav-index" aria-hidden="true">02</span>Torque & drag study
          <small>Pickup · Slackoff · Contact torque</small>
        </button>
        <button type="button" aria-current={study === 'nozzle-velocity' ? 'page' : undefined}
          aria-controls="nozzle-view" onClick={() => setStudy('nozzle-velocity')}>
          <span className="nav-index" aria-hidden="true">03</span>Nozzle velocity study
          <small>Flow · Total area · Velocity</small>
        </button>
        <button type="button" aria-current={study === 'bit-nozzle-pressure-loss' ? 'page' : undefined}
          aria-controls="bit-loss-view" onClick={() => setStudy('bit-nozzle-pressure-loss')}>
          <span className="nav-index" aria-hidden="true">04</span>Bit/nozzle pressure-loss study
          <small>Density · Flow · Total area · Pressure loss</small>
        </button>
        <button type="button" aria-current={study === 'bingham-rheology' ? 'page' : undefined}
          aria-controls="bingham-view" onClick={() => setStudy('bingham-rheology')}>
          <span className="nav-index" aria-hidden="true">05</span>Bingham rheology study
          <small>PV · YP · shear curve</small>
        </button>
        <button type="button" aria-current={study === 'power-law-rheology' ? 'page' : undefined}
          aria-controls="power-law-view" onClick={() => setStudy('power-law-rheology')}>
          <span className="nav-index" aria-hidden="true">06</span>Power Law rheology study
          <small>Flow index · consistency · shear curve</small>
        </button>
        <p className="nav-note">Six independent studies.<br />Only hydraulic snapshots are saved locally; other studies are temporary.</p>
      </nav>
    <main>
      <div className="view-heading"><div><p className="eyebrow">Analysis / {study === 'hydraulics' ? '01' : study === 'torque-drag' ? '02' : study === 'nozzle-velocity' ? '03' : study === 'bit-nozzle-pressure-loss' ? '04' : study === 'bingham-rheology' ? '05' : '06'}</p>
        <h2>{study === 'hydraulics' ? 'Hydraulics' : study === 'torque-drag' ? 'Torque & drag' : study === 'nozzle-velocity' ? 'Nozzle velocity' : study === 'bit-nozzle-pressure-loss' ? 'Bit/nozzle pressure loss' : study === 'bingham-rheology' ? 'Bingham rheology' : 'Power Law rheology'}</h2></div>
        <span className="view-mode">{study === 'hydraulics' ? 'SNAPSHOT WORKSPACE' : 'CALCULATE ONLY'}</span></div>
      {/* Keep inactive studies mounted so navigation never discards work or repeats requests. */}
      <div id="hydraulics-view" hidden={study !== 'hydraulics'}>
      <aside className="scope" aria-label="Engineering scope warning">
        <strong>Hydraulics model / Explicit limits. No reference-solver parity claimed.</strong> Simplified Newtonian, incompressible, single-phase flow in a concentric vertical well. Not validated for field decisions or safety-critical limits in any study.
      </aside>
      <div className="workspace grid items-start gap-6">
        <section className="inputs panel" id="inputs" tabIndex={-1} aria-labelledby="input-heading">
          <div className="section-heading"><p className="eyebrow">01 / Define the system</p><h2 id="input-heading">Geometry & circulation</h2></div>
          <form onSubmit={event => { event.preventDefault(); calculate(false); }}>
            <fieldset className="editor" disabled={!!busy}>
              <legend className="sr-only">Calculation inputs</legend>
              <p className="hint">Sections run from surface to bottom. Length = vertical depth increment; all dimensions are SI.</p>
              {inputs.sections.map((section, index) => <fieldset className="geometry" key={index}>
                <legend>Section {index + 1}</legend>
                <div className="field-grid">{geometry.map(([key, label]) => <label key={key}>{label}
                  <input type="number" step="any" required value={section[key]} onChange={event => edit({
                    ...inputs, sections: inputs.sections.map((old, i) => i === index ? { ...old, [key]: event.target.value } : old),
                  })} />
                </label>)}</div>
                <button className="text-button" type="button" disabled={inputs.sections.length === 1}
                  onClick={() => edit({ ...inputs, sections: inputs.sections.filter((_, i) => i !== index) })}>Remove section {index + 1}</button>
              </fieldset>)}
              <button className="secondary" type="button" onClick={() => edit({ ...inputs, sections: [...inputs.sections, { ...defaultSection }] })}>Add section</button>
              <p className="hint">Required: 0 &lt; pipe ID &lt; pipe OD &lt; hole ID; pipe OD / hole ID ≤ 0.8.</p>
              <h3>Fluid & flow</h3>
              <div className="fluid-grid">{fluid.map(([key, label]) => <label key={key}>{label}
                <input type="number" step="any" required value={inputs[key]} onChange={event => edit({ ...inputs, [key]: event.target.value })} />
              </label>)}</div>
              <p className="hint">Positive circulation only. Supported Re: &lt; 2,300 or 4,000–100,000 in both passages. Other regimes are rejected.</p>
              <div className="actions"><button className="primary" type="submit">Calculate</button>
                <button type="submit" formAction="" onClick={event => {
                  // Use native form validity for both submit actions.
                  if (event.currentTarget.form?.reportValidity()) { event.preventDefault(); calculate(true); }
                }}>Save case</button></div>
            </fieldset>
          </form>
          <p className="status" role="status">{busy ? `${busy}…` : status}</p>
          {error && <p role="alert" className="error">{error}</p>}
          <section className="case-library" aria-labelledby="cases-heading">
            <div className="library-heading"><h3 id="cases-heading">Case ledger</h3>
              <button type="button" disabled={!!busy} onClick={() => void run('Refreshing cases', async () => {
                setCases(await request<SavedCase[]>('/api/v1/cases')); setStatus('Case list refreshed.');
              })}>Refresh cases</button></div>
            {cases.length === 0 ? <p className="hint">No saved cases. Save a validated input to start the ledger.</p> :
              <ul>{cases.map(record => <li key={record.id}><button type="button" disabled={!!busy} onClick={() => void run(`Loading case ${record.id}`, async () => {
                const loaded = await request<SavedCase>(`/api/v1/cases/${record.id}`);
                setInputs(loaded.input); setSnapshot(loaded);
                setStatus(`Loaded case ${loaded.id}. Results are a stored snapshot.`);
              })}>Load case {record.id}<span>{record.input.sections.length} section(s) · {record.result.depth_m} m</span><span>Provenance not exposed by the v1 API</span></button></li>)}</ul>}
          </section>
        </section>
        <section className="results panel" aria-labelledby="results-heading" aria-busy={!!busy}>
          <div className="section-heading"><p className="eyebrow">02 / Inspect the response</p><h2 id="results-heading">Pressure & equivalent density</h2></div>
          {snapshot ? <Results snapshot={snapshot} /> :
            <div className="empty"><div className="well-icon" aria-hidden="true">↓</div><h3>Your pressure profile starts here.</h3><p>Define geometry, fluid and circulation. Calculate to inspect section friction, annular pressure and ECD.</p><span>NO RESULT / AWAITING CALCULATION</span></div>}
          <p className="result-note">Gauge pressure; zero surface annular pressure. Pipe friction is not standpipe pressure. No bit/nozzle or surface losses. Display rounding does not imply engineering accuracy.</p>
        </section>
      </div>
      </div>
      <div id="torque-view" hidden={study !== 'torque-drag'}><TorqueDragStudy /></div>
      <div id="nozzle-view" hidden={study !== 'nozzle-velocity'}><NozzleVelocityStudy /></div>
      <div id="bit-loss-view" hidden={study !== 'bit-nozzle-pressure-loss'}><BitNozzlePressureLossStudy /></div>
      <div id="bingham-view" hidden={study !== 'bingham-rheology'}><BinghamRheologyStudy /></div>
      <div id="power-law-view" hidden={study !== 'power-law-rheology'}><PowerLawRheologyStudy /></div>
      <footer><strong>Know the boundary.</strong> Hydraulics excludes cuttings, bit optimization, swab/surge, real-time data and torque/drag coupling. Its vertical model excludes eccentricity, roughness, inclination, non-Newtonian rheology and thermal effects. The standalone Bingham and Power Law studies are not coupled to hydraulics and have their own two-point limits. The separate torque/drag study has its own straight-well limits. Independently validate before any engineering use.</footer>
    </main>
    </div>
  </>;
}
