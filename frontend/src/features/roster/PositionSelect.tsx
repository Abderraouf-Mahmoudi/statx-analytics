export const POSITION_OPTIONS = [
  ["GK", "Gardien"], ["RB", "Latéral droit"], ["CB", "Défenseur central"], ["LB", "Latéral gauche"],
  ["DM", "Milieu défensif"], ["CM", "Milieu central"], ["AM", "Milieu offensif"], ["RW", "Ailier droit"],
  ["LW", "Ailier gauche"], ["ST", "Avant-centre"], ["OTHER", "Autre"],
] as const;

export function PositionSelect({ name = "primary_position", value, onChange, required = false }: {
  name?: string;
  value?: string;
  onChange?: (value: string) => void;
  required?: boolean;
}) {
  return <select className="touch-target" name={name} value={value} defaultValue={value === undefined ? "CM" : undefined} required={required} onChange={(event) => onChange?.(event.target.value)}>
    {POSITION_OPTIONS.map(([code, label]) => <option key={code} value={code}>{code} · {label}</option>)}
  </select>;
}
