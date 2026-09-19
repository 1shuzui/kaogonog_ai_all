// Regenerate the small, offline WeChat icon set from the existing PC dependency.
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const source = path.join(root, 'civil-interview-frontend/node_modules/@ant-design/icons-svg/inline-svg/outlined')
const target = path.join(root, 'civil-interview-miniprogram/src/static/learner-icons')
const names = ['audio', 'video-camera', 'read', 'field-time', 'aim', 'history', 'solution', 'file-text', 'cloud-upload', 'reload', 'check-circle', 'sound', 'environment', 'wallet', 'arrow-right', 'home']
await mkdir(target, { recursive: true })
for (const name of names) {
  const svg = await readFile(path.join(source, `${name}.svg`), 'utf8')
  // Ant's inline SVGs inherit the browser document namespace. A WeChat <image>
  // loads a separate document, so it needs an explicit SVG namespace and size.
  const standalone = svg
    .replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" fill="#326BE5" ')
    .replace('<defs><style /></defs>', '')
  await writeFile(path.join(target, `${name}.svg`), standalone)
}
console.log(`Exported ${names.length} Ant Design outlined icons.`)
