export const MANUAL_VERIFICATION_MAX_LEN = 240;

export type ManualVerificationFieldErrors = Record<string, string>;

export function validateManualVerificationFields(data: {
  developer: string;
  project: string;
  permit: string;
  address: string;
}): ManualVerificationFieldErrors | null {
  const developer = data.developer.trim();
  const project = data.project.trim();
  const permit = data.permit.trim();
  const address = data.address.trim();

  const fieldErrors: ManualVerificationFieldErrors = {};

  if (!developer)
    fieldErrors.developer = "Indicá el desarrollador o constructor.";
  else if (developer.length > MANUAL_VERIFICATION_MAX_LEN)
    fieldErrors.developer = `Máximo ${MANUAL_VERIFICATION_MAX_LEN} caracteres.`;

  if (!project) fieldErrors.project = "Indicá el nombre del proyecto.";
  else if (project.length > MANUAL_VERIFICATION_MAX_LEN)
    fieldErrors.project = `Máximo ${MANUAL_VERIFICATION_MAX_LEN} caracteres.`;

  if (!permit) fieldErrors.permit = "Indicá número o referencia de permiso.";
  else if (permit.length > MANUAL_VERIFICATION_MAX_LEN)
    fieldErrors.permit = `Máximo ${MANUAL_VERIFICATION_MAX_LEN} caracteres.`;

  if (!address) fieldErrors.address = "Indicá una dirección aproximada.";
  else if (address.length > MANUAL_VERIFICATION_MAX_LEN)
    fieldErrors.address = `Máximo ${MANUAL_VERIFICATION_MAX_LEN} caracteres.`;

  if (Object.keys(fieldErrors).length > 0) return fieldErrors;
  return null;
}
