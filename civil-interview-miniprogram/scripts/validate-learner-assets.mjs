import { readFileSync } from 'node:fs'
import { join } from 'node:path'

export const learnerIconNames = ['audio', 'video-camera', 'read', 'field-time', 'aim', 'history', 'solution', 'file-text', 'cloud-upload', 'reload', 'check-circle', 'sound', 'environment', 'wallet', 'arrow-right', 'home']

// Check the emitted files, not Vue source: an external <style src> can compile
// successfully to an empty JS module without emitting any learner WXSS.
export function validateLearnerAssets(outputDir) {
  const failures = []
  const readAsset = (name) => {
    try { return readFileSync(join(outputDir, name), 'utf8') }
    catch { failures.push(`missing learner asset: ${name}`); return '' }
  }
  const globalStyles = readAsset('app.wxss')
  for (const page of ['home', 'prepare', 'room', 'result']) {
    if (!globalStyles.includes(`.learner-${page}`)) {
      failures.push(`app.wxss is missing the learner-${page} theme`)
    }
  }
  const actionStyles = readAsset('components/RoomActions.wxss')
  if (!/\.room-actions[^{}]*\{[^}]*display\s*:\s*grid/.test(actionStyles)) {
    failures.push('RoomActions.wxss must own its action-bar layout; parent scoped styles do not cross mini-program components')
  }
  for (const name of learnerIconNames) {
    const file = `static/learner-icons/${name}.svg`
    const svg = readAsset(file)
    if (!/<svg\b[^>]*\bxmlns="http:\/\/www\.w3\.org\/2000\/svg"/.test(svg)) {
      failures.push(`${file} must be a standalone SVG with the SVG namespace`)
    }
    if (!/<svg\b[^>]*\bviewBox="[^"]+"/.test(svg) || !/<path\b/.test(svg)) {
      failures.push(`${file} must retain its viewBox and vector paths`)
    }
  }
  return failures
}
