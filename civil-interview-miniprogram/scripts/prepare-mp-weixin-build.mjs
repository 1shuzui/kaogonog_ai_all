import {
  cpSync,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync
} from 'node:fs'
import { dirname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const rootDir = dirname(scriptDir)
const distDir = join(rootDir, 'dist')
const buildDir = join(distDir, 'build')
const canonicalBuild = join(buildDir, 'mp-weixin')
const prodAliasBuild = join(buildDir, 'mp-weixin-prod')
const staleBuildDirs = [
  canonicalBuild,
  prodAliasBuild,
  join(buildDir, 'mp-weixin-dev'),
  join(distDir, 'dev', 'mp-weixin')
]

function walkFiles(dir) {
  if (!existsSync(dir)) return []
  const entries = readdirSync(dir)
  return entries.flatMap((entry) => {
    const fullPath = join(dir, entry)
    const stat = statSync(fullPath)
    return stat.isDirectory() ? walkFiles(fullPath) : [fullPath]
  })
}

function clean() {
  for (const dir of staleBuildDirs) {
    rmSync(dir, { recursive: true, force: true })
  }
  mkdirSync(buildDir, { recursive: true })
  console.log('[mini-build] cleaned stale mp-weixin outputs')
}

function validate({ mirrorProd = false } = {}) {
  const failures = []
  if (!existsSync(canonicalBuild)) {
    failures.push('dist/build/mp-weixin does not exist')
  }

  const files = walkFiles(canonicalBuild)
  const jsonFiles = files.filter((file) => file.endsWith('.json'))
  const doubledJsonFiles = files.filter((file) => file.endsWith('.json.json'))
  const requiredFiles = [
    'app.json',
    'project.config.json',
    'pages/login/index.json'
  ]

  for (const relPath of requiredFiles) {
    const fullPath = join(canonicalBuild, relPath)
    if (!existsSync(fullPath)) {
      failures.push(`missing required file: ${relPath}`)
    }
  }

  for (const file of doubledJsonFiles) {
    failures.push(`unexpected doubled json filename: ${relative(canonicalBuild, file)}`)
  }

  for (const file of jsonFiles) {
    const relPath = relative(canonicalBuild, file)
    const content = readFileSync(file, 'utf8')
    if (!content.trim()) {
      failures.push(`empty json file: ${relPath}`)
      continue
    }
    try {
      JSON.parse(content)
    } catch (error) {
      failures.push(`invalid json file: ${relPath}: ${error.message}`)
    }
  }

  if (failures.length) {
    console.error('[mini-build] validation failed')
    for (const failure of failures) {
      console.error(`- ${failure}`)
    }
    process.exit(1)
  }

  if (mirrorProd) {
    rmSync(prodAliasBuild, { recursive: true, force: true })
    cpSync(canonicalBuild, prodAliasBuild, { recursive: true })
    console.log('[mini-build] mirrored dist/build/mp-weixin to dist/build/mp-weixin-prod')
  }

  console.log(`[mini-build] validated ${jsonFiles.length} json files`)
}

const [command, ...flags] = process.argv.slice(2)

if (command === 'clean') {
  clean()
} else if (command === 'validate') {
  validate({ mirrorProd: flags.includes('--mirror-prod') })
} else {
  console.error(`Usage: node scripts/prepare-mp-weixin-build.mjs <clean|validate> [--mirror-prod]`)
  process.exit(1)
}
