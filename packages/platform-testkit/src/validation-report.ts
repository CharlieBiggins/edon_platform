export type ValidationReport = { profile: string; started_at: string; finished_at: string; passed: boolean; checks: Array<{ name: string; passed: boolean; detail: string }> };
export function createValidationReport(profile: string, checks: ValidationReport['checks'], startedAt = new Date().toISOString()): ValidationReport {
  return { profile, started_at: startedAt, finished_at: new Date().toISOString(), passed: checks.every(check => check.passed), checks };
}
