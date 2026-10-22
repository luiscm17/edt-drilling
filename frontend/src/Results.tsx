import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import type { Snapshot } from './types';

const number = (value: number, digits = 0) => value.toLocaleString('en-US', { maximumFractionDigits: digits });
const tick = (value: number) => value.toLocaleString('en-US', { notation: 'compact' });
const colors = { pipe: '#142b3b', annulus: '#a64026', hydro: '#526c79', grid: '#d7d9d1' };
const margins = { top: 24, right: 24, bottom: 18, left: 24 };

export function Results({ snapshot: { input, result, provenance } }: { snapshot: Snapshot }) {
  const losses = result.sections.map((section, i) => ({
    section: `S${i + 1}`, pipe: section.pipe.pressure_loss_pa, annulus: section.annulus.pressure_loss_pa,
  }));
  // Display interpolation of returned totals, not a second hydraulic model.
  let depth = 0;
  let friction = 0;
  const profile = [{ depth: 0, hydrostatic: 0, circulating: 0 }];
  result.sections.forEach((section, i) => {
    depth += Number(input.sections[i].length_m);
    friction += section.annulus.pressure_loss_pa;
    const hydrostatic = result.hydrostatic_pa * (depth / result.depth_m);
    profile.push({ depth, hydrostatic, circulating: hydrostatic + friction });
  });
  return <>
    <div className="readouts grid grid-cols-1 gap-3 sm:grid-cols-3" aria-label="Snapshot highlights">
      {([
        ['Annular pressure', result.bottomhole_annular_pa, 'Pa'],
        ['ECD', result.ecd_kg_m3, 'kg/m³'],
        ['Vertical depth', result.depth_m, 'm'],
      ] as const).map(([label, value, unit]) => <div className="readout" key={label}>
        <span>{label}</span><strong>{number(value, unit === 'kg/m³' ? 1 : 2)}</strong><small>{unit}</small>
      </div>)}
    </div>
    <section className={`provenance ${provenance ? '' : 'unknown'}`} aria-label="Snapshot provenance">
      <p className="eyebrow">Result identity / {provenance ? 'Recorded' : 'Unknown'}</p>
      {provenance ? <>
        <strong>{provenance.model_id}</strong>
        <p>Model version {provenance.model_version}</p>
        <p>Input schema {provenance.input_schema_version} · Result schema {provenance.result_schema_version} · {provenance.units}</p>
        <p>Created <time dateTime={provenance.created_at}>{provenance.created_at}</time></p>
        <details><summary>Recorded model assumptions</summary><ul>{provenance.assumptions.map(text => <li key={text}>{text}</li>)}</ul></details>
      </> : <><strong>Unknown model · legacy snapshot</strong><p>No provenance was recorded. Loading preserves this snapshot; calculate explicitly to obtain a new model identity.</p></>}
    </section>
    <div className="table-scroll"><table aria-label="Pressure and density summary" className="summary-table">
      <thead><tr><th scope="col">Quantity</th><th scope="col">Value</th><th scope="col">Unit</th></tr></thead>
      <tbody>{([
        ['Vertical depth', result.depth_m, 'm'], ['Pipe friction total', result.pipe_friction_pa, 'Pa'],
        ['Annular friction total', result.annular_friction_pa, 'Pa'], ['Hydrostatic pressure', result.hydrostatic_pa, 'Pa'],
        ['Bottomhole annular pressure', result.bottomhole_annular_pa, 'Pa'], ['Equivalent circulating density (ECD)', result.ecd_kg_m3, 'kg/m³'],
      ] as const).map(([label, value, unit]) => <tr key={label}><th scope="row">{label}</th><td>{number(value, unit === 'kg/m³' ? 1 : 2)}</td><td>{unit}</td></tr>)}</tbody>
    </table></div>
    <figure>
      <figcaption><p className="eyebrow">01 / Loss distribution</p><h3>Friction by section</h3><p>Pipe and annular loss magnitudes in Pa; same linear scale. Values also appear in the section audit below.</p></figcaption>
      <div className="chart" role="img" aria-label="Section friction losses in Pa, pipe and annulus">
        <ResponsiveContainer width="100%" height={Math.max(240, losses.length * 64 + 100)} initialDimension={{ width: 640, height: 280 }}>
          <BarChart data={losses} layout="vertical" margin={margins} accessibilityLayer={false}>
            <CartesianGrid stroke={colors.grid} horizontal={false} />
            <XAxis type="number" tickFormatter={tick} label={{ value: 'Pressure loss (Pa)', position: 'insideBottom', offset: -10 }} />
            <YAxis type="category" dataKey="section" width={36} />
            <Tooltip formatter={(value: number) => `${number(value, 2)} Pa`} />
            <Legend verticalAlign="top" />
            <Bar dataKey="pipe" name="Pipe" fill={colors.pipe} isAnimationActive={false} />
            <Bar dataKey="annulus" name="Annulus" fill={colors.annulus} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
    <figure>
      <figcaption><p className="eyebrow">02 / Pressure traverse</p><h3>Annular pressure profile</h3><p>Section-boundary interpolation of returned hydrostatic total and cumulative annular losses. Depth increases downwards.</p></figcaption>
      <div className="chart" role="img" aria-label="Annular pressure versus vertical depth, hydrostatic and circulating">
        <ResponsiveContainer width="100%" height={360} initialDimension={{ width: 640, height: 360 }}>
          <LineChart data={profile} layout="vertical" margin={margins} accessibilityLayer={false}>
            <CartesianGrid stroke={colors.grid} />
            <XAxis type="number" tickFormatter={tick} label={{ value: 'Gauge pressure (Pa)', position: 'insideBottom', offset: -10 }} />
            <YAxis type="number" dataKey="depth" domain={[0, result.depth_m]} tickFormatter={tick} label={{ value: 'Depth (m)', angle: -90, position: 'insideLeft' }} />
            <Tooltip formatter={(value: number) => `${number(value, 2)} Pa`} labelFormatter={(_, payload) => `Depth: ${number(Number(payload[0]?.payload.depth ?? 0), 2)} m`} />
            <Legend verticalAlign="top" />
            <Line dataKey="hydrostatic" name="Hydrostatic (dashed)" stroke={colors.hydro} strokeDasharray="6 4" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line dataKey="circulating" name="Circulating" stroke={colors.annulus} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="hint">Curves can overlap at low friction. See the table for exact differences.</p>
      <details><summary>Profile values (accessible data)</summary><div className="table-scroll"><table aria-label="Annular pressure profile values">
        <thead><tr><th scope="col">Depth (m)</th><th scope="col">Hydrostatic (Pa)</th><th scope="col">Circulating (Pa)</th></tr></thead>
        <tbody>{profile.map((p, i) => <tr key={i}><td>{number(p.depth, 2)}</td><td>{number(p.hydrostatic, 2)}</td><td>{number(p.circulating, 2)}</td></tr>)}</tbody>
      </table></div></details>
    </figure>
    <h3>Section audit</h3>
    <div className="table-scroll"><table aria-label="Section pressure losses">
      <thead><tr>{['Section', 'Passage', 'Loss (Pa)', 'Velocity (m/s)', 'Re', 'Darcy f', 'Regime'].map(label => <th scope="col" key={label}>{label}</th>)}</tr></thead>
      <tbody>{result.sections.flatMap((section, index) => (['pipe', 'annulus'] as const).map(passage => <tr key={`${index}-${passage}`}>
        <th scope="row">S{index + 1}</th><td>{passage}</td><td>{number(section[passage].pressure_loss_pa, 2)}</td>
        <td>{number(section[passage].velocity_m_s, 4)}</td><td>{number(section[passage].reynolds, 1)}</td>
        <td>{number(section[passage].darcy_factor, 5)}</td><td>{section[passage].regime}</td>
      </tr>))}</tbody>
    </table></div>
  </>;
}
