type NumericInput = number | string;
export interface Section {
  length_m: NumericInput;
  pipe_id_m: NumericInput;
  pipe_od_m: NumericInput;
  hole_id_m: NumericInput;
}
export interface Inputs {
  sections: Section[];
  density_kg_m3: NumericInput;
  viscosity_pa_s: NumericInput;
  flow_m3_s: NumericInput;
}
export interface Passage {
  velocity_m_s: number;
  reynolds: number;
  regime: string;
  darcy_factor: number;
  pressure_loss_pa: number;
}
export interface Result {
  sections: { pipe: Passage; annulus: Passage }[];
  depth_m: number;
  pipe_friction_pa: number;
  annular_friction_pa: number;
  hydrostatic_pa: number;
  bottomhole_annular_pa: number;
  ecd_kg_m3: number;
}
export interface Provenance {
  model_id: string;
  model_version: string;
  units: 'SI';
  input_schema_version: string;
  result_schema_version: string;
  assumptions: string[];
  created_at: string;
}
export interface Snapshot { input: Inputs; result: Result; provenance: Provenance | null }
export interface SavedCase extends Snapshot { id: number }
